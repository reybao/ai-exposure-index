# data/private (gitignored)

Put your own licensed extracts here. Nothing in this folder except this README is ever committed.

| File | Columns | Used for |
|---|---|---|
| `ai_postings.csv` | `msa_code`, `ai_postings_per_10k` | Figure 1, AI job posting intensity (Lightcast or equivalent) |
| `ai_investment.csv` | `msa_code`, `ai_investment_usd` | Figure 2, AI investment (PitchBook or equivalent) |

`msa_code` is the 5-digit CBSA code used by BLS (see `config/study_msas.csv`). Both measures should start in December 2022.

Rankings, bins or normalized versions of these values are still derived data. Figures built from them are written to `output/private/`, also gitignored.
