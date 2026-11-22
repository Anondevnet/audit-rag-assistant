from __future__ import annotations

import os
from abc import ABC, abstractmethod

import numpy as np


class Embedder(ABC):
    """Text embedder. `kind` is stored in the index metadata."""

    kind: str
    dim: int
    query_prefix: str = ""
    document_prefix: str = ""

    @abstractmethod
    def embed_texts(self, texts: list[str], *, prefix: str = "") -> np.ndarray:
        """Return an (n, dim) float32 matrix, one L2-normalized row per text."""

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        return self.embed_texts(texts, prefix=self.document_prefix)

    def embed_query(self, text: str) -> np.ndarray:
        return self.embed_texts([text], prefix=self.query_prefix)[0]


def get_embedder(name: str | None = None) -> Embedder:
    from audit_rag.embeddings.hashing import HashingEmbedder
    from audit_rag.embeddings.ollama import OllamaEmbedder

    choice = (name or os.environ.get("AUDIT_RAG_EMBEDDER") or "auto").strip().lower()
    if choice == "hashing":
        return HashingEmbedder()
    if choice == "ollama":
        return OllamaEmbedder()
    if choice == "auto":
        if OllamaEmbedder.available():
            return OllamaEmbedder()
        return HashingEmbedder()
    raise ValueError(f"Unknown embedder {choice!r}. Use hashing, ollama, or auto.")
