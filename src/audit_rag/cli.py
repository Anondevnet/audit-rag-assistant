"""Command-line interface: ingest and search."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from audit_rag.chunk.chunker import chunk_document
from audit_rag.citations.format import format_search_results
from audit_rag.embeddings.base import get_embedder
from audit_rag.index.store import IndexStore
from audit_rag.ingest.loader import load_corpus
from audit_rag.paths import project_root
from audit_rag.generate.base import generate
from audit_rag.retrieve.hybrid import hybrid_search


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="audit-rag",
        description="License-cleared audit-report RAG assistant (Milestone 2: retrieval, cited answers, evals).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_ingest = sub.add_parser("ingest", help="Chunk the corpus and build the SQLite index.")
    p_ingest.add_argument("--corpus", type=Path, default=None, help="Corpus directory (*.md).")
    p_ingest.add_argument("--index", type=Path, default=None, help="Output SQLite path.")
    p_ingest.add_argument("--embedder", default=None, help="hashing, ollama, or auto.")

    p_search = sub.add_parser("search", help="Hybrid search with citations.")
    p_search.add_argument("query", help="Natural-language query.")
    p_search.add_argument("--index", type=Path, default=None, help="SQLite index path.")
    p_search.add_argument("--k", type=int, default=5, help="Number of chunks to return.")
    p_search.add_argument("--embedder", default=None, help="Must match the embedder used at ingest.")
    p_search.add_argument("--no-rerank", action="store_true")

    p_ask = sub.add_parser("ask", help="Retrieve, apply injection guards, and generate a cited answer.")
    p_ask.add_argument("query", help="Natural-language query.")
    p_ask.add_argument("--index", type=Path, default=None, help="SQLite index path.")
    p_ask.add_argument("--k", type=int, default=8, help="Number of chunks to retrieve.")
    p_ask.add_argument("--embedder", default=None, help="Must match the embedder used at ingest.")
    p_ask.add_argument("--generator", default=None, help="extractive (default, CI) or ollama.")

    args = parser.parse_args(argv)
    if args.command == "ingest":
        return _cmd_ingest(args)
    if args.command == "search":
        return _cmd_search(args)
    if args.command == "ask":
        return _cmd_ask(args)
    parser.error(f"unknown command {args.command}")
    return 2


def _resolve_index(path: Path | None) -> Path:
    if path:
        return path
    env = os.environ.get("AUDIT_RAG_INDEX")
    root = project_root()
    return Path(env) if env else root / "data" / "indexes" / "audit.db"


def _cmd_ingest(args: argparse.Namespace) -> int:
    root = project_root()
    corpus = args.corpus or (root / "data" / "corpus")
    index_path = _resolve_index(args.index)
    docs = load_corpus(corpus)
    if not docs:
        raise SystemExit(f"No markdown documents in {corpus}")
    chunks = []
    for doc in docs:
        chunks.extend(chunk_document(doc.text, doc_id=doc.doc_id, metadata=doc.metadata))
    embedder = get_embedder(args.embedder)
    with IndexStore(index_path) as store:
        store.rebuild(docs, chunks, embedder)
        vec = "sqlite-vec" if store.vec_enabled else "numpy-fallback"
        print(
            f"Indexed {len(docs)} documents / {len(chunks)} chunks "
            f"with {embedder.kind} embeddings (dim={embedder.dim}, vectors={vec}) "
            f"at {index_path}"
        )
    return 0


def _cmd_search(args: argparse.Namespace) -> int:
    index_path = _resolve_index(args.index)
    if not index_path.exists():
        raise SystemExit(f"Index not found: {index_path}. Run `audit-rag ingest` first.")
    embedder = get_embedder(args.embedder)
    with IndexStore(index_path) as store:
        indexed_kind = store.get_meta("embedder")
        if indexed_kind and indexed_kind != embedder.kind:
            raise SystemExit(
                f"Embedder mismatch: index was built with {indexed_kind!r}, "
                f"but the current embedder is {embedder.kind!r}. "
                "Re-ingest or set AUDIT_RAG_EMBEDDER to match."
            )
        hits = hybrid_search(
            store,
            embedder,
            args.query,
            k=args.k,
            rerank=not args.no_rerank,
        )
    print(format_search_results(args.query, hits), end="")
    return 0


def _cmd_ask(args: argparse.Namespace) -> int:
    index_path = _resolve_index(args.index)
    if not index_path.exists():
        raise SystemExit(f"Index not found: {index_path}. Run `audit-rag ingest` first.")
    embedder = get_embedder(args.embedder)
    with IndexStore(index_path) as store:
        indexed_kind = store.get_meta("embedder")
        if indexed_kind and indexed_kind != embedder.kind:
            raise SystemExit(
                f"Embedder mismatch: index was built with {indexed_kind!r}, "
                f"but the current embedder is {embedder.kind!r}."
            )
        hits = hybrid_search(store, embedder, args.query, k=args.k, rerank=True)
        answer = generate(args.query, hits, name=args.generator)
    print(format_search_results(args.query, hits), end="")
    print("---")
    print("Generator:", answer.generator)
    print("Refused:", answer.refused)
    if answer.injection_flags:
        print("Injection flags:")
        for chunk_id, flag in answer.injection_flags:
            print(f"  {chunk_id}: {flag.rule}")
    print()
    print(answer.text)
    return 0
