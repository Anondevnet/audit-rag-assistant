#!/usr/bin/env python3
"""Record docs/demo.gif from real CLI ask output and the eval dashboard metrics.

Requires ffmpeg. Pillow is optional but used when installed for cleaner frames.
This script does not invent answers: it reruns `audit-rag ask` against a local
index, or reuses capture files passed with --from-dir.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from audit_rag.paths import project_root


def _run_ask(index: Path, query: str) -> str:
    env = os.environ.copy()
    env.setdefault("AUDIT_RAG_EMBEDDER", "hashing")
    env.setdefault("AUDIT_RAG_RERANKER", "token")
    env.setdefault("AUDIT_RAG_GENERATOR", "extractive")
    result = subprocess.run(
        [sys.executable, "-m", "audit_rag", "ask", query, "--index", str(index), "--k", "5"],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    return result.stdout


def _wrap(text: str, width: int) -> list[str]:
    lines: list[str] = []
    for raw in text.splitlines() or [""]:
        if not raw:
            lines.append("")
            continue
        while len(raw) > width:
            cut = raw.rfind(" ", 0, width)
            if cut < 20:
                cut = width
            lines.append(raw[:cut])
            raw = raw[cut:].lstrip()
        lines.append(raw)
    return lines


def _render_ppm(path: Path, lines: list[str], *, title: str) -> None:
    width, height = 960, 540
    bg = (13, 17, 23)
    fg = (230, 237, 243)
    accent = (88, 166, 255)
    muted = (139, 148, 158)
    # 5x7 font will be drawn as 2x2 blocks -> 10x14 glyphs
    # Fallback: draw using a very small builtin font if Pillow is missing.
    try:
        from PIL import Image, ImageDraw, ImageFont

        img = Image.new("RGB", (width, height), bg)
        draw = ImageDraw.Draw(img)
        font_paths = [
            "/System/Library/Fonts/Supplemental/Courier New.ttf",
            "/System/Library/Fonts/Menlo.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        ]
        font = None
        title_font = None
        for fp in font_paths:
            if Path(fp).exists():
                font = ImageFont.truetype(fp, 16)
                title_font = ImageFont.truetype(fp, 22)
                break
        if font is None:
            font = ImageFont.load_default()
            title_font = font
        draw.rectangle((0, 0, width, 48), fill=(22, 27, 34))
        draw.text((24, 12), title, fill=accent, font=title_font)
        y = 64
        for line in lines[:28]:
            color = fg
            if line.startswith("$ ") or line.startswith("Query:"):
                color = accent
            elif line.startswith("I don't have enough") or line.startswith("Refused: True"):
                color = (248, 81, 73)
            elif "[1:" in line or line.startswith("Generator:"):
                color = muted if line.startswith("Generator:") else fg
            draw.text((24, y), line, fill=color, font=font)
            y += 16
        img.save(path)
        return
    except Exception:
        pass

    # PPM fallback, monospaced 6x8 cells
    pixels = [list(bg) for _ in range(width * height)]

    def put(x: int, y: int, color: tuple[int, int, int]) -> None:
        if 0 <= x < width and 0 <= y < height:
            idx = (y * width + x) * 0
            # store as triples in flat list of pixels
            pixels[y * width + x] = color

    for x in range(width):
        for y in range(48):
            put(x, y, (22, 27, 34))
    # very small: write raw title/body as blocks of 6x8 using bitmap of python font via ord
    def glyph(ch: str) -> list[str]:
        return ["######", "#    #", "#    #", "######", "#    #", "#    #", "#    #", "      "] if ch.isalnum() else ["      "] * 8

    def text(x0: int, y0: int, s: str, color: tuple[int, int, int]) -> None:
        x = x0
        for ch in s:
            bits = glyph(ch)
            for gy, row in enumerate(bits):
                for gx, cell in enumerate(row):
                    if cell == "#":
                        for dx in range(2):
                            for dy in range(2):
                                put(x + gx * 2 + dx, y0 + gy * 2 + dy, color)
            x += 14

    text(24, 12, title[:40], accent)
    y = 64
    for line in lines[:22]:
        text(24, y, line[:80], fg)
        y += 20
    with path.open("wb") as fh:
        fh.write(f"P6\n{width} {height}\n255\n".encode())
        fh.write(b"".join(bytes(px) for px in pixels))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    root = project_root()
    out = args.out or (root / "docs" / "demo.gif")
    index = args.index or (root / "data" / "indexes" / "audit.db")
    if not index.exists():
        # fall back to the eval index if the default has not been built
        alt = root / "data" / "indexes" / "eval.db"
        if alt.exists():
            index = alt
        else:
            raise SystemExit(f"Index not found: {index}. Run `python -m audit_rag ingest` first.")

    q_answer = "Why is authorization through tx.origin considered unsafe?"
    q_refuse = "What high-severity findings were reported in a 2024 Uniswap audit contest on Code4rena?"
    answer_out = _run_ask(index, q_answer)
    refuse_out = _run_ask(index, q_refuse)
    report = json.loads((root / "evals" / "reports" / "latest.json").read_text(encoding="utf-8"))
    metrics = report["metrics"]
    metric_lines = [
        "CI-reproducible stack: hashing embedder, token rerank, extractive generator",
        f"Recall@10 (all gold): {metrics['recall@10_all']:.4f}",
        f"Mean recall@10:       {metrics['mean_recall@10']:.4f}",
        f"MRR@10:               {metrics['mrr@10']:.4f}",
        f"Doc recall@10:        {metrics['doc_recall@10']:.4f}",
        f"Citation accuracy:    {metrics['citation_accuracy']:.4f}",
        f"Faithfulness (lexical): {metrics['faithfulness']:.4f}",
        f"Refusal accuracy:     {metrics['refusal_accuracy']:.4f}",
        f"Harness time (20 q):  {metrics['elapsed_ms']} ms",
        "",
        "These are lexical metrics, not an LLM-as-judge score.",
        "Source: evals/reports/latest.json",
    ]

    def clip(text: str, query: str, keep: int = 18) -> list[str]:
        # Keep the query, a couple of hit headers, the generator line, and the answer.
        raw_lines = text.strip().splitlines()
        kept: list[str] = [f"$ python -m audit_rag ask \"{query}\"" , ""]
        # first 8 lines of retrieval + from --- onward
        head = raw_lines[:8]
        tail = []
        if "---" in raw_lines:
            tail = raw_lines[raw_lines.index("---"):]
        body = head + ([""] if tail else []) + tail
        kept.extend(_wrap("\n".join(body), 92))
        return kept[:keep]

    frames: list[tuple[str, list[str], int]] = [
        (
            "audit-rag-assistant  —  Milestone 2",
            [
                "Cited RAG over a license-cleared SWC + not-so-smart-contracts corpus.",
                "",
                "$ python -m audit_rag ingest",
                "$ python -m audit_rag ask \"Why is authorization through tx.origin considered unsafe?\"",
                "$ python -m audit_rag ask \"What high-severity findings were reported in a 2024 Uniswap",
                "    audit contest on Code4rena?\"",
                "$ python scripts/eval.py --k 10",
                "",
                "Answers cite [rank:chunk_id]. The assistant refuses when evidence is missing.",
                "No public deploy in this milestone.",
            ],
            90,
        ),
        ("Cited answer", clip(answer_out, q_answer, 24), 150),
        ("Refusal when the corpus has no evidence", clip(refuse_out, q_refuse, 22), 130),
        ("Eval results  (hashing + extractive, 20 approved goldens)", metric_lines, 140),
    ]

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise SystemExit("ffmpeg not found on PATH")

    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="audit-rag-demo-") as tmp:
        tmp_path = Path(tmp)
        concat_lines = []
        for i, (title, lines, frames_n) in enumerate(frames, start=1):
            # Pillow saves png; fallback saves ppm. ffmpeg reads both.
            frame = tmp_path / f"frame-{i:02d}.png"
            try:
                from PIL import Image  # noqa: F401

                _render_ppm(frame, lines, title=title)
            except Exception:
                frame = tmp_path / f"frame-{i:02d}.ppm"
                _render_ppm(frame, lines, title=title)
            # duration in 1/30 s
            concat_lines.append(f"file '{frame}'")
            concat_lines.append(f"duration {frames_n / 30:.2f}")
        # last frame must be repeated for concat demuxer
        concat_lines.append(concat_lines[-2])
        list_file = tmp_path / "frames.txt"
        list_file.write_text("\n".join(concat_lines) + "\n")
        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_file),
                "-vf",
                "fps=10,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse",
                "-loop",
                "0",
                str(out),
            ],
            check=True,
        )
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
