"""Shared dark security theme for the demo and eval dashboard."""

from __future__ import annotations

import html

GITHUB_URL = "https://github.com/Anondevnet/audit-rag-assistant"
FONT_HREF = (
    "https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&display=swap"
)

THEME_CSS = """
:root {
  --bg: #0c1117;
  --bg-elev: #141b24;
  --bg-elev-2: #1b2430;
  --line: #2a3544;
  --line-strong: #3a4a5c;
  --text: #e8eef5;
  --muted: #a8b4c2;
  --accent: #7ee8c8;
  --accent-ink: #06251c;
  --accent-dim: rgba(126, 232, 200, 0.12);
  --accent-glow: rgba(126, 232, 200, 0.22);
  --danger: #ffb4a8;
  --danger-ink: #3a1010;
  --danger-bg: #2a1514;
  --danger-line: #8a3d36;
  --pass: #7ee8c8;
  --fail: #ffb4a8;
  --shadow: 0 18px 50px rgba(0, 0, 0, 0.35);
  --radius: 16px;
  --sans: "IBM Plex Sans", ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
  --max: 920px;
}
*, *::before, *::after { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
html { color-scheme: dark; }
body {
  font-family: var(--sans);
  background:
    radial-gradient(1200px 500px at 50% -80px, rgba(126, 232, 200, 0.08), transparent 60%),
    var(--bg);
  color: var(--text);
  line-height: 1.55;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
a { color: var(--accent); text-decoration-thickness: 1px; text-underline-offset: 0.18em; }
a:hover { text-decoration-thickness: 2px; }
a:focus-visible, button:focus-visible, .chip:focus-visible, summary:focus-visible, textarea:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}
.wrap { width: min(var(--max), calc(100% - 2rem)); margin: 0 auto; }
.site-header {
  border-bottom: 1px solid var(--line);
  background: rgba(12, 17, 23, 0.88);
  backdrop-filter: blur(10px);
  position: sticky;
  top: 0;
  z-index: 10;
}
.header-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem 1.5rem;
  padding: 0.9rem 0;
  flex-wrap: wrap;
}
.brand { display: flex; gap: 0.8rem; align-items: center; min-width: 0; text-decoration: none; color: inherit; }
.brand:hover { text-decoration: none; }
.mark {
  width: 2.25rem; height: 2.25rem; flex: none;
  border: 1px solid var(--line-strong);
  border-radius: 8px;
  background: var(--accent-dim);
  display: grid; place-items: center;
  color: var(--accent);
}
.brand-text { min-width: 0; }
.brand-text strong { display: block; font-size: 1.02rem; font-weight: 600; letter-spacing: -0.02em; }
.tagline { display: block; color: var(--muted); font-size: 0.86rem; margin-top: 0.05rem; }
.nav { display: flex; align-items: center; gap: 0.4rem 0.9rem; flex-wrap: wrap; }
.nav a {
  color: var(--muted);
  text-decoration: none;
  font-weight: 500;
  font-size: 0.92rem;
  padding: 0.35rem 0.55rem;
  border-radius: 999px;
}
.nav a:hover, .nav a[aria-current="page"] { color: var(--text); background: var(--bg-elev-2); }
.nav .gh {
  border: 1px solid var(--line);
  color: var(--text);
  padding: 0.35rem 0.75rem;
}
.nav .gh:hover { border-color: var(--accent); color: var(--accent); background: var(--accent-dim); }
main { flex: 1; padding: 1.6rem 0 2.5rem; }
.hero { text-align: center; margin: 0.4rem 0 1.4rem; }
.hero h1 { font-size: clamp(1.5rem, 3vw, 2rem); font-weight: 650; letter-spacing: -0.03em; margin: 0 0 0.4rem; }
.hero p { margin: 0 auto; max-width: 46rem; color: var(--muted); }
.ask-card {
  background: var(--bg-elev);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 1rem;
}
.ask-card textarea {
  width: 100%;
  min-height: 6.2rem;
  resize: vertical;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--bg);
  color: var(--text);
  font: inherit;
  padding: 0.85rem 0.95rem;
}
.ask-card textarea::placeholder { color: #7d8b9a; }
.ask-row { display: flex; flex-wrap: wrap; gap: 0.55rem; align-items: center; margin-top: 0.8rem; }
button.primary {
  appearance: none;
  border: 0;
  background: var(--accent);
  color: var(--accent-ink);
  font: inherit;
  font-weight: 600;
  padding: 0.6rem 1.1rem;
  border-radius: 999px;
  cursor: pointer;
  min-height: 44px;
}
button.primary:hover { filter: brightness(1.06); }
button.primary:disabled { opacity: 0.65; cursor: wait; }
.chips { display: flex; flex-wrap: wrap; gap: 0.45rem; }
.chip {
  appearance: none;
  border: 1px solid var(--line);
  background: var(--bg);
  color: var(--text);
  font: inherit;
  font-size: 0.88rem;
  padding: 0.4rem 0.75rem;
  border-radius: 999px;
  cursor: pointer;
  min-height: 40px;
}
.chip:hover { border-color: var(--accent); color: var(--accent); background: var(--accent-dim); }
.results { margin-top: 1.25rem; }
.meta-row { color: var(--muted); font-size: 0.88rem; margin: 0 0 0.7rem; }
.answer-card {
  background: var(--bg-elev);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 1.05rem 1.15rem;
  box-shadow: var(--shadow);
}
.answer-card.refuse {
  background: var(--danger-bg);
  border-color: var(--danger-line);
}
.answer-kicker {
  font-size: 0.76rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--accent);
  margin: 0 0 0.45rem;
}
.answer-card.refuse .answer-kicker { color: var(--danger); }
.answer-body { font-size: 1.02rem; white-space: pre-wrap; overflow-wrap: anywhere; }
.cite-chip {
  display: inline-flex;
  align-items: baseline;
  gap: 0.28rem;
  margin: 0 0.12rem;
  padding: 0.05rem 0.4rem;
  border-radius: 999px;
  border: 1px solid var(--accent);
  background: var(--accent-dim);
  color: var(--accent);
  text-decoration: none;
  font-size: 0.82rem;
  font-weight: 600;
  white-space: nowrap;
  vertical-align: middle;
}
.cite-chip:hover { background: rgba(126, 232, 200, 0.22); text-decoration: none; }
.cite-chip .cite-id { font-weight: 500; color: var(--text); opacity: 0.9; }
.sources { margin-top: 1.4rem; }
.sources h2 { font-size: 1rem; font-weight: 600; margin: 0 0 0.7rem; letter-spacing: -0.02em; }
.source {
  border: 1px solid var(--line);
  background: var(--bg-elev);
  border-radius: 12px;
  margin: 0 0 0.55rem;
  padding: 0;
}
.source[open] { border-color: var(--line-strong); }
.source summary {
  cursor: pointer;
  list-style: none;
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem 0.7rem;
  align-items: center;
  padding: 0.75rem 0.9rem;
}
.source summary::-webkit-details-marker { display: none; }
.source .passage { margin: 0; padding: 0 0.9rem 0.9rem; color: var(--text); white-space: pre-wrap; overflow-wrap: anywhere; }
.source .src-links { padding: 0 0.9rem 0.9rem; font-size: 0.88rem; }
.license {
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  border: 1px solid var(--line-strong);
  border-radius: 999px;
  padding: 0.1rem 0.45rem;
  color: var(--muted);
}
.loading {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  color: var(--muted);
  padding: 0.8rem 0;
}
.spinner {
  width: 1.05rem; height: 1.05rem;
  border: 2px solid var(--line-strong);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
@media (prefers-reduced-motion: reduce) {
  .spinner { animation: none; border-top-color: var(--line-strong); }
  html { scroll-behavior: auto; }
}
.error { color: var(--danger); }
.metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 0.75rem;
  margin: 1rem 0 1.4rem;
}
.metric {
  background: var(--bg-elev);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 0.85rem 0.95rem;
}
.metric span { display: block; color: var(--muted); font-size: 0.8rem; }
.metric strong { display: block; font-size: 1.35rem; margin-top: 0.25rem; letter-spacing: -0.03em; }
.table-wrap { overflow-x: auto; border: 1px solid var(--line); border-radius: 12px; }
table { border-collapse: collapse; width: 100%; font-size: 0.92rem; }
th, td { padding: 0.55rem 0.7rem; text-align: left; vertical-align: top; border-bottom: 1px solid var(--line); }
th { background: var(--bg-elev-2); font-weight: 600; color: var(--muted); font-size: 0.78rem; letter-spacing: 0.04em; text-transform: uppercase; }
tr.bad { background: var(--danger-bg); }
tr:last-child td { border-bottom: 0; }
.pill { display: inline-block; border-radius: 999px; padding: 0.08rem 0.5rem; font-size: 0.78rem; font-weight: 600; }
.pill.pass { background: var(--accent-dim); color: var(--accent); }
.pill.fail { background: var(--danger-bg); color: var(--danger); border: 1px solid var(--danger-line); }
.note, .method-notes { color: var(--muted); }
.method-notes { max-width: 75ch; }
.method-notes li { margin: 0.35rem 0; }
.failures pre {
  white-space: pre-wrap;
  background: var(--bg-elev-2);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 0.6rem;
  overflow-wrap: anywhere;
}
.site-footer {
  border-top: 1px solid var(--line);
  padding: 1.1rem 0 1.4rem;
  color: var(--muted);
  font-size: 0.84rem;
}
.site-footer p { margin: 0.25rem 0; }
h1.page-title { font-size: 1.55rem; letter-spacing: -0.03em; margin: 0 0 0.4rem; }
@media (max-width: 640px) {
  .header-inner { padding: 0.75rem 0; }
  .ask-card, .answer-card { padding: 0.85rem; }
  .cite-chip .cite-id { display: none; }
}
"""


def page_start(title: str) -> str:
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '  <meta charset="utf-8">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '  <meta name="color-scheme" content="dark">\n'
        '  <meta name="theme-color" content="#0c1117">\n'
        f"  <title>{html.escape(title)}</title>\n"
        '  <link rel="preconnect" href="https://fonts.googleapis.com">\n'
        '  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
        f'  <link href="{FONT_HREF}" rel="stylesheet">\n'
        f"  <style>{THEME_CSS}</style>\n"
        "</head>\n"
        "<body>\n"
    )


def render_header(active: str = "ask") -> str:
    ask_cur = ' aria-current="page"' if active == "ask" else ""
    dash_cur = ' aria-current="page"' if active == "dashboard" else ""
    mark = (
        '<svg class="mark" viewBox="0 0 32 32" width="36" height="36" aria-hidden="true">'
        '<rect x="1.5" y="1.5" width="29" height="29" rx="7" fill="none" stroke="currentColor" stroke-width="1.5"/>'
        '<path d="M9 16.5l4 4 10-10" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>'
        "</svg>"
    )
    return f"""
<header class="site-header">
  <div class="wrap header-inner">
    <a class="brand" href="/">
      {mark}
      <span class="brand-text">
        <strong>audit-rag-assistant</strong>
        <span class="tagline">Cited answers over license-cleared audit knowledge</span>
      </span>
    </a>
    <nav class="nav" aria-label="Primary">
      <a href="/"{ask_cur}>Ask</a>
      <a href="/dashboard"{dash_cur}>Dashboard</a>
      <a class="gh" href="{GITHUB_URL}" rel="noopener noreferrer">GitHub</a>
    </nav>
  </div>
</header>
"""


def render_footer() -> str:
    return """
<footer class="site-footer">
  <div class="wrap">
    <p>Sources: SWC Registry (MIT) and not-so-smart-contracts (Apache-2.0). This is a demo, not an audit.</p>
    <p>Educational write-ups only. Not a substitute for a professional security review.</p>
  </div>
</footer>
"""


def page_end() -> str:
    return "</body>\n</html>\n"
