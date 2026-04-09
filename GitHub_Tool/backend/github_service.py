# github_service.py — Responsible for all GitHub REST API calls

import re
import requests
from datetime import datetime
from config import GITHUB_API_URL, GITHUB_TOKEN, MAX_PAGES, PER_PAGE


# ── Auth headers ──────────────────────────────────────────────────────────────
def _headers() -> dict:
    h = {"Accept": "application/vnd.github+json"}
    if GITHUB_TOKEN:
        h["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return h


# ── URL parsing ───────────────────────────────────────────────────────────────
def parse_repo_url(url: str) -> tuple[str | None, str | None]:
    """
    Extract (owner, repo) from any of these formats:
        https://github.com/facebook/react
        https://github.com/facebook/react/
        https://github.com/facebook/react.git
        github.com/facebook/react
    Returns (None, None) on failure.
    """
    match = re.search(r"github\.com/([^/\s]+)/([^/\s?#]+)", url)
    if not match:
        return None, None
    owner = match.group(1)
    repo  = match.group(2).rstrip(".git").rstrip("/")
    return owner, repo


# ── Repo metadata ─────────────────────────────────────────────────────────────
def fetch_repo_meta(owner: str, repo: str) -> dict:
    """
    Returns basic repo info: description, stars, language, default_branch.
    Raises requests.HTTPError on non-200 responses.
    """
    url  = f"{GITHUB_API_URL}/repos/{owner}/{repo}"
    resp = requests.get(url, headers=_headers(), timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return {
        "description":      data.get("description") or "",
        "stars":            data.get("stargazers_count", 0),
        "language":         data.get("language") or "Unknown",
        "default_branch":   data.get("default_branch", "main"),
        "open_issues":      data.get("open_issues_count", 0),
        "forks":            data.get("forks_count", 0),
    }


# ── Commits ───────────────────────────────────────────────────────────────────
def fetch_commits(owner: str, repo: str) -> list[dict]:
    """
    Fetches up to MAX_PAGES * PER_PAGE commits from the default branch.
    Each returned dict has the shape expected by processing.py:
        {
            "sha":     str,
            "message": str,        # first line only
            "author":  str,
            "date":    datetime | None,
        }
    """
    raw_commits = []

    for page in range(1, MAX_PAGES + 1):
        url  = f"{GITHUB_API_URL}/repos/{owner}/{repo}/commits"
        resp = requests.get(
            url,
            headers=_headers(),
            params={"per_page": PER_PAGE, "page": page},
            timeout=15,
        )

        # Stop pagination on any non-200 (private repo, rate limit, etc.)
        if resp.status_code != 200:
            break

        batch = resp.json()
        if not batch:
            break

        raw_commits.extend(batch)

    return [_normalise_commit(c) for c in raw_commits]


def _normalise_commit(c: dict) -> dict:
    """Map raw GitHub API commit object → clean internal dict."""
    commit_data = c.get("commit", {})

    # Message — take only the subject line
    message = (commit_data.get("message") or "").split("\n")[0].strip()

    # Author — prefer display name, fall back to login
    author = (
        commit_data.get("author", {}).get("name")
        or (c.get("author") or {}).get("login")
        or "Unknown"
    )

    # Date
    date_str = commit_data.get("author", {}).get("date", "")
    try:
        date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        date = None

    return {
        "sha":     c.get("sha", "")[:7],
        "message": message,
        "author":  author,
        "date":    date,
    }
