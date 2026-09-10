"""Charts from the IRS migration tables built by irs_flows.py."""
from pathlib import Path
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
FIG = ROOT / "output" / "figures"
TAB = ROOT / "output" / "tables"
LOW = ["$1-10k", "$10-25k", "$25-50k"]
BANDS = LOW + ["$50-75k", "$75-100k", "$100-200k", "$200k+"]


def inflow_chart(ci: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    for ax, geo in zip(axes, ["Manhattan", "NYC"]):
        d = ci[ci.geo == geo]
        ax.plot(d.year, d.inflow_returns / 1000, marker="o", label="returns")
        ax.plot(d.year, d.inflow_people / 1000, marker="s", label="people")
        ax.set_title(f"Tax returns moving into {geo} from outside NYC")
        ax.set_ylabel("thousands")
        ax.set_ylim(0)
        ax.grid(alpha=0.3)
        ax.legend()
    fig.suptitle("IRS SOI county-to-county migration, filing years 2011-12 to 2022-23", fontsize=10)
    fig.tight_layout()
    fig.savefig(FIG / "fig4_irs_inflows.png", dpi=150)


def agi_chart(ci: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(7, 4.2))
    for geo in ["Manhattan", "NYC"]:
        d = ci[ci.geo == geo]
        ax.plot(d.year, d.mean_agi_in_2023usd / 1000, marker="o", label=f"{geo} in-movers")
    d = ci[ci.geo == "Manhattan"]
    ax.plot(d.year, d.nonmigrant_mean_agi_2023usd / 1000, ls="--", color="gray", label="Manhattan non-movers")
    ax.set_title("Mean AGI of returns moving in, 2023 dollars")
    ax.set_ylabel("$ thousands")
    ax.set_ylim(0)
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG / "fig5_irs_mean_agi.png", dpi=150)


def young_agi_chart(st: pd.DataFrame, shares: pd.DataFrame) -> None:
    y = st[st.age == "under 26"].pivot(index="year", columns="agi_band", values="inflow_returns")
    share = y[LOW].sum(axis=1) / y["all"]
    s = shares.set_index("year")
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    ax = axes[0]
    bottom = pd.Series(0, index=y.index, dtype=float)
    for b in BANDS:
        ax.bar(y.index, y[b] / 1000, bottom=bottom / 1000, label=b)
        bottom += y[b]
    ax.set_title("Returns moving into New York State, filer under 26")
    ax.set_ylabel("thousands of returns")
    ax.legend(fontsize=7, ncol=2)
    ax.grid(alpha=0.3, axis="y")
    ax = axes[1]
    ax.plot(s.index, 100 * s.ny_inmovers, marker="o", label="moved into NY State")
    ax.plot(s.index, 100 * s.ny_nonmovers, marker="s", label="already in NY State")
    ax.plot(s.index, 100 * s.other_states_inmovers, ls="--", label="moved into any other state")
    ax.plot(s.index, 100 * s.other_states_nonmovers, ls="--", label="already in other states")
    ax.set_title("Share of under-26 filers with AGI under $50,000 (nominal)")
    ax.set_ylabel("percent")
    ax.set_ylim(50, 100)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    fig.suptitle("IRS state-level migration file; county files carry no age", fontsize=10)
    fig.tight_layout()
    fig.savefig(FIG / "fig6_irs_ny_under26_agi.png", dpi=150)
    out = y[["all"] + BANDS].copy()
    out["share_under_50k"] = share.round(3)
    out.to_csv(TAB / "irs_ny_under26_by_agi.csv")


def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    TAB.mkdir(parents=True, exist_ok=True)
    ci = pd.read_csv(PROC / "irs_county_inflows.csv")
    st = pd.read_csv(PROC / "irs_ny_state_inflow_age_agi.csv")
    shares = pd.read_csv(PROC / "irs_under26_low_agi_shares.csv")
    shares.to_csv(TAB / "irs_under26_low_agi_shares.csv", index=False)
    ci[ci.geo.isin(["Manhattan", "NYC"])].to_csv(TAB / "irs_inflows_manhattan_nyc.csv", index=False)
    inflow_chart(ci)
    agi_chart(ci)
    young_agi_chart(st, shares)


if __name__ == "__main__":
    main()
