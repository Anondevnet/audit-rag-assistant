"""Load corpus markdown and the data/MANIFEST file."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from audit_rag.chunk.chunker import parse_front_matter


@dataclass
class Document:
    doc_id: str
    title: str
    path: Path
    text: str
    body: str
    metadata: dict[str, str]

    @property
    def source_url(self) -> str:
        return self.metadata.get("source_url", "")

    @property
    def license(self) -> str:
        return self.metadata.get("license", "")


def load_corpus(corpus_dir: Path) -> list[Document]:
    paths = sorted(corpus_dir.glob("*.md"))
    docs: list[Document] = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        meta, body = parse_front_matter(text)
        doc_id = meta.get("id") or path.stem
        title = meta.get("title") or path.stem
        docs.append(
            Document(
                doc_id=doc_id,
                title=title,
                path=path,
                text=text,
                body=body,
                metadata=meta,
            )
        )
    docs.sort(key=lambda d: d.doc_id)
    return docs


def load_manifest(path: Path) -> list[dict]:
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    if isinstance(data, dict) and "documents" in data:
        return list(data["documents"])
    if isinstance(data, list):
        return data
    raise ValueError(f"Unrecognized manifest shape in {path}")
