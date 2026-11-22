"""Small FastAPI demo for the cited RAG assistant."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from audit_rag.embeddings.base import get_embedder
from audit_rag.generate.base import generate
from audit_rag.index.store import IndexStore
from audit_rag.paths import project_root
from audit_rag.retrieve.hybrid import hybrid_search

app = FastAPI(title="audit-rag-assistant", version="0.2.0")


def _index_path() -> Path:
    env = os.environ.get("AUDIT_RAG_INDEX")
    root = project_root()
    return Path(env) if env else root / "data" / "indexes" / "audit.db"


@app.on_event("startup")
def _startup() -> None:
    path = _index_path()
    if not path.exists():
        raise RuntimeError(f"Index not found: {path}. Run `python -m audit_rag ingest` first.")
    app.state.index_path = path
    app.state.embedder = get_embedder()


class AskRequest(BaseModel):
    question: str = Field(min_length=1)
    k: int = Field(default=5, ge=1, le=20)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/ask")
def api_ask(body: AskRequest) -> dict:
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
        return HTMLResponse("<p>Dashboard not built. Run python scripts/eval.py.</p>", status_code=404)
    return HTMLResponse(path.read_text(encoding="utf-8"))


@app.get("/", response_class=HTMLResponse)
def home() -> HTMLResponse:
    return HTMLResponse(_HOME_HTML)


_HOME_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>audit-rag-assistant</title>
  <style>
    body { font-family: ui-sans-serif, system-ui, sans-serif; margin: 2rem auto; max-width: 860px; color: #111; }
    h1 { font-weight: 650; }
    textarea { width: 100%; min-height: 5rem; font: inherit; padding: 0.6rem; }
    button, .chip { font: inherit; padding: 0.45rem 0.8rem; margin: 0.2rem 0.2rem 0 0; cursor: pointer; }
    .chip { background: #f3f3f3; border: 1px solid #ddd; border-radius: 999px; display: inline-block; }
    .answer { background: #f7f7f7; padding: 1rem; border-radius: 8px; white-space: pre-wrap; }
    .refuse { background: #fff4f0; }
    .hit { border: 1px solid #eee; padding: 0.6rem 0.8rem; margin: 0.5rem 0; border-radius: 6px; }
    .muted { color: #555; font-size: 0.9rem; }
    a { color: #0b57d0; }
  </style>
</head>
<body>
  <h1>audit-rag-assistant</h1>
  <p class="muted">Cited answers from a license-cleared SWC Registry + not-so-smart-contracts knowledge base. Not a professional audit. <a href="/dashboard">Eval dashboard</a></p>
  <form id="form">
    <textarea id="q" name="q" placeholder="Ask a question…" required></textarea>
    <div>
      <button type="submit">Ask</button>
      <span class="chip" data-q="Why is authorization through tx.origin considered unsafe?">tx.origin</span>
      <span class="chip" data-q="What remediations does the SWC Registry recommend for reentrancy?">reentrancy</span>
      <span class="chip" data-q="What high-severity findings were reported in a 2024 Uniswap audit contest on Code4rena?">should refuse</span>
    </div>
  </form>
  <div id="out"></div>
  <script>
    const q = document.getElementById('q');
    const out = document.getElementById('out');
    document.querySelectorAll('.chip').forEach(el => el.onclick = () => { q.value = el.dataset.q; });
    document.getElementById('form').onsubmit = async (e) => {
      e.preventDefault();
      out.innerHTML = '<p class="muted">Retrieving…</p>';
      const res = await fetch('/api/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: q.value, k: 5 })
      });
      const data = await res.json();
      if (!res.ok) { out.innerHTML = '<p>Request failed.</p>'; return; }
      const cls = data.refused ? 'answer refuse' : 'answer';
      const hits = (data.hits || []).map(h =>
        `<div class="hit"><strong>[${h.rank}:${h.chunk_id}]</strong> ${h.title} — ${h.section}<br>
         <span class="muted">${h.license} · <a href="${h.source_url}">source</a></span>
         <div>${h.text}</div></div>`
      ).join('');
      out.innerHTML = `<p class="muted">Generator: ${data.generator} · Refused: ${data.refused}</p>
        <div class="${cls}">${data.answer}</div><h2>Retrieved chunks</h2>${hits}`;
    };
  </script>
</body>
</html>
"""
