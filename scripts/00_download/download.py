"""Download archived inputs listed in download_manifest.csv and check SHA-256.

Upstream sources may later change; a mismatch stops the fetch and does not
silently replace an authenticated local copy. No raw data ships in Git.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import os
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", help="Only download a manifest source class")
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    rows = list(csv.DictReader((HERE / "download_manifest.csv").open(encoding="utf-8", newline="")))
    if args.source:
        rows = [r for r in rows if r["source"] == args.source]
    if args.limit is not None:
        rows = rows[:args.limit]
    for row in rows:
        rel = Path(row["relative_path"])
        target = (ROOT / rel).resolve()
        if not target.is_relative_to(ROOT.resolve()):
            raise ValueError(f"Path escapes repository: {rel}")
        if target.exists() and sha(target) == row["sha256"]:
            print(f"OK {rel}")
            continue
        if args.verify_only:
            raise RuntimeError(f"Missing or SHA-256 mismatch: {rel}")
        target.parent.mkdir(parents=True, exist_ok=True)
        partial = target.with_name(target.name + ".partial")
        req = urllib.request.Request(row["url"], headers={"User-Agent": "Auto-SqPCA-reproducibility/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=120) as response, partial.open("wb") as f:
                while block := response.read(1024 * 1024):
                    f.write(block)
            actual = sha(partial)
            if actual != row["sha256"]:
                raise RuntimeError(f"SHA-256 mismatch for {rel}: expected {row['sha256']}, got {actual}")
            os.replace(partial, target)
            print(f"DOWNLOADED {rel}")
        finally:
            partial.unlink(missing_ok=True)


if __name__ == "__main__":
    main()

