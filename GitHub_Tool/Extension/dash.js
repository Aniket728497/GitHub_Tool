// dash.js — Content script injected into every github.com/<owner>/<repo> page
// Responsibilities: render the trigger button, manage the side panel, call backend.

const GS_BACKEND = "http://localhost:5000";
const GS_PANEL_ID = "gs-panel";
const GS_BTN_ID   = "gs-trigger-btn";

// ── Guard: only run on repo root pages ───────────────────────────────────────
(function init() {
  if (!_isRepoRoot()) return;

  // Inject on first load
  _injectTriggerButton();

  // Re-inject after GitHub's soft navigations (pjax / turbo)
  document.addEventListener("turbo:render",   _injectTriggerButton);
  document.addEventListener("pjax:end",       _injectTriggerButton);
  document.addEventListener("DOMContentLoaded", _injectTriggerButton);

  // Allow popup.js to trigger analysis programmatically
  window.addEventListener("gs:analyse", (e) => {
    _runAnalysis(e.detail?.url || location.href);
  });
})();


// ── Trigger button ────────────────────────────────────────────────────────────

function _injectTriggerButton() {
  if (!_isRepoRoot()) return;
  if (document.getElementById(GS_BTN_ID)) return;   // already injected

  const btn = document.createElement("button");
  btn.id = GS_BTN_ID;
  btn.innerHTML = `
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
         stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
      <circle cx="12" cy="12" r="10"/>
      <path d="M12 8v4l3 3"/>
    </svg>
    Analyse Story
  `;

  // Find the best anchor point on GitHub's DOM
  const anchor =
    document.querySelector("#repos-sticky-header") ||
    document.querySelector(".file-navigation") ||
    document.querySelector(".repository-content") ||
    document.querySelector("main");

  if (anchor) {
    anchor.insertAdjacentElement("beforebegin", btn);
  } else {
    document.body.prepend(btn);
  }

  btn.addEventListener("click", () => {
    _runAnalysis(location.href);
  });
}


// ── Analysis pipeline ─────────────────────────────────────────────────────────

async function _runAnalysis(repoUrl) {
  const btn = document.getElementById(GS_BTN_ID);

  // Disable button during request
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `
      <svg class="gs-btn-spin" width="14" height="14" viewBox="0 0 24 24"
           fill="none" stroke="currentColor" stroke-width="2.5">
        <circle cx="12" cy="12" r="10"/>
        <path d="M12 8v4l3 3"/>
      </svg>
      Analysing…`;
  }

  _removePanel();
  _showLoadingPanel();

  try {
    const response = await fetch(`${GS_BACKEND}/analyze`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ url: repoUrl }),
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.error || `Server responded with HTTP ${response.status}`);
    }

    const data = await response.json();
    _renderResultPanel(data);

  } catch (err) {
    _renderErrorPanel(err.message || "Unknown error occurred.");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
          <circle cx="12" cy="12" r="10"/>
          <path d="M12 8v4l3 3"/>
        </svg>
        Re-analyse`;
    }
  }
}


// ── Panel: Loading ─────────────────────────────────────────────────────────────

function _showLoadingPanel() {
  const panel = _createPanelShell();
  panel.innerHTML += `
    <div class="gs-loading">
      <div class="gs-spinner"></div>
      <p class="gs-loading-text">Fetching commits & building your story…</p>
      <p class="gs-loading-sub">This may take a few seconds for large repos.</p>
    </div>`;
  document.body.appendChild(panel);
}


// ── Panel: Results ─────────────────────────────────────────────────────────────

function _renderResultPanel(data) {
  _removePanel();

  const meta  = data.meta  || {};
  const story = data.story || "";
  const chart = data.chart || "";

  const panel = _createPanelShell();

  // ── Meta chips ──
  const chipsHtml = `
    <div class="gs-meta-row">
      ${_chip("📦 " + (meta.total_commits_analyzed ?? "?") + " commits")}
      ${_chip("🔍 " + (meta.features_detected ?? "?") + " features")}
      ${_chip("👥 " + (meta.unique_authors ?? "?") + " authors")}
      ${meta.language && meta.language !== "Unknown" ? _chip("💻 " + meta.language) : ""}
      ${meta.stars ? _chip("⭐ " + _fmtNum(meta.stars)) : ""}
    </div>`;

  // ── Tabs + panes ──
  panel.innerHTML += `
    ${chipsHtml}
    <div class="gs-tabs" role="tablist">
      <button class="gs-tab gs-tab--active" data-pane="story" role="tab">📝 Story</button>
      <button class="gs-tab"               data-pane="chart" role="tab">📊 Chart</button>
    </div>
    <div class="gs-body">
      <div class="gs-pane gs-pane--active" id="gs-pane-story">
        <div class="gs-story-content">${_mdToHtml(story)}</div>
      </div>
      <div class="gs-pane" id="gs-pane-chart">
        ${chart
          ? `<img class="gs-chart-img" src="data:image/png;base64,${chart}" alt="Contribution chart" />`
          : `<p class="gs-no-chart">Chart unavailable.</p>`
        }
      </div>
    </div>`;

  document.body.appendChild(panel);

  // Wire up tab switching
  panel.querySelectorAll(".gs-tab").forEach(tab => {
    tab.addEventListener("click", () => {
      panel.querySelectorAll(".gs-tab, .gs-pane").forEach(el => {
        el.classList.remove("gs-tab--active", "gs-pane--active");
      });
      tab.classList.add("gs-tab--active");
      panel.querySelector(`#gs-pane-${tab.dataset.pane}`)
           ?.classList.add("gs-pane--active");
    });
  });
}


// ── Panel: Error ───────────────────────────────────────────────────────────────

function _renderErrorPanel(message) {
  _removePanel();
  const panel = _createPanelShell();
  panel.innerHTML += `
    <div class="gs-error">
      <span class="gs-error-icon">⚠️</span>
      <p>${_escHtml(message)}</p>
      <p class="gs-error-hint">
        Make sure the Flask server is running on <code>localhost:5000</code>
        and the repo is public.
      </p>
    </div>`;
  document.body.appendChild(panel);
}


// ── Shared panel shell ────────────────────────────────────────────────────────

function _createPanelShell() {
  const panel = document.createElement("div");
  panel.id = GS_PANEL_ID;

  panel.innerHTML = `
    <div class="gs-header">
      <span class="gs-header-logo">📖</span>
      <span class="gs-header-title">GitHub Analytics</span>
      <button class="gs-close-btn" title="Close panel" aria-label="Close">✕</button>
    </div>`;

  panel.querySelector(".gs-close-btn")
       .addEventListener("click", _removePanel);

  return panel;
}

function _removePanel() {
  document.getElementById(GS_PANEL_ID)?.remove();
}


// ── Markdown → HTML (minimal, safe) ──────────────────────────────────────────

function _mdToHtml(md) {
  return md
    // Escape raw HTML first
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    // Headings
    .replace(/^# (.+)$/gm,   "<h1>$1</h1>")
    .replace(/^## (.+)$/gm,  "<h2>$1</h2>")
    .replace(/^### (.+)$/gm, "<h3>$1</h3>")
    // Blockquote
    .replace(/^&gt; (.+)$/gm, "<blockquote>$1</blockquote>")
    // HR
    .replace(/^---$/gm, "<hr>")
    // Bold / italic / code
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g,     "<em>$1</em>")
    .replace(/`([^`]+)`/g,     "<code>$1</code>")
    // Line breaks → paragraphs
    .replace(/\n\n+/g, "</p><p>")
    .replace(/\n/g, "<br>")
    .replace(/^/, "<p>").replace(/$/, "</p>");
}


// ── Utility ───────────────────────────────────────────────────────────────────

function _isRepoRoot() {
  const parts = location.pathname.split("/").filter(Boolean);
  return location.hostname === "github.com" && parts.length === 2;
}

function _chip(text) {
  return `<span class="gs-chip">${_escHtml(text)}</span>`;
}

function _escHtml(str) {
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function _fmtNum(n) {
  return n >= 1000 ? (n / 1000).toFixed(1) + "k" : String(n);
}
