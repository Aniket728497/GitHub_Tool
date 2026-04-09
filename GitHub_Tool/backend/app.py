# app.py — Flask entry point; orchestrates the full analysis pipeline

from flask import Flask, request, jsonify
import requests as req_lib

from config import FLASK_PORT, FLASK_DEBUG
from github_service import parse_repo_url, fetch_commits, fetch_repo_meta
from processing    import clean_commits, build_features, compute_summary_stats
from narrator      import generate_story
from graph         import generate_charts

app = Flask(__name__)

@app.after_request
def add_cors(response):
    response.headers["Access-Control-Allow-Origin"]  = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response

@app.route("/analyze", methods=["OPTIONS"])
def options_analyze():
    return jsonify({}), 200


# ── Health check ──────────────────────────────────────────────────────────────

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "version": "1.0.0"})


# ── Main analysis endpoint ────────────────────────────────────────────────────

@app.route("/analyze", methods=["POST"])
def analyze():
    """
    Expects JSON body: { "url": "https://github.com/owner/repo" }

    Returns:
    {
        "story":  "<markdown string>",
        "chart":  "<base64 PNG>",
        "meta": {
            "owner":                  str,
            "repo":                   str,
            "total_commits_analyzed": int,
            "features_detected":      int,
            "top_feature":            str,
            "unique_authors":         int,
            "span_days":              int,
            "language":               str,
            "stars":                  int,
        }
    }
    """
    body = request.get_json(force=True, silent=True) or {}
    url  = (body.get("url") or "").strip()

    if not url:
        return jsonify({"error": "Missing 'url' field in request body."}), 400

    # 1. Parse repo URL
    owner, repo = parse_repo_url(url)
    if not owner:
        return jsonify({"error": "Could not parse a valid GitHub repo URL."}), 400

    # 2. Fetch repo metadata (non-fatal — continue even if this fails)
    repo_meta = {}
    try:
        repo_meta = fetch_repo_meta(owner, repo)
    except req_lib.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            return jsonify({"error": f"Repository '{owner}/{repo}' not found or is private."}), 404
        # Other HTTP errors: log and continue without meta
    except Exception:
        pass   # metadata is optional

    # 3. Fetch commits
    try:
        raw_commits = fetch_commits(owner, repo)
    except req_lib.HTTPError as e:
        status = e.response.status_code if e.response is not None else 500
        return jsonify({"error": f"GitHub API error while fetching commits (HTTP {status})."}), 502
    except Exception as e:
        return jsonify({"error": f"Unexpected error fetching commits: {str(e)}"}), 502

    if not raw_commits:
        return jsonify({"error": "No commits found. The repository may be empty or private."}), 404

    # 4. Clean + process
    commits  = clean_commits(raw_commits)
    features = build_features(commits)
    stats    = compute_summary_stats(commits)

    # 5. Generate narrative
    story = generate_story(owner, repo, features, stats, meta=repo_meta)

    # 6. Generate charts
    chart_b64 = generate_charts(features, stats)

    # 7. Build meta response
    meta = {
        "owner":                  owner,
        "repo":                   repo,
        "total_commits_analyzed": stats.get("total_commits", 0),
        "features_detected":      len(features),
        "top_feature":            features[0]["name"] if features else "N/A",
        "unique_authors":         stats.get("unique_authors", 0),
        "span_days":              stats.get("span_days", 0),
        "language":               repo_meta.get("language", "Unknown"),
        "stars":                  repo_meta.get("stars", 0),
    }

    return jsonify({
        "story": story,
        "chart": chart_b64,
        "meta":  meta,
    })


# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=FLASK_DEBUG, port=FLASK_PORT)
