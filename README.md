# Are fewer young people moving to New York?

Working repo for an article testing two claims: that fewer people in their twenties move to New York City (and Manhattan in particular) each year than in the early 2010s, and that the drop is concentrated among lower earners. Nothing here is settled; the numbers below are the first pass, from one source.

## What the first source says

The Census Bureau's county population estimates (PEP) give the population of each borough by age and sex every July. A group that is 20-24 in one year is 25-29 five years later, and almost nobody that age dies, so the change in that group's size is net migration. This is not survey-based, so it does not depend on young people answering the ACS.

Result: the estimates do **not** show fewer young adults arriving. For women aged 20-24 in Manhattan, net gain over the following five years:

| 5-year window | Net gain, women 20-24 at start | Series |
|---|---|---|
| 2010 to 2015 | +27,500 | 2010-base estimates |
| 2015 to 2020 | +34,200 | 2010-base estimates |
| 2020 to 2025 | +35,700 | 2020-base estimates |

Citywide the same window went from +74,600 to +74,900 to +92,800. Men look the same. Year by year since 2020, Manhattan gained 13,000 to 20,000 people aged 20-28 a year from 2022 to 2024 and 9,000 in 2025 (fig 2). The 2025 slowdown is one data point.

![fig1](output/figures/fig1_five_year_cohort_20_24.png)

## Why this is not the end of the question

1. **The 2010s estimates missed young women in Manhattan.** The 2010-base series put women 20-24 in Manhattan at 61,100 in July 2020; the 2020 census-based series put the same group at 77,600, 27% higher (fig 3). The 2010s series was carried forward from the 2010 census with administrative data and drifted low. That means the 2010s cohort gains in the table above are probably *understated*, which would narrow the gap between then and now, not widen it. It also means the two series should not be joined into one line.
2. **The 2020 census itself had a college-age problem.** It was taken in April 2020, when students had left campuses. How the Bureau handled that affects the 2020-base series' starting point for exactly this age group.
3. **This is net, not gross.** More people arriving and more people leaving would look the same as no change. Only IRS flows and ACS can separate arrivals from departures.
4. **Nothing here says anything about income.** The low-earner claim needs IRS county-to-county flows by AGI band and ACS PUMS by personal income.

![fig3](output/figures/fig3_levels_women_20_29.png)

## Sources and files

| Source | Years | Age detail | File |
|---|---|---|---|
| PEP vintage 2020, county by age and sex | 2010-2020 | 5-year groups | `data/raw/CC-EST2020-AGESEX-36.csv` |
| PEP vintage 2025, county by age and sex | 2020-2025 | 5-year groups | `data/raw/CC-EST2025-AGESEX-36.csv` |
| PEP vintage 2025, county by single year of age and sex | 2020-2025 | single year | `data/raw/cc-est2025-syasex-36.csv` |

Single year of age for 2010-2019 exists only through the Census API (`pep/charage`), which now requires a free API key. With a key, `annual_cohort.csv` can be extended back to 2011.

## Run it

```
pip install -r requirements.txt
python src/fetch_pep.py       # downloads the three CSVs above (skips ones present)
python src/cohort_method.py   # writes data/processed/{levels,five_year_cohort,annual_cohort}.csv
python src/figures.py         # writes output/figures/fig1..fig3
```

## Method notes

- `five_year_cohort.csv`: for each borough, NYC total, sex and start year, `net_migration = pop(next 5-year group, start+5) - pop(group, start)`. Computed within one estimate series only; no window straddles the 2020 break.
- `annual_cohort.csv`: for ages 20-28 in year t, `net = sum over a of pop(a, t) - pop(a-1, t-1)`. Single-year data, 2021-2025.
- Deaths are ignored. At ages 20-29 the death rate is roughly 1 per 1,000 a year, under 1% over five years.
- Year codes: vintage 2020 file, code 2 = July 2010 through code 12 = July 2020; vintage 2025 file, code 2 = July 2020 through code 7 = July 2025. Base-population rows (April 1) are dropped.

## Plan for the rest of the project

1. IRS SOI county-to-county migration, 2011-2022: inflows to each borough, share of in-moving returns with AGI under $50k. Tests the low-earner claim and separates arrivals from departures.
2. ACS 1-year PUMS, 2011-2024 (2025 due October 2026): people 20-28 who lived outside NYC a year earlier, by sex and personal income, with margins of error from replicate weights.
3. A table putting the three methods side by side, then the draft.
