"""Public input files: where they come from, which version is pinned, and their checksums.

Every file listed here is redistributable or freely downloadable. Licensed data
(Lightcast, PitchBook) is never listed here and never downloaded by this repo.
"""

from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"


@dataclass(frozen=True)
class Source:
    key: str
    filename: str
    url: str
    sha256: str
    license: str
    citation: str
    note: str = ""


SOURCES = {
    "eloundou": Source(
        key="eloundou",
        filename="occ_level.csv",
        url="https://raw.githubusercontent.com/openai/GPTs-are-GPTs/main/data/occ_level.csv",
        sha256="40c74f53de40aec91c0017d80690cbba915f83a8bb414bcf2f884692f1749acb",
        license="MIT (openai/GPTs-are-GPTs)",
        citation=(
            "Eloundou, T., Manning, S., Mishkin, P., & Rock, D. (2024). GPTs are GPTs: "
            "Labor market impact potential of LLMs. Science, 384(6702)."
        ),
    ),
    "anthropic": Source(
        key="anthropic",
        filename="job_exposure.csv",
        url=(
            "https://huggingface.co/datasets/Anthropic/EconomicIndex/resolve/main/"
            "labor_market_impacts/job_exposure.csv"
        ),
        sha256="4f0a3adf5feeb2ec5f5d02ab18cc5e851a2a4b8470bde84c0c9335017be12d68",
        license="CC BY (Anthropic Economic Index); attribution required",
        citation="Anthropic Economic Index (2026), labor_market_impacts/job_exposure.csv.",
        note="Anthropic updates this dataset. The checksum pins the version used here.",
    ),
    "bls_msa": Source(
        key="bls_msa",
        filename="MSA_M2024_dl.xlsx",
        url="https://www.bls.gov/oes/special-requests/oesm24ma.zip",
        sha256="2a172aed29693f50afa398be03fd107ce6bfff8b04e5fd163b4c5ddcf941d6ec",
        license="Public domain (U.S. Bureau of Labor Statistics)",
        citation="U.S. Bureau of Labor Statistics, Occupational Employment and Wage Statistics, May 2024, MSA file.",
        note="The zip contains oesm24ma/MSA_M2024_dl.xlsx; the checksum is for the xlsx.",
    ),
}
