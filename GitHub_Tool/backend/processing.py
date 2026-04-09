# processing.py — Cleans, classifies and groups commits into feature buckets

import re
import json
import requests
from collections import defaultdict
from datetime import datetime

from config import NOISE_PATTERNS, OLLAMA_URL, OLLAMA_MODEL


# ── Pre-compile noise patterns once ──────────────────────────────────────────
_NOISE_RE = re.compile(
    "(" + "|".join(NOISE_PATTERNS) + ")",
    re.IGNORECASE,
)


# ── Public API ────────────────────────────────────────────────────────────────

def clean_commits(commits: list[dict]) -> list[dict]:
    """
    Remove noise commits (merge commits, version bumps, whitespace-only, etc.).
    Returns a filtered list of the same dicts.
    """
    cleaned = []
    for c in commits:
        msg = c.get("message", "").strip()
        if msg and not _NOISE_RE.match(msg):
            cleaned.append(c)
    return cleaned


def classify_commits_batch(messages: list[str]) -> list[str]:
    """
    Send all commit messages to Ollama in a single prompt.
    Returns a list of category strings in the same order as messages.
    Falls back to 'General' for any message that can't be classified.
    """
    if not messages:
        return []

    numbered = "\n".join(f"{i+1}. {m}" for i, m in enumerate(messages))

    prompt = f"""You are a commit classifier. Classify each commit message below into exactly one category.

Rules:
- Reply with ONLY a JSON array of strings, one category per commit, in the same order.
- Each category must be a short noun phrase (2-4 words), e.g. "Bug Fixes", "API Integration", "UI Components", "Performance", "Testing", "Security", "Database", "Documentation", "Refactoring", "Build & CI/CD", "Authentication", "Dependency Updates".
- Invent a specific category if none of the above fit — do not force a bad match.
- No explanation, no markdown, no code fences. Just the raw JSON array.

Commits:
{numbered}

Reply:"""

    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model":  OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
            },
            timeout=120,
        )
        resp.raise_for_status()
        raw = resp.json().get("response", "").strip()

        # Strip markdown code fences if model adds them
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw).strip()

        categories = json.loads(raw)

        if isinstance(categories, list) and len(categories) == len(messages):
            return [str(c).strip() or "General" for c in categories]

    except Exception as e:
        print(f"[Ollama] Classification failed: {e} — falling back to 'General'")

    return ["General"] * len(messages)


def build_features(commits: list[dict]) -> list[dict]:
    """
    Group cleaned commits into feature buckets and compute stats per bucket.
    Uses Ollama to classify all commits in one batch call.
    """
    messages   = [c["message"] for c in commits]
    categories = classify_commits_batch(messages)

    buckets: dict[str, dict] = defaultdict(lambda: {
        "commits": [],
        "authors": set(),
        "dates":   [],
    })

    for c, category in zip(commits, categories):
        buckets[category]["commits"].append(c["message"])
        buckets[category]["authors"].add(c["author"])
        if c["date"]:
            buckets[category]["dates"].append(c["date"])

    features = []
    for name, data in buckets.items():
        dates    = sorted(data["dates"])
        first    = dates[0]  if dates else None
        last     = dates[-1] if dates else None
        duration = (last - first).days + 1 if first and last and first != last else 1

        features.append({
            "name":           name,
            "commit_count":   len(data["commits"]),
            "contributors":   sorted(data["authors"]),
            "duration_days":  duration,
            "sample_commits": _pick_samples(data["commits"], n=3),
            "first_date":     first,
            "last_date":      last,
        })

    return sorted(features, key=lambda x: -x["commit_count"])


def compute_summary_stats(commits: list[dict]) -> dict:
    """
    High-level stats across all cleaned commits.
    """
    from collections import Counter

    if not commits:
        return {}

    author_counts = Counter(c["author"] for c in commits)
    dates = [c["date"] for c in commits if c["date"]]

    earliest  = min(dates) if dates else None
    latest    = max(dates) if dates else None
    span_days = (latest - earliest).days if earliest and latest else 0

    return {
        "total_commits":  len(commits),
        "unique_authors": len(author_counts),
        "top_authors":    [a for a, _ in author_counts.most_common(5)],
        "author_counts":  dict(author_counts),
        "earliest_date":  earliest,
        "latest_date":    latest,
        "span_days":      span_days,
    }


# ── Private helpers ───────────────────────────────────────────────────────────

def _pick_samples(messages: list[str], n: int = 3) -> list[str]:
    """
    Pick up to n representative commit messages.
    Prefers longer, more descriptive messages.
    """
    ranked = sorted(messages, key=len, reverse=True)
    seen   = set()
    picked = []
    for msg in ranked:
        normalised = msg.lower().strip()
        if normalised not in seen:
            seen.add(normalised)
            picked.append(msg[:80])
        if len(picked) == n:
            break
    return picked
