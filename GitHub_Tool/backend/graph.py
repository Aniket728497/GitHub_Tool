# graph.py — Generates all charts; returns base64-encoded PNG strings

import io
import base64

import matplotlib
matplotlib.use("Agg")   # must be before pyplot import
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

from config import (
    CHART_DPI, CHART_BG, CHART_SURFACE, CHART_BORDER,
    CHART_TEXT_PRIMARY, CHART_TEXT_SECONDARY,
    CHART_ACCENT_1, CHART_ACCENT_2,
    TOP_CONTRIBUTORS, TOP_FEATURES,
)


# ── Public API ────────────────────────────────────────────────────────────────

def generate_charts(features: list[dict], stats: dict) -> str:
    """
    Create a 2-panel figure:
      Left  — Horizontal bar chart: top contributors by commit count
      Right — Donut chart: commit distribution across feature categories

    Returns a base64-encoded PNG string (no prefix).
    """
    author_counts = stats.get("author_counts", {})
    top_authors   = _top_n(author_counts, TOP_CONTRIBUTORS)
    top_features  = features[:TOP_FEATURES]

    fig, axes = plt.subplots(
    2, 1,
    figsize=(10, 13),
    facecolor=CHART_BG,
)

    ax_bar, ax_donut = axes

    _draw_contributor_bar(ax_bar, top_authors)
    _draw_feature_donut(ax_donut, top_features)

    fig.subplots_adjust(hspace=0.4)

    return _fig_to_b64(fig)


def generate_timeline_chart(features: list[dict]) -> str:
    """
    Optional standalone chart: activity timeline across features.
    Returns base64 PNG. Only includes features that have date info.
    """
    dated = [
        f for f in features
        if f.get("first_date") and f.get("last_date")
    ]
    if not dated:
        return ""

    fig, ax = plt.subplots(figsize=(13, max(3, len(dated) * 0.7)), facecolor=CHART_BG)
    _draw_timeline(ax, dated)
    plt.tight_layout(pad=2.5)
    return _fig_to_b64(fig)


# ── Chart renderers ───────────────────────────────────────────────────────────

def _draw_contributor_bar(ax: plt.Axes, top_authors: dict) -> None:
    _style_axes(ax)

    if not top_authors:
        ax.text(0.5, 0.5, "No contributor data", transform=ax.transAxes,
                color=CHART_TEXT_SECONDARY, ha="center", va="center")
        return

    names  = list(top_authors.keys())
    values = list(top_authors.values())
    y_pos  = np.arange(len(names))

    # Gradient colours from accent to accent2
    colours = plt.cm.plasma(np.linspace(0.2, 0.85, len(names)))

    bars = ax.barh(
        y_pos, values,
        color=colours, height=0.6,
        edgecolor=CHART_BORDER, linewidth=0.6,
    )

    # Value labels
    max_val = max(values) if values else 1
    for bar, val in zip(bars, values):
        ax.text(
            bar.get_width() + max_val * 0.015,
            bar.get_y() + bar.get_height() / 2,
            str(val),
            va="center", color=CHART_TEXT_PRIMARY,
            fontsize=9, fontweight="bold",
            fontfamily="monospace",
        )

    ax.set_yticks(y_pos)
    ax.set_yticklabels(names, color=CHART_TEXT_SECONDARY, fontsize=10)
    ax.set_xlabel("Commits", color=CHART_TEXT_SECONDARY, fontsize=10)
    ax.set_title(
        "Top Contributors", color=CHART_TEXT_PRIMARY,
        fontsize=13, fontweight="bold", pad=14,
    )
    ax.set_xlim(0, max_val * 1.2)
    ax.invert_yaxis()


def _draw_feature_donut(ax: plt.Axes, features: list[dict]) -> None:
    ax.set_facecolor(CHART_SURFACE)
    ax.set_aspect('equal')
    if not features:
        ax.text(0.5, 0.5, "No feature data", transform=ax.transAxes,
                color=CHART_TEXT_SECONDARY, ha="center", va="center")
        return

    sizes  = [f["commit_count"] for f in features]
    labels = [f["name"] for f in features]
    colours = plt.cm.plasma(np.linspace(0.12, 0.92, len(features)))

    wedges, _, autotexts = ax.pie(
        sizes,
        labels=None,
        autopct="%1.0f%%",
        colors=colours,
        startangle=135,
        pctdistance=0.72,
        wedgeprops={"edgecolor": CHART_BG, "linewidth": 2.5},
    )
    for at in autotexts:
        at.set_color("#0d1117")
        at.set_fontsize(8)
        at.set_fontweight("bold")

    # Donut hole
    hole = plt.Circle((0, 0), 0.48, color=CHART_SURFACE)
    ax.add_patch(hole)

    # Centre annotation
    total = sum(sizes)
    ax.text(0, 0.08, str(total), ha="center", va="center",
            color=CHART_TEXT_PRIMARY, fontsize=16, fontweight="bold",
            fontfamily="monospace")
    ax.text(0, -0.12, "commits", ha="center", va="center",
            color=CHART_TEXT_SECONDARY, fontsize=9, fontfamily="monospace")

    ax.legend(
    wedges, labels,
    loc="center left",
    bbox_to_anchor=(1.05, 0.5),
    frameon=False,
    labelcolor=CHART_TEXT_SECONDARY,
    fontsize=8,
)
    ax.set_title(
        "Commits by Feature", color=CHART_TEXT_PRIMARY,
        fontsize=13, fontweight="bold", pad=14,
    )


def _draw_timeline(ax: plt.Axes, features: list[dict]) -> None:
    _style_axes(ax)
    colours = plt.cm.plasma(np.linspace(0.15, 0.85, len(features)))

    for i, (f, colour) in enumerate(zip(features, colours)):
        start = f["first_date"].timestamp()
        end   = f["last_date"].timestamp()
        ax.barh(
            i, end - start,
            left=start,
            color=colour, height=0.5,
            edgecolor=CHART_BORDER, linewidth=0.5,
        )

    names = [f["name"] for f in features]
    ax.set_yticks(range(len(features)))
    ax.set_yticklabels(names, color=CHART_TEXT_SECONDARY, fontsize=9)
    ax.set_title("Feature Activity Timeline", color=CHART_TEXT_PRIMARY,
                 fontsize=13, fontweight="bold", pad=12)
    ax.invert_yaxis()

    # Format x-axis as dates
    import matplotlib.dates as mdates
    from datetime import datetime
    ax.xaxis_date()
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))
    ax.tick_params(axis="x", colors=CHART_TEXT_SECONDARY, labelsize=8)


# ── Shared helpers ────────────────────────────────────────────────────────────

def _style_axes(ax: plt.Axes) -> None:
    ax.set_facecolor(CHART_SURFACE)
    ax.tick_params(colors=CHART_TEXT_SECONDARY)
    for spine in ax.spines.values():
        spine.set_color(CHART_BORDER)


def _top_n(counter: dict, n: int) -> dict:
    sorted_items = sorted(counter.items(), key=lambda x: -x[1])
    return dict(sorted_items[:n])


def _fig_to_b64(fig: plt.Figure) -> str:
    buf = io.BytesIO()
    fig.savefig(
        buf, format="png", dpi=CHART_DPI,
        bbox_inches="tight", facecolor=CHART_BG,
    )
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")
