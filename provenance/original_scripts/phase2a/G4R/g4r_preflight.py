"""Read-only verification of G0 through G2-R before G4-R execution."""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
G2R = ROOT / "phase2a/G2R"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024*1024), b""):
            h.update(block)
    return h.hexdigest()


def csvrows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def frozen_inventory() -> dict[str, str]:
    paths = []
    for folder in ("G0", "D1", "D2", "S7", "S7B", "S7C"):
        paths += [p for p in (ROOT / "phase2a" / folder).rglob("*") if p.is_file()]
    paths += [p for p in (ROOT / "phase2a/raw/wdc_format_hourly").rglob("*") if p.is_file()]
    paths += [p for p in G2R.rglob("*") if p.is_file() and not any(x in {"_deps", "__pycache__", ".pytest_cache"} for x in p.relative_to(G2R).parts)]
    return {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(paths)}


def verify_against_before(before: dict[str, str]) -> int:
    current = frozen_inventory()
    bad = [p for p in before.keys() | current.keys() if before.get(p) != current.get(p)]
    if bad:
        raise RuntimeError(f"Frozen artifacts changed: {bad[:10]}")
    return len(current)


def main() -> None:
    protocol = OUT / "G4R_protocol_v1.md"
    source = Path("D:/Downloads/G4-R_protokol.md")
    if sha(source) != sha(protocol): raise RuntimeError("G4R protocol copy differs from source")
    g0 = ROOT / "phase2a/G0/input_manifest.csv"
    manifest = csvrows(g0)
    mismatch = [r["relative_path"] for r in manifest if not (ROOT / r["relative_path"]).is_file() or sha(ROOT / r["relative_path"]) != r["sha256"]]
    if mismatch: raise RuntimeError(f"G0 raw/phase1 SHA-256 mismatch: {mismatch[:10]}")
    previous = json.loads((G2R / "G2R_preflight.json").read_text(encoding="utf-8"))["frozen_sha256_before"]
    current = frozen_inventory()
    mismatch = [p for p, digest in previous.items() if current.get(p) != digest]
    if mismatch: raise RuntimeError(f"G0-S7C changed since G2-R: {mismatch[:10]}")
    config = G2R / "G2R_frozen_config.json"
    config_hash = sha(config)
    if config_hash != "25676d831262eef44857d6bd9b14f4aba72909ec4968760d53406f906976a320":
        raise RuntimeError(f"G2R frozen config SHA-256 unexpected: {config_hash}")
    cfg = json.loads(config.read_text(encoding="utf-8"))
    if cfg["variant"] != "V1": raise RuntimeError("G2R frozen variant is not V1")
    for name, digest in cfg["code_sha256"].items():
        if sha(G2R / name) != digest: raise RuntimeError(f"G2R frozen code changed: {name}")
    for line in (G2R / "G2R_checksums.sha256").read_text().splitlines():
        digest, name = line.split("  ", 1)
        if sha(G2R / name) != digest: raise RuntimeError(f"G2R package content changed: {name}")
    review = G2R / "G2R_review.zip"
    if sha(review) != (G2R / "G2R_review.zip.sha256").read_text().split()[0]:
        raise RuntimeError("G2R ZIP sidecar SHA-256 mismatch")
    with zipfile.ZipFile(review) as z:
        if z.testzip(): raise RuntimeError("G2R ZIP CRC failed")
    result = json.loads((G2R / "G2R_result.json").read_text(encoding="utf-8"))
    if result["label"] != "S-DEVIATE" or result["config_sha256"] != config_hash:
        raise RuntimeError("G2R result does not match frozen config/label")
    data = {"verified_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "protocol_sha256": sha(protocol), "G0_manifest_rows": len(manifest), "G0_manifest_sha256": sha(g0),
            "G0_S7C_prior_hashes_checked": len(previous), "all_frozen_files_snapshot": current,
            "G2R_config_sha256": config_hash, "G2R_label": result["label"],
            "G1_registration2": "HOLD", "G1_registration3": "HOLD"}
    (OUT / "G4R_preflight.json").write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"G4R preflight: G0 {len(manifest)} match; historical {len(previous)} match; current {len(current)} frozen hashes snapshotted; G2R V1/S-DEVIATE verified")


if __name__ == "__main__":
    main()
