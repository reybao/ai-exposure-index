"""Build the metro AI Exposure Index from public data.

Method
------
1. Occupation scores (6-digit SOC 2018):
   - Eloundou (primary): `dv_rating_beta` from occ_level.csv (GPT-4 rated,
     beta = E1 + 0.5 * E2). O*NET-SOC 8-digit codes are averaged to 6-digit SOC.
   - Anthropic (cross-validation): `observed_exposure` from job_exposure.csv.
2. Common occupation set: only SOC codes scored by BOTH sources are used, so the
   two metro indexes are built on identical employment weights.
3. Metro index = employment-weighted mean of occupation scores, using BLS OEWS
   May 2024 detailed-occupation employment for each MSA. Suppressed cells are dropped.

Outputs (data/processed/):
    occupation_exposure.csv   SOC-level scores (both sources)
    msa_exposure_all.csv      every MSA in the BLS file
    msa_exposure_study.csv    the 50-metro study universe, with ranks
    validation.json           agreement between the two methods

Usage:
    python -m ai_exposure.build_index
"""

import json

import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr

from .sources import RAW, ROOT

PROCESSED = ROOT / "data" / "processed"
CONFIG = ROOT / "config"


def occupation_scores():
    elo = pd.read_csv(RAW / "occ_level.csv")
    elo["soc"] = elo["O*NET-SOC Code"].str[:7]
    elo = (
        elo.groupby("soc")
        .agg(elo_beta=("dv_rating_beta", "mean"), onet_codes=("O*NET-SOC Code", "count"))
        .reset_index()
    )
    ant = pd.read_csv(RAW / "job_exposure.csv").rename(
        columns={"occ_code": "soc", "title": "soc_title", "observed_exposure": "ant_observed"}
    )
    occ = elo.merge(ant, on="soc", how="inner")
    return occ[["soc", "soc_title", "elo_beta", "ant_observed", "onet_codes"]].sort_values("soc")


def bls_msa():
    cols = ["AREA", "AREA_TITLE", "O_GROUP", "OCC_CODE", "TOT_EMP"]
    df = pd.read_excel(RAW / "MSA_M2024_dl.xlsx", usecols=cols, dtype={"AREA": str, "OCC_CODE": str})
    df["emp"] = pd.to_numeric(df["TOT_EMP"], errors="coerce")  # "**" = suppressed
    total = (
        df[df.O_GROUP == "total"][["AREA", "AREA_TITLE", "emp"]]
        .rename(columns={"AREA": "msa_code", "AREA_TITLE": "msa_title", "emp": "total_employment"})
    )
    detail = df[(df.O_GROUP == "detailed") & df.emp.notna()][["AREA", "OCC_CODE", "emp"]]
    return total, detail.rename(columns={"AREA": "msa_code", "OCC_CODE": "soc"})


def msa_index(occ, total, detail):
    x = detail.merge(occ[["soc", "elo_beta", "ant_observed"]], on="soc", how="inner")
    g = x.groupby("msa_code")
    out = pd.DataFrame(
        {
            "exposure_eloundou": g.apply(lambda d: np.average(d.elo_beta, weights=d.emp), include_groups=False),
            "exposure_anthropic": g.apply(lambda d: np.average(d.ant_observed, weights=d.emp), include_groups=False),
            "covered_employment": g.emp.sum(),
            "n_occupations": g.soc.nunique(),
        }
    ).reset_index()
    out = total.merge(out, on="msa_code", how="inner")
    out["coverage_share"] = out.covered_employment / out.total_employment
    return out


def main():
    PROCESSED.mkdir(parents=True, exist_ok=True)
    occ = occupation_scores()
    total, detail = bls_msa()
    allm = msa_index(occ, total, detail)

    study_cfg = pd.read_csv(CONFIG / "study_msas.csv", dtype={"msa_code": str})
    study = study_cfg.merge(allm, on="msa_code", how="left")
    missing = study[study.exposure_eloundou.isna()].msa_code.tolist()
    if missing:
        raise SystemExit(f"Study MSAs not found in BLS file: {missing}")
    study["rank_eloundou"] = study.exposure_eloundou.rank(ascending=False, method="min").astype(int)
    study["rank_anthropic"] = study.exposure_anthropic.rank(ascending=False, method="min").astype(int)
    study = study.sort_values("rank_eloundou")

    rnd = {"exposure_eloundou": 6, "exposure_anthropic": 6, "coverage_share": 4}
    occ.round({"elo_beta": 6, "ant_observed": 6}).to_csv(PROCESSED / "occupation_exposure.csv", index=False)
    allm.round(rnd).sort_values("msa_code").to_csv(PROCESSED / "msa_exposure_all.csv", index=False)
    study.round(rnd).to_csv(PROCESSED / "msa_exposure_study.csv", index=False)

    val = {
        "n_occupations_common": int(len(occ)),
        "study_50": {
            "spearman": round(float(spearmanr(study.exposure_eloundou, study.exposure_anthropic)[0]), 4),
            "pearson": round(float(pearsonr(study.exposure_eloundou, study.exposure_anthropic)[0]), 4),
            "level_ratio_eloundou_to_anthropic": round(
                float(study.exposure_eloundou.mean() / study.exposure_anthropic.mean()), 3
            ),
        },
        "all_msas": {
            "n": int(len(allm)),
            "spearman": round(float(spearmanr(allm.exposure_eloundou, allm.exposure_anthropic)[0]), 4),
        },
        "median_employment_coverage_study": round(float(study.coverage_share.median()), 4),
    }
    (PROCESSED / "validation.json").write_text(json.dumps(val, indent=2) + "\n")
    print(json.dumps(val, indent=2))
    print(f"Wrote {len(occ)} occupations, {len(allm)} MSAs, {len(study)} study metros to {PROCESSED}")


if __name__ == "__main__":
    main()
