#!/usr/bin/env python3
"""Thin wrapper around `python -m audit_rag ingest`."""

from audit_rag.cli import main

if __name__ == "__main__":
    raise SystemExit(main(["ingest", *(__import__("sys").argv[1:])]))
