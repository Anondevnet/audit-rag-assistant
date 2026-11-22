from audit_rag.citations.format import (
    citation_marker,
    excerpt,
    format_hit,
    format_search_results,
    parse_citation_markers,
)
from audit_rag.index.store import SearchHit


def _hit(**kwargs) -> SearchHit:
    defaults = dict(
        chunk_id="swc-107#c0",
        doc_id="swc-107",
        title="SWC-107: Reentrancy",
        section="Remediation",
        text="Use the Checks-Effects-Interactions pattern and a reentrancy lock.",
        source_url="https://github.com/SmartContractSecurity/SWC-registry/blob/main/entries/docs/SWC-107.md",
        license="MIT",
        score=0.042,
        bm25_rank=1,
        vector_rank=2,
        hybrid_rank=1,
        rerank_score=1.5,
    )
    defaults.update(kwargs)
    return SearchHit(**defaults)


def test_citation_marker_is_stable_and_parseable() -> None:
    marker = citation_marker(1, "swc-107#c0")
    assert marker == "[1:swc-107#c0]"
    assert parse_citation_markers("See " + marker + " for the fix.") == [(1, "swc-107#c0")]


def test_format_hit_includes_required_attribution_fields() -> None:
    text = format_hit(_hit(), rank=1)
    assert "[1:swc-107#c0]" in text
    assert "SWC-107: Reentrancy" in text
    assert "MIT" in text
    assert "source=https://github.com/SmartContractSecurity/SWC-registry" in text
    assert "doc=swc-107" in text
    assert "Checks-Effects-Interactions" in text


def test_format_search_results_and_parser_round_trip() -> None:
    hits = [_hit(), _hit(chunk_id="nssc-reentrancy#c0", doc_id="nssc-reentrancy", title="Re-entrancy")]
    rendered = format_search_results("how do I prevent reentrancy?", hits)
    parsed = parse_citation_markers(rendered)
    assert parsed == [(1, "swc-107#c0"), (2, "nssc-reentrancy#c0")]
    assert rendered.startswith("Query: how do I prevent reentrancy?")


def test_empty_results_message() -> None:
    assert "No results" in format_search_results("zzz", [])


def test_excerpt_truncates() -> None:
    short = excerpt("one two", width=20)
    assert short == "one two"
    long = excerpt("word " * 80, width=40)
    assert long.endswith("...")
    assert len(long) <= 40
