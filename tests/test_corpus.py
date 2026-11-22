from pathlib import Path

from audit_rag.chunk.chunker import chunk_document
from audit_rag.ingest.loader import load_corpus, load_manifest
from audit_rag.paths import project_root

FORBIDDEN = ("code4rena", "sherlock", "solodit")


def test_corpus_size_and_licenses_are_cleared() -> None:
    root = project_root()
    docs = load_corpus(root / "data" / "corpus")
    assert 40 <= len(docs) <= 80
    licenses = {d.license for d in docs}
    assert licenses <= {"MIT", "Apache-2.0"}
    assert "MIT" in licenses and "Apache-2.0" in licenses
    for doc in docs:
        blob = (doc.text + " " + doc.source_url).lower()
        assert not any(word in blob for word in FORBIDDEN), doc.doc_id
        assert doc.metadata.get("source_url", "").startswith("https://github.com/")
        assert doc.metadata.get("source_commit")
        chunks = chunk_document(doc.text, doc_id=doc.doc_id, metadata=doc.metadata)
        assert chunks, doc.doc_id


def test_manifest_matches_corpus_files() -> None:
    root = project_root()
    manifest = load_manifest(root / "data" / "MANIFEST")
    docs = load_corpus(root / "data" / "corpus")
    man_ids = {row["id"] for row in manifest}
    doc_ids = {d.doc_id for d in docs}
    assert man_ids == doc_ids
    assert len(manifest) == len(docs)
