"""Deterministic evaluation metrics.

These methods are lexical, not an LLM-as-judge. They are reproducible in CI
and will miss some valid paraphrases. See docs in the README Results section.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from audit_rag.citations.format import parse_citation_markers
from audit_rag.generate.answer import REFUSAL_TEXT, Answer
from audit_rag.index.store import SearchHit

_STOP = {
    "a", "an", "the", "and", "or", "of", "to", "in", "on", "for", "is", "are",
    "was", "were", "be", "as", "by", "with", "that", "this", "it", "from",
    "at", "if", "can", "what", "why", "how", "does", "do", "about", "into",
}


def content_terms(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9_]+", text.lower()) if t not in _STOP and len(t) > 2}


def claim_sentences(text: str) -> list[str]:
    parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", text.strip()) if p.strip()]
    merged: list[str] = []
    for part in parts:
        # A leftover "[1:chunk#c0]" after a period belongs to the previous claim.
        if merged and parse_citation_markers(part) and not content_terms(re.sub(r"\[\d+:[^\]]+\]", " ", part)):
            merged[-1] = merged[-1].rstrip() + " " + part
            continue
        merged.append(part)
    return [p for p in merged if len(content_terms(p)) >= 3]


def chunk_supports_claim(claim: str, chunk_text: str, *, min_overlap: int = 3) -> bool:
    """A claim is supported if enough of its content tokens appear in the chunk.

    This is a bag-of-tokens overlap test. It does not score semantic entailment.
    """
    terms = content_terms(re.sub(r"\[\d+:[^\]]+\]", " ", claim))
    if not terms:
        return False
    overlap = terms & content_terms(chunk_text)
    need = min(min_overlap, max(1, len(terms) // 2))
    return len(overlap) >= need


@dataclass
class RetrievalScores:
    recall_at_k_all: float  # questions where ALL gold chunks are in top k
    mean_recall_at_k: float  # macro average of |hit ∩ gold| / |gold|
    mrr: float
    doc_recall_at_k: float  # questions where at least one gold doc is in top k
    n_scored: int


def retrieval_scores(
    records: list[dict],
    *,
    k: int,
) -> RetrievalScores:
    rec_all = []
    rec_mean = []
    rr = []
    doc_hit = []
    n = 0
    for rec in records:
        if rec.get("must_refuse"):
            continue
        gold = list(rec.get("gold_chunk_ids") or [])
        gold_docs = list(rec.get("gold_doc_ids") or [])
        retrieved = list(rec.get("retrieved_chunk_ids") or [])[:k]
        if not gold and not gold_docs:
            continue
        n += 1
        if gold:
            found = [c for c in gold if c in retrieved]
            rec_all.append(1.0 if len(found) == len(gold) else 0.0)
            rec_mean.append(len(found) / len(gold))
            ranks = [retrieved.index(c) + 1 for c in gold if c in retrieved]
            rr.append(1.0 / min(ranks) if ranks else 0.0)
        else:
            rec_all.append(0.0)
            rec_mean.append(0.0)
            rr.append(0.0)
        retrieved_docs = list(rec.get("retrieved_doc_ids") or [])[:k]
        doc_hit.append(1.0 if (set(gold_docs) & set(retrieved_docs)) else 0.0)
    if n == 0:
        return RetrievalScores(0, 0, 0, 0, 0)
    return RetrievalScores(
        recall_at_k_all=sum(rec_all) / n,
        mean_recall_at_k=sum(rec_mean) / n,
        mrr=sum(rr) / n,
        doc_recall_at_k=sum(doc_hit) / n,
        n_scored=n,
    )


def citation_accuracy(answer: Answer, hits: list[SearchHit]) -> tuple[float, list[dict]]:
    """Cited chunk IDs must exist in the retrieved set and support the claim.

    Refusal answers with no citations score as 1.0 (nothing was mis-cited).
    """
    if answer.refused:
        markers = parse_citation_markers(answer.text)
        return (1.0 if not markers else 0.0), []
    claims = claim_sentences(answer.text)
    if not claims:
        return 0.0, [{"error": "no claim sentences"}]
    by_id = {h.chunk_id: h for h in hits}
    retrieved = set(by_id)
    details = []
    ok = 0
    for claim in claims:
        markers = parse_citation_markers(claim)
        if not markers:
            details.append({"claim": claim, "ok": False, "reason": "missing citation"})
            continue
        claim_ok = True
        reason = "ok"
        for _, chunk_id in markers:
            if chunk_id not in retrieved:
                claim_ok = False
                reason = f"citation not in retrieved set: {chunk_id}"
                break
            if not chunk_supports_claim(claim, by_id[chunk_id].text):
                claim_ok = False
                reason = f"chunk does not lexically support claim: {chunk_id}"
                break
        if claim_ok:
            ok += 1
        details.append({"claim": claim, "ok": claim_ok, "reason": reason})
    return ok / len(claims), details


def faithfulness(answer: Answer, hits: list[SearchHit]) -> tuple[float, list[dict]]:
    """Fraction of answer claims supported by at least one cited chunk.

    Same lexical support test as citation accuracy. Documented as a simple
    overlap method, not a semantic faithfulness judge.
    """
    return citation_accuracy(answer, hits)


def is_refusal(text: str, refused_flag: bool) -> bool:
    if refused_flag:
        return True
    lowered = text.lower()
    needles = [
        REFUSAL_TEXT[:40].lower(),
        "don't have enough evidence",
        "does not appear to contain",
        "not in the knowledge base",
        "insufficient evidence",
    ]
    return any(n in lowered for n in needles)


def refusal_accuracy(records: list[dict]) -> tuple[float, dict]:
    tp = fp = tn = fn = 0
    for rec in records:
        must = bool(rec.get("must_refuse"))
        did = bool(rec.get("did_refuse"))
        if must and did:
            tp += 1
        elif must and not did:
            fn += 1
        elif not must and did:
            fp += 1
        else:
            tn += 1
    n = tp + fp + tn + fn
    acc = (tp + tn) / n if n else 0.0
    return acc, {"true_refuse": tp, "false_refuse": fp, "true_answer": tn, "false_answer": fn, "n": n}
