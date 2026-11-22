"""Local Ollama embeddings (nomic-embed-text by default)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

import numpy as np

from audit_rag.embeddings.base import Embedder


class OllamaEmbedder(Embedder):
    kind = "ollama"
    query_prefix = "search_query: "
    document_prefix = "search_document: "

    def __init__(
        self,
        model: str | None = None,
        host: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.model = model or os.environ.get("OLLAMA_EMBED_MODEL") or "nomic-embed-text"
        self.host = (host or os.environ.get("OLLAMA_HOST") or "http://127.0.0.1:11434").rstrip("/")
        self.timeout = timeout
        self.dim = 768

    @classmethod
    def available(cls, host: str | None = None, timeout: float = 0.4) -> bool:
        base = (host or os.environ.get("OLLAMA_HOST") or "http://127.0.0.1:11434").rstrip("/")
        try:
            with urllib.request.urlopen(base + "/api/tags", timeout=timeout) as resp:
                return 200 <= resp.status < 300
        except (urllib.error.URLError, TimeoutError, OSError):
            return False

    def embed_texts(self, texts: list[str], *, prefix: str = "") -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        payload = json.dumps({"model": self.model, "input": [prefix + t for t in texts]}).encode()
        req = urllib.request.Request(
            self.host + "/api/embed",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = json.loads(resp.read().decode())
        embeddings = data.get("embeddings")
        if not embeddings:
            raise RuntimeError(f"Ollama returned no embeddings: {data!r}")
        arr = np.asarray(embeddings, dtype=np.float32)
        self.dim = int(arr.shape[1])
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms = np.maximum(norms, 1e-12)
        return arr / norms
