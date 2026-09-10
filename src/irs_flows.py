"""Tax-return inflows to NYC boroughs from IRS SOI county-to-county migration data.

A return "moves in" when its filing address changes to a borough from somewhere else between
two filing years. n1 = returns, n2 = individuals (filers plus dependents), agi = year-2 AGI
in thousands of dollars. Flows between the five boroughs are excluded from the NYC totals
and reported separately.

Outputs (data/processed/):
  irs_county_inflows.csv           inflows to each borough and to NYC from outside NYC, by year
  irs_ny_state_inflow_age_agi.csv  inflows to New York State by age of filer and AGI band
  irs_under26_low_agi_shares.csv   share of under-26 filers with AGI under $50k: NY in-movers, NY
                                   non-movers, in-movers to other states, non-movers elsewhere
"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "irs"
OUT = ROOT / "data" / "processed"

BOROUGHS = {"005": "Bronx", "047": "Brooklyn", "061": "Manhattan", "081": "Queens", "085": "Staten Island"}
YEARS = ["1112", "1213", "1314", "1415", "1516", "1617", "1718", "1819", "1920", "2021", "2122", "2223"]
# CPI-U, annual average (BLS), used to put year-2 AGI in 2023 dollars.
CPI = {
    2012: 229.594, 2013: 232.957, 2014: 236.736, 2015: 237.017, 2016: 240.007, 2017: 245.120,
    2018: 251.107, 2019: 255.657, 2020: 258.811, 2021: 270.970, 2022: 292.655, 2023: 304.702,
}
AGI_BANDS = {
    0: "all", 1: "$1-10k", 2: "$10-25k", 3: "$25-50k", 4: "$50-75k", 5: "$75-100k", 6: "$100-200k", 7: "$200k+",
}
AGE_BANDS = {0: "all", 1: "under 26", 2: "26-34", 3: "35-44", 4: "45-54", 5: "55-64", 6: "65+"}


def year2(code: str) -> int:
    return 2000 + int(code[2:])


def county_inflows() -> pd.DataFrame:
    rows = []
    for code in YEARS:
        df = pd.read_csv(RAW / f"countyinflow{code}.csv", dtype=str, encoding="latin-1")
        for c in ["y2_statefips", "y1_statefips"]:
            df[c] = df[c].str.strip().str.zfill(2)
        for c in ["y2_countyfips", "y1_countyfips"]:
            df[c] = df[c].str.strip().str.zfill(3)
        for c in ["n1", "n2", "agi"]:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
        nyc = df[(df.y2_statefips == "36") & df.y2_countyfips.isin(BOROUGHS)]
        yr = year2(code)
        for fips, name in BOROUGHS.items():
            d = nyc[nyc.y2_countyfips == fips]
            total = d[(d.y1_statefips == "96")].iloc[0]  # US and foreign
            foreign_n1 = d[(d.y1_statefips == "98")].n1.sum()
            intra = d[(d.y1_statefips == "36") & d.y1_countyfips.isin(BOROUGHS) & (d.y1_countyfips != fips)]
            stay = d[(d.y1_statefips == "36") & (d.y1_countyfips == fips)].iloc[0]
            rows.append(
                dict(
                    geo=name, year=yr,
                    inflow_returns=int(total.n1 - intra.n1.sum()),
                    inflow_people=int(total.n2 - intra.n2.sum()),
                    inflow_agi_k=int(total.agi - intra.agi.sum()),
                    from_other_boroughs_returns=int(intra.n1.sum()),
                    foreign_returns=int(foreign_n1),
                    nonmigrant_returns=int(stay.n1),
                    nonmigrant_agi_k=int(stay.agi),
                )
            )
        b = pd.DataFrame([r for r in rows if r["year"] == yr])
        rows.append(
            dict(
                geo="NYC", year=yr,
                inflow_returns=int(b.inflow_returns.sum()),
                inflow_people=int(b.inflow_people.sum()),
                inflow_agi_k=int(b.inflow_agi_k.sum()),
                from_other_boroughs_returns=int(b.from_other_boroughs_returns.sum()),
                foreign_returns=int(b.foreign_returns.sum()),
                nonmigrant_returns=int(b.nonmigrant_returns.sum()),
                nonmigrant_agi_k=int(b.nonmigrant_agi_k.sum()),
            )
        )
    out = pd.DataFrame(rows)
    defl = out.year.map(lambda y: CPI[2023] / CPI[y])
    out["mean_agi_in_2023usd"] = (1000 * out.inflow_agi_k / out.inflow_returns * defl).round(0)
    out["nonmigrant_mean_agi_2023usd"] = (1000 * out.nonmigrant_agi_k / out.nonmigrant_returns * defl).round(0)
    out["people_per_return"] = (out.inflow_people / out.inflow_returns).round(2)
    out["inflow_per_100_resident_returns"] = (100 * out.inflow_returns / out.nonmigrant_returns).round(2)
    return out.sort_values(["geo", "year"])


def ny_state_age_agi() -> pd.DataFrame:
    rows = []
    for code in YEARS:
        df = pd.read_csv(RAW / f"{code}inmigall.csv", dtype=str, encoding="latin-1")
        ny = df[df.statefips.str.strip().str.zfill(2) == "36"]
        for _, r in ny.iterrows():
            stub = int(r.agi_stub)
            for age_code, age in AGE_BANDS.items():
                rows.append(
                    dict(
                        year=year2(code),
                        agi_band=AGI_BANDS[stub],
                        agi_stub=stub,
                        age=age,
                        inflow_returns=int(float(r[f"inflow_n1_{age_code}"])),
                        inflow_people=int(float(r[f"inflow_n2_{age_code}"])),
                        outflow_returns=int(float(r[f"outflow_n1_{age_code}"])),
                        nonmigrant_returns=int(float(r[f"nonmig_n1_{age_code}"])),
                    )
                )
    return pd.DataFrame(rows).sort_values(["age", "agi_stub", "year"])


def under26_low_agi_shares() -> pd.DataFrame:
    low = [1, 2, 3]
    rows = []
    for code in YEARS:
        df = pd.read_csv(RAW / f"{code}inmigall.csv", dtype=str, encoding="latin-1")
        df["statefips"] = df.statefips.str.strip().str.zfill(2)
        df["agi_stub"] = df.agi_stub.astype(int)
        ny, other = df[df.statefips == "36"], df[df.statefips != "36"]

        def share(d: pd.DataFrame, col: str) -> float:
            return d[d.agi_stub.isin(low)][col].astype(float).sum() / d[d.agi_stub == 0][col].astype(float).sum()

        rows.append(
            dict(
                year=year2(code),
                ny_inmovers=share(ny, "inflow_n1_1"),
                ny_nonmovers=share(ny, "nonmig_n1_1"),
                other_states_inmovers=share(other, "inflow_n1_1"),
                other_states_nonmovers=share(other, "nonmig_n1_1"),
            )
        )
    out = pd.DataFrame(rows)
    out["ny_gap"] = out.ny_inmovers - out.ny_nonmovers
    out["other_states_gap"] = out.other_states_inmovers - out.other_states_nonmovers
    return out.round(4)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    ci = county_inflows()
    ci.to_csv(OUT / "irs_county_inflows.csv", index=False)
    st = ny_state_age_agi()
    st.to_csv(OUT / "irs_ny_state_inflow_age_agi.csv", index=False)
    shares = under26_low_agi_shares()
    shares.to_csv(OUT / "irs_under26_low_agi_shares.csv", index=False)

    cols = ["year", "inflow_returns", "inflow_people", "people_per_return", "mean_agi_in_2023usd", "inflow_per_100_resident_returns"]
    for geo in ["Manhattan", "NYC"]:
        print(geo)
        print(ci[ci.geo == geo][cols].to_string(index=False))
        print()
    young = st[(st.age == "under 26")].pivot(index="year", columns="agi_band", values="inflow_returns")
    print("NY State inflow returns, filer under 26, by AGI band")
    print(young[["all", "$1-10k", "$10-25k", "$25-50k", "$50-75k", "$75-100k", "$100-200k", "$200k+"]].to_string())
    print()
    print("Share of under-26 filers with AGI under $50k (percent)")
    print((100 * shares.set_index("year")).round(1).to_string())


if __name__ == "__main__":
    main()
