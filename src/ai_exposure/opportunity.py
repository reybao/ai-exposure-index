"""Y-axis (AI opportunity) inputs: loaders for licensed data and a synthetic sample.

This repo does NOT ship any Lightcast or PitchBook values. To reproduce the
figures you must supply your own licensed extracts in data/private/ (gitignored),
in the format below.

Expected input format (one row per MSA, CSV):

    Figure 1, AI job posting intensity  -> data/private/ai_postings.csv
        msa_code              5-digit CBSA code, e.g. 41860
        ai_postings_per_10k   AI job postings per 10,000 workers, Dec 2022 onward

    Figure 2, AI investment            -> data/private/ai_investment.csv
        msa_code              5-digit CBSA code
        ai_investment_usd     AI-related deal value in USD, Dec 2022 onward

Any rescaling of these values (ranks, bins, normalization) is still derived
data under most licenses. Keep outputs built from them in output/private/.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .sources import ROOT

PRIVATE = ROOT / "data" / "private"
SAMPLE = ROOT / "data" / "sample"


@dataclass(frozen=True)
class Metric:
    key: str
    column: str
    private_file: str
    axis_label: str
    source_line: str
    window: str
    title: str


METRICS = {
    "postings": Metric(
        key="postings",
        column="ai_postings_per_10k",
        private_file="ai_postings.csv",
        axis_label="AI job postings per 10,000 workers (log scale)",
        source_line="AI job postings: Lightcast Data, as of April 2026 (licensed; not redistributed)",
        window="Job postings: monthly average from Dec 2022 (post-ChatGPT), per 10,000 workers (BLS OEWS).",
        title="AI Exposure vs AI Job Posting Intensity",
    ),
    "investment": Metric(
        key="investment",
        column="ai_investment_usd",
        private_file="ai_investment.csv",
        axis_label="AI investment, USD (log scale)",
        source_line="AI investment: PitchBook (licensed; not redistributed)",
        window="Investment: disclosed AI company funding, Jan 2023 to Apr 2026, by company HQ metro.",
        title="AI Exposure vs AI Investment",
    ),
}


def load(metric_key, path=None):
    """Load a licensed extract and validate its schema."""
    m = METRICS[metric_key]
    path = path or PRIVATE / m.private_file
    df = pd.read_csv(path, dtype={"msa_code": str})
    missing = {"msa_code", m.column} - set(df.columns)
    if missing:
        raise ValueError(f"{path}: missing columns {sorted(missing)}")
    df["msa_code"] = df.msa_code.str.zfill(5)
    if (df[m.column] <= 0).any():
        raise ValueError(f"{path}: {m.column} must be positive for a log axis")
    if df.msa_code.duplicated().any():
        raise ValueError(f"{path}: duplicate msa_code rows")
    return df[["msa_code", m.column]]


def make_synthetic(study_msas, seed=20261009):
    """Write clearly labeled synthetic y-axis files with the same schema.

    Values are random draws, independent of exposure and of any real dataset.
    They exist only so the pipeline runs end to end without licensed data.
    """
    SAMPLE.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    codes = study_msas.msa_code.tolist()
    post = pd.DataFrame(
        {"msa_code": codes, "ai_postings_per_10k": np.round(rng.lognormal(mean=2.0, sigma=0.8, size=len(codes)), 2)}
    )
    inv = pd.DataFrame(
        {"msa_code": codes, "ai_investment_usd": np.round(rng.lognormal(mean=19.0, sigma=1.6, size=len(codes)), -3)}
    )
    for df, name in [(post, "SYNTHETIC_ai_postings.csv"), (inv, "SYNTHETIC_ai_investment.csv")]:
        df.insert(0, "is_synthetic", True)
        df.to_csv(SAMPLE / name, index=False)
    return SAMPLE / "SYNTHETIC_ai_postings.csv", SAMPLE / "SYNTHETIC_ai_investment.csv"
