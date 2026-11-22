"""Flag and strip instruction-like content in retrieved documents.

Retrieved chunks are treated as data, not as instructions to the assistant.
Patterns are conservative lexical checks, not a complete security boundary.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace

from audit_rag.index.store import SearchHit

# Each pattern is a likely "ignore the system / follow the document" jailbreak.
INSTRUCTION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("ignore_instructions", re.compile(r"ignore (all )?(previous|prior|above|the) instructions", re.I)),
    ("override_prompt", re.compile(r"(override|disregard|discard) (the )?(system )?prompt", re.I)),
    ("you_are_now", re.compile(r"\byou are now\b", re.I)),
    ("reveal_prompt", re.compile(r"reveal (your|the) (system )?prompt", re.I)),
    ("new_instructions", re.compile(r"\bnew instructions:\s", re.I)),
    ("from_now_on", re.compile(r"\bfrom now on,? you (must|will|should)\b", re.I)),
    ("exfiltrate", re.compile(r"\b(exfiltrate|exfiltration)\b", re.I)),
    ("send_secrets", re.compile(r"send (all )?(secrets|api keys|credentials) to\b", re.I)),
    ("hidden_instruction", re.compile(r"hidden instruction", re.I)),
    ("jailbreak", re.compile(r"\bjailbreak\b", re.I)),
]


@dataclass(frozen=True)
class InjectionFlag:
    rule: str
    excerpt: str


def scan_text(text: str) -> list[InjectionFlag]:
    flags: list[InjectionFlag] = []
    for rule, pattern in INSTRUCTION_PATTERNS:
        match = pattern.search(text)
        if match:
            start = max(0, match.start() - 40)
            end = min(len(text), match.end() + 40)
            flags.append(InjectionFlag(rule=rule, excerpt=text[start:end].replace("\n", " ")))
    return flags


def _strip_flagged_sentences(text: str) -> str:
    parts = re.split(r"(?<=[.!?])\s+|[\n]+", text)
    kept: list[str] = []
    for part in parts:
        if not part.strip():
            continue
        if scan_text(part):
            continue
        kept.append(part.strip())
    return " ".join(kept).strip()


def wrap_as_data(chunk_id: str, text: str) -> str:
    return (
        f"<retrieved_document id={chunk_id!r} untrusted=true>\n"
        f"{text}\n"
        f"</retrieved_document>"
    )


def sanitize_hits(hits: list[SearchHit]) -> tuple[list[SearchHit], list[tuple[str, InjectionFlag]]]:
    """Return hits with instruction-like sentences removed, plus the flags found.

    A hit that is only instruction text is dropped. Remaining text is unchanged
    in meaning; we do not try to rewrite educational content.
    """
    clean: list[SearchHit] = []
    flags: list[tuple[str, InjectionFlag]] = []
    for hit in hits:
        found = scan_text(hit.text)
        for flag in found:
            flags.append((hit.chunk_id, flag))
        text = _strip_flagged_sentences(hit.text) if found else hit.text
        if not text.strip():
            continue
        clean.append(replace(hit, text=text) if found else hit)
    return clean, flags
