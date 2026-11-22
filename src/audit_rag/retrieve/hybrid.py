"""Hybrid BM25 + vector retrieval with Reciprocal Rank Fusion."""

from __future__ import annotations

from collections import defaultdict

from audit_rag.embeddings.base import Embedder
from audit_rag.index.store import IndexStore, SearchHit
from audit_rag.rerank.base import get_reranker

RRF_K = 60


def rrf_fuse(
    ranked_lists: list[list[tuple[str, int]]],
    *,
    k: int = RRF_K,
) -> list[tuple[str, float]]:
    """Fuse rank lists of (id, 1-based-rank) into (id, rrf_score) descending."""
    scores: dict[str, float] = defaultdict(float)
    for ranked in ranked_lists:
        for item_id, rank in ranked:
            scores[item_id] += 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda kv: kv[1], reverse=True)


def hybrid_search(
    store: IndexStore,
    embedder: Embedder,
    query: str,
    *,
    k: int = 5,
    fetch_k: int | None = None,
    rerank: bool = True,
) -> list[SearchHit]:
    if not query.strip():
        return []
    pool = fetch_k or max(k * 4, 20)
    bm25 = store.bm25_search(query, pool)
    query_vec = embedder.embed_query(query)
    vectors = store.vector_search(query_vec, pool)
    fused = rrf_fuse([bm25, vectors])[:pool]
    hits = store.fetch_hits(fused)
    bm25_rank = {chunk_id: rank for chunk_id, rank in bm25}
    vec_rank = {chunk_id: rank for chunk_id, rank in vectors}
    hybrid_rank = {chunk_id: i + 1 for i, (chunk_id, _) in enumerate(fused)}
    for i, hit in enumerate(hits):
        hit.bm25_rank = bm25_rank.get(hit.chunk_id)
        hit.vector_rank = vec_rank.get(hit.chunk_id)
        hit.hybrid_rank = hybrid_rank.get(hit.chunk_id, i + 1)
    if rerank:
        reranker = get_reranker()
        hits = reranker.rerank(query, hits)
    return hits[:k]
