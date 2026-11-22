from __future__ import annotations

import math
import os
import re
from abc import ABC, abstractmethod

from audit_rag.index.store import SearchHit

_CONTENT_SECTIONS = (
    "description", "remediation", "mitigation", "attack", "vulnerability",
)
_LOW_PRIORITY_SECTIONS = (
    "source notice", "references", "samples", "example files", "relationships",
)


class Reranker(ABC):
    kind: str

    @abstractmethod
    def rerank(self, query: str, hits: list[SearchHit]) -> list[SearchHit]:
        """Return hits in new order, writing rerank_score on each."""


class IdentityReranker(Reranker):
    kind = "none"

    def rerank(self, query: str, hits: list[SearchHit]) -> list[SearchHit]:
        del query
        for hit in hits:
            hit.rerank_score = hit.score
        return hits


class TokenOverlapReranker(Reranker):
    """Offline lexical reranker used in CI and when FlashRank is unavailable."""

    kind = "token"

    def rerank(self, query: str, hits: list[SearchHit]) -> list[SearchHit]:
        q_terms = set(_terms(query))
        if not q_terms:
            return IdentityReranker().rerank(query, hits)
        scored: list[tuple[float, SearchHit]] = []
        for hit in hits:
            doc_terms = _terms(hit.title + " " + hit.section + " " + hit.text)
            overlap = len(q_terms & set(doc_terms))
            # Floor the length so 5-token title stubs cannot dominate
            # longer description or remediation sections.
            denom = math.sqrt(max(len(doc_terms), 25))
            score = overlap / denom
            section = (hit.section or "").lower()
            if any(name in section for name in _CONTENT_SECTIONS):
                score *= 1.12
            if any(name in section for name in _LOW_PRIORITY_SECTIONS):
                score *= 0.85
            hit.rerank_score = score
            scored.append((score, hit))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [hit for _, hit in scored]


class FlashRankReranker(Reranker):
    kind = "flashrank"

    def __init__(self, model_name: str | None = None) -> None:
        from flashrank import Ranker

        model_name = model_name or os.environ.get("FLASHRANK_MODEL") or "ms-marco-MiniLM-L-12-v2"
        cache_dir = os.environ.get("FLASHRANK_CACHE_DIR")
        kwargs = {"model_name": model_name}
        if cache_dir:
            kwargs["cache_dir"] = cache_dir
        self._ranker = Ranker(**kwargs)

    def rerank(self, query: str, hits: list[SearchHit]) -> list[SearchHit]:
        if not hits:
            return hits
        from flashrank import RerankRequest

        passages = [{"id": i, "text": hit.text} for i, hit in enumerate(hits)]
        request = RerankRequest(query=query, passages=passages)
        ranked = self._ranker.rerank(request)
        ordered: list[SearchHit] = []
        for item in ranked:
            # flashrank versions differ; support object or dict
            idx = item["id"] if isinstance(item, dict) else getattr(item, "id")
            score = item["score"] if isinstance(item, dict) else getattr(item, "score")
            hit = hits[int(idx)]
            hit.rerank_score = float(score)
            ordered.append(hit)
        # keep any hits the reranker dropped
        seen = {h.chunk_id for h in ordered}
        ordered.extend(h for h in hits if h.chunk_id not in seen)
        return ordered


def get_reranker(name: str | None = None) -> Reranker:
    choice = (name or os.environ.get("AUDIT_RAG_RERANKER") or "token").strip().lower()
    if choice in {"none", "off", "identity"}:
        return IdentityReranker()
    if choice in {"token", "lexical", "overlap"}:
        return TokenOverlapReranker()
    if choice == "flashrank":
        try:
            return FlashRankReranker()
        except Exception as exc:  # pragma: no cover - depends on optional extra
            raise RuntimeError(
                "FlashRank is not available. Install the local extra (pip install -e '.[local]') "
                "or set AUDIT_RAG_RERANKER=token."
            ) from exc
    if choice == "auto":
        try:
            return FlashRankReranker()
        except Exception:
            return TokenOverlapReranker()
    raise ValueError(f"Unknown reranker {choice!r}. Use flashrank, token, none, or auto.")


def _terms(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9_]+", text.lower()) if len(t) > 1]
