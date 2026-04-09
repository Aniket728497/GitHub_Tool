# processing.py — Cleans, classifies and groups commits into feature buckets

import re
from collections import defaultdict
from datetime import datetime

from config import NOISE_PATTERNS, FEATURE_TAXONOMY


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


def classify_commit(message: str) -> str:
    """
    Map a commit message to a feature category using FEATURE_TAXONOMY.
    Returns the category name, or "General" if no keyword matches.
    """
    msg_lower = message.lower()
    for feature, keywords in FEATURE_TAXONOMY.items():
        if any(kw in msg_lower for kw in keywords):
            return feature
    return "General"


def build_features(commits: list[dict]) -> list[dict]:
    """
    Group cleaned commits into feature buckets and compute stats per bucket.

    Returns a list of feature dicts sorted by commit count (descending):
    [
        {
            "name":           str,
            "commit_count":   int,
            "contributors":   list[str],   # sorted, unique
            "duration_days":  int,
            "sample_commits": list[str],   # up to 3 representative messages
            "first_date":     datetime | None,
            "last_date":      datetime | None,
        },
        ...
    ]
    """
    buckets: dict[str, dict] = defaultdict(lambda: {
        "commits":  [],
        "authors":  set(),
        "dates":    [],
    })

    for c in commits:
        category = classify_commit(c["message"])
        buckets[category]["commits"].append(c["message"])
        buckets[category]["authors"].add(c["author"])
        if c["date"]:
            buckets[category]["dates"].append(c["date"])

    features = []
    for name, data in buckets.items():
        dates = sorted(data["dates"])
        first = dates[0]  if dates else None
        last  = dates[-1] if dates else None
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
    High-level stats across all cleaned commits — used by the narrator
    and returned in the API meta field.
    """
    from collections import Counter

    if not commits:
        return {}

    author_counts = Counter(c["author"] for c in commits)
    dates = [c["date"] for c in commits if c["date"]]

    earliest = min(dates) if dates else None
    latest   = max(dates) if dates else None
    span_days = (latest - earliest).days if earliest and latest else 0

    return {
        "total_commits":    len(commits),
        "unique_authors":   len(author_counts),
        "top_authors":      [a for a, _ in author_counts.most_common(5)],
        "author_counts":    dict(author_counts),
        "earliest_date":    earliest,
        "latest_date":      latest,
        "span_days":        span_days,
    }


# ── Private helpers ───────────────────────────────────────────────────────────

def _pick_samples(messages: list[str], n: int = 3) -> list[str]:
    """
    Pick up to n representative commit messages.
    Prefers longer, more descriptive messages over very short ones.
    """
    ranked = sorted(messages, key=len, reverse=True)
    seen   = set()
    picked = []
    for msg in ranked:
        normalised = msg.lower().strip()
        if normalised not in seen:
            seen.add(normalised)
            picked.append(msg[:80])   # truncate to 80 chars
        if len(picked) == n:
            break
    return picked
