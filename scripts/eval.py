#!/usr/bin/env python3
"""Run the golden-set eval harness and write evals/reports/latest.json."""

from __future__ import annotations

import argparse
import json

from audit_rag.eval.harness import run_harness


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument("--no-rebuild", action="store_true")
    parser.add_argument("--tag", default="latest", help="Output tag (latest writes latest.json).")
    args = parser.parse_args()
    report = run_harness(k=args.k, rebuild=not args.no_rebuild, tag=args.tag)
    metrics = report["metrics"]
    print(json.dumps(metrics, indent=2))
    outputs = report.get("_outputs", {})
    print("Wrote", outputs or "evals/reports/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
