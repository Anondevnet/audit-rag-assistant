"""Citation formatting for search hits and generated answers."""

from __future__ import annotations

import re
import textwrap

from audit_rag.index.store import SearchHit

# [1:swc-107#c0]  — stable, machine-parseable marker
MARKER_RE = re.compile(r"\[(\d+):([A-Za-z0-9_.:-]+#[A-Za-z0-9_.:-]+)\]")


def citation_marker(rank: int, chunk_id: str) -> str:
    return f"[{rank}:{chunk_id}]"


def excerpt(text: str, width: int = 240) -> str:
    collapsed = re.sub(r"\s+", " ", text).strip()
    if len(collapsed) <= width:
        return collapsed
    return collapsed[: width - 3].rstrip() + "..."


def format_hit(hit: SearchHit, rank: int, excerpt_width: int = 240) -> str:
    marker = citation_marker(rank, hit.chunk_id)
    ranks = []
    if hit.bm25_rank is not None:
        ranks.append(f"bm25@{hit.bm25_rank}")
    if hit.vector_rank is not None:
        ranks.append(f"vec@{hit.vector_rank}")
    if hit.hybrid_rank is not None:
        ranks.append(f"rrf@{hit.hybrid_rank}")
    rank_note = f" ({', '.join(ranks)})" if ranks else ""
    rerank = ""
    if hit.rerank_score is not None:
        rerank = f" rerank={hit.rerank_score:.4f}"
    header = (
        f"{marker} {hit.title}  [{hit.license or 'license unknown'}]\n"
        f"    doc={hit.doc_id}  section={hit.section or '-'}  score={hit.score:.6f}{rerank}{rank_note}\n"
        f"    source={hit.source_url or '(no source url)'}"
    )
    body = textwrap.indent(excerpt(hit.text, excerpt_width), "    ")
    return header + "\n" + body


def format_search_results(query: str, hits: list[SearchHit]) -> str:
    if not hits:
        return f"No results for: {query}"
    lines = [f"Query: {query}", f"Results: {len(hits)}", ""]
    for i, hit in enumerate(hits, start=1):
        lines.append(format_hit(hit, i))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def parse_citation_markers(text: str) -> list[tuple[int, str]]:
    """Parse [rank:chunk_id] markers from generated or formatted text."""
    return [(int(rank), chunk_id) for rank, chunk_id in MARKER_RE.findall(text)]
