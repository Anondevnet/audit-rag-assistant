"""Heading-aware markdown chunking with a token budget and overlap."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
FENCE_RE = re.compile(r"(^```.*?\n.*?^```\s*$)", re.MULTILINE | re.DOTALL)

DEFAULT_MAX_TOKENS = 700
DEFAULT_OVERLAP_TOKENS = 100


def estimate_tokens(text: str) -> int:
    """Whitespace-token estimate. Good enough for a budget, not a tokenizer."""
    return len(text.split()) if text.strip() else 0


def parse_front_matter(text: str) -> tuple[dict[str, str], str]:
    match = FRONT_MATTER_RE.match(text)
    if not match:
        return {}, text
    meta: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()
    body = text[match.end() :]
    return meta, body


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    ordinal: int
    section: str
    text: str
    token_count: int
    metadata: dict[str, str] = field(default_factory=dict)

    @property
    def title(self) -> str:
        return self.metadata.get("title") or self.doc_id


def chunk_document(
    text: str,
    *,
    doc_id: str,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    overlap_tokens: int = DEFAULT_OVERLAP_TOKENS,
    metadata: dict[str, str] | None = None,
) -> list[Chunk]:
    if max_tokens <= 0:
        raise ValueError("max_tokens must be positive")
    if overlap_tokens < 0 or overlap_tokens >= max_tokens:
        raise ValueError("overlap_tokens must be in [0, max_tokens)")

    parsed_meta, body = parse_front_matter(text)
    meta = {**parsed_meta, **(metadata or {})}
    doc_id = meta.get("id") or doc_id
    sections = _split_sections(body)
    raw_parts: list[tuple[str, str]] = []
    for heading, content in sections:
        raw_parts.extend((heading, piece) for piece in _split_long(content, max_tokens))

    merged = _apply_overlap(raw_parts, max_tokens, overlap_tokens)
    chunks: list[Chunk] = []
    for i, (section, piece) in enumerate(merged):
        piece = piece.strip()
        if not piece:
            continue
        chunk_id = f"{doc_id}#c{i}"
        chunks.append(
            Chunk(
                chunk_id=chunk_id,
                doc_id=doc_id,
                ordinal=i,
                section=section,
                text=piece,
                token_count=estimate_tokens(piece),
                metadata=dict(meta),
            )
        )
    return chunks


def _split_sections(body: str) -> list[tuple[str, str]]:
    matches = list(HEADING_RE.finditer(body))
    if not matches:
        return [("body", body.strip())]
    sections: list[tuple[str, str]] = []
    if matches[0].start() > 0:
        preface = body[: matches[0].start()].strip()
        if preface:
            sections.append(("preface", preface))
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        heading = match.group(2).strip()
        content = body[match.end() : end].strip()
        block = f"{match.group(0).strip()}\n\n{content}".strip() if content else match.group(0).strip()
        sections.append((heading, block))
    return sections


def _split_long(text: str, max_tokens: int) -> list[str]:
    if estimate_tokens(text) <= max_tokens:
        return [text] if text.strip() else []
    parts = _split_keep_fences(text)
    bins: list[str] = []
    current: list[str] = []
    current_tokens = 0
    for part in parts:
        n = estimate_tokens(part)
        if current and current_tokens + n > max_tokens:
            bins.append("\n\n".join(current).strip())
            current, current_tokens = [part], n
        else:
            current.append(part)
            current_tokens += n
    if current:
        bins.append("\n\n".join(current).strip())
    # if a single fence/paragraph is still too big, hard-wrap by lines, then words
    out: list[str] = []
    for item in bins:
        if estimate_tokens(item) <= max_tokens:
            if item:
                out.append(item)
            continue
        lines = item.splitlines()
        buf: list[str] = []
        tok = 0
        for line in lines:
            pieces = _split_words(line, max_tokens) if estimate_tokens(line) > max_tokens else [line]
            for piece in pieces:
                lt = estimate_tokens(piece)
                if buf and tok + lt > max_tokens:
                    out.append("\n".join(buf).strip())
                    buf, tok = [piece], lt
                else:
                    buf.append(piece)
                    tok += lt
        if buf:
            out.append("\n".join(buf).strip())
    return [b for b in out if b]


def _split_words(text: str, max_tokens: int) -> list[str]:
    words = text.split()
    if not words:
        return []
    bins: list[str] = []
    buf: list[str] = []
    for word in words:
        if buf and len(buf) + 1 > max_tokens:
            bins.append(" ".join(buf))
            buf = [word]
        else:
            buf.append(word)
    if buf:
        bins.append(" ".join(buf))
    return bins


def _split_keep_fences(text: str) -> list[str]:
    parts: list[str] = []
    pos = 0
    for match in FENCE_RE.finditer(text):
        before = text[pos : match.start()].strip()
        if before:
            parts.extend([p.strip() for p in re.split(r"\n\s*\n", before) if p.strip()])
        parts.append(match.group(1).strip())
        pos = match.end()
    rest = text[pos:].strip()
    if rest:
        parts.extend([p.strip() for p in re.split(r"\n\s*\n", rest) if p.strip()])
    return parts


def _apply_overlap(
    parts: list[tuple[str, str]],
    max_tokens: int,
    overlap_tokens: int,
) -> list[tuple[str, str]]:
    if not parts or overlap_tokens <= 0:
        return parts
    result: list[tuple[str, str]] = []
    previous_words: list[str] = []
    for heading, text in parts:
        words = text.split()
        if previous_words and result:
            prefix = " ".join(previous_words[-overlap_tokens:])
            # only prepend overlap if it still fits
            if estimate_tokens(prefix) + estimate_tokens(text) <= max_tokens + overlap_tokens:
                text = prefix + "\n\n" + text
        result.append((heading, text))
        previous_words = words
    return result
