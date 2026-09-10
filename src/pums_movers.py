"""ACS 1-year PUMS: people aged 20-29 who lived outside NYC a year earlier.

Geography is the PUMA, which in NYC is a community district (or a pair of
small ones). 2010 PUMAs are used through the 2021 ACS, 2020 PUMAs from 2022;
both are mapped to community districts so neighborhoods line up across years.
Manhattan CDs 4, 5 and 6 are pooled because the two vintages split them
differently.

Standard errors use the 80 replicate weights (successive difference
replication): SE^2 = (4/80) * sum((rep - full)^2). MOE is 90%.

Writes data/processed/pums_*.csv.
"""
from pathlib import Path
import re
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "pums"
OUT = ROOT / "data" / "processed"
YEARS = [y for y in range(2011, 2025) if y != 2020]
REPS = [f"PWGTP{i}" for i in range(1, 81)]

# CPI-U annual average, all items, U.S. city average (BLS)
CPI = {2011: 224.939, 2012: 229.594, 2013: 232.957, 2014: 236.736, 2015: 237.017,
       2016: 240.007, 2017: 245.120, 2018: 251.107, 2019: 255.657, 2021: 270.970,
       2022: 292.655, 2023: 304.702, 2024: 313.689}

BOROUGH = {"2010": {37: "Bronx", 38: "Manhattan", 39: "Staten Island", 40: "Brooklyn", 41: "Queens"},
           "2020": {41: "Manhattan", 42: "Bronx", 43: "Brooklyn", 44: "Queens", 45: "Staten Island"}}
# MIGPUMA (residence one year ago) is borough-level in NYC in both vintages
NYC_MIGPUMA = {"2010": {3700, 3800, 3900, 4000, 4100}, "2020": {4100, 4200, 4300, 4400, 4500}}
INCOME_BANDS = [(-np.inf, 25_000, "<$25k"), (25_000, 50_000, "$25-50k"),
                (50_000, 100_000, "$50-100k"), (100_000, np.inf, "$100k+")]


def vintage(year: int) -> str:
    return "2010" if year <= 2021 else "2020"


def crosswalk() -> pd.DataFrame:
    """PUMA -> borough, community-district unit, neighborhood label."""
    names = pd.read_csv(ROOT / "data" / "puma_names_nyc.csv", dtype=str)
    rows = []
    for _, r in names.iterrows():
        m = re.search(r"NYC-(.+?) Community Districts? (\d+)(?: & (\d+))?--(.+)", r["name"])
        boro, cds = m.group(1), sorted(int(c) for c in (m.group(2), m.group(3)) if c)
        if boro == "Manhattan" and cds[0] in (4, 5, 6):
            cds = [4, 5, 6]
        rows.append(dict(vintage=r["vintage"], puma=int(r["puma"]), borough=boro,
                         cd=f"{boro} CD {'-'.join(map(str, cds))}", label_raw=m.group(4)))
    xw = pd.DataFrame(rows)
    lab = xw[xw.vintage == "2020"].drop_duplicates("cd").set_index("cd").label_raw
    lab["Manhattan CD 4-5-6"] = "Chelsea, Hell's Kitchen & Midtown"
    xw["neighborhood"] = xw.cd.map(lab)
    return xw.drop(columns="label_raw")


def load(year: int, xw: pd.DataFrame) -> pd.DataFrame:
    df = pd.read_parquet(RAW / f"pums_{year}.parquet")
    v = vintage(year)
    df["puma"] = df.PUMA.astype(int)
    df = df.merge(xw[xw.vintage == v][["puma", "borough", "cd", "neighborhood"]], on="puma")
    df["MIGSP"] = pd.to_numeric(df.MIGSP, errors="coerce")
    df["MIGPUMA"] = pd.to_numeric(df.MIGPUMA, errors="coerce")
    from_abroad = df.MIG == 2
    from_us_outside_nyc = (df.MIG == 3) & ~((df.MIGSP == 36) & df.MIGPUMA.isin(NYC_MIGPUMA[v]))
    df["inmover"] = from_abroad | from_us_outside_nyc
    df["nonmover"] = df.MIG == 1
    df["young"] = df.AGEP.between(20, 29)
    df["income_2024"] = df.PINCP * CPI[2024] / CPI[year]
    df["low_income"] = df.income_2024 < 50_000
    df["band"] = pd.cut(df.income_2024, [b[0] for b in INCOME_BANDS] + [np.inf],
                        labels=[b[2] for b in INCOME_BANDS], right=False)
    df["year"] = year
    return df


def est(df: pd.DataFrame, mask: pd.Series) -> tuple[float, float]:
    """Weighted count of rows where mask, and its SE."""
    d = df[mask]
    full = d.PWGTP.sum()
    reps = d[REPS].sum().to_numpy()
    return float(full), float(np.sqrt(4 / 80 * ((reps - full) ** 2).sum()))


def ratio(df: pd.DataFrame, num: pd.Series, den: pd.Series) -> tuple[float, float]:
    n, d = df[num], df[den]
    full = n.PWGTP.sum() / d.PWGTP.sum()
    reps = n[REPS].sum().to_numpy() / d[REPS].sum().to_numpy()
    return float(full), float(np.sqrt(4 / 80 * ((reps - full) ** 2).sum()))


def yearly(frames: dict[int, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for year, df in frames.items():
        for geo, gmask in (("NYC", pd.Series(True, index=df.index)), ("Manhattan", df.borough == "Manhattan")):
            for sex, smask in (("all", pd.Series(True, index=df.index)), ("women", df.SEX == 2), ("men", df.SEX == 1)):
                base = gmask & smask & df.young
                n, se = est(df, base & df.inmover)
                pop, _ = est(df, base)
                lo_n, lo_n_se = est(df, base & df.inmover & df.low_income)
                lo, lo_se = ratio(df, base & df.inmover & df.low_income, base & df.inmover)
                lo_stay, lo_stay_se = ratio(df, base & df.nonmover & df.low_income, base & df.nonmover)
                rows.append(dict(year=year, geo=geo, sex=sex, inmovers=n, inmovers_moe=1.645 * se,
                                 pop_20_29=pop, inmover_rate=n / pop,
                                 low_income_inmovers=lo_n, low_income_inmovers_moe=1.645 * lo_n_se,
                                 sample_inmovers=int((base & df.inmover).sum()),
                                 low_income_share=lo, low_income_share_moe=1.645 * lo_se,
                                 nonmover_low_income_share=lo_stay, nonmover_low_income_share_moe=1.645 * lo_stay_se))
    return pd.DataFrame(rows)


def by_band(frames: dict[int, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for year, df in frames.items():
        for geo, gmask in (("NYC", pd.Series(True, index=df.index)), ("Manhattan", df.borough == "Manhattan")):
            base = gmask & df.young & df.inmover
            for b in INCOME_BANDS:
                n, se = est(df, base & (df.band == b[2]))
                rows.append(dict(year=year, geo=geo, band=b[2], inmovers=n, moe=1.645 * se))
    return pd.DataFrame(rows)


def pooled_neighborhoods(frames: dict[int, pd.DataFrame], periods: dict[str, list[int]]) -> pd.DataFrame:
    """Average annual in-movers 20-29 per community district, pooled over years."""
    rows = []
    for name, years in periods.items():
        for cd in sorted(frames[years[0]].cd.unique()):
            counts, vars_, low_n, low_d, low_reps_n, low_reps_d = [], [], 0.0, 0.0, np.zeros(80), np.zeros(80)
            samp = 0
            for y in years:
                df = frames[y]
                m = (df.cd == cd) & df.young & df.inmover
                n, se = est(df, m)
                counts.append(n); vars_.append(se ** 2); samp += int(m.sum())
                d = df[m]
                low_n += d[d.low_income].PWGTP.sum(); low_d += d.PWGTP.sum()
                low_reps_n += d[d.low_income][REPS].sum().to_numpy(); low_reps_d += d[REPS].sum().to_numpy()
            k = len(years)
            share = low_n / low_d
            share_se = np.sqrt(4 / 80 * ((low_reps_n / low_reps_d - share) ** 2).sum())
            rows.append(dict(period=name, cd=cd, borough=frames[years[0]].loc[frames[years[0]].cd == cd, "borough"].iloc[0],
                             neighborhood=frames[years[0]].loc[frames[years[0]].cd == cd, "neighborhood"].iloc[0],
                             inmovers_per_year=np.mean(counts), moe=1.645 * np.sqrt(sum(vars_)) / k,
                             sample=samp, low_income_share=share, low_income_share_moe=1.645 * share_se))
    return pd.DataFrame(rows)


def main() -> None:
    xw = crosswalk()
    xw.to_csv(OUT / "pums_puma_crosswalk.csv", index=False)
    frames = {y: load(y, xw) for y in YEARS}

    yr = yearly(frames)
    yr.to_csv(OUT / "pums_yearly.csv", index=False)
    by_band(frames).to_csv(OUT / "pums_inmovers_by_income_band.csv", index=False)

    periods = {"2011-13": [2011, 2012, 2013], "2017-19": [2017, 2018, 2019], "2022-24": [2022, 2023, 2024]}
    nb = pooled_neighborhoods(frames, periods)
    nb.to_csv(OUT / "pums_neighborhoods.csv", index=False)

    pd.set_option("display.width", 200)
    print("In-movers aged 20-29 from outside NYC (90% MOE), and share with income under $50k (2024 dollars)")
    for geo in ("NYC", "Manhattan"):
        d = yr[(yr.geo == geo) & (yr.sex == "all")]
        print(f"\n{geo}")
        print(d[["year", "inmovers", "inmovers_moe", "sample_inmovers", "inmover_rate", "low_income_inmovers",
                 "low_income_inmovers_moe", "low_income_share", "low_income_share_moe",
                 "nonmover_low_income_share"]].round(3).to_string(index=False))
    w = yr[(yr.geo == "Manhattan") & (yr.sex == "women")]
    print("\nManhattan women 20-29 in-movers")
    print(w[["year", "inmovers", "inmovers_moe", "sample_inmovers"]].round(0).to_string(index=False))
    print("\nTop 15 community districts by in-movers 20-29 per year, 2022-24, with change vs 2011-13")
    p = nb.pivot(index=["cd", "borough", "neighborhood"], columns="period", values="inmovers_per_year")
    p["chg_vs_2011_13"] = p["2022-24"] / p["2011-13"] - 1
    print(p.sort_values("2022-24", ascending=False).head(15).round(2).to_string())
    print("\nShare of in-movers 20-29 under $50k (2024 dollars), Manhattan community districts")
    s = nb[nb.borough == "Manhattan"].pivot(index="neighborhood", columns="period", values="low_income_share")
    print(s.round(2).to_string())


if __name__ == "__main__":
    main()
