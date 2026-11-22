# Build notes

## Status

Milestone 1 of 3, as of 22 November 2026 (America/Detroit). Retrieval only. No generator, no guardrails, no eval dashboard, no public demo, and no reported metrics.

## What Milestone 1 delivered

- Package layout, MIT license for the code, CI that runs pytest with the offline hashing embedder.
- 49 corpus documents from SWC-registry (MIT, 37) and not-so-smart-contracts (Apache-2.0, 12). See DATA.md.
- Heading-aware chunking, SQLite FTS5 BM25 + sqlite-vec (NumPy fallback), RRF hybrid search, optional FlashRank or an offline token-overlap reranker.
- CLI: `python -m audit_rag ingest` and `python -m audit_rag search "query"`.
- Unit tests for chunking, retrieval, and citation formatting.
- 20 seed golden questions at `evals/golden_seed.jsonl`, all marked `needs_human_review`.

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

## Milestone 2 (next)

Generation with forced citations, retrieved-document prompt-injection guardrails plus a held-out injection set, grow the gold set to 80–100 after human review of the seed questions, a full metric harness (Recall@k, MRR, citation accuracy, faithfulness), baseline-vs-improved report, dashboard tab, and a local demo GIF. Do not invent metrics before that eval script has been run.
