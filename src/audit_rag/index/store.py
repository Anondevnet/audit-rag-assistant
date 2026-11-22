"""SQLite index: FTS5 BM25 plus sqlite-vec (with a NumPy fallback)."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from audit_rag.chunk.chunker import Chunk
from audit_rag.embeddings.base import Embedder
from audit_rag.ingest.loader import Document

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS documents (
    doc_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    path TEXT NOT NULL,
    source_name TEXT,
    source_url TEXT,
    license TEXT,
    license_url TEXT,
    copyright TEXT,
    text TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS chunks (
    chunk_id TEXT PRIMARY KEY,
    doc_id TEXT NOT NULL REFERENCES documents(doc_id),
    ordinal INTEGER NOT NULL,
    section TEXT,
    text TEXT NOT NULL,
    token_count INTEGER,
    embedding BLOB
);
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    chunk_id UNINDEXED,
    title,
    section,
    text,
    tokenize = 'porter unicode61'
);
"""


def _blob(vec: np.ndarray) -> bytes:
    return np.asarray(vec, dtype=np.float32).tobytes()


def _from_blob(data: bytes, dim: int) -> np.ndarray:
    arr = np.frombuffer(data, dtype=np.float32)
    if arr.size != dim:
        raise ValueError(f"Embedding blob size {arr.size} != dim {dim}")
    return arr


def _try_load_sqlite_vec(conn: sqlite3.Connection) -> bool:
    try:
        import sqlite_vec
    except ImportError:
        return False
    try:
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        return True
    except sqlite3.Error:
        return False


@dataclass
class SearchHit:
    chunk_id: str
    doc_id: str
    title: str
    section: str
    text: str
    source_url: str
    license: str
    score: float
    bm25_rank: int | None = None
    vector_rank: int | None = None
    hybrid_rank: int | None = None
    rerank_score: float | None = None


class IndexStore:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA)
        self.vec_enabled = _try_load_sqlite_vec(self.conn)

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "IndexStore":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def set_meta(self, key: str, value: str) -> None:
        self.conn.execute(
            "INSERT INTO meta(key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )

    def get_meta(self, key: str, default: str | None = None) -> str | None:
        row = self.conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default

    def document_titles(self) -> dict[str, str]:
        rows = self.conn.execute("SELECT doc_id, title FROM documents").fetchall()
        return {row["doc_id"]: row["title"] for row in rows}

    @property
    def dim(self) -> int:
        value = self.get_meta("embedding_dim")
        if not value:
            raise RuntimeError("Index has no embedding_dim; ingest first.")
        return int(value)

    def rebuild(self, documents: list[Document], chunks: list[Chunk], embedder: Embedder) -> None:
        self.conn.execute("DELETE FROM chunks_fts")
        self.conn.execute("DELETE FROM chunks")
        self.conn.execute("DELETE FROM documents")
        if self.vec_enabled:
            self.conn.execute("DROP TABLE IF EXISTS vec_chunks")

        embeddings = embedder.embed_documents([c.text for c in chunks]) if chunks else np.zeros((0, embedder.dim))
        dim = int(embeddings.shape[1]) if embeddings.size else embedder.dim
        self.set_meta("embedder", embedder.kind)
        self.set_meta("embedding_dim", str(dim))
        self.set_meta("chunk_count", str(len(chunks)))
        self.set_meta("document_count", str(len(documents)))

        if self.vec_enabled:
            self.conn.execute(
                f"CREATE VIRTUAL TABLE vec_chunks USING vec0(chunk_id TEXT PRIMARY KEY, embedding FLOAT[{dim}])"
            )

        for doc in documents:
            meta = doc.metadata
            self.conn.execute(
                """
                INSERT INTO documents(
                    doc_id, title, path, source_name, source_url, license, license_url, copyright, text
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    doc.doc_id,
                    doc.title,
                    str(doc.path),
                    meta.get("source_name", ""),
                    meta.get("source_url", ""),
                    meta.get("license", ""),
                    meta.get("license_url", ""),
                    meta.get("copyright", ""),
                    doc.text,
                ),
            )

        title_by_id = {d.doc_id: d.title for d in documents}
        for chunk, vec in zip(chunks, embeddings, strict=True):
            blob = _blob(vec)
            self.conn.execute(
                """
                INSERT INTO chunks(chunk_id, doc_id, ordinal, section, text, token_count, embedding)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    chunk.chunk_id,
                    chunk.doc_id,
                    chunk.ordinal,
                    chunk.section,
                    chunk.text,
                    chunk.token_count,
                    blob,
                ),
            )
            self.conn.execute(
                "INSERT INTO chunks_fts(chunk_id, title, section, text) VALUES (?, ?, ?, ?)",
                (chunk.chunk_id, title_by_id.get(chunk.doc_id, chunk.doc_id), chunk.section, chunk.text),
            )
            if self.vec_enabled:
                self.conn.execute(
                    "INSERT INTO vec_chunks(chunk_id, embedding) VALUES (?, ?)",
                    (chunk.chunk_id, blob),
                )
        self.conn.commit()

    def bm25_search(self, query: str, limit: int) -> list[tuple[str, int]]:
        match = _fts_match_query(query)
        if not match:
            return []
        sql = """
            SELECT chunk_id
            FROM chunks_fts
            WHERE chunks_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """
        rows = self.conn.execute(sql, (match, limit)).fetchall()
        return [(row["chunk_id"], i + 1) for i, row in enumerate(rows)]

    def vector_search(self, query_vec: np.ndarray, limit: int) -> list[tuple[str, int]]:
        blob = _blob(query_vec)
        if self.vec_enabled:
            rows = self.conn.execute(
                """
                SELECT chunk_id
                FROM vec_chunks
                WHERE embedding MATCH ?
                  AND k = ?
                """,
                (blob, limit),
            ).fetchall()
            if rows:
                return [(row["chunk_id"], i + 1) for i, row in enumerate(rows)]
        # NumPy fallback (also used if the MATCH syntax is unsupported)
        dim = self.dim
        all_rows = self.conn.execute(
            "SELECT chunk_id, embedding FROM chunks WHERE embedding IS NOT NULL"
        ).fetchall()
        if not all_rows:
            return []
        ids = [r["chunk_id"] for r in all_rows]
        mat = np.stack([_from_blob(r["embedding"], dim) for r in all_rows], axis=0)
        q = query_vec.astype(np.float32)
        scores = mat @ q
        order = np.argsort(-scores)[:limit]
        return [(ids[i], rank + 1) for rank, i in enumerate(order)]

    def fetch_hits(self, ranked: list[tuple[str, float]]) -> list[SearchHit]:
        if not ranked:
            return []
        ids = [chunk_id for chunk_id, _ in ranked]
        placeholders = ",".join("?" for _ in ids)
        rows = self.conn.execute(
            f"""
            SELECT c.chunk_id, c.doc_id, c.section, c.text,
                   d.title, d.source_url, d.license
            FROM chunks c
            JOIN documents d ON d.doc_id = c.doc_id
            WHERE c.chunk_id IN ({placeholders})
            """,
            ids,
        ).fetchall()
        by_id = {row["chunk_id"]: row for row in rows}
        hits: list[SearchHit] = []
        for chunk_id, score in ranked:
            row = by_id.get(chunk_id)
            if not row:
                continue
            hits.append(
                SearchHit(
                    chunk_id=row["chunk_id"],
                    doc_id=row["doc_id"],
                    title=row["title"],
                    section=row["section"] or "",
                    text=row["text"],
                    source_url=row["source_url"] or "",
                    license=row["license"] or "",
                    score=score,
                )
            )
        return hits


def _fts_match_query(query: str) -> str:
    import re

    terms = re.findall(r"[A-Za-z0-9_]+", query)
    if not terms:
        return ""
    return " OR ".join('"' + t + '"' for t in terms)
