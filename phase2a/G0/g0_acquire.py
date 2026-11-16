#!/usr/bin/env python3
"""Unduh input mentah G0 secara berurutan dan catat setiap respons."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import time
from urllib.parse import urlparse
from zipfile import ZipFile, BadZipFile

import requests

ROOT = Path(__file__).resolve().parents[1]
G0 = ROOT/'G0'
RAW = ROOT/'raw'
EVENTS = G0/'download_events.jsonl'
MENDELEY_URL = 'https://data.mendeley.com/public-api/zip/jcmdrm5f5x/download/1'
WDC_BASE = 'https://wdcapi.bgs.ac.uk/data/zipped-data/hour/COI'
GFZ_BASE = 'https://datapub.gfz-potsdam.de/download/10.5880.Kp.0001/Quiet_Disturbed_Days'


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as raw:
        for block in iter(lambda: raw.read(1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()


def valid_zip(path: Path) -> bool:
    try:
        with ZipFile(path) as archive:
            return len(archive.infolist()) > 0 and archive.testzip() is None
    except (BadZipFile, OSError, EOFError):
        return False


def record(item: dict) -> dict:
    item['recorded_utc'] = datetime.now(timezone.utc).isoformat()
    G0.mkdir(parents=True, exist_ok=True)
    with EVENTS.open('a', encoding='utf-8') as log:
        log.write(json.dumps(item, ensure_ascii=False)+'\n')
    print(item['source'], item.get('year',''), item['status'],
          item.get('bytes',0), item.get('error','')[:160], flush=True)
    return item


def fetch(session: requests.Session, source: str, year: int | None,
          url: str, target: Path, *, zip_expected: bool) -> dict:
    target.parent.mkdir(parents=True, exist_ok=True)
    base = {'source': source, 'year': year, 'url': url,
            'path': str(target.resolve()), 'http_status': None,
            'bytes': 0, 'sha256': None, 'error': '', 'final_host': None}
    if target.exists() and target.stat().st_size > 0:
        if zip_expected and not valid_zip(target):
            return record(base | {'status': 'LOCAL_INVALID',
                                  'error': f'ZIP cache tidak valid: {target}'})
        return record(base | {'status': 'CACHED', 'bytes': target.stat().st_size,
                              'sha256': sha256(target)})
    temp = target.with_name(target.name+'.part')
    for attempt in range(3):
        try:
            with session.get(url, stream=True, timeout=(20, 300)) as response:
                base['http_status'] = response.status_code
                base['final_host'] = urlparse(response.url).hostname
                if response.status_code == 202:
                    return record(base | {'status': 'NO_DATA',
                                          'error': response.text[:1000]})
                if response.status_code != 200:
                    body = response.text[:1000]
                    error = f'HTTP {response.status_code}: {body}'
                    if response.status_code in (400, 401, 403, 404, 413, 422, 451):
                        return record(base | {'status': 'HTTP_ERROR', 'error': error})
                    raise requests.HTTPError(error)
                expected = response.headers.get('Content-Length')
                with temp.open('wb') as out:
                    for block in response.iter_content(chunk_size=1024*1024):
                        if block:
                            out.write(block)
                size = temp.stat().st_size
                encoding = response.headers.get('Content-Encoding', 'identity').lower()
                if expected is not None and encoding in ('identity', '') and size != int(expected):
                    raise IOError(f'Content-Length {expected}, diterima {size} byte')
                if zip_expected and not valid_zip(temp):
                    raise BadZipFile(f'HTTP 200 tetapi ZIP/CRC invalid: {temp}')
                temp.replace(target)
                return record(base | {'status': 'DOWNLOADED', 'bytes': size,
                                      'sha256': sha256(target)})
        except (requests.RequestException, OSError, BadZipFile, ValueError) as exc:
            base['error'] = f'{type(exc).__name__}: {exc}'
            temp.unlink(missing_ok=True)
            if attempt < 2:
                time.sleep(min(2**attempt, 8))
    return record(base | {'status': 'DOWNLOAD_ERROR'})


def extract_mendeley(archive_path: Path, output: Path) -> dict:
    if not valid_zip(archive_path):
        return record({'source': 'MENDELEY_EXTRACT', 'status': 'INVALID_ZIP',
                       'path': str(archive_path.resolve()),
                       'error': 'Arsip Mendeley tidak valid'})
    output.mkdir(parents=True, exist_ok=True)
    root = output.resolve()
    count = 0
    total = 0
    with ZipFile(archive_path) as archive:
        names = [entry.filename for entry in archive.infolist() if not entry.is_dir()]
        if len(names) != len(set(name.lower() for name in names)):
            raise ValueError('Nama anggota Mendeley duplikat pada filesystem Windows')
        for member in archive.infolist():
            relative = Path(member.filename)
            if relative.is_absolute() or '..' in relative.parts:
                raise ValueError(f'Nama anggota ZIP tidak aman: {member.filename!r}')
            target = (output/relative).resolve()
            if not target.is_relative_to(root):
                raise ValueError(f'Anggota ZIP keluar dari folder raw: {member.filename!r}')
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                if target.stat().st_size != member.file_size:
                    raise ValueError(f'File ekstraksi berbeda ukuran: {target}')
                with archive.open(member) as src, target.open('rb') as dst:
                    while True:
                        a, b = src.read(1024*1024), dst.read(1024*1024)
                        if a != b:
                            raise ValueError(f'File ekstraksi berbeda isi: {target}')
                        if not a:
                            break
            else:
                temp = target.with_name(target.name+'.part')
                with archive.open(member) as src, temp.open('wb') as dst:
                    shutil.copyfileobj(src, dst, length=1024*1024)
                temp.replace(target)
            count += 1
            total += member.file_size
    return record({'source': 'MENDELEY_EXTRACT', 'status': 'OK',
                   'path': str(root), 'files': count, 'bytes': total,
                   'error': ''})


def main() -> None:
    session = requests.Session()
    session.headers['User-Agent'] = 'AutoSqPCA-G0-InputAudit/1.0 (research)'
    mendeley = fetch(session, 'MENDELEY_V1', None, MENDELEY_URL,
                     RAW/'mendeley'/'jcmdrm5f5x-1.zip', zip_expected=True)
    if mendeley['status'] in ('DOWNLOADED', 'CACHED'):
        extract_mendeley(RAW/'mendeley'/'jcmdrm5f5x-1.zip',
                         RAW/'mendeley'/'jcmdrm5f5x-1')
    for year in range(2007, 2018):
        url = f'{WDC_BASE}?years={year}&file_format=iaga&orientation=XYZF'
        fetch(session, 'WDC_COI_HOURLY', year, url,
              RAW/'wdc_hourly'/f'COI_{year}_hour_iaga_XYZF.zip', zip_expected=True)
        time.sleep(1)
    for year in range(2007, 2018):
        url = f'{GFZ_BASE}/QD_days{year}.txt'
        fetch(session, 'GFZ_IQD_IDD', year, url,
              RAW/'gfz'/f'QD_days{year}.txt', zip_expected=False)
        time.sleep(0.5)


if __name__ == '__main__':
    main()
