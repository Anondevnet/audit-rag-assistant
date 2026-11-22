
from audit_rag.retrieve.expand import expand_query
from audit_rag.rerank.base import TokenOverlapReranker
from audit_rag.index.store import SearchHit
from audit_rag.chunk.chunker import chunk_document


def test_expand_query_adds_swc_title_and_hyphen_variants() -> None:
    titles = {"swc-128": "SWC-128: DoS With Block Gas Limit"}
    expanded = expand_query("What is SWC-128 about?", titles)
    assert "DoS With Block Gas Limit" in expanded
    tx = expand_query("Why is authorization through tx.origin considered unsafe?")
    assert "tx origin" in tx.lower()


def test_short_heading_merges_into_following_section() -> None:
    text = """---
id: demo
title: Demo
---

# Demo Title That Is Tiny

## Description

This description is long enough that it stays a content section after the
short heading-only block is merged into it for retrieval quality.
"""
    chunks = chunk_document(text, doc_id="demo", max_tokens=700, overlap_tokens=0, min_tokens=40)
    assert len(chunks) == 1
    assert "description" in (chunks[0].section + chunks[0].text).lower()
    assert "Demo Title That Is Tiny" in chunks[0].text


def test_token_reranker_does_not_prefer_tiny_title_stub() -> None:
    short = SearchHit(
        chunk_id="swc-128#c0",
        doc_id="swc-128",
        title="SWC-128: DoS With Block Gas Limit",
        section="SWC-128: DoS With Block Gas Limit",
        text="# SWC-128: DoS With Block Gas Limit",
        source_url="https://example.test/swc-128",
        license="MIT",
        score=1.0,
    )
    long = SearchHit(
        chunk_id="swc-128#c2",
        doc_id="swc-128",
        title="SWC-128: DoS With Block Gas Limit",
        section="Description",
        text=(
            "SWC-128 is about denial of service with the block gas limit. "
            "Programming patterns that are harmless in centralized applications can "
            "lead to Denial of Service conditions in smart contracts when the cost of "
            "executing a function exceeds the block gas limit. Modifying an array of "
            "unknown size that increases over time can lead to such a condition."
        ),
        source_url="https://example.test/swc-128",
        license="MIT",
        score=0.5,
    )
    ranked = TokenOverlapReranker().rerank("What is SWC-128 about?", [short, long])
    assert ranked[0].chunk_id == "swc-128#c2"
