"""Cohort-residual net migration for young adults in NYC, from Census PEP county files.

Idea: a cohort that is 20-24 in year t is 25-29 in year t+5. Deaths at these ages are
~0.1% a year, so pop(25-29, t+5) - pop(20-24, t) is almost entirely net migration.
Same for single years of age one year apart where single-year data exists (2020-2025).

Outputs (data/processed/):
  levels.csv             population by geography, sex, age group, year, vintage
  five_year_cohort.csv   5-year cohort residuals, start years 2010-2015 and 2020
  annual_cohort.csv      1-year cohort residuals for ages 20-28, 2021-2025 (single year of age)
"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"

BOROUGHS = {
    "005": "Bronx",
    "047": "Brooklyn",
    "061": "Manhattan",
    "081": "Queens",
    "085": "Staten Island",
}
# YEAR code -> July 1 estimate year. Base-population codes are dropped.
V2020_YEARS = {code: 2008 + code for code in range(2, 13)}  # 2 -> 2010 ... 12 -> 2020
V2025_YEARS = {code: 2018 + code for code in range(2, 8)}  # 2 -> 2020 ... 7 -> 2025
GROUPS = ["1519", "2024", "2529", "3034"]
SEXES = {"MALE": "male", "FEM": "female", "TOT": "all"}


def read_agesex(name: str, years: dict[int, int], vintage: str) -> pd.DataFrame:
    df = pd.read_csv(RAW / name, dtype={"COUNTY": str}, encoding="latin-1")
    df = df[df["COUNTY"].isin(BOROUGHS) & df["YEAR"].isin(years)].copy()
    df["year"] = df["YEAR"].map(years)
    df["geo"] = df["COUNTY"].map(BOROUGHS)
    rows = []
    for g in GROUPS:
        for col, sex in SEXES.items():
            sub = df[["geo", "year", f"AGE{g}_{col}"]].rename(columns={f"AGE{g}_{col}": "pop"})
            sub["age_group"] = f"{g[:2]}-{g[2:]}"
            sub["sex"] = sex
            rows.append(sub)
    out = pd.concat(rows)
    out["vintage"] = vintage
    return out


def add_nyc_total(df: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    nyc = df.groupby(keys, as_index=False)["pop"].sum()
    nyc["geo"] = "NYC"
    return pd.concat([df, nyc], ignore_index=True)


def five_year_cohorts(levels: pd.DataFrame) -> pd.DataFrame:
    transitions = [("15-19", "20-24"), ("20-24", "25-29"), ("25-29", "30-34")]
    rows = []
    for (geo, sex, vintage), g in levels.groupby(["geo", "sex", "vintage"]):
        wide = g.pivot(index="year", columns="age_group", values="pop")
        for start, end in transitions:
            for s in wide.index:
                e = s + 5
                if e not in wide.index:
                    continue
                start_pop = wide.loc[s, start]
                net = wide.loc[e, end] - start_pop
                rows.append(
                    dict(
                        geo=geo,
                        sex=sex,
                        vintage=vintage,
                        start_year=s,
                        end_year=e,
                        age_at_start=start,
                        age_at_end=end,
                        start_pop=int(start_pop),
                        end_pop=int(wide.loc[e, end]),
                        net_migration=int(net),
                        net_pct_of_start=round(100 * net / start_pop, 1),
                    )
                )
    return pd.DataFrame(rows).sort_values(["geo", "sex", "age_at_start", "start_year"])


def annual_single_year() -> pd.DataFrame:
    df = pd.read_csv(RAW / "cc-est2025-syasex-36.csv", dtype={"COUNTY": str}, encoding="latin-1")
    df = df[df["COUNTY"].isin(BOROUGHS) & df["YEAR"].isin(V2025_YEARS)].copy()
    df["year"] = df["YEAR"].map(V2025_YEARS)
    df["geo"] = df["COUNTY"].map(BOROUGHS)
    long = df.melt(
        id_vars=["geo", "year", "AGE"],
        value_vars=["TOT_POP", "TOT_MALE", "TOT_FEMALE"],
        var_name="sex",
        value_name="pop",
    )
    long["sex"] = long["sex"].map({"TOT_POP": "all", "TOT_MALE": "male", "TOT_FEMALE": "female"})
    long = add_nyc_total(long, ["year", "AGE", "sex"])

    rows = []
    for (geo, sex), g in long.groupby(["geo", "sex"]):
        wide = g.pivot(index="year", columns="AGE", values="pop")
        for t in wide.index:
            if t - 1 not in wide.index:
                continue
            ages = range(20, 29)
            end_pop = sum(wide.loc[t, a] for a in ages)
            start_pop = sum(wide.loc[t - 1, a - 1] for a in ages)
            rows.append(
                dict(
                    geo=geo,
                    sex=sex,
                    year=t,
                    ages_at_end="20-28",
                    pop_20_28=int(end_pop),
                    net_migration=int(end_pop - start_pop),
                    net_pct_of_start=round(100 * (end_pop - start_pop) / start_pop, 1),
                )
            )
    return pd.DataFrame(rows).sort_values(["geo", "sex", "year"])


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    levels = pd.concat(
        [
            read_agesex("CC-EST2020-AGESEX-36.csv", V2020_YEARS, "v2020"),
            read_agesex("CC-EST2025-AGESEX-36.csv", V2025_YEARS, "v2025"),
        ],
        ignore_index=True,
    )
    levels = add_nyc_total(levels, ["year", "age_group", "sex", "vintage"])
    levels = levels[["geo", "sex", "age_group", "year", "vintage", "pop"]].sort_values(
        ["geo", "sex", "age_group", "vintage", "year"]
    )
    levels.to_csv(OUT / "levels.csv", index=False)

    five = five_year_cohorts(levels)
    five.to_csv(OUT / "five_year_cohort.csv", index=False)

    annual = annual_single_year()
    annual.to_csv(OUT / "annual_cohort.csv", index=False)

    show = five[(five.geo.isin(["Manhattan", "NYC"])) & (five.sex != "all")]
    print(show.to_string(index=False))
    print()
    print(annual[annual.geo.isin(["Manhattan", "NYC"]) & (annual.sex != "all")].to_string(index=False))


if __name__ == "__main__":
    main()
