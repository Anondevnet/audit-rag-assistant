"""Hybrid BM25 + vector retrieval with Reciprocal Rank Fusion."""

from __future__ import annotations

import os
from collections import defaultdict

from audit_rag.embeddings.base import Embedder
from audit_rag.index.store import IndexStore, SearchHit
from audit_rag.rerank.base import get_reranker
from audit_rag.retrieve.expand import expand_query

RRF_K = 60


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return float(raw)


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


def _env_flag(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def rrf_fuse(
    ranked_lists: list[list[tuple[str, int]]],
    *,
    k: int = RRF_K,
    weights: list[float] | None = None,
) -> list[tuple[str, float]]:
    """Fuse rank lists of (id, 1-based-rank) into (id, rrf_score) descending."""
    scores: dict[str, float] = defaultdict(float)
    if weights is None:
        weights = [1.0] * len(ranked_lists)
    if len(weights) != len(ranked_lists):
        raise ValueError("weights must match the number of rank lists")
    for weight, ranked in zip(weights, ranked_lists, strict=True):
        for item_id, rank in ranked:
            scores[item_id] += weight / (k + rank)
    return sorted(scores.items(), key=lambda kv: kv[1], reverse=True)


def hybrid_search(
    store: IndexStore,
    embedder: Embedder,
    query: str,
    *,
    k: int = 5,
    fetch_k: int | None = None,
    rerank: bool = True,
    expand: bool | None = None,
    rrf_k: int | None = None,
    bm25_weight: float | None = None,
    vector_weight: float | None = None,
    titles: dict[str, str] | None = None,
) -> list[SearchHit]:
    if not query.strip():
        return []
    if expand is None:
        expand = _env_flag("AUDIT_RAG_EXPAND", True)
    pool = fetch_k or _env_int("AUDIT_RAG_FETCH_K", 0) or max(k * 4, 24)
    rrf_k = rrf_k if rrf_k is not None else _env_int("AUDIT_RAG_RRF_K", RRF_K)
    bm25_weight = bm25_weight if bm25_weight is not None else _env_float("AUDIT_RAG_BM25_WEIGHT", 1.0)
    vector_weight = vector_weight if vector_weight is not None else _env_float("AUDIT_RAG_VEC_WEIGHT", 1.0)

    search_query = query
    if expand:
        search_query = expand_query(query, titles if titles is not None else store.document_titles())

    bm25 = store.bm25_search(search_query, pool)
    query_vec = embedder.embed_query(search_query)
    vectors = store.vector_search(query_vec, pool)
    fused = rrf_fuse([bm25, vectors], k=rrf_k, weights=[bm25_weight, vector_weight])[:pool]
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
