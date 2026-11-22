"""General query expansion. This is not gold-answer look-up.

Expansions are limited to identifier/title lookup from the index, hyphen
variants, and a small domain synonym list (reentrancy, tx.origin, etc.).
"""

from __future__ import annotations

import re

_SYNONYMS: list[tuple[re.Pattern[str], list[str]]] = [
    (re.compile(r"\bre-?entrancy\b", re.I), ["reentrancy", "re-entrancy", "recursive call"]),
    (re.compile(r"\btx\.origin\b", re.I), ["tx.origin", "tx origin"]),
    (re.compile(r"\bdelegatecall\b", re.I), ["delegatecall", "delegate call"]),
    (re.compile(r"\bfloating pragma\b", re.I), ["floating pragma", "pragma version", "compiler version"]),
    (re.compile(r"\bblock\.timestamp\b", re.I), ["block.timestamp", "block timestamp"]),
    (re.compile(r"\berc-?20\b", re.I), ["ERC20", "ERC-20"]),
]


def expand_query(query: str, titles: dict[str, str] | None = None) -> str:
    extras: list[str] = []
    seen: set[str] = set()

    def add(term: str) -> None:
        key = re.sub(r"\s+", " ", term).strip().lower()
        if key and key not in seen and key not in query.lower():
            seen.add(key)
            extras.append(term)

    if titles:
        for match in re.finditer(r"\bSWC\s*[- ]?\s*(\d{1,3})\b", query, re.I):
            doc_id = f"swc-{int(match.group(1)):03d}"
            title = titles.get(doc_id)
            if title:
                add(title)
    for token in re.findall(r"[A-Za-z0-9]+(?:[.\-][A-Za-z0-9]+)+", query):
        add(token.replace(".", " ").replace("-", " "))
        add(re.sub(r"[.\-]", "", token))
    for pattern, synonyms in _SYNONYMS:
        if pattern.search(query):
            for synonym in synonyms:
                add(synonym)
    if not extras:
        return query
    return query + " " + " ".join(extras)
