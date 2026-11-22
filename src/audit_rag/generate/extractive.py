"""Deterministic extractive answers for CI and machines without a chat model.

Sentences are copied from retrieved (and guarded) chunks. Every included
sentence is tagged with a [rank:chunk_id] citation. If no sentence has
enough lexical overlap with the question, the generator refuses.
"""

from __future__ import annotations

import re

from audit_rag.citations.format import citation_marker
from audit_rag.generate.answer import REFUSAL_TEXT, Answer
from audit_rag.guardrails.scanner import sanitize_hits
from audit_rag.index.store import SearchHit

_STOP = {
    "a", "an", "the", "and", "or", "of", "to", "in", "on", "for", "is", "are",
    "was", "were", "be", "as", "by", "with", "that", "this", "it", "from",
    "at", "if", "can", "what", "why", "how", "does", "do", "about", "into",
}


def _expand_token(token: str) -> set[str]:
    """Split mixed alphanumeric tokens ('erc20' -> erc, 20, erc20)."""
    parts = {token}
    for piece in re.findall(r"[a-z]+|\d+", token):
        if len(piece) > 1:
            parts.add(piece)
    return parts


def _terms(text: str) -> set[str]:
    out: set[str] = set()
    for token in re.findall(r"[a-z0-9_]+", text.lower()):
        for piece in _expand_token(token):
            if piece not in _STOP and len(piece) > 1:
                out.add(piece)
    return out


def _overlap(query_terms: set[str], sent_terms: set[str]) -> int:
    """Count term matches, including prefix/substring matches for longer tokens.

    This lets 'reentrancy' match 'ReentrancyGuard' without stemming.
    """
    score = 0
    for qt in query_terms:
        if qt in sent_terms or (qt.endswith("s") and qt[:-1] in sent_terms) or (qt + "s") in sent_terms:
            score += 1
            continue
        if len(qt) >= 4 and any(qt in st for st in sent_terms if len(st) >= len(qt)):
            score += 1
    return score


def _enough_overlap(overlap: int, query_terms: set[str], sent_terms: set[str], min_overlap: int) -> bool:
    if overlap >= min_overlap:
        return True
    # A single distinctive term (length >= 5) is enough to keep a sentence.
    if overlap >= 1:
        for qt in query_terms:
            if len(qt) >= 5 and (
                qt in sent_terms
                or any(qt in st for st in sent_terms if len(st) >= len(qt))
            ):
                return True
    return False



_QUESTION_WORDS = {"what", "why", "how", "who", "when", "where", "which"}
_QUANT_QUESTION = re.compile(
    r"\b((exact|dollar)\s+(dollar\s+)?loss|dollar loss|how much\b|amount lost)\b",
    re.I,
)
_QUANT_ANSWER = re.compile(
    r"(\$\s?\d|\d[\d,]*(\.\d+)?\s*(usd|dollars?)\b|\b(usd|dollars?)\s*\d)",
    re.I,
)


def _token_set(text: str) -> set[str]:
    out: set[str] = set()
    for token in re.findall(r"[a-z0-9_]+", text.lower()):
        out |= _expand_token(token)
    return out


def _term_in_tokens(term: str, tokens: set[str]) -> bool:
    if term in tokens:
        return True
    if len(term) >= 5 and any(term in tok for tok in tokens if len(tok) >= len(term)):
        return True
    return False


def proper_entities(query: str) -> set[str]:
    """Named entities and identifiers the answer is expected to mention.

    Mid-question capitalized words, mixed-case tokens, and digit-bearing
    identifiers (years, SWC ids) are treated as required evidence, not as
    generic English. The first question word is ignored.
    """
    words = re.findall(r"[A-Za-z0-9_]+", query)
    entities: set[str] = set()
    for i, word in enumerate(words):
        if i == 0 and word.lower() in _QUESTION_WORDS:
            continue
        if any(ch.isdigit() for ch in word) and len(word) >= 3:
            entities.add(word.lower())
        elif sum(1 for ch in word if ch.isupper()) >= 2 and len(word) >= 3:
            entities.add(word.lower())
        elif i > 0 and word[0].isupper() and len(word) >= 3:
            entities.add(word.lower())
    return entities


def evidence_is_insufficient(query: str, hits: list[SearchHit], answer_text: str) -> str | None:
    """Return a refusal reason if retrieved text cannot support the question.

    Method (lexical, documented):
    1. Every proper-noun / identifier token in the question must appear in
       the retrieved (and sanitized) hits.
    2. Questions that ask for an exact dollar/amount loss must have a
       numeric currency quantity in the candidate answer. Attribution
       footers or related historical links are not enough.
    """
    ev_tokens: set[str] = set()
    for hit in hits:
        ev_tokens |= _token_set(hit.text)
    missing = [term for term in sorted(proper_entities(query)) if not _term_in_tokens(term, ev_tokens)]
    if missing:
        return "retrieved chunks do not mention required question entities: " + ", ".join(missing)
    if _QUANT_QUESTION.search(query) and not _QUANT_ANSWER.search(answer_text or ""):
        return "question asks for a quantitative loss or amount, but no currency figure is in the candidate evidence"
    return None


def _sentences(text: str) -> list[str]:
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    # keep markdown headings from becoming empty
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    out: list[str] = []
    for part in parts:
        s = re.sub(r"\s+", " ", part).strip()
        if len(_terms(s)) >= 4:
            out.append(s)
    return out


def extractive_generate(query: str, hits: list[SearchHit], *, min_overlap: int = 2) -> Answer:
    clean, flags = sanitize_hits(list(hits))
    q_terms = _terms(query)
    scored: list[tuple[float, str, SearchHit, int]] = []
    for rank, hit in enumerate(clean, start=1):
        for sent in _sentences(hit.text):
            sent_terms = _terms(sent)
            overlap = _overlap(q_terms, sent_terms)
            if not _enough_overlap(overlap, q_terms, sent_terms, min_overlap):
                continue
            score = overlap / max(len(q_terms), 1)
            scored.append((score, sent, hit, rank))
    scored.sort(key=lambda item: item[0], reverse=True)

    picked: list[tuple[str, SearchHit, int]] = []
    seen_text: set[str] = set()
    seen_chunks: set[str] = set()
    for score, sent, hit, rank in scored:
        key = re.sub(r"\s+", " ", sent.lower())
        if key in seen_text:
            continue
        # prefer diversity across chunks, allow a second sentence from the same chunk
        if hit.chunk_id in seen_chunks and sum(1 for _, h, _ in picked if h.chunk_id == hit.chunk_id) >= 1:
            continue
        picked.append((sent, hit, rank))
        seen_text.add(key)
        seen_chunks.add(hit.chunk_id)
        if len(picked) >= 4:
            break

    # If a chunk already contributed a query-overlap sentence, add one more
    # cited sentence from the same chunk so remediations that sit next to a
    # keyword mention can be included.
    if picked and len(picked) < 4:
        used_ids = {hit.chunk_id for _, hit, _ in picked}
        for rank, hit in enumerate(clean, start=1):
            if hit.chunk_id not in used_ids or len(picked) >= 4:
                continue
            already = {
                re.sub(r"\s+", " ", sent.lower())
                for sent, h, _ in picked
                if h.chunk_id == hit.chunk_id
            }
            extras = [
                sent
                for sent in _sentences(hit.text)
                if re.sub(r"\s+", " ", sent.lower()) not in already
            ]
            extras.sort(key=lambda sent: len(_terms(sent)), reverse=True)
            if not extras:
                continue
            sent = extras[0]
            key = re.sub(r"\s+", " ", sent.lower())
            if key in seen_text:
                continue
            picked.append((sent, hit, rank))
            seen_text.add(key)

    if not picked:
        return Answer(
            text=REFUSAL_TEXT,
            refused=True,
            reason="no retrieved sentence had enough lexical overlap with the question",
            generator="extractive",
            injection_flags=flags,
        )

    draft = " ".join(sent for sent, _, _ in picked)
    reason = evidence_is_insufficient(query, clean, draft)
    if reason:
        return Answer(
            text=REFUSAL_TEXT,
            refused=True,
            reason=reason,
            generator="extractive",
            injection_flags=flags,
        )

    lines: list[str] = []
    used: list[str] = []
    citations: list[str] = []
    for sent, hit, rank in picked:
        marker = citation_marker(rank, hit.chunk_id)
        # Put the marker before trailing punctuation so citation metrics
        # keep the claim and its citation in the same sentence.
        if sent and sent[-1] in ".!?":
            lines.append(f"{sent[:-1]} {marker}{sent[-1]}")
        else:
            lines.append(f"{sent} {marker}")
        if hit.chunk_id not in used:
            used.append(hit.chunk_id)
            citations.append(marker)
    return Answer(
        text=" ".join(lines),
        refused=False,
        reason="extractive sentences from retrieved chunks",
        citations=citations,
        used_chunk_ids=used,
        generator="extractive",
        injection_flags=flags,
    )
