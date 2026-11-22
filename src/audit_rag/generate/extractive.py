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


_CONTENT_SECTIONS = ("description", "remediation", "mitigation", "attack", "vulnerability")
_LOW_SECTIONS = (
    "relationships", "references", "source notice", "samples", "example files",
)
_HEADING_ONLY = {
    "description", "remediation", "mitigation", "mitigations", "references",
    "relationships", "samples", "examples", "source notice", "attack",
    "attack scenario", "attack scenarios",
}


def clean_markdown(text: str) -> str:
    """Strip markdown markup so extractive sentences read as prose."""
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    previous = None
    while previous != text:
        previous = text
        text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", text)
        text = re.sub(r"\[([^\[\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"(\*\*|__)(.*?)\1", r"\2", text)
    text = re.sub(r"(?<!\w)_(?!\s)(.+?)(?<!\s)_(?!\w)", r"\1", text)
    # Headings become breaks even when a prior section is glued mid-line in a chunk.
    text = re.sub(r"(^|\n)\s*#{1,6}\s+", r"\1", text)
    text = re.sub(r"\s+#{1,6}\s+", "\n", text)
    text = re.sub(
        r"(^|\n)\s*(Description|Remediation|Mitigations?|References|Relationships|Samples|Examples|Source Notice|Attack Scenarios?|Attack)\s+",
        r"\1",
        text,
        flags=re.I,
    )
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.M)
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.M)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def _norm_sentence(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text.lower())).strip()


def _is_boilerplate(sentence: str, hit: SearchHit | None = None) -> bool:
    """Drop title-only lines, relationship catalogs, and reference lists."""
    text = sentence.strip()
    if not text:
        return True
    low = text.lower()
    if low.rstrip(":") in _HEADING_ONLY:
        return True
    title = (hit.title if hit else "") or ""
    if title and _norm_sentence(text) == _norm_sentence(title):
        return True
    if re.match(r"^swc-\d+", low) and ":" in text and len(_terms(text)) <= 10:
        return True
    if "cwe-" in low or "ethtrust" in low or "security levels" in low:
        return True
    if "](" in text or re.search(r"https?://", text):
        return True
    if "adapted from" in low or "licensed under" in low or "source notice" in low:
        return True
    if re.search(r"\b(documentation|best practices|blog)\b", low) and len(_terms(text)) < 12:
        return True
    if low.endswith(":") and len(_terms(text)) <= 5:
        return True
    section = (hit.section if hit else "") or ""
    if any(name in section.lower() for name in _LOW_SECTIONS):
        # Keep a real prose sentence even in a low-priority section; drop lists.
        if len(_terms(text)) < 8 or text.count(",") >= 2 and " and " not in low:
            return True
    return False


def _section_weight(hit: SearchHit) -> float:
    section = (hit.section or "").lower()
    if any(name in section for name in _CONTENT_SECTIONS):
        return 1.35
    if any(name in section for name in _LOW_SECTIONS) or section.endswith(".sol"):
        return 0.55
    return 1.0


_ABBREVIATIONS = ("a.k.a.", "e.g.", "i.e.", "etc.", "vs.", "cf.")
_ABBR_DOT = "\u2044"


def _unwrap_lines(text: str) -> str:
    """Join soft-wrapped lines so a sentence split by a newline stays one sentence."""
    pieces: list[str] = []
    buf = ""
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            if buf:
                pieces.append(buf)
                buf = ""
            continue
        if not buf:
            buf = line
        elif line.startswith(("#", "-", "*", "+")):
            pieces.append(buf)
            buf = line
        elif buf[-1] in ",;-" or (
            buf[-1] not in ".!?"
            and line[0].islower()
            and not re.match(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+", line)
        ):
            # Soft-wrapped continuation (often starts lowercase), but not a new
            # identifier sentence such as "tx.origin is a global variable...".
            buf = f"{buf} {line}"
        else:
            pieces.append(buf)
            buf = line
    if buf:
        pieces.append(buf)
    return "\n".join(pieces)


def _protect_abbreviations(text: str) -> str:
    out = text
    for abbr in _ABBREVIATIONS:
        out = re.sub(re.escape(abbr), abbr.replace(".", _ABBR_DOT), out, flags=re.I)
    return out


def _restore_abbreviations(text: str) -> str:
    return text.replace(_ABBR_DOT, ".")


def _strip_title_prefix(sentence: str, hit: SearchHit | None) -> str:
    if hit is None or not (hit.title or "").strip():
        return sentence
    title = hit.title.strip()
    if sentence.lower().startswith(title.lower()):
        rest = sentence[len(title):].lstrip(" \t:-—–")
        if rest:
            return rest
    return sentence


def _starts_like_prose(sentence: str) -> bool:
    """Drop mid-chunk fragments that begin in the middle of a sentence."""
    text = sentence.lstrip()
    if not text:
        return False
    if text[0].isupper() or text[0].isdigit() or text[0] in "\"'`(":
        return True
    if re.match(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+\b", text):
        return True
    if re.match(r"^(delegatecall|require|revert|assert|pragma|function|address)\b", text, re.I):
        return True
    return False


def _sentences(text: str, hit: SearchHit | None = None) -> list[str]:
    text = _unwrap_lines(clean_markdown(text))
    text = _protect_abbreviations(text)
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    out: list[str] = []
    for part in parts:
        sent = _restore_abbreviations(re.sub(r"\s+", " ", part).strip(" \t-•"))
        sent = _strip_title_prefix(sent, hit)
        if not sent:
            continue
        if not _starts_like_prose(sent):
            continue
        if sent[-1] not in ".!?":
            # Headings and bullets often have no period; only keep if they are prose.
            if _is_boilerplate(sent, hit) or len(_terms(sent)) < 8:
                continue
        if len(_terms(sent)) < 4:
            continue
        if _is_boilerplate(sent, hit):
            continue
        out.append(sent)
    return out


def _dedupe_key(sentence: str) -> str:
    return _norm_sentence(sentence)




def _is_duplicate(key: str, seen_text: set[str]) -> bool:
    if key in seen_text:
        return True
    return any(
        key in seen or seen in key
        for seen in seen_text
        if min(len(key), len(seen)) >= 20
    )


def extractive_generate(query: str, hits: list[SearchHit], *, min_overlap: int = 2) -> Answer:
    clean, flags = sanitize_hits(list(hits))
    q_terms = _terms(query)
    scored: list[tuple[float, int, str, SearchHit, int]] = []
    for rank, hit in enumerate(clean, start=1):
        for sent_i, sent in enumerate(_sentences(hit.text, hit)):
            # Identifier lookups like "What is SWC-128 about?" mention the id in
            # the document title, not always again in the body sentence.
            sent_terms = _terms(sent) | _terms(hit.title or "") | _terms(hit.doc_id or "")
            overlap = _overlap(q_terms, sent_terms)
            if not _enough_overlap(overlap, q_terms, sent_terms, min_overlap):
                continue
            score = (overlap / max(len(q_terms), 1)) * _section_weight(hit)
            scored.append((score, sent_i, sent, hit, rank))

    content = [item for item in scored if _section_weight(item[3]) >= 1.2]
    other = [item for item in scored if _section_weight(item[3]) < 1.2]
    # Content-section prose is shown in document order so a definition is not
    # displaced by a later sentence that merely repeats the query terms.
    content.sort(key=lambda item: (item[4], item[1]))
    other.sort(key=lambda item: item[0], reverse=True)

    picked: list[tuple[str, SearchHit, int]] = []
    seen_text: set[str] = set()

    def _try_add(sent: str, hit: SearchHit, rank: int, *, limit: int) -> bool:
        if len(picked) >= 4:
            return False
        key = _dedupe_key(sent)
        if _is_duplicate(key, seen_text):
            return False
        same = sum(1 for _, existing, _ in picked if existing.chunk_id == hit.chunk_id)
        if same >= limit:
            return False
        picked.append((sent, hit, rank))
        seen_text.add(key)
        return True

    leading_doc = content[0][3].doc_id if content else None
    for _score, _sent_i, sent, hit, rank in content:
        if leading_doc and hit.doc_id != leading_doc:
            continue
        _try_add(sent, hit, rank, limit=3)
    preferred_docs = {hit.doc_id for _sent, hit, _rank in picked}
    if leading_doc:
        preferred_docs.add(leading_doc)
    same_doc = [item for item in other if item[3].doc_id in preferred_docs]
    for _score, _sent_i, sent, hit, rank in same_doc:
        _try_add(sent, hit, rank, limit=2)
    # Additional documents fill remaining slots after the leading doc (and any
    # same-document remediation) has been given first shot.
    if len(picked) < 4:
        for _score, _sent_i, sent, hit, rank in content:
            if hit.doc_id in preferred_docs:
                continue
            _try_add(sent, hit, rank, limit=3)
    if len(picked) < 3:
        distant = [item for item in other if item[3].doc_id not in preferred_docs]
        for _score, _sent_i, sent, hit, rank in distant:
            _try_add(sent, hit, rank, limit=1)

    # If a chunk already contributed a query-overlap sentence, add one more
    # cited sentence from the same chunk so remediations that sit next to a
    # keyword mention can be included.
    if picked and len(picked) < 4:
        used_ids = {hit.chunk_id for _, hit, _ in picked}
        for rank, hit in enumerate(clean, start=1):
            if hit.chunk_id not in used_ids or len(picked) >= 4:
                continue
            already = {
                _dedupe_key(sent)
                for sent, h, _ in picked
                if h.chunk_id == hit.chunk_id
            }
            extras = [
                sent
                for sent in _sentences(hit.text, hit)
                if _dedupe_key(sent) not in already and _dedupe_key(sent) not in seen_text
            ]
            extras.sort(key=lambda sent: len(_terms(sent)), reverse=True)
            if not extras:
                continue
            sent = extras[0]
            key = _dedupe_key(sent)
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

    def _order(item: tuple[str, SearchHit, int]) -> tuple[int, int]:
        sent, hit, rank = item
        section = (hit.section or "").lower()
        if "description" in section:
            bucket = 0
        elif "attack" in section:
            bucket = 1
        elif "remediation" in section or "mitigation" in section:
            bucket = 2
        else:
            bucket = 3
        return (bucket, rank)

    picked.sort(key=_order)

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
