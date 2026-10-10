"""Download the three public inputs into data/raw/ and verify checksums.

Usage:
    python -m ai_exposure.download

BLS sometimes rejects scripted requests. If that happens, download
https://www.bls.gov/oes/special-requests/oesm24ma.zip in a browser, unzip it,
and place MSA_M2024_dl.xlsx in data/raw/. The checksum is still verified.
"""

import hashlib
import io
import sys
import urllib.request
import zipfile

from .sources import RAW, SOURCES

HEADERS = {"User-Agent": "ai-exposure-index (academic research; contact via GitHub issues)"}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    ok = True
    for src in SOURCES.values():
        dest = RAW / src.filename
        if not dest.exists():
            print(f"Downloading {src.key} ...")
            try:
                blob = fetch(src.url)
                if src.url.endswith(".zip"):
                    with zipfile.ZipFile(io.BytesIO(blob)) as z:
                        member = next(n for n in z.namelist() if n.endswith(src.filename))
                        dest.write_bytes(z.read(member))
                else:
                    dest.write_bytes(blob)
            except Exception as e:  # noqa: BLE001
                print(f"  Could not download {src.key}: {e}")
                print(f"  Download manually from {src.url} and save as {dest}")
                ok = False
                continue
        digest = sha256(dest)
        if digest != src.sha256:
            print(f"  WARNING {src.filename}: checksum differs from the pinned version.")
            print(f"    expected {src.sha256}\n    got      {digest}")
            print("    Results may not match the published numbers.")
            ok = False
        else:
            print(f"  {src.filename}: checksum OK")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
