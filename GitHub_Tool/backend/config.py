# config.py — Central configuration for GitHub Storyteller backend

import os

# Auto-load .env if present (no external library needed)
_env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _, _v = _line.partition("=")
                os.environ.setdefault(_k.strip(), _v.strip())

# ── Ollama ────────────────────────────────────────────────────────────────────
OLLAMA_URL   = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "gemma4:e2b")

# ── GitHub API ────────────────────────────────────────────────────────────────
GITHUB_TOKEN   = os.environ.get("GITHUB_TOKEN", "")
GITHUB_API_URL = "https://api.github.com"
MAX_PAGES      = 5          # 5 pages × 100 commits = up to 500 commits
PER_PAGE       = 100

# ── Flask ─────────────────────────────────────────────────────────────────────
FLASK_PORT  = 5000
FLASK_DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
ALLOWED_ORIGINS = ["*"]     # Tighten this in production

# ── Processing ────────────────────────────────────────────────────────────────
# Commit messages that match any of these patterns are treated as noise
NOISE_PATTERNS = [
    r"^fix typo",
    r"^update readme",
    r"^minor (fix|update|change|tweak)",
    r"^wip\b",
    r"^formatting",
    r"^whitespace",
    r"^merge (branch|pull request|remote)",
    r"^bump version",
    r"^update (deps|dependencies|packages)",
    r"^changelog",
    r"^release \d",
    r"^revert \"",
    r"^\s*$",
]

# Feature keyword taxonomy  →  { display_name: [keywords …] }
FEATURE_TAXONOMY = {
    "Authentication":   ["auth", "login", "logout", "token", "oauth",
                         "session", "password", "credential", "jwt", "sso"],
    "UI / Components":  ["ui", "button", "modal", "component", "style",
                         "css", "layout", "design", "theme", "dark mode",
                         "icon", "font", "animation", "tooltip", "sidebar"],
    "API & Networking": ["api", "fetch", "request", "endpoint", "graphql",
                         "rest", "http", "network", "axios", "websocket",
                         "grpc", "webhook", "route"],
    "Performance":      ["perf", "performance", "optimize", "cache",
                         "memoize", "lazy", "speed", "bundle", "memory",
                         "slow", "throttle", "debounce"],
    "Testing":          ["test", "spec", "jest", "coverage", "mock",
                         "e2e", "cypress", "unit", "integration", "fixture",
                         "assert", "vitest"],
    "Bug Fixes":        ["fix", "bug", "patch", "hotfix", "regression",
                         "broken", "issue", "error", "crash", "null",
                         "undefined", "typo fix"],
    "Database":         ["db", "database", "schema", "migration", "query",
                         "orm", "sql", "mongo", "redis", "postgres", "index"],
    "Build & CI/CD":    ["build", "ci", "cd", "deploy", "pipeline",
                         "docker", "webpack", "vite", "rollup", "lint",
                         "eslint", "prettier", "action", "workflow"],
    "Documentation":    ["docs", "readme", "comment", "jsdoc",
                         "docstring", "changelog", "guide", "example"],
    "Refactoring":      ["refactor", "cleanup", "rewrite", "restructure",
                         "rename", "reorganize", "extract", "simplify"],
    "Security":         ["security", "xss", "csrf", "injection", "sanitize",
                         "escape", "cve", "vulnerability", "audit"],
    "Features":         ["add", "implement", "introduce", "support",
                         "enable", "new feature", "feat"],
}

# ── Graph ─────────────────────────────────────────────────────────────────────
CHART_DPI        = 150
CHART_BG         = "#0d1117"
CHART_SURFACE    = "#161b22"
CHART_BORDER     = "#21262d"
CHART_TEXT_PRIMARY   = "#e6edf3"
CHART_TEXT_SECONDARY = "#8b949e"
CHART_ACCENT_1   = "#ff0080"
CHART_ACCENT_2   = "#7928ca"
CHART_FONT_MONO  = "monospace"
TOP_CONTRIBUTORS = 10       # max bars in contributor chart
TOP_FEATURES     = 8        # max slices in donut chart
