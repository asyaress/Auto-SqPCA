"""Read-only verification of frozen Phase 1 and Phase 2 before Phase 3 A."""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "phase3"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def frozen_inventory() -> dict[str, str]:
    paths = []
    for folder in ("G0", "D1", "D2", "S7", "S7B", "S7C", "G2R", "G4R"):
        base = ROOT / "phase2a" / folder
        paths.extend(p for p in base.rglob("*") if p.is_file() and
                     not any(x in {"_deps", "__pycache__", ".pytest_cache"} for x in p.relative_to(base).parts))
    paths.extend(p for p in (ROOT / "phase2a/raw/wdc_format_hourly").rglob("*") if p.is_file())
    return {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(paths)}


def verify_snapshot() -> int:
    expected = json.loads((OUT / "F3A_preflight.json").read_text(encoding="utf-8"))["frozen_sha256"]
    actual = frozen_inventory()
    bad = [p for p in expected.keys() | actual.keys() if expected.get(p) != actual.get(p)]
    if bad: raise RuntimeError(f"Phase 1-2 frozen artifacts changed: {bad[:10]}")
    freeze = json.loads((ROOT / "audit_final/dataset_freeze.json").read_text(encoding="utf-8"))
    for item in freeze["inputs"]:
        archive = item.get("archive")
        if archive and sha(ROOT / archive["path"]) != archive["sha256"]:
            raise RuntimeError(f"Phase 1 minute ZIP changed: {archive['path']}")
    return len(actual)


def main() -> None:
    protocol = OUT / "F3_protocol_v1.md"
    source = Path("D:/Downloads/Fase3_protokol_AutoSqPCA.md")
    if sha(protocol) != sha(source): raise RuntimeError("Protocol copy differs from source")
    freeze = json.loads((ROOT / "audit_final/dataset_freeze.json").read_text(encoding="utf-8"))
    minute = []
    for item in freeze["inputs"]:
        archive = item.get("archive")
        if archive:
            p = ROOT / archive["path"]
            if not p.is_file() or sha(p) != archive["sha256"]:
                raise RuntimeError(f"Frozen minute ZIP mismatch: {archive['path']}")
            minute.append(archive["path"])
    g0 = ROOT / "phase2a/G0/input_manifest.csv"
    manifest = rows(g0)
    for item in manifest:
        p = ROOT / item["relative_path"]
        if not p.is_file() or sha(p) != item["sha256"]:
            raise RuntimeError(f"G0 manifest mismatch: {item['relative_path']}")
    g4_pre = json.loads((ROOT / "phase2a/G4R/G4R_preflight.json").read_text(encoding="utf-8"))["all_frozen_files_snapshot"]
    current = frozen_inventory()
    # Compiled Python caches were included in the historical snapshot but are
    # generated files, not frozen research artifacts. Compare source/output files.
    compared = {p: digest for p, digest in g4_pre.items()
                if not any(part in {"_deps", "__pycache__", ".pytest_cache"} for part in Path(p).parts)}
    bad = [p for p, digest in compared.items() if current.get(p) != digest]
    if bad: raise RuntimeError(f"Phase 2 pre-G4R hash mismatch: {bad[:10]}")
    g2cfg = ROOT / "phase2a/G2R/G2R_frozen_config.json"
    cfg_hash = sha(g2cfg)
    if cfg_hash != "25676d831262eef44857d6bd9b14f4aba72909ec4968760d53406f906976a320":
        raise RuntimeError(f"G2R V1 frozen config SHA unexpected: {cfg_hash}")
    cfg = json.loads(g2cfg.read_text(encoding="utf-8"))
    if cfg["variant"] != "V1": raise RuntimeError("Frozen V1 configuration changed")
    for name, digest in cfg["code_sha256"].items():
        if sha(ROOT / "phase2a/G2R" / name) != digest:
            raise RuntimeError(f"G2R frozen code changed: {name}")
    for folder in ("G2R", "G4R"):
        base = ROOT / "phase2a" / folder
        archive = base / f"{folder}_review.zip"
        sidecar = base / f"{folder}_review.zip.sha256"
        if sha(archive) != sidecar.read_text().split()[0]:
            raise RuntimeError(f"{folder} ZIP SHA sidecar mismatch")
        with zipfile.ZipFile(archive) as z:
            if z.testzip(): raise RuntimeError(f"{folder} ZIP CRC failure")
    data = {"utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "protocol_sha256": sha(protocol), "phase1_minute_archives_checked": len(minute),
            "G0_manifest_rows_checked": len(manifest), "G0_manifest_sha256": sha(g0),
            "G2R_config_sha256": cfg_hash, "historical_pre_G4R_hashes_compared": len(compared),
            "historical_pre_G4R_cache_paths_excluded": len(g4_pre)-len(compared),
            "frozen_sha256": current,
            "frozen_count": len(current), "G2R_label": "S-DEVIATE", "G4R_label": "D-AGREE",
            "G1_registration2": "HOLD", "G1_registration3": "HOLD"}
    (OUT / "F3A_preflight.json").write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"F3A preflight: {len(minute)} minute archives, {len(manifest)} G0 manifest files, {len(current)} frozen outputs, V1 verified")


if __name__ == "__main__":
    main()
