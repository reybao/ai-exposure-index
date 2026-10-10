"""Build the exposure index for any set of regions from a generic employment table.

Use this for other countries (for example Canadian CMAs) or other U.S. geographies.
The occupation scores and the method are identical to the U.S. metro index.

Input: a CSV with one row per region and SOC 2018 occupation
    region_code       any identifier (CMA code, MSA code, ...)
    region_name       display name
    soc               6-digit SOC 2018 code, formatted like 15-1252
    employment        employment in that occupation and region
    total_employment  optional; all-occupation employment in the region
                      (used only for the coverage share)

If your employment data uses another occupation system (for example Canada's NOC),
convert it first with `python -m ai_exposure.crosswalk`.

Usage:
    python -m ai_exposure.regional --employment path/to/region_soc_employment.csv \\
        --out data/processed/canada
"""

import argparse
import json
from pathlib import Path

import pandas as pd
from scipy.stats import spearmanr

from .build_index import msa_index, occupation_scores

REQUIRED = {"region_code", "region_name", "soc", "employment"}


def load_employment(path):
    df = pd.read_csv(path, dtype={"region_code": str, "soc": str})
    missing = REQUIRED - set(df.columns)
    if missing:
        raise SystemExit(f"{path}: missing columns {sorted(missing)}")
    bad = ~df.soc.str.fullmatch(r"\d{2}-\d{4}")
    if bad.any():
        raise SystemExit(f"{path}: {bad.sum()} rows have SOC codes not formatted like 15-1252")
    df = df[df.employment > 0]
    if "total_employment" in df.columns:
        total = df.groupby(["region_code", "region_name"], as_index=False).total_employment.first()
    else:
        total = df.groupby(["region_code", "region_name"], as_index=False).employment.sum()
        total = total.rename(columns={"employment": "total_employment"})
    detail = df[["region_code", "soc", "employment"]]
    return total, detail


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--employment", required=True, help="region x SOC employment CSV")
    p.add_argument("--out", required=True, help="output folder")
    args = p.parse_args()

    occ = occupation_scores()
    total, detail = load_employment(args.employment)
    # reuse the U.S. computation by mapping column names
    t = total.rename(columns={"region_code": "msa_code", "region_name": "msa_title"})
    d = detail.rename(columns={"region_code": "msa_code", "employment": "emp"})
    res = msa_index(occ, t, d).rename(columns={"msa_code": "region_code", "msa_title": "region_name"})
    res["rank_eloundou"] = res.exposure_eloundou.rank(ascending=False, method="min").astype(int)
    res["rank_anthropic"] = res.exposure_anthropic.rank(ascending=False, method="min").astype(int)
    res = res.sort_values("rank_eloundou")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    res.round({"exposure_eloundou": 6, "exposure_anthropic": 6, "coverage_share": 4}).to_csv(
        out / "region_exposure.csv", index=False)
    stats = {"n_regions": int(len(res)),
             "median_employment_coverage": round(float(res.coverage_share.median()), 4)}
    if len(res) >= 3:
        stats["spearman_eloundou_vs_anthropic"] = round(
            float(spearmanr(res.exposure_eloundou, res.exposure_anthropic)[0]), 4)
    (out / "validation.json").write_text(json.dumps(stats, indent=2) + "\n")
    print(res[["region_name", "exposure_eloundou", "exposure_anthropic", "coverage_share"]].to_string(index=False))
    print(json.dumps(stats, indent=2))
    print(f"Wrote {out / 'region_exposure.csv'}")


if __name__ == "__main__":
    main()
