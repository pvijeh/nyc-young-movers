"""Download Census Population Estimates (PEP) county age/sex files for New York State.

Files land in data/raw/. Re-running skips files that already exist.

Vintage 2020 (2010-2020): 5-year age groups only (AGESEX file).
Vintage 2025 (2020-2025): 5-year age groups (AGESEX) and single year of age (SYASEX).
"""
from pathlib import Path
import sys
import requests

BASE = "https://www2.census.gov/programs-surveys/popest/datasets"
FILES = {
    "CC-EST2020-AGESEX-36.csv": f"{BASE}/2010-2020/counties/asrh/CC-EST2020-AGESEX-36.csv",
    "CC-EST2025-AGESEX-36.csv": f"{BASE}/2020-2025/counties/asrh/cc-est2025-agesex-36.csv",
    "cc-est2025-syasex-36.csv": f"{BASE}/2020-2025/counties/asrh/cc-est2025-syasex-36.csv",
}
RAW = Path(__file__).resolve().parents[1] / "data" / "raw"


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    for name, url in FILES.items():
        dest = RAW / name
        if dest.exists():
            print(f"have {name}")
            continue
        r = requests.get(url, timeout=120)
        r.raise_for_status()
        dest.write_bytes(r.content)
        print(f"got  {name} ({len(r.content):,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
