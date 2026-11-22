from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
src = ROOT / "src"
if str(src) not in sys.path:
    sys.path.insert(0, str(src))

# Force the offline embedder/reranker for the whole test session.
@pytest.fixture(autouse=True)
def _offline_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUDIT_RAG_EMBEDDER", "hashing")
    monkeypatch.setenv("AUDIT_RAG_RERANKER", "token")
