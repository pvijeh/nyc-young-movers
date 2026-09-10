"""Charts from data/processed/*.csv into output/figures/."""
from pathlib import Path
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
FIG = ROOT / "output" / "figures"
COLORS = {"female": "#c0392b", "male": "#2c3e50"}


def five_year_chart(five: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), sharey=False)
    for ax, geo in zip(axes, ["Manhattan", "NYC"]):
        d = five[(five.geo == geo) & (five.age_at_start == "20-24") & (five.sex != "all")]
        for sex, g in d.groupby("sex"):
            v20 = g[g.vintage == "v2020"]
            v25 = g[g.vintage == "v2025"]
            ax.plot(v20.end_year, v20.net_migration / 1000, "o-", color=COLORS[sex], label=f"{sex} (2010-base estimates)")
            ax.plot(v25.end_year, v25.net_migration / 1000, "s", color=COLORS[sex], markersize=9, label=f"{sex} (2020-base estimates)")
        ax.axvspan(2020.5, 2025.5, color="grey", alpha=0.08)
        ax.set_title(f"{geo}: 5-year net migration, cohort aged 20-24 at start", fontsize=10)
        ax.set_xlabel("end year of 5-year window")
        ax.set_ylabel("thousand people (net)")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
    fig.suptitle("Cohort residual: pop(25-29, t) minus pop(20-24, t-5). Census PEP, vintages 2020 and 2025.", fontsize=10)
    fig.tight_layout()
    fig.savefig(FIG / "fig1_five_year_cohort_20_24.png", dpi=150)
    plt.close(fig)


def annual_chart(annual: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    for ax, geo in zip(axes, ["Manhattan", "NYC"]):
        d = annual[(annual.geo == geo) & (annual.sex != "all")]
        w = 0.4
        for i, (sex, g) in enumerate(d.groupby("sex")):
            ax.bar(g.year + (i - 0.5) * w, g.net_migration / 1000, width=w, color=COLORS[sex], label=sex)
        ax.axhline(0, color="black", linewidth=0.8)
        ax.set_title(f"{geo}: annual net migration into ages 20-28", fontsize=10)
        ax.set_ylabel("thousand people (net)")
        ax.grid(alpha=0.3, axis="y")
        ax.legend()
    fig.suptitle("Single-year-of-age cohort residual, July to July. Census PEP vintage 2025.", fontsize=10)
    fig.tight_layout()
    fig.savefig(FIG / "fig2_annual_cohort_20_28.png", dpi=150)
    plt.close(fig)


def levels_chart(levels: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    for ax, geo in zip(axes, ["Manhattan", "NYC"]):
        d = levels[(levels.geo == geo) & (levels.sex == "female") & (levels.age_group.isin(["20-24", "25-29"]))]
        for (grp, vintage), g in d.groupby(["age_group", "vintage"]):
            style = "-" if vintage == "v2020" else "--"
            ax.plot(g.year, g["pop"] / 1000, style, marker="o", markersize=3, label=f"{grp} ({vintage})")
        ax.axvline(2020, color="grey", linestyle=":", linewidth=1)
        ax.set_title(f"{geo}: women aged 20-24 and 25-29, July 1 estimates", fontsize=10)
        ax.set_ylabel("thousand people")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
    fig.suptitle("The two estimate series disagree at 2020: the 2010-base series missed young women, especially in Manhattan.", fontsize=10)
    fig.tight_layout()
    fig.savefig(FIG / "fig3_levels_women_20_29.png", dpi=150)
    plt.close(fig)


def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    five = pd.read_csv(PROC / "five_year_cohort.csv")
    annual = pd.read_csv(PROC / "annual_cohort.csv")
    levels = pd.read_csv(PROC / "levels.csv")
    five_year_chart(five)
    annual_chart(annual)
    levels_chart(levels)
    print("wrote", sorted(p.name for p in FIG.iterdir()))


if __name__ == "__main__":
    main()
