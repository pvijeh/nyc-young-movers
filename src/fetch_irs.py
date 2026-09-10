"""Download IRS SOI migration files, filing years 2011-12 through 2022-23.

countyinflowYYYY.csv  county-to-county inflows: returns (n1), individuals (n2), AGI ($000s)
YYYYinmigall.csv      state-level flows by AGI band and age of primary filer
"""
from pathlib import Path
import sys
import requests

BASE = "https://www.irs.gov/pub/irs-soi"
YEARS = ["1112", "1213", "1314", "1415", "1516", "1617", "1718", "1819", "1920", "2021", "2122", "2223"]
RAW = Path(__file__).resolve().parents[1] / "data" / "raw" / "irs"


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    for y in YEARS:
        for name in (f"countyinflow{y}.csv", f"{y}inmigall.csv"):
            dest = RAW / name
            if dest.exists():
                continue
            r = requests.get(f"{BASE}/{name}", timeout=120)
            r.raise_for_status()
            dest.write_bytes(r.content)
            print(f"got {name} ({len(r.content):,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
