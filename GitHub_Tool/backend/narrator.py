# narrator.py — Converts structured feature data into a readable Markdown story

from datetime import datetime


# ── Public API ────────────────────────────────────────────────────────────────

def generate_story(
    owner: str,
    repo: str,
    features: list[dict],
    stats: dict,
    meta: dict | None = None,
) -> str:
    """
    Build a Markdown narrative from feature groups + summary stats.

    Parameters
    ----------
    owner    : GitHub username / org
    repo     : Repository name
    features : Output of processing.build_features()
    stats    : Output of processing.compute_summary_stats()
    meta     : Optional repo metadata from github_service.fetch_repo_meta()

    Returns
    -------
    A Markdown string ready to be rendered in the extension panel.
    """
    sections = [
        _header(owner, repo, stats, meta),
        _summary_block(stats),
        "---",
        _feature_sections(features),
    ]
    if stats.get("top_authors"):
        sections.append(_contributor_spotlight(stats))

    return "\n\n".join(sections)


# ── Section builders ──────────────────────────────────────────────────────────

def _header(owner: str, repo: str, stats: dict, meta: dict | None) -> str:
    lang     = meta.get("language", "") if meta else ""
    stars    = meta.get("stars", 0)     if meta else 0
    desc     = meta.get("description", "") if meta else ""
    lang_tag = f" · {lang}" if lang and lang != "Unknown" else ""
    star_tag = f" · ⭐ {stars:,}" if stars else ""

    lines = [f"# 📖 {owner}/{repo}"]
    if desc:
        lines.append(f"*{desc}*")
    if lang_tag or star_tag:
        lines.append(f"`{lang}{star_tag}`" if lang else f"`{star_tag.strip(' · ')}`")
    return "\n".join(lines)


def _summary_block(stats: dict) -> str:
    total   = stats.get("total_commits", 0)
    authors = stats.get("unique_authors", 0)
    span    = stats.get("span_days", 0)
    top     = stats.get("top_authors", [])

    earliest = stats.get("earliest_date")
    latest   = stats.get("latest_date")
    date_range = ""
    if earliest and latest:
        date_range = (
            f"  from **{_fmt_date(earliest)}** to **{_fmt_date(latest)}**"
        )

    contributors_str = ", ".join(f"**{a}**" for a in top[:3])
    if len(top) > 3:
        contributors_str += f" +{len(top) - 3} others"

    return (
        f"> Analysed **{total:,} meaningful commits** across "
        f"**{authors}** contributor{'s' if authors != 1 else ''}"
        f"{date_range} (**{span} days** of active work).\n"
        f"> Top contributors: {contributors_str}."
    )


def _feature_sections(features: list[dict]) -> str:
    if not features:
        return "_No features detected._"

    blocks = []
    for i, f in enumerate(features[:10], 1):
        blocks.append(_feature_block(i, f))

    return "\n\n".join(blocks)


def _feature_block(index: int, f: dict) -> str:
    name     = f["name"]
    count    = f["commit_count"]
    duration = f["duration_days"]
    contribs = f["contributors"]
    samples  = f["sample_commits"]

    # Contributor list — max 4 named, then "+N others"
    contrib_str = ", ".join(contribs[:4])
    if len(contribs) > 4:
        contrib_str += f" +{len(contribs) - 4} others"

    # Emoji badge per category
    badge = _category_badge(name)

    # Sample commits — formatted as inline code snippets
    sample_lines = "  \n".join(
        f"  · `{s}`" for s in samples
    ) if samples else ""

    lines = [
        f"### {badge} {index}. {name}",
        f"**{count} commit{'s' if count != 1 else ''}** "
        f"· {duration} day span "
        f"· Contributors: {contrib_str}",
    ]
    if sample_lines:
        lines.append(sample_lines)

    return "\n".join(lines)


def _contributor_spotlight(stats: dict) -> str:
    author_counts = stats.get("author_counts", {})
    top = stats.get("top_authors", [])[:5]
    if not top:
        return ""

    rows = ["### 🏆 Contributor Spotlight", ""]
    for i, author in enumerate(top, 1):
        count = author_counts.get(author, 0)
        bar   = _mini_bar(count, max(author_counts.values()))
        rows.append(f"{i}. **{author}** — {count} commits {bar}")

    return "\n".join(rows)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt_date(dt: datetime) -> str:
    return dt.strftime("%b %Y")


def _mini_bar(value: int, max_val: int, width: int = 10) -> str:
    filled = round((value / max_val) * width) if max_val else 0
    return "█" * filled + "░" * (width - filled)


def _category_badge(name: str) -> str:
    badges = {
        "Authentication":   "🔐",
        "UI / Components":  "🎨",
        "API & Networking": "🌐",
        "Performance":      "⚡",
        "Testing":          "🧪",
        "Bug Fixes":        "🐛",
        "Database":         "🗄️",
        "Build & CI/CD":    "🔧",
        "Documentation":    "📚",
        "Refactoring":      "♻️",
        "Security":         "🛡️",
        "Features":         "✨",
        "General":          "📦",
    }
    return badges.get(name, "📌")
