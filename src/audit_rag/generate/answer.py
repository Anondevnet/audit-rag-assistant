from __future__ import annotations

from dataclasses import dataclass, field

from audit_rag.guardrails.scanner import InjectionFlag

REFUSAL_TEXT = (
    "I don't have enough evidence in the retrieved documents to answer that. "
    "The knowledge base does not appear to contain this information."
)


@dataclass
class Answer:
    text: str
    refused: bool
    reason: str
    citations: list[str] = field(default_factory=list)
    used_chunk_ids: list[str] = field(default_factory=list)
    generator: str = "extractive"
    injection_flags: list[tuple[str, InjectionFlag]] = field(default_factory=list)
