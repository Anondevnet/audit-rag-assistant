from audit_rag.chunk.chunker import chunk_document, estimate_tokens, parse_front_matter


def test_parse_front_matter_extracts_fields_and_body() -> None:
    text = "---\nid: swc-107\ntitle: Reentrancy\n---\n\n# Hello\n\nBody text.\n"
    meta, body = parse_front_matter(text)
    assert meta["id"] == "swc-107"
    assert meta["title"] == "Reentrancy"
    assert body.startswith("# Hello")


def test_chunks_split_on_headings_and_keep_section() -> None:
    text = """---
id: demo
title: Demo
---

# Demo

## Description

The description talks about reentrancy in some detail so the section is kept.

## Remediation

Use the checks-effects-interactions pattern and a reentrancy lock.
"""
    chunks = chunk_document(text, doc_id="demo", max_tokens=700, overlap_tokens=0, min_tokens=0)
    assert len(chunks) >= 2
    sections = {c.section for c in chunks}
    assert "Description" in sections
    assert "Remediation" in sections
    assert chunks[0].chunk_id == "demo#c0"
    assert chunks[0].metadata["title"] == "Demo"
    assert all(c.doc_id == "demo" for c in chunks)


def test_long_section_is_split_under_token_budget() -> None:
    words = " ".join(f"word{i}" for i in range(500))
    text = f"---\nid: long\ntitle: Long\n---\n\n## Section\n\n{words}\n"
    chunks = chunk_document(text, doc_id="long", max_tokens=120, overlap_tokens=20)
    assert len(chunks) >= 3
    assert all(c.token_count <= 120 + 20 + 5 for c in chunks)
    # overlap should repeat some trailing words of the previous chunk
    first_tail = chunks[0].text.split()[-5:]
    assert any(w in chunks[1].text.split()[:30] for w in first_tail)


def test_code_fence_is_not_split_on_blank_lines() -> None:
    fence = "```solidity\npragma solidity ^0.8.0;\n\ncontract X {\n  function f() public {}\n}\n```"
    text = f"---\nid: code\ntitle: Code\n---\n\n## Sample\n\nIntro paragraph.\n\n{fence}\n"
    chunks = chunk_document(text, doc_id="code", max_tokens=200, overlap_tokens=0)
    joined = "\n".join(c.text for c in chunks)
    assert "```solidity" in joined
    assert joined.count("```") % 2 == 0


def test_emptyish_document_still_returns_no_crash() -> None:
    chunks = chunk_document("   \n", doc_id="empty")
    assert chunks == [] or all(c.text.strip() for c in chunks)
    assert estimate_tokens("") == 0
