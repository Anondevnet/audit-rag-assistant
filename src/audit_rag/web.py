"""Small FastAPI demo for the cited RAG assistant."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from audit_rag.embeddings.base import get_embedder
from audit_rag.generate.base import generate
from audit_rag.index.store import IndexStore
from audit_rag.paths import project_root
from audit_rag.retrieve.hybrid import hybrid_search
from audit_rag.theme import page_end, page_start, render_footer, render_header

app = FastAPI(title="audit-rag-assistant", version="0.2.0")


def _index_path() -> Path:
    env = os.environ.get("AUDIT_RAG_INDEX")
    root = project_root()
    return Path(env) if env else root / "data" / "indexes" / "audit.db"


def _ensure_runtime() -> str | None:
    """Load the index lazily. Returns an error message if it is missing."""
    path = _index_path()
    if not path.exists():
        return f"Index not found: {path}. Run `python -m audit_rag ingest` first."
    if getattr(app.state, "embedder", None) is None or getattr(app.state, "index_path", None) != path:
        app.state.index_path = path
        app.state.embedder = get_embedder()
    return None


class AskRequest(BaseModel):
    question: str = Field(min_length=1)
    k: int = Field(default=5, ge=1, le=20)


@app.get("/health")
def health() -> dict[str, str]:
    status = "ok" if _index_path().exists() else "no-index"
    return {"status": status}


@app.post("/api/ask")
def api_ask(body: AskRequest):
    error = _ensure_runtime()
    if error:
        return JSONResponse({"detail": error}, status_code=503)
    embedder = app.state.embedder
    with IndexStore(app.state.index_path) as store:
        hits = hybrid_search(store, embedder, body.question, k=body.k, rerank=True)
        answer = generate(body.question, hits)
    return {
        "question": body.question,
        "refused": answer.refused,
        "generator": answer.generator,
        "answer": answer.text,
        "citations": answer.citations,
        "used_chunk_ids": answer.used_chunk_ids,
        "hits": [
            {
                "rank": i,
                "chunk_id": hit.chunk_id,
                "doc_id": hit.doc_id,
                "title": hit.title,
                "section": hit.section,
                "license": hit.license,
                "source_url": hit.source_url,
                "text": hit.text[:800],
            }
            for i, hit in enumerate(hits, start=1)
        ],
    }


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard() -> HTMLResponse:
    path = project_root() / "evals" / "reports" / "dashboard.html"
    if not path.exists():
        body = (
            page_start("Dashboard · audit-rag-assistant")
            + render_header("dashboard")
            + '<main class="wrap"><p class="note">Dashboard not built. Run python scripts/eval.py.</p></main>'
            + render_footer()
            + page_end()
        )
        return HTMLResponse(body, status_code=404)
    return HTMLResponse(path.read_text(encoding="utf-8"))


@app.get("/", response_class=HTMLResponse)
def home() -> HTMLResponse:
    return HTMLResponse(_HOME_HTML)


_HOME_HTML = (
    page_start("audit-rag-assistant")
    + render_header("ask")
    + """
<main class="wrap">
  <section class="hero">
    <h1>Ask a cited security question</h1>
    <p>Answers are drawn only from retrieved chunks in a license-cleared knowledge base. Every claim is cited. If the evidence is not there, the assistant refuses.</p>
  </section>
  <form id="form" class="ask-card" action="/api/ask" method="post">
    <label class="visually-hidden" for="q" style="position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0);">Question</label>
    <textarea id="q" name="q" placeholder="Ask about a smart-contract weakness…" required></textarea>
    <div class="ask-row">
      <button class="primary" type="submit" id="ask-btn">Ask</button>
      <div class="chips" role="group" aria-label="Example questions">
        <button type="button" class="chip" data-q="Why is authorization through tx.origin considered unsafe?">tx.origin authorization</button>
        <button type="button" class="chip" data-q="What remediations does the SWC Registry recommend for reentrancy?">Reentrancy remediations</button>
        <button type="button" class="chip" data-q="What is SWC-128 about?">SWC-128</button>
        <button type="button" class="chip" data-q="What high-severity findings were reported in a 2024 Uniswap audit contest on Code4rena?">Should refuse: Code4rena contest</button>
      </div>
    </div>
  </form>
  <div id="out" class="results" aria-live="polite"></div>
</main>
"""
    + render_footer()
    + """
<script>
  const MARKER = /\\[(\\d+):([A-Za-z0-9_.:-]+#[A-Za-z0-9_.:-]+)\\]/g;

  function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, (ch) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    }[ch]));
  }

  function sourceId(chunkId) {
    return "src-" + String(chunkId).replace(/[^A-Za-z0-9_-]/g, "-");
  }

  function renderAnswer(text) {
    return escapeHtml(text).replace(MARKER, (_, rank, id) => {
      const label = escapeHtml(id);
      return `<a class="cite-chip" href="#${sourceId(id)}" data-target="${sourceId(id)}" title="${label}"><span>${escapeHtml(rank)}</span><span class="cite-id">${label}</span></a>`;
    });
  }

  function renderSources(hits, used) {
    const usedSet = new Set(used || []);
    const ordered = [
      ...hits.filter((h) => usedSet.has(h.chunk_id)),
      ...hits.filter((h) => !usedSet.has(h.chunk_id)),
    ];
    if (!ordered.length) return "";
    const items = ordered.map((h) => {
      const open = usedSet.has(h.chunk_id) ? " open" : "";
      const src = h.source_url
        ? `<div class="src-links"><a href="${escapeHtml(h.source_url)}" rel="noopener noreferrer">Source document</a> · ${escapeHtml(h.license || "license unknown")}</div>`
        : `<div class="src-links">${escapeHtml(h.license || "license unknown")}</div>`;
      return `<details class="source" id="${sourceId(h.chunk_id)}"${open}>
        <summary>
          <span class="cite-chip"><span>${escapeHtml(String(h.rank))}</span><span class="cite-id">${escapeHtml(h.chunk_id)}</span></span>
          <span>${escapeHtml(h.title || h.doc_id)} — ${escapeHtml(h.section || "body")}</span>
          <span class="license">${escapeHtml(h.license || "unknown")}</span>
        </summary>
        <p class="passage">${escapeHtml(h.text || "")}</p>
        ${src}
      </details>`;
    }).join("");
    return `<section class="sources"><h2>Sources</h2>${items}</section>`;
  }

  const q = document.getElementById("q");
  const out = document.getElementById("out");
  const askBtn = document.getElementById("ask-btn");
  document.querySelectorAll(".chip").forEach((el) => {
    el.addEventListener("click", () => { q.value = el.dataset.q; q.focus(); });
  });
  document.getElementById("form").addEventListener("submit", async (event) => {
    event.preventDefault();
    askBtn.disabled = true;
    out.innerHTML = '<div class="loading"><span class="spinner" aria-hidden="true"></span><span>Retrieving cited evidence…</span></div>';
    try {
      const res = await fetch("/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q.value, k: 5 })
      });
      const data = await res.json();
      if (!res.ok) {
        out.innerHTML = `<p class="error">${escapeHtml(data.detail || "Request failed.")}</p>`;
        return;
      }
      const kicker = data.refused ? "Not enough evidence" : "Cited answer";
      const cardClass = data.refused ? "answer-card refuse" : "answer-card";
      out.innerHTML = `
        <p class="meta-row">Generator: ${escapeHtml(data.generator || "extractive")}</p>
        <article class="${cardClass}">
          <p class="answer-kicker">${kicker}</p>
          <div class="answer-body">${renderAnswer(data.answer || "")}</div>
        </article>
        ${renderSources(data.hits || [], data.used_chunk_ids || [])}`;
      out.querySelectorAll(".cite-chip[data-target]").forEach((chip) => {
        chip.addEventListener("click", (ev) => {
          const target = document.getElementById(chip.dataset.target);
          if (target) {
            ev.preventDefault();
            target.open = true;
            target.scrollIntoView({ behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "nearest" });
          }
        });
      });
    } catch (err) {
      out.innerHTML = '<p class="error">The request failed. Try again.</p>';
    } finally {
      askBtn.disabled = false;
    }
  });
</script>
"""
    + page_end()
)
