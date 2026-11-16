"""Register approved G0-registration-3 without changing any prior artifacts."""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import shutil
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "phase2a/S7C"
SOURCE = Path(r"D:\Downloads\G0-registration-3_D2c.md")
EXPECTED_SOURCE_SHA = "cb5fdd487d460d986ec568916979bac0e7b6c0bb6d4891f3d423e770c2889573"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def frozen_hashes() -> dict[str, str]:
    return {rel(path): sha(path) for gate in ("G0", "D1", "D2", "S7", "S7B")
            for path in (ROOT / "phase2a" / gate).rglob("*")
            if path.is_file() and "__pycache__" not in path.parts}


def check_g0_manifest() -> dict:
    manifest_path = ROOT / "phase2a/G0/input_manifest.csv"
    with manifest_path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    bad = []
    for row in rows:
        path = ROOT / row["relative_path"]
        if not path.is_file():
            bad.append(f"MISSING {row['relative_path']}")
        elif sha(path).lower() != row["sha256"].lower():
            bad.append(f"SHA_MISMATCH {row['relative_path']}")
    if bad:
        raise RuntimeError(f"G0 input manifest mismatches: {bad[:10]}")
    return {"rows": len(rows), "all_sha256_match": True,
            "manifest_sha256": sha(manifest_path)}


def main() -> None:
    if not SOURCE.is_file():
        raise FileNotFoundError(f"Approved registration-3 source missing: {SOURCE}")
    source_digest = sha(SOURCE)
    if source_digest != EXPECTED_SOURCE_SHA:
        raise RuntimeError(f"Approved registration-3 SHA-256 changed: expected {EXPECTED_SOURCE_SHA}, got {source_digest}")
    frozen = frozen_hashes()
    g0 = check_g0_manifest()
    s7b_zip = ROOT / "phase2a/S7B/S7B_review.zip"
    s7b_old_sidecar = ROOT / "phase2a/S7B/S7B_review.sha256"
    s7b_zip_hash = sha(s7b_zip)
    old_sidecar_line = s7b_old_sidecar.read_text(encoding="utf-8").strip()
    with __import__("zipfile").ZipFile(s7b_zip) as archive:
        if archive.testzip() is not None:
            raise RuntimeError("Frozen S7B ZIP CRC failed")
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / SOURCE.name
    shutil.copyfile(SOURCE, target)
    if sha(target) != source_digest:
        raise RuntimeError("Registration-3 Markdown copy differs from source")
    source_text = target.read_text(encoding="utf-8")
    required = [f"| A{i} |" for i in range(1, 8)] + ["## 4. Spesifikasi D2c", "## 5. Aturan keputusan G1", "## 6. Rekonsiliasi provenans ZIP"]
    if any(marker not in source_text for marker in required):
        raise RuntimeError("Registration-3 source lacks required A1-A7 / D2c / G1 / ZIP sections")
    body = source_text.split("## 8. Instruksi untuk Claude Code")[0].rstrip()
    reg2 = ROOT / "phase2a/S7B/S7B_protocol_amendment.md"
    registered = ("# Registrasi resmi G0-registration-3 untuk D2c\n\n"
                  "**Status: APPROVED** oleh peneliti utama, 13 November 2026, menurut dokumen keputusan terlampir. Ketentuan A1–A7, D2c, prioritas G1, dan provenans ZIP di bawah disalin tanpa mengubah substansi. Semua K1–K11 registration-2 tetap berlaku kecuali perubahan eksplisit. D2b dan G1 HOLD registration-2 adalah catatan permanen.\n\n"
                  f"Sumber: `{SOURCE}`; SHA-256 `{source_digest}`. Salinan utuh tersedia pada `{target.name}`. "
                  f"Protokol registration-2 tidak diubah; SHA-256 `{sha(reg2)}`.\n\n"
                  "## Teks amandemen yang disetujui\n\n" + body + "\n")
    protocol_path = OUT / "S7C_protocol_registration3.md"
    protocol_path.write_text(registered, encoding="utf-8")
    changes = f"""# Changelog G0-registration-3 terhadap registration-2

Tanggal 13 November 2026. Status **APPROVED**. Tidak ada perubahan pada G0-registration-1, registration-2, D2b, atau G1 HOLD historis. Sumber registration-3 ditemukan di `{SOURCE}` dan disalin utuh tanpa perubahan.

| Artefak | SHA-256 |
|---|---|
| G0-registration-2 | `{sha(reg2)}` |
| G0-registration-3 sumber/salinan | `{source_digest}` |
| Registrasi resmi S7C | `{sha(protocol_path)}` |
| S7B ZIP yang tersedia saat preflight | `{s7b_zip_hash}` |

## Perubahan konseptual

| Perubahan | Alasan | Risiko dan mitigasi | Rollback |
|---|---|---|---|
| A1–A2: D2c memakai tabular base WDC resmi per hari/elemen; hasil D2b absolut tetap FAIL | Registration-2 belum memeriksa kerangka level meanField | Uji tidak buta karena konstanta eksploratoris telah diketahui; transformasi hanya dari metadata dan diuji silang >99,9% jam | Simpan dua hasil terpisah; kembali ke G1 HOLD registration-2 jika WDC format gagal |
| A3: bila baris G1 tumpang tindih, pilih status paling konservatif | Tabel lama tanpa prioritas | Potensi beberapa baris terpicu wajib dilaporkan seluruhnya | Nonaktifkan amandemen, gunakan status historis HOLD |
| A4: V0-A dan V0-T didaftarkan sebelum D3 | V0 peka level acuan | Belum ada PCA di S7C; jangan memilih varian sekarang | Gunakan aturan registration-2 untuk hasil lama, simpan delta |
| A5: X pada 2008-04/06/09/11 menjadi SUSPECT_DIAGNOSTIC pada tingkat deret | Inkonsistensi meanField `_y_all` sudah ditemukan di S7-B | DAT multi-tahun; delta memakai `target_year=2008`, tidak menurunkan status tahun lain atau Y/Z | Hapus lapisan delta dari analisis mendatang tanpa menimpa manifest lama |
| A6–A7: ungkap non-buta; R1 bukan target | Menjaga klaim sepadan bukti | Tidak boleh menyatakan R2/R3/R4 telah tercapai | Kembali ke klaim historis; tetap laporkan D2b/S7-C |

## Provenans ZIP S7-B

ZIP S7-B yang **tersedia saat preflight** berukuran `{s7b_zip.stat().st_size}` byte dengan SHA-256 `{s7b_zip_hash}`. Berkas eksternal lama `phase2a/S7B/S7B_review.sha256` berisi `{old_sidecar_line}` sehingga tidak cocok dengan ZIP saat ini. ZIP saat ini juga memuat `S7B_review.sha256` internal yang mengacu ke hash sebelumnya; hash ZIP yang menyertakan hash dirinya tidak dapat dipakai sebagai verifikasi paket final. Semua artefak S7-B tetap beku. Checksum pendamping yang benar dibuat di **S7C**, di luar ZIP dan dihitung dari ZIP S7-B yang tersedia; tidak ada berkas S7-B yang diubah.

## Batas dan penghentian

D2c hanya berjalan bila akuisisi dan validasi silang sumber WDC lolos. Jika format tidak tersedia atau >0,1% jam tidak konsisten >0,1 nT, G1 registration-3 HOLD baris 0a dan D2c tidak dihitung. Setelah D2c (bila lolos), forensik benchmark ditutup; tidak ada D2d. Semua hasil S7-C masuk folder baru dan dapat diabaikan untuk rollback tanpa menghapus catatan historis.
"""
    (OUT / "S7C_changes.md").write_text(changes, encoding="utf-8")
    now = dt.datetime.now(dt.timezone.utc)
    pre = {"started_utc": now.isoformat(), "started_local_Asia_Makassar": now.astimezone(ZoneInfo("Asia/Makassar")).isoformat(),
           "source_path": str(SOURCE), "source_sha256": source_digest, "copied_sha256": sha(target),
           "protocol_registration_sha256": sha(protocol_path), "registration2_sha256": sha(reg2),
           "G0_manifest": g0, "frozen_outputs_sha256_before": frozen,
           "S7B_zip_bytes": s7b_zip.stat().st_size, "S7B_zip_sha256": s7b_zip_hash,
           "S7B_old_sidecar_text": old_sidecar_line, "S7B_old_sidecar_matches_zip": old_sidecar_line.startswith(s7b_zip_hash)}
    (OUT / "S7C_preflight.json").write_text(json.dumps(pre, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT / "S7C_execution.log").write_text(f"INFO {now.isoformat()} registration-3 APPROVED source copied, {g0['rows']} G0 inputs and {len(frozen)} frozen outputs hashed before S7C\n", encoding="utf-8")
    print(f"Registered G0-registration-3 SHA-256 {source_digest}; {len(frozen)} frozen outputs; S7B ZIP {s7b_zip.stat().st_size} bytes SHA-256 {s7b_zip_hash}")


if __name__ == "__main__":
    main()
