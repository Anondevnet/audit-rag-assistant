"""Normalize openly licensed sources into data/corpus + data/MANIFEST.json.

Only two sources are used, both verified by reading their LICENSE files:
  - SmartContractSecurity/SWC-registry   (MIT)
  - crytic/not-so-smart-contracts        (Apache-2.0)
No Code4rena, Sherlock, or Solodit content is used.

Usage:
  git clone --depth 1 https://github.com/SmartContractSecurity/SWC-registry.git /tmp/src/SWC-registry
  git clone --depth 1 https://github.com/crytic/not-so-smart-contracts.git /tmp/src/not-so-smart-contracts
  python scripts/build_corpus.py --sources /tmp/src
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SOURCES = {
    "swc": {
        "dir": "SWC-registry",
        "name": "SWC Registry",
        "repo": "https://github.com/SmartContractSecurity/SWC-registry",
        "license": "MIT",
        "license_file": "LICENSE",
        "copyright": "Copyright (c) 2018-present Smart Contract Weakness Classification Registry",
    },
    "nssc": {
        "dir": "not-so-smart-contracts",
        "name": "not-so-smart-contracts (Trail of Bits / crytic)",
        "repo": "https://github.com/crytic/not-so-smart-contracts",
        "license": "Apache-2.0",
        "license_file": "LICENSE",
        "copyright": "Copyright Trail of Bits and not-so-smart-contracts contributors",
    },
}

SWC_DISCLAIMER_RE = re.compile(
    r"\A# Please note, this content is no longer actively maintained\..*?(?=^# Title\s*$)",
    re.DOTALL | re.MULTILINE,
)


def git_sha(repo_dir: Path) -> str:
    return subprocess.check_output(["git", "-C", str(repo_dir), "rev-parse", "HEAD"], text=True).strip()


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def yaml_value(value: str) -> str:
    # single-line, no colons-at-start issues for our simple parser
    return value.replace("\n", " ").strip()


def front_matter(meta: dict[str, str]) -> str:
    lines = ["---"]
    for key, value in meta.items():
        lines.append(f"{key}: {yaml_value(value)}")
    lines.append("---")
    return "\n".join(lines) + "\n\n"


def build_swc(src_root: Path, out_dir: Path) -> list[dict]:
    cfg = SOURCES["swc"]
    repo_dir = src_root / cfg["dir"]
    sha = git_sha(repo_dir)
    records = []
    for path in sorted((repo_dir / "entries" / "docs").glob("SWC-*.md")):
        raw = path.read_text(encoding="utf-8")
        body = SWC_DISCLAIMER_RE.sub("", raw).strip()
        m = re.search(r"^# Title\s*\n+(.+?)\s*$", body, re.MULTILINE)
        title = m.group(1).strip() if m else path.stem
        # Turn "# Title\n\nReentrancy" into a single "# SWC-107: Reentrancy" heading
        body = re.sub(r"^# Title\s*\n+.+?\s*$", f"# {path.stem}: {title}", body, count=1, flags=re.MULTILINE)
        swc_id = path.stem.lower()
        rel = path.relative_to(repo_dir).as_posix()
        source_url = f"{cfg['repo']}/blob/{sha}/{rel}"
        meta = {
            "id": swc_id,
            "title": f"{path.stem}: {title}",
            "source_name": cfg["name"],
            "source_url": source_url,
            "source_commit": sha,
            "license": cfg["license"],
            "license_url": f"{cfg['repo']}/blob/{sha}/{cfg['license_file']}",
            "copyright": cfg["copyright"],
            "modifications": "Removed the upstream maintenance banner (preserved in NOTICE below); merged the Title heading into the H1; content otherwise unchanged.",
            "upstream_status": "SWC registry is no longer actively maintained (last substantive update 2020).",
        }
        notice = (
            "\n\n## Source notice\n\n"
            f"Adapted from {cfg['name']} ({source_url}), {cfg['license']} licensed. "
            "Upstream marks this registry as no longer actively maintained since 2020; "
            "check current guidance such as the EEA EthTrust Security Levels specification.\n"
        )
        text = front_matter(meta) + body + notice
        out_path = out_dir / f"{swc_id}.md"
        out_path.write_text(text, encoding="utf-8")
        records.append({**meta, "file": out_path.relative_to(ROOT).as_posix(), "upstream_path": rel})
    return records


def build_nssc(src_root: Path, out_dir: Path) -> list[dict]:
    cfg = SOURCES["nssc"]
    repo_dir = src_root / cfg["dir"]
    sha = git_sha(repo_dir)
    records = []
    for readme in sorted(repo_dir.glob("*/README.md")):
        category = readme.parent.name
        raw = readme.read_text(encoding="utf-8").strip()
        lines = [ln for ln in raw.splitlines() if ln.strip()]
        title = lines[0].lstrip("# ").strip() if lines else category
        doc_id = f"nssc-{slug(category)}"
        rel = readme.relative_to(repo_dir).as_posix()
        source_url = f"{cfg['repo']}/blob/{sha}/{rel.replace(' ', '%20')}"
        # list example files (names only; code not copied in M1)
        examples = sorted(
            p.relative_to(readme.parent).as_posix()
            for p in readme.parent.rglob("*")
            if p.is_file() and p.name != "README.md"
        )
        meta = {
            "id": doc_id,
            "title": f"not-so-smart-contracts: {title}",
            "source_name": cfg["name"],
            "source_url": source_url,
            "source_commit": sha,
            "license": cfg["license"],
            "license_url": f"{cfg['repo']}/blob/{sha}/{cfg['license_file']}",
            "copyright": cfg["copyright"],
            "modifications": "Added front matter, a normalized H1, and an example-file index; README prose unchanged.",
        }
        body = raw
        if not body.lstrip().startswith("#"):
            body = f"# {title}\n\n{body}"
        else:
            body = re.sub(r"\A#+\s*.+", f"# not-so-smart-contracts: {title}", body, count=1)
        if examples:
            ex_lines = "\n".join(f"- `{e}`" for e in examples[:40])
            body += f"\n\n## Example files in upstream\n\n{ex_lines}\n"
        notice = (
            "\n\n## Source notice\n\n"
            f"Adapted from {cfg['name']} ({source_url}), licensed under the Apache License 2.0. "
            "Modified: front matter, heading normalization, example-file index. "
            "See data/licenses/not-so-smart-contracts-LICENSE.\n"
        )
        text = front_matter(meta) + body + notice
        out_path = out_dir / f"{doc_id}.md"
        out_path.write_text(text, encoding="utf-8")
        records.append({**meta, "file": out_path.relative_to(ROOT).as_posix(), "upstream_path": rel})
    return records


def copy_licenses(src_root: Path) -> None:
    lic_dir = ROOT / "data" / "licenses"
    lic_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src_root / "SWC-registry" / "LICENSE", lic_dir / "SWC-registry-LICENSE")
    shutil.copyfile(src_root / "not-so-smart-contracts" / "LICENSE", lic_dir / "not-so-smart-contracts-LICENSE")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources", type=Path, required=True, help="Directory with the cloned source repos.")
    args = parser.parse_args()
    out_dir = ROOT / "data" / "corpus"
    if out_dir.exists():
        for p in out_dir.glob("*.md"):
            p.unlink()
    out_dir.mkdir(parents=True, exist_ok=True)

    records = build_swc(args.sources, out_dir) + build_nssc(args.sources, out_dir)
    copy_licenses(args.sources)
    by_license: dict[str, int] = {}
    for r in records:
        by_license[r["license"]] = by_license.get(r["license"], 0) + 1
    manifest = {
        "description": "Every corpus document, its upstream source URL (pinned to a commit), and its license.",
        "excluded_sources": [
            "Code4rena (ToS forbids scraping, embeddings, and model evaluation on C4 content)",
            "Sherlock (report rights governed by per-engagement agreements)",
            "Solodit / Cyfrin (terms reserve content rights; deferred until API terms are confirmed)",
        ],
        "document_count": len(records),
        "license_breakdown": by_license,
        "documents": records,
    }
    (ROOT / "data" / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(records)} documents: {by_license}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
