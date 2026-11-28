"""What the CfD rounds held so far say about bidders: cleared strikes against the official cost of the day.

    python scripts/replay_cfd_rounds.py        # -> results/cfd_rounds_replay.md

For every allocation round and technology (offshore wind, onshore wind, solar) this sets the cleared
strike beside the levelised cost that the government's own generation-cost report, the edition current
when the round was held, gave for a project commissioning in the round's delivery year. Both are put in
2024 prices. The ratio of the two is what a model would have to "learn" from each round if it started
from the published costs: below 1, bidders asked for less than the official cost (lower costs, a
higher yield or a lower return than assumed); above 1, they asked for more.

The point of the table is whether that ratio is a stable property of bidders that could be estimated
on early rounds and applied to later ones. It is not (see the output), which is why the model takes its
costs and required returns from published sources and uses auction results only as a check
(docs/calibration.md).

Data: data/pypsagb_snapshot/cfd_strike_prices_by_round.csv (cleared strikes and capacity by round,
technology and delivery year; DESNZ and LCCC, via PyPSA-GB); data/history/desnz_generation_costs.csv
(levelised cost, central case, by edition and commissioning year); data/history/annual_inputs.csv (GDP
deflator). Strikes are converted from 2012 prices with the CPI factor used by DESNZ (1.393).
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
STRIKES = ROOT / "data" / "pypsagb_snapshot" / "cfd_strike_prices_by_round.csv"
COSTS = ROOT / "data" / "history" / "desnz_generation_costs.csv"
ANNUAL = ROOT / "data" / "history" / "annual_inputs.csv"
CPI_2012_TO_2024 = 1.393
# round -> (year held, generation-cost edition current when bids were made)
ROUNDS = {
    "AR1": (2015, "DECC EGC 2013 (December 2013)"),
    "AR2": (2017, "BEIS EGC 2016"),
    "AR3": (2019, "BEIS EGC 2016"),
    "AR4": (2022, "BEIS EGC 2020"),
    "AR5": (2023, "BEIS EGC 2020"),
    "AR6": (2024, "DESNZ EGC 2023"),
    "AR7": (2025, "DESNZ EGC 2025"),
    "AR7a": (2025, "DESNZ EGC 2025"),
}
TECH = {"offshore": "wind_offshore", "offshore_scotland": "wind_offshore", "onshore": "wind_onshore", "solar": "solar"}
NAME = {"wind_offshore": "offshore wind", "wind_onshore": "onshore wind", "solar": "solar"}
# where an edition splits a technology, the label used (offshore wind: the newer, deeper-water class)
PREFER = {"wind_offshore": ("Offshore Round 3", "Offshore R3")}


def official_lcoe(costs: pd.DataFrame, edition: str, tech: str, year: int) -> tuple[float, int]:
    """Central levelised cost (GBP/MWh, the edition's price base) for a project commissioning in *year*,
    interpolated between the edition's commissioning years (held flat outside them), and the price-base year."""
    x = costs[(costs.publication == edition) & (costs.technology == tech) & (costs.metric == "lcoe_total")
              & (costs.scenario == "central")]
    labels = x.technology_label.unique()
    pick = [l for l in labels if l in PREFER.get(tech, ())] or list(labels)
    x = x[x.technology_label == pick[0]].sort_values("commissioning_year")
    base = int(str(x.price_base.iloc[0])[:4])
    return float(np.interp(year, x.commissioning_year, x.value)), base


def main():
    s = pd.read_csv(STRIKES)
    costs = pd.read_csv(COSTS)
    deflator = pd.read_csv(ANNUAL).set_index("year").deflator_2024        # GDP deflator, 2024 = 1
    s = s[s.cfd_round.isin(ROUNDS) & s.technology.isin(TECH) & (s.capacity_mw > 0)].copy()
    s["tech"] = s.technology.map(TECH)
    s["delivery"] = s.delivery_year.astype(str).str[:4].astype(int) + 1      # 2026-27 -> 2027
    rows = []
    for (rnd, tech), g in s.groupby(["cfd_round", "tech"], sort=False):
        held, edition = ROUNDS[rnd]
        mw = g.capacity_mw.sum()
        strike = float((g.strike_price_gbp_per_mwh_2012 * g.capacity_mw).sum() / mw) * CPI_2012_TO_2024
        delivery = int(round((g.delivery * g.capacity_mw).sum() / mw))
        lcoe, base = official_lcoe(costs, edition, tech, delivery)
        lcoe24 = lcoe / float(deflator.loc[base])
        rows.append(dict(round=rnd, held=held, technology=NAME[tech], delivery=delivery, mw=mw, strike_2024=strike,
                         edition=edition.split(" (")[0], official_lcoe_2024=lcoe24, ratio=strike / lcoe24))
    df = pd.DataFrame(rows).sort_values(["technology", "held", "round"])
    md = ["| technology | round (held) | delivery | awarded (MW) | cleared strike | official levelised cost of the day | strike / cost |",
          "|---|---|---|---|---|---|---|"]
    for r in df.itertuples():
        md.append(f"| {r.technology} | {r.round} ({r.held}) | {r.delivery} | {r.mw:,.0f} | {r.strike_2024:.0f} | "
                  f"{r.official_lcoe_2024:.0f} ({r.edition}) | {r.ratio:.2f} |")
    span = df.groupby("technology").ratio.agg(["min", "max"])
    lines = [f"* **{t}**: {v['min']:.2f} to {v['max']:.2f}" for t, v in span.iterrows()]
    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    except Exception:
        commit = "unknown"
    text = ("# CfD rounds held so far: cleared strikes against the official cost of the day\n\n"
            f"£/MWh in 2024 prices; capacity-weighted over a round's delivery years; code at {commit}.\n"
            "Official cost: the central levelised cost in the generation-cost report current when the round was held, "
            "for a project\ncommissioning in the delivery year (offshore wind in the 2013 and 2016 editions: Round 3 sites).\n\n"
            + "\n".join(md) + "\n\nRange of strike / cost over the rounds:\n\n" + "\n".join(lines) + "\n\n"
            "Allocation Round 5 (2023) drew no offshore wind bids at an administrative strike price of £44/MWh (2012 prices, "
            "£61 in 2024 prices):\nbidders needed more than that; it is not in the table because nothing cleared.\n\n"
            "Reading: the ratio is what a model starting from published costs would have to learn from each round. It is "
            "not stable.\nA value estimated on Rounds 1 to 4 would have been wrong by a factor of two for Round 6. The "
            "published costs lag\nthe market in both directions: they were too high while costs fell (2015 to 2022) and "
            "too low after costs rose (2023 to 2024).\nThe 2025 edition is within about 10 % of Round 7 for offshore "
            "wind and solar and 20 % below it for onshore wind.\n")
    out = ROOT / "results" / "cfd_rounds_replay.md"
    out.write_text(text, encoding="utf-8")
    df.round(3).to_csv(out.with_suffix(".csv"), index=False)
    print(text)


if __name__ == "__main__":
    main()
