"""Treat retrieved document text as untrusted data."""

from audit_rag.guardrails.scanner import (
    InjectionFlag,
    scan_text,
    sanitize_hits,
    wrap_as_data,
)

__all__ = ["InjectionFlag", "scan_text", "sanitize_hits", "wrap_as_data"]
