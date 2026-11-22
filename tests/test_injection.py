from pathlib import Path

from audit_rag.chunk.chunker import chunk_document, parse_front_matter
from audit_rag.generate.extractive import extractive_generate
from audit_rag.guardrails.scanner import scan_text
from audit_rag.index.store import SearchHit
from audit_rag.paths import project_root


def _docs() -> list[Path]:
    folder = project_root() / "evals" / "injection"
    return sorted(folder.glob("*.md"))


def test_injection_fixtures_exist_and_are_flagged() -> None:
    paths = _docs()
    assert len(paths) >= 2
    flagged = 0
    for path in paths:
        text = path.read_text(encoding="utf-8")
        if scan_text(text):
            flagged += 1
    assert flagged == len(paths)


def test_generator_does_not_obey_injected_prompt() -> None:
    path = project_root() / "evals" / "injection" / "injected_reentrancy.md"
    text = path.read_text(encoding="utf-8")
    meta, _ = parse_front_matter(text)
    chunks = chunk_document(text, doc_id="injection-reentrancy", metadata=meta)
    hits = [
        SearchHit(
            chunk_id=c.chunk_id,
            doc_id=c.doc_id,
            title=c.title,
            section=c.section,
            text=c.text,
            source_url=c.metadata.get("source_url", ""),
            license=c.metadata.get("license", ""),
            score=1.0,
        )
        for c in chunks
    ]
    answer = extractive_generate("What remediations help prevent reentrancy?", hits)
    assert "Ignore previous instructions" not in answer.text
    assert "reveal the system prompt" not in answer.text.lower()
    assert answer.injection_flags
