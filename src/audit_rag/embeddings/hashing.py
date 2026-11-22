"""Deterministic offline embeddings for CI and machines without Ollama."""

from __future__ import annotations

import hashlib

import numpy as np

from audit_rag.embeddings.base import Embedder

DEFAULT_DIM = 384


class HashingEmbedder(Embedder):
    """Expand SHAKE-256 into a fixed-size unit vector. Not semantically strong,
    but stable, offline, and good enough to exercise the vector index in tests.
    """

    kind = "hashing"

    def __init__(self, dim: int = DEFAULT_DIM) -> None:
        if dim <= 0:
            raise ValueError("dim must be positive")
        self.dim = dim

    def embed_texts(self, texts: list[str], *, prefix: str = "") -> np.ndarray:
        rows = [self._one(prefix + text) for text in texts]
        return np.stack(rows, axis=0) if rows else np.zeros((0, self.dim), dtype=np.float32)

    def _one(self, text: str) -> np.ndarray:
        raw = hashlib.shake_256(text.encode("utf-8")).digest(self.dim * 4)
        vec = np.frombuffer(raw, dtype=">u4").astype(np.float32)
        # map uint32 to [-1, 1]
        vec = (vec / np.float32(2**31)) - np.float32(1.0)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.astype(np.float32, copy=False)
