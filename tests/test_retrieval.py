from pathlib import Path

from audit_rag.chunk.chunker import chunk_document
from audit_rag.embeddings.hashing import HashingEmbedder
from audit_rag.index.store import IndexStore
from audit_rag.ingest.loader import Document
from audit_rag.retrieve.hybrid import hybrid_search, rrf_fuse


def _doc(tmp: Path, doc_id: str, title: str, body: str) -> Document:
    text = f"---\nid: {doc_id}\ntitle: {title}\nlicense: MIT\nsource_url: https://example.test/{doc_id}\n---\n\n# {title}\n\n{body}\n"
    path = tmp / f"{doc_id}.md"
    path.write_text(text, encoding="utf-8")
    return Document(
        doc_id=doc_id,
        title=title,
        path=path,
        text=text,
        body=body,
        metadata={
            "id": doc_id,
            "title": title,
            "license": "MIT",
            "source_url": f"https://example.test/{doc_id}",
        },
    )


def _build(tmp_path: Path) -> tuple[IndexStore, HashingEmbedder]:
    docs = [
        _doc(
            tmp_path,
            "swc-107",
            "SWC-107: Reentrancy",
            "## Description\n\nA reentrancy attack lets a malicious contract call back before state is updated.\n\n"
            "## Remediation\n\nUse the checks-effects-interactions pattern and a reentrancy lock.\n",
        ),
        _doc(
            tmp_path,
            "swc-115",
            "SWC-115: Authorization through tx.origin",
            "## Description\n\nauthorization through tx.origin is insecure because a phished user can be tricked.\n\n"
            "## Remediation\n\nUse msg.sender for authorization instead of tx.origin.\n",
        ),
        _doc(
            tmp_path,
            "swc-120",
            "SWC-120: Weak Sources of Randomness",
            "## Description\n\nUsing block.timestamp or blockhash as randomness is predictable.\n",
        ),
    ]
    chunks = []
    for doc in docs:
        chunks.extend(chunk_document(doc.text, doc_id=doc.doc_id, metadata=doc.metadata, overlap_tokens=0))
    embedder = HashingEmbedder(dim=64)
    store = IndexStore(tmp_path / "test.db")
    store.rebuild(docs, chunks, embedder)
    return store, embedder


def test_rrf_prefers_items_ranked_well_in_both_lists() -> None:
    a = [("x", 1), ("y", 2), ("z", 3)]
    b = [("y", 1), ("x", 2), ("w", 3)]
    fused = rrf_fuse([a, b])
    # y and x appear in both lists; y/x should beat z and w
    ids = [i for i, _ in fused]
    assert set(ids[:2]) == {"x", "y"}
    assert fused[0][1] >= fused[-1][1]


def test_bm25_finds_unique_keyword(tmp_path: Path) -> None:
    store, _ = _build(tmp_path)
    ranked = store.bm25_search("tx.origin authorization", limit=5)
    assert ranked
    assert any(chunk_id.startswith("swc-115") for chunk_id, _ in ranked)
    store.close()


def test_hybrid_search_returns_cited_hits_for_reentrancy(tmp_path: Path) -> None:
    store, embedder = _build(tmp_path)
    hits = hybrid_search(store, embedder, "How do I prevent a reentrancy attack?", k=3)
    assert hits
    top_ids = {h.doc_id for h in hits}
    assert "swc-107" in top_ids
    top = hits[0]
    assert top.source_url.startswith("https://example.test/")
    assert top.license == "MIT"
    assert top.chunk_id.startswith(top.doc_id + "#")
    assert "reentrancy" in (top.title + top.text).lower()
    store.close()


def test_index_metadata_records_embedder(tmp_path: Path) -> None:
    store, embedder = _build(tmp_path)
    assert store.get_meta("embedder") == "hashing"
    assert int(store.get_meta("document_count")) == 3
    assert int(store.get_meta("chunk_count")) >= 3
    assert store.dim == embedder.dim
    store.close()
