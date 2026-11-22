"""Run retrieval + generation over the golden set and write a JSON report."""

from __future__ import annotations

import json
import time
from pathlib import Path

from audit_rag.chunk.chunker import chunk_document
from audit_rag.embeddings.base import get_embedder
from audit_rag.eval.dashboard import render_dashboard
from audit_rag.eval.metrics import (
    citation_accuracy,
    faithfulness,
    is_refusal,
    refusal_accuracy,
    retrieval_scores,
)
from audit_rag.generate.base import generate
from audit_rag.index.store import IndexStore
from audit_rag.ingest.loader import load_corpus
from audit_rag.paths import project_root
from audit_rag.rerank.base import get_reranker
from audit_rag.retrieve.hybrid import hybrid_search


def load_golden(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def run_harness(
    *,
    golden_path: Path | None = None,
    index_path: Path | None = None,
    corpus_dir: Path | None = None,
    k: int = 10,
    rebuild: bool = True,
    tag: str = "latest",
) -> dict:
    root = project_root()
    golden_path = golden_path or (root / "evals" / "golden_seed.jsonl")
    index_path = index_path or (root / "data" / "indexes" / "eval.db")
    corpus_dir = corpus_dir or (root / "data" / "corpus")
    gold = load_golden(golden_path)
    embedder = get_embedder()
    docs = load_corpus(corpus_dir)
    chunks = []
    for doc in docs:
        chunks.extend(chunk_document(doc.text, doc_id=doc.doc_id, metadata=doc.metadata))

    store = IndexStore(index_path)
    if rebuild or store.get_meta("embedder") != embedder.kind:
        store.rebuild(docs, chunks, embedder)

    records = []
    t0 = time.perf_counter()
    for item in gold:
        q = item["question"]
        t_ret = time.perf_counter()
        hits = hybrid_search(store, embedder, q, k=k, rerank=True)
        retrieve_ms = (time.perf_counter() - t_ret) * 1000
        t_gen = time.perf_counter()
        answer = generate(q, hits)
        generate_ms = (time.perf_counter() - t_gen) * 1000
        cite_score, cite_detail = citation_accuracy(answer, hits)
        faith_score, faith_detail = faithfulness(answer, hits)
        records.append(
            {
                "id": item.get("id"),
                "question": q,
                "question_type": item.get("question_type"),
                "must_refuse": bool(item.get("must_refuse")),
                "gold_chunk_ids": item.get("proposed_chunk_ids") or [],
                "gold_doc_ids": item.get("proposed_doc_ids") or [],
                "retrieved_chunk_ids": [h.chunk_id for h in hits],
                "retrieved_doc_ids": [h.doc_id for h in hits],
                "answer": answer.text,
                "did_refuse": is_refusal(answer.text, answer.refused),
                "generator": answer.generator,
                "used_chunk_ids": answer.used_chunk_ids,
                "citation_accuracy": cite_score,
                "faithfulness": faith_score,
                "citation_detail": cite_detail,
                "retrieve_ms": round(retrieve_ms, 2),
                "generate_ms": round(generate_ms, 2),
                "injection_flags": [
                    {"chunk_id": cid, "rule": flag.rule, "excerpt": flag.excerpt}
                    for cid, flag in answer.injection_flags
                ],
            }
        )
    elapsed_ms = (time.perf_counter() - t0) * 1000
    store.close()

    answerable = [r for r in records if not r["must_refuse"]]
    r5 = retrieval_scores(records, k=5)
    r10 = retrieval_scores(records, k=10)
    refuse_acc, refuse_break = refusal_accuracy(records)
    cited = [r["citation_accuracy"] for r in records if not r["did_refuse"]]
    faith = [r["faithfulness"] for r in records if not r["did_refuse"]]
    report = {
        "schema": "audit-rag-eval/v1",
        "method": {
            "embedder": embedder.kind,
            "generator": records[0]["generator"] if records else "extractive",
            "retriever": "hybrid BM25+sqlite-vec weighted RRF with optional query expansion; reranker from AUDIT_RAG_RERANKER",
            "recall_at_k_all": "Fraction of answerable questions where every gold chunk_id appears in the top k retrieved chunks.",
            "mean_recall_at_k": "Macro-average of |gold ∩ retrieved@k| / |gold| on answerable questions.",
            "mrr": "Mean reciprocal rank of the first gold chunk in the retrieved list, on answerable questions.",
            "doc_recall_at_k": "Fraction of answerable questions where at least one gold doc_id appears in the top k.",
            "citation_accuracy": "On non-refusal answers, each claim sentence must have a [rank:chunk_id] marker, the chunk must be in the retrieved set, and at least half of the claim's content tokens (min 3, or all if fewer) must appear in the cited chunk. Refusals with no citations score 1.0.",
            "faithfulness": "Same lexical support test as citation accuracy. This is not an LLM-as-judge score and can miss valid paraphrases.",
            "refusal_accuracy": "(true refusals + true answers) / N, using must_refuse from the golden set.",
            "refusal_rule": "The extractive generator also refuses when a proper-noun or identifier token from the question is missing from the retrieved chunks, or when a question asks for an exact dollar/amount loss and the candidate answer has no currency figure. This is lexical, not an LLM judge.",
        },
        "settings": {
            "k": k,
            "golden": str(golden_path.relative_to(root).as_posix()) if golden_path.is_relative_to(root) else golden_path.as_posix(),
            "document_count": len(docs),
            "chunk_count": len(chunks),
            "question_count": len(records),
            "answerable_count": len(answerable),
            "expand": True,
            "reranker": get_reranker().kind,
        },
        "metrics": {
            "recall@5_all": round(r5.recall_at_k_all, 4),
            "mean_recall@5": round(r5.mean_recall_at_k, 4),
            "mrr@5": round(r5.mrr, 4),
            "doc_recall@5": round(r5.doc_recall_at_k, 4),
            "recall@10_all": round(r10.recall_at_k_all, 4),
            "mean_recall@10": round(r10.mean_recall_at_k, 4),
            "mrr@10": round(r10.mrr, 4),
            "doc_recall@10": round(r10.doc_recall_at_k, 4),
            "citation_accuracy": round(sum(cited) / len(cited), 4) if cited else 0.0,
            "faithfulness": round(sum(faith) / len(faith), 4) if faith else 0.0,
            "refusal_accuracy": round(refuse_acc, 4),
            "refusal_breakdown": refuse_break,
            "n_answerable": r10.n_scored,
            "n_non_refusal_answers": len(cited),
            "elapsed_ms": round(elapsed_ms, 1),
        },
        "records": records,
    }
    out_dir = root / "evals" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    report_name = "latest.json" if tag == "latest" else f"{tag}.json"
    dash_name = "dashboard.html" if tag == "latest" else f"dashboard-{tag}.html"
    latest = out_dir / report_name
    latest.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    render_dashboard(report, out_dir / dash_name)
    report["_outputs"] = {"json": str(latest.as_posix()), "dashboard": str((out_dir / dash_name).as_posix())}
    return report
