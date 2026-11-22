"""Answer generation with forced citations."""

from __future__ import annotations

import os
from audit_rag.generate.answer import Answer
from audit_rag.generate.extractive import extractive_generate
from audit_rag.index.store import SearchHit

def generate(
    query: str,
    hits: list[SearchHit],
    *,
    name: str | None = None,
) -> Answer:
    """Generate a cited answer, or refuse when evidence is insufficient.

    Default and CI path is the deterministic extractive generator.
    Set AUDIT_RAG_GENERATOR=ollama to try a local chat model (optional).
    """
    choice = (name or os.environ.get("AUDIT_RAG_GENERATOR") or "extractive").strip().lower()
    if choice in {"ollama", "auto"}:
        try:
            from audit_rag.generate.ollama_gen import ollama_generate

            if choice == "ollama" or ollama_generate.available():
                return ollama_generate(query, hits)
        except Exception:
            if choice == "ollama":
                raise
    return extractive_generate(query, hits)
