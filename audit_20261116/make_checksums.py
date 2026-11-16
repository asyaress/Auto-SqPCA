"""Write an audit-only SHA-256 list, excluding itself and local demo byproducts."""
from __future__ import annotations

import hashlib
from pathlib import Path

root=Path(__file__).resolve().parent
lines=[]
for path in sorted(root.rglob("*")):
    if not path.is_file() or path.name=="checksums.sha256" or any(x in {"demo","clean_demo","__pycache__"} for x in path.relative_to(root).parts):
        continue
    # Windows CSV/redirected logs use CRLF; archive text with stable LF endings.
    if path.suffix.lower() in {".csv", ".json", ".log", ".md", ".py"}:
        original = path.read_bytes()
        normalized = original.replace(b"\r\n", b"\n")
        if normalized != original: path.write_bytes(normalized)
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):h.update(block)
    lines.append(f"{h.hexdigest()}  audit_20261116/{path.relative_to(root).as_posix()}")
with (root/"checksums.sha256").open("w", encoding="utf-8", newline="\n") as f:
    f.write("\n".join(lines)+"\n")
print(f"{len(lines)} audit files hashed")
