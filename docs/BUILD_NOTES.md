# Build notes

## Status

Milestone 3 retrieval pass, 22 November 2026 (America/Detroit). Default retriever is still hashing + token + extractive, but short heading chunks are merged, queries are expanded, and the token reranker no longer over-rewards title stubs. A FastAPI + Dockerfile + render.yaml + fly.toml demo is in the repo; a public URL is only published when a free-tier CLI is already authenticated. Metrics in README Results compare `evals/reports/m2-baseline.json` to `evals/reports/latest.json`.

## What Milestone 1 delivered

- Package layout, MIT license for the code, CI that runs pytest with the offline hashing embedder.
- 49 corpus documents from SWC-registry (MIT, 37) and not-so-smart-contracts (Apache-2.0, 12). See DATA.md.
- Heading-aware chunking, SQLite FTS5 BM25 + sqlite-vec (NumPy fallback), RRF hybrid search, optional FlashRank or an offline token-overlap reranker.
- CLI: `python -m audit_rag ingest`, `search`, and `ask`.
- Unit tests for chunking, retrieval, citation formatting, generation, guardrails, and injection fixtures.
- 20 seed golden questions at `evals/golden_seed.jsonl`, all marked `approved` by the owner on 22 November 2026.

## Local ingest (Mac, optional Ollama)

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
# optional, better vectors than the CI hashing fallback:
#   ollama pull nomic-embed-text
#   export AUDIT_RAG_EMBEDDER=ollama
export AUDIT_RAG_EMBEDDER=hashing   # matches CI; always works offline
python -m audit_rag ingest
python -m audit_rag search "How do I prevent reentrancy?"
```

The index at `data/indexes/audit.db` is gitignored. Re-ingest after corpus changes. The embedder used at search time must match the one used at ingest time.

## Milestone 2 (delivered)

- Forced-citation generation: answers are built only from retrieved (and sanitized) chunks; every included sentence carries a `[rank:chunk_id]` marker. CI uses the deterministic extractive generator. Optional Ollama chat is used only when `AUDIT_RAG_GENERATOR=ollama` and `OLLAMA_CHAT_MODEL` are set; the repo does not default to an unofficial or uncensored model.
- Prompt-injection guards treat retrieved text as data, strip instruction-like sentences, and drop instruction-only hits. Fixtures live in `evals/injection/`.
- Eval harness: Recall@k, MRR, citation accuracy, refusal accuracy, and a lexical faithfulness score. Methods are documented in the README Results section. Real numbers only, from `evals/reports/latest.json`.
- Static dashboard at `evals/reports/dashboard.html` and `docs/demo.gif`.
- Growing the gold set to 80–100 questions and a public deploy are **not** part of this milestone.

## Milestone 3 (later)

Free-tier deploy only when requested. Optional larger gold set. Do not invent metrics or change the committed baseline without a new harness run.
