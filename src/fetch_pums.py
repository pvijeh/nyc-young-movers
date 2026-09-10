"""Download ACS 1-year PUMS person records for New York State, 2011-2024.

The API caps a query at 50 variables, so each year is two requests joined
on SERIALNO+SPORDER: core variables with replicate weights 1-40, then 41-80.
Needs CENSUS_API_KEY in the environment. Writes data/raw/pums/pums_YYYY.parquet.
"""
from pathlib import Path
import os
import sys
import pandas as pd
import requests

YEARS = [y for y in range(2011, 2025) if y != 2020]  # no standard 2020 1-year ACS
CORE = ["SERIALNO", "SPORDER", "AGEP", "SEX", "MIG", "MIGPUMA", "MIGSP", "PINCP", "PUMA", "PWGTP"]
RAW = Path(__file__).resolve().parents[1] / "data" / "raw" / "pums"


def get(year: int, vars_: list[str], key: str) -> pd.DataFrame:
    url = f"https://api.census.gov/data/{year}/acs/acs1/pums"
    r = requests.get(url, params={"get": ",".join(vars_), "for": "state:36", "key": key}, timeout=600)
    r.raise_for_status()
    rows = r.json()
    return pd.DataFrame(rows[1:], columns=rows[0]).drop(columns="state")


def main() -> int:
    key = os.environ["CENSUS_API_KEY"].rstrip(".")
    RAW.mkdir(parents=True, exist_ok=True)
    for y in YEARS:
        dest = RAW / f"pums_{y}.parquet"
        if dest.exists():
            continue
        a = get(y, CORE + [f"PWGTP{i}" for i in range(1, 41)], key)
        b = get(y, ["SERIALNO", "SPORDER"] + [f"PWGTP{i}" for i in range(41, 81)], key)
        df = a.merge(b, on=["SERIALNO", "SPORDER"], validate="1:1")
        num = ["AGEP", "SEX", "MIG", "PINCP", "PWGTP"] + [f"PWGTP{i}" for i in range(1, 81)]
        for c in num:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        df["year"] = y
        df.to_parquet(dest, index=False)
        print(f"{y}: {len(df):,} persons")
    return 0


if __name__ == "__main__":
    sys.exit(main())
