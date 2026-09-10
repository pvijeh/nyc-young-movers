"""Charts and tables from data/processed/pums_*.csv."""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
FIG = ROOT / "output" / "figures"
TAB = ROOT / "output" / "tables"
SRC = "ACS 1-year PUMS 2011-2024 (no 2020). Bands: 90% margin of error from replicate weights."


def inmovers_chart(yr: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), sharex=True)
    for ax, geo in zip(axes, ["NYC", "Manhattan"]):
        for sex, color in (("all", "k"), ("women", "C3"), ("men", "C0")):
            d = yr[(yr.geo == geo) & (yr.sex == sex)]
            ax.plot(d.year, d.inmovers / 1000, marker="o", color=color, label=sex)
            ax.fill_between(d.year, (d.inmovers - d.inmovers_moe) / 1000, (d.inmovers + d.inmovers_moe) / 1000,
                            color=color, alpha=0.15)
        ax.set_title(f"{geo}: arrivals aged 20-29 from outside NYC")
        ax.set_ylabel("thousands per year")
        ax.set_ylim(0)
        ax.axvspan(2019.5, 2020.5, color="grey", alpha=0.2)
        ax.grid(alpha=0.3)
    axes[0].legend()
    fig.text(0.5, 0.01, SRC, ha="center", fontsize=9)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(FIG / "fig7_pums_inmovers_20_29.png", dpi=150)


def low_income_chart(yr: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), sharey=True)
    for ax, geo in zip(axes, ["NYC", "Manhattan"]):
        d = yr[(yr.geo == geo) & (yr.sex == "all")]
        ax.plot(d.year, 100 * d.low_income_share, marker="o", label="moved in from outside NYC")
        ax.fill_between(d.year, 100 * (d.low_income_share - d.low_income_share_moe),
                        100 * (d.low_income_share + d.low_income_share_moe), alpha=0.15)
        ax.plot(d.year, 100 * d.nonmover_low_income_share, marker="s", label="same house as last year")
        ax.set_title(f"{geo}: 20-29 year olds under $50k income (2024 dollars)")
        ax.set_ylabel("%")
        ax.set_ylim(30, 90)
        ax.grid(alpha=0.3)
    axes[0].legend()
    fig.text(0.5, 0.01, SRC, ha="center", fontsize=9)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(FIG / "fig8_pums_low_income_share.png", dpi=150)


def neighborhood_chart(nb: pd.DataFrame) -> None:
    p = nb.pivot(index=["borough", "neighborhood"], columns="period", values="inmovers_per_year").reset_index()
    m = nb.pivot(index=["borough", "neighborhood"], columns="period", values="moe").reset_index()
    p = p.sort_values("2022-24", ascending=True).tail(25)
    m = m.set_index(["borough", "neighborhood"]).loc[list(zip(p.borough, p.neighborhood))].reset_index()
    abbr = {"Manhattan": "Mn", "Brooklyn": "Bk", "Bronx": "Bx", "Queens": "Qn", "Staten Island": "SI"}
    labels = [f"{n} ({abbr[b]})" for b, n in zip(p.borough, p.neighborhood)]
    y = range(len(p))
    fig, ax = plt.subplots(figsize=(11, 9))
    ax.hlines(y, p["2011-13"] / 1000, p["2022-24"] / 1000, color="grey", lw=2)
    ax.errorbar(p["2011-13"] / 1000, y, xerr=m["2011-13"] / 1000, fmt="o", color="C0", label="2011-13 average", capsize=2)
    ax.errorbar(p["2022-24"] / 1000, y, xerr=m["2022-24"] / 1000, fmt="o", color="C3", label="2022-24 average", capsize=2)
    ax.set_yticks(list(y))
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel("people aged 20-29 arriving from outside NYC, thousands per year")
    ax.set_title("Where 20-29 year olds arriving from outside NYC live: top 25 community districts")
    ax.legend(loc="lower right")
    ax.grid(axis="x", alpha=0.3)
    fig.text(0.5, 0.01, SRC, ha="center", fontsize=9)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(FIG / "fig9_pums_neighborhoods.png", dpi=150)


def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    TAB.mkdir(parents=True, exist_ok=True)
    yr = pd.read_csv(PROC / "pums_yearly.csv")
    nb = pd.read_csv(PROC / "pums_neighborhoods.csv")
    inmovers_chart(yr)
    low_income_chart(yr)
    neighborhood_chart(nb)

    t = yr[yr.sex == "all"][["year", "geo", "inmovers", "inmovers_moe", "low_income_inmovers", "low_income_inmovers_moe",
                             "low_income_share", "nonmover_low_income_share", "sample_inmovers"]]
    t.round(3).to_csv(TAB / "pums_inmovers_20_29.csv", index=False)
    yr[yr.sex != "all"][["year", "geo", "sex", "inmovers", "inmovers_moe", "sample_inmovers"]].round(0) \
        .to_csv(TAB / "pums_inmovers_20_29_by_sex.csv", index=False)
    wide = nb.pivot(index=["borough", "cd", "neighborhood"], columns="period",
                    values=["inmovers_per_year", "moe", "low_income_share", "sample"])
    wide.columns = [f"{a}_{b}" for a, b in wide.columns]
    wide["change_2011_13_to_2022_24"] = wide["inmovers_per_year_2022-24"] / wide["inmovers_per_year_2011-13"] - 1
    wide.sort_values("inmovers_per_year_2022-24", ascending=False).round(3).to_csv(TAB / "pums_neighborhoods.csv")


if __name__ == "__main__":
    main()
