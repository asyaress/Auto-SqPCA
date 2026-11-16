"""Prepare approved S7-B amendment and per-DAT policy; no D2b computation."""
from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "phase2a/S7B"
SOURCE = Path(r"D:\Downloads\Keputusan S7-B dan Instruksi Eksekusi Claude Code (G0-registration-2).docx")
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def text(element: ET.Element) -> str:
    return "".join(t.text or "" for t in element.iter(W + "t"))


def convert_decisions() -> tuple[list[str], dict]:
    if not SOURCE.is_file():
        raise FileNotFoundError(f"Approved decision document missing: {SOURCE}")
    with ZipFile(SOURCE) as archive:
        root = ET.fromstring(archive.read("word/document.xml"))
    body = root.find(W + "body")
    if body is None:
        raise RuntimeError("DOCX word/document.xml has no w:body")
    lines = []
    paragraphs = []
    tables = []
    for element in body:
        if element.tag == W + "p":
            content = text(element)
            if not content.strip():
                continue
            ppr = element.find(W + "pPr")
            style = ppr.find(W + "pStyle") if ppr is not None else None
            style_name = style.attrib.get(W + "val", "") if style is not None else ""
            paragraphs.append(content)
            if style_name.startswith("Heading"):
                level = min(int(style_name.replace("Heading", "")), 6)
                lines.append("#" * level + " " + content)
            elif style_name == "ListParagraph":
                lines.append("- " + content)
            elif style_name == "Code":
                lines.extend(["```text", content, "```"])
            else:
                lines.append(content)
            lines.append("")
        elif element.tag == W + "tbl":
            rows = [[text(cell) for cell in row.findall(W + "tc")]
                    for row in element.findall(W + "tr")]
            if not rows or len({len(row) for row in rows}) != 1:
                raise RuntimeError("Empty/ragged DOCX decision table")
            tables.append(rows)
            def escape(cell: str) -> str:
                return cell.replace("|", r"\|").replace("\n", "<br>")
            lines.append("| " + " | ".join(map(escape, rows[0])) + " |")
            lines.append("| " + " | ".join(["---"] * len(rows[0])) + " |")
            for row in rows[1:]:
                lines.append("| " + " | ".join(map(escape, row)) + " |")
            lines.append("")
        elif element.tag != W + "sectPr":
            raise RuntimeError(f"Unconverted DOCX body element: {element.tag}")
    full = "\n".join(lines).rstrip() + "\n"
    if len(tables) != 5 or len(paragraphs) < 50:
        raise RuntimeError(f"Decision conversion incomplete: {len(paragraphs)} paragraphs, {len(tables)} tables")
    for k in range(1, 12):
        if not any(row[0] == f"K{k}" for row in tables[0][1:]):
            raise RuntimeError(f"Decision K{k} lost in conversion")
    for paragraph in paragraphs:
        if paragraph not in full:
            raise RuntimeError(f"Decision paragraph lost: {paragraph[:80]}")
    for table in tables:
        for row in table:
            for cell in row:
                if cell.replace("|", r"\|").replace("\n", "<br>") not in full:
                    raise RuntimeError(f"Decision table cell lost: {cell[:80]}")
    output = OUT / "S7B_decisions_approved.md"
    output.write_text(full, encoding="utf-8")
    return lines, {"source_path": str(SOURCE), "source_sha256": sha(SOURCE),
                   "markdown_sha256": sha(output), "paragraphs": len(paragraphs),
                   "tables": len(tables), "table_rows": [len(t) for t in tables],
                   "content_preservation": "all source paragraph and table-cell text located in Markdown; table pipes escaped"}


def development_evidence(paths: set[str]) -> dict[str, set[str]]:
    evidence: dict[str, set[str]] = defaultdict(set)
    def add(path: str, source: str) -> None:
        if path in paths:
            evidence[path].add(source)
    d1 = json.loads((ROOT / "phase2a/D1/D1_validation.json").read_text(encoding="utf-8"))
    for path in d1["input_sha256"]:
        add(path, "D1_validation.input_sha256")
    for row in read_csv(ROOT / "phase2a/D1/D1_evidence.csv"):
        add(row["source_file"], "D1_evidence.source_file")
    for row in read_csv(ROOT / "phase2a/D2/D2_meanfield_anomaly.csv"):
        for key in ("Y_file", "Z_file"):
            add(row[key], "D2_meanfield_anomaly." + row["record_type"])
    for row in read_csv(ROOT / "phase2a/D2/D2_benchmark_offset.csv"):
        add(row["source_file"], "D2_benchmark_offset")
    for row in read_csv(ROOT / "phase2a/S7/S7_mode_consistency.csv"):
        for path in re.findall(r"phase2a/raw/mendeley/[^|:]+?\.dat", row["observed_and_prediction_input_sha256"]):
            add(path.strip(), "S7_mode_consistency")
    for row in read_csv(ROOT / "phase2a/S7/S7_sq_baseline_diagnostics.csv"):
        for path in row["source_path"].split("|"):
            add(path, "S7_sq_baseline_diagnostics")
    return evidence


def policy() -> dict:
    src = read_csv(ROOT / "phase2a/S7/S7_benchmark_manifest.csv")
    if len(src) != 684 or len({r["relative_path"] for r in src}) != 684:
        raise RuntimeError("S7 benchmark manifest must have 684 unique DAT")
    paths = {r["relative_path"] for r in src}
    evidence = development_evidence(paths)
    out = []
    for row in src:
        path = row["relative_path"]
        if sha(ROOT / path) != row["sha256"]:
            raise RuntimeError(f"S7 DAT SHA-256 mismatch: {path}")
        family = row["family"]
        comp = row["component"]
        month = int(row["month"])
        name = Path(path).name
        original = row["status"]
        if original == "UNUSABLE_FOR_NUMERIC_BENCHMARK":
            allowed = "EXCLUDED"
            reason = "Six February Y meanField/mode DAT byte-identical to Z counterpart; invalid Y numeric target"
        elif family == "IQD Sq and SD":
            allowed = "ABSOLUTE_REPORTED_ONLY"
            reason = ""
        elif original == "SUSPECT":
            allowed = "SUSPECT_DIAGNOSTIC"
            reason = ""
        else:
            allowed = "ORIGINAL_ABSOLUTE"
            reason = ""
        if family == "IQD Sq and SD" or re.match(r"COI_[XYZ]_PC[123]_m\d\d\.dat$", name) or re.match(r"COI_[XYZ]_VF[123]_m\d\d\.dat$", name):
            scope = "ANNUAL_AND_ALL"
        elif "_y_all" in name:
            scope = "ALL_YEARS"
        else:
            scope = "ANNUAL"
        seen = path in evidence
        d3_eligible = family == "PCA modes" and month != 2 and allowed == "ORIGINAL_ABSOLUTE"
        out.append({"relative_path": path, "sha256": row["sha256"], "family": family,
                    "component": comp, "month": f"{month:02d}", "year_scope": scope,
                    "status_original_S7": original, "allowed_use": allowed,
                    "excluded_reason": reason, "development_seen": str(seen).lower(),
                    "development_seen_evidence": "|".join(sorted(evidence.get(path, set()))),
                    "d3_eligible": str(d3_eligible).lower(),
                    "validation_limitations": row["checks_and_limitations"] +
                    ("; file-level DEVELOPMENT_SEEN is conservative; no comparison trace found" if not seen else
                     "; file-level DEVELOPMENT_SEEN because at least one comparison was logged")})
    counts = Counter(r["allowed_use"] for r in out)
    original_counts = Counter(r["status_original_S7"] for r in out)
    if original_counts != {"VERIFIED": 624, "SUSPECT": 54, "UNUSABLE_FOR_NUMERIC_BENCHMARK": 6}:
        raise RuntimeError(f"S7 status reconciliation failed: {original_counts}")
    if counts != {"ORIGINAL_ABSOLUTE": 624, "ABSOLUTE_REPORTED_ONLY": 36,
                  "SUSPECT_DIAGNOSTIC": 18, "EXCLUDED": 6}:
        raise RuntimeError(f"Approved policy counts failed: {counts}")
    if any(r["month"] == "02" and r["d3_eligible"] != "false" for r in out):
        raise RuntimeError("February D3 eligibility leak")
    if any(r["allowed_use"] == "EXCLUDED" and not r["excluded_reason"] for r in out):
        raise RuntimeError("Excluded DAT lacks reason")
    if any(r["allowed_use"] not in {"ORIGINAL_ABSOLUTE", "ABSOLUTE_REPORTED_ONLY",
                                     "SUSPECT_DIAGNOSTIC", "EXCLUDED"} for r in out):
        raise RuntimeError("Invalid allowed_use")
    fields = list(out[0])
    with (OUT / "S7B_benchmark_policy.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(out)
    return {"rows": len(out), "allowed_use_counts": dict(counts),
            "original_status_counts": dict(original_counts),
            "development_seen_true_files": sum(r["development_seen"] == "true" for r in out),
            "development_seen_false_no_trace_files": sum(r["development_seen"] == "false" for r in out),
            "d3_eligible_files": sum(r["d3_eligible"] == "true" for r in out),
            "unique_paths": len(paths), "all_sha256_match_S7": True,
            "file_level_seen_rule": "true if any D1/D2/S7-A comparison trace names DAT; false if none found; hash-only D2 Y/Z pair checks included by explicit user rule on compared files"}


def amendment(lines: list[str], provenance: dict, policy_summary: dict) -> None:
    first_instruction = next(i for i, line in enumerate(lines) if line.startswith("## Instruksi untuk Claude Code"))
    approved_body = "\n".join(lines[:first_instruction]).rstrip()
    preface = (
        "# Amandemen resmi G0-registration-2 untuk Fase 2A\n\n"
        "**Status: APPROVED.** Berlaku 13 November 2026 melalui delegasi peneliti utama yang dinyatakan dalam dokumen keputusan sumber. Protokol G0-registration-1 tetap utuh. Isi keputusan K1–K11 dan tabel di bawah disalin dari dokumen resmi; instruksi operasional untuk Claude Code di akhir sumber tersedia utuh dalam `S7B_decisions_approved.md`.\n\n"
        f"Sumber: `{provenance['source_path']}`; SHA-256 DOCX `{provenance['source_sha256']}`; "
        f"SHA-256 konversi Markdown `{provenance['markdown_sha256']}`. Dokumen sumber tidak berada di working directory saat preflight; ditemukan di lokasi tersebut.\n\n"
        "## Penerapan kebijakan per DAT\n\n"
        f"Manifest `S7B_benchmark_policy.csv` berisi {policy_summary['rows']} DAT: "
        f"ORIGINAL_ABSOLUTE={policy_summary['allowed_use_counts']['ORIGINAL_ABSOLUTE']}, "
        f"ABSOLUTE_REPORTED_ONLY={policy_summary['allowed_use_counts']['ABSOLUTE_REPORTED_ONLY']}, "
        f"SUSPECT_DIAGNOSTIC={policy_summary['allowed_use_counts']['SUSPECT_DIAGNOSTIC']}, "
        f"EXCLUDED={policy_summary['allowed_use_counts']['EXCLUDED']}. "
        "Pengecualian tetap berada dalam target_total. `development_seen` dicatat pada tingkat DAT bila ada jejak perbandingan dalam D1/D2/S7-A; hal itu tidak membuktikan seluruh seri dalam berkas telah dianalisis. "
        "Untuk denominator prospektif, hitung kategori berurutan dan saling eksklusif: EXCLUDED, lalu SUSPECT_DIAGNOSTIC, lalu DEVELOPMENT_SEEN pada sisa, lalu ELIGIBLE_PROSPECTIVE. Laporkan jumlah label development_seen mentah secara terpisah agar tidak terjadi pengurangan ganda.\n\n"
        "## Aturan klasifikasi D2b yang tumpang tindih\n\n"
        "MATCH dan QUANT pada sumber dapat sama-sama benar untuk |d| di atas 0,02 nT hingga batas MATCH. Kode D2b mencatat semua predikat yang benar, overlap, dan gabungan MATCH∪QUANT tanpa prioritas baru. Jika ambiguitas mengubah baris keputusan G1, keputusan ditandai UNRESOLVED. Ini mencatat masalah logika sumber, bukan mengubah ambang.\n\n"
        "## Teks keputusan resmi yang berlaku\n\n")
    (OUT / "S7B_protocol_amendment.md").write_text(preface + approved_body + "\n", encoding="utf-8")


def changes(provenance: dict) -> None:
    old = ROOT / "phase2a/G0/Protokol Final Fase 2A Replikasi Morozova & Rebbah (2023) untuk Auto-SqPCA.docx"
    new = OUT / "S7B_protocol_amendment.md"
    body = f"""# Perubahan konseptual G0-registration-2 terhadap G0-registration-1

Tanggal berlaku: 13 November 2026. Status: **APPROVED** melalui delegasi peneliti utama sebagaimana dinyatakan dalam dokumen keputusan. Sumber DOCX berada di `{provenance['source_path']}`; tidak ditemukan di working directory pada preflight.

| Artefak | SHA-256 |
|---|---|
| Protokol G0-registration-1 (tidak diubah) | `{sha(old)}` |
| Keputusan sumber DOCX G0-registration-2 | `{provenance['source_sha256']}` |
| Konversi keputusan Markdown | `{provenance['markdown_sha256']}` |
| Amandemen resmi Markdown | `{sha(new)}` |

## Perubahan, alasan, risiko, rollback

| Perubahan | Alasan dari keputusan | Risiko dan batas | Rollback |
|---|---|---|---|
| K1–K2: ambang absolut Sq ≤0,1 nT tetap; metrik kebal offset deskriptif dan uji kesepakatan G4 | 0/18 kontrol gagal absolut tetapi bentuk dekat | Metrik bentuk tidak boleh menjadi PASS Tingkat 1 | Kembali memakai hanya metrik absolut lama; pertahankan semua FAIL |
| K3–K5: development_seen, Februari tidak memilih D3, enam Y dikecualikan | Menghindari kebocoran informasi dan target salah label | Penyebut prospektif menyusut; pengecualian tidak boleh hilang | Nonaktifkan lapisan kebijakan, jangan ubah file sumber atau jejak audit |
| K6–K7: F ditunda untuk PCA XYZ; IQD Feb 2016 Q1–Q5 tetap provisional | Analisis asal memakai XYZ; GFZ menempatkan 29 Feb sebagai Q5 | F harus dibuka kembali bila pemicu K6 terjadi; IQD belum confirmed | Kembalikan status F ke unresolved dan catat 2016 sebagai provisional |
| K8–K9: satu D2b, lalu tutup forensik | Menguji meanField tanpa PCA dan mencegah audit tanpa akhir | Versi historis penulis tidak dapat dipastikan | Laporkan D2b sebagai diagnostik terpisah; status lama tetap beku |
| K10–K11: kriteria henti pilot dan jalur loader tanpa analisis | Membatasi klaim dan pekerjaan lanjutan | K10 tidak boleh dieksekusi sebelum pilot G2; jalur K11 tidak memvalidasi Sq | Jangan jalankan jalur tersebut sampai instruksi baru |

Perubahan hanya berlaku sebagai lapisan analisis baru di `phase2a/S7B/`. Rollback tidak menghapus artefak S7-B; pilih kembali aturan G0-registration-1 untuk analisis berikutnya dan laporkan perbedaan versi. Tidak ada berkas Fase 1/G0/D1/D2/S7-A atau data mentah yang ditimpa.
"""
    (OUT / "S7B_changes.md").write_text(body, encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    lines, provenance = convert_decisions()
    pol = policy()
    amendment(lines, provenance, pol)
    changes(provenance)
    (OUT / "S7B_preparation.json").write_text(json.dumps({"decision_conversion": provenance,
        "benchmark_policy": pol, "amendment_sha256": sha(OUT / "S7B_protocol_amendment.md"),
        "changes_sha256": sha(OUT / "S7B_changes.md")}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"source_sha256": provenance["source_sha256"], **pol}, ensure_ascii=False))


if __name__ == "__main__":
    main()
