"""Pre-push check: make sure no value from a licensed file appears in tracked files.

Usage:
    python scripts/leak_check.py data/private/ai_postings.csv [more.csv ...]

What it checks, against every file `git ls-files` would publish:
  1. Licensed file names or paths are not tracked.
  2. No numeric value from the licensed files appears as text (several roundings).
  3. Tracked notebooks have no outputs, and no HTML file is tracked.
Exit code 1 if anything is found.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def tracked_files():
    out = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"],
                         cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return [ROOT / p for p in out.splitlines() if p]


def needles(paths):
    vals = set()
    for p in paths:
        df = pd.read_csv(p, dtype={"msa_code": str})
        for col in df.select_dtypes("number").columns:
            for v in df[col].dropna():
                if abs(v) < 1e-9:
                    continue
                for d in (1, 2, 3, 4):
                    s = f"{v:.{d}f}"
                    if len(s.replace(".", "").lstrip("0-")) >= 4:  # skip short, ambiguous strings
                        vals.add(s)
                if float(v).is_integer() and abs(v) >= 1000:
                    vals.add(str(int(v)))
    return vals


def main(private_paths):
    problems = []
    files = tracked_files()
    names = {Path(p).name for p in private_paths}
    for f in files:
        rel = f.relative_to(ROOT)
        in_private_dir = str(rel).startswith(("data/private/", "output/private/"))
        if f.name in names or (in_private_dir and f.name not in {"README.md", ".gitkeep"}):
            problems.append(f"licensed path is tracked: {rel}")
        if f.suffix == ".html":
            problems.append(f"HTML file tracked (may embed data): {rel}")
        if f.suffix == ".ipynb":
            nb = json.loads(f.read_text())
            if any(c.get("outputs") for c in nb.get("cells", [])):
                problems.append(f"notebook has outputs: {rel}")

    vals = needles(private_paths) if private_paths else set()
    pattern = re.compile("|".join(re.escape(v) for v in sorted(vals, key=len, reverse=True))) if vals else None
    if pattern:
        for f in files:
            if f.suffix.lower() in {".png", ".jpg", ".pdf", ".xlsx", ".zip"} or not f.exists():
                continue
            text = f.read_text(errors="ignore")
            for m in pattern.finditer(text):
                # ignore matches that are part of a longer number
                a, b = m.start(), m.end()
                if (a and text[a - 1].isdigit()) or (b < len(text) and text[b].isdigit()):
                    continue
                problems.append(f"value {m.group()} from licensed data found in {f.relative_to(ROOT)}")
                break

    print(f"Scanned {len(files)} files against {len(vals)} licensed values.")
    if problems:
        print("FOUND PROBLEMS:")
        for p in problems:
            print("  -", p)
        sys.exit(1)
    print("OK: nothing from the licensed files is in the publishable set.")


if __name__ == "__main__":
    main([a for a in sys.argv[1:] if Path(a).exists()])
