"""Convert employment counted in another occupation system (for example Canada's NOC)
into SOC 2018 employment, so it can feed `ai_exposure.regional`.

Inputs
    --employment   CSV: region_code, region_name, occ_code, employment
                   (optional total_employment, carried through unchanged)
    --crosswalk    CSV: occ_code, soc  (optional column: weight)
                   One row per pair. One source code may map to several SOC codes
                   and vice versa.

How many-to-one and one-to-many links are split
    If the crosswalk has a `weight` column, each source code's employment is split
    in proportion to its weights. Otherwise it is split by `--split`:
      us_employment  (default) in proportion to U.S. national employment of each SOC
                     code, from the BLS file in data/raw/. Large U.S. occupations get
                     a larger share, which is usually closer to reality than an even split.
      equal          evenly across the linked SOC codes.

Usage:
    python -m ai_exposure.crosswalk --employment canada_cma_noc.csv \\
        --crosswalk noc2021_to_soc2018.csv --out canada_cma_soc.csv
"""

import argparse

import pandas as pd

from .sources import RAW


def us_soc_weights():
    df = pd.read_excel(RAW / "MSA_M2024_dl.xlsx", usecols=["O_GROUP", "OCC_CODE", "TOT_EMP"], dtype={"OCC_CODE": str})
    df = df[df.O_GROUP == "detailed"]
    df["emp"] = pd.to_numeric(df.TOT_EMP, errors="coerce")
    return df.groupby("OCC_CODE").emp.sum()


def convert(emp, cw, split="us_employment"):
    cw = cw.copy()
    if "weight" not in cw.columns:
        if split == "equal":
            cw["weight"] = 1.0
        else:
            w = us_soc_weights()
            cw["weight"] = cw.soc.map(w).fillna(0)
            # a source code whose SOC links all lack U.S. employment falls back to an even split
            zero = cw.groupby("occ_code").weight.transform("sum") == 0
            cw.loc[zero, "weight"] = 1.0
    cw["share"] = cw.weight / cw.groupby("occ_code").weight.transform("sum")
    unmatched = set(emp.occ_code) - set(cw.occ_code)
    x = emp.merge(cw[["occ_code", "soc", "share"]], on="occ_code", how="inner")
    x["employment"] = x.employment * x.share
    keys = ["region_code", "region_name", "soc"]
    extra = ["total_employment"] if "total_employment" in emp.columns else []
    agg = {"employment": "sum", **{c: "first" for c in extra}}
    out = x.groupby(keys, as_index=False).agg(agg)
    lost = emp[emp.occ_code.isin(unmatched)].employment.sum() / emp.employment.sum()
    return out, sorted(unmatched), lost


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--employment", required=True)
    p.add_argument("--crosswalk", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--split", choices=["us_employment", "equal"], default="us_employment")
    args = p.parse_args()

    emp = pd.read_csv(args.employment, dtype={"region_code": str, "occ_code": str})
    cw = pd.read_csv(args.crosswalk, dtype={"occ_code": str, "soc": str})
    out, unmatched, lost = convert(emp, cw, args.split)
    out.to_csv(args.out, index=False)
    print(f"Wrote {args.out}: {len(out)} region x SOC rows")
    print(f"Source codes with no crosswalk match: {len(unmatched)} ({lost:.1%} of employment dropped)")
    if unmatched:
        print("  e.g.", ", ".join(unmatched[:10]))


if __name__ == "__main__":
    main()
