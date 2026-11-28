"""Check the model's first auctions against the auctions that were held, without fitting anything.

    python scripts/check_auctions.py            # -> results/auction_check.md

The model starts in 2025 with published costs (DESNZ Electricity Generation Costs 2025), CEPA's hurdle
rates, measured capacity factors and the contracted pipeline. Its first CfD round (held in 2025) is the
counterpart of Allocation Round 7 (results January-February 2026), and its first T-4 Capacity Market
auction (delivery 2029) of the T-4 auction for 2029-30. Nothing in the model was set to reproduce
either. The table reports, for seeds 1-5:

* the cleared CfD strike by technology against AR7 and AR6 (2024 prices), and the *implied cost factor*:
  the factor on a project's capital cost at which the model's clearing strike would equal the AR7
  strike. It is the model's measure of how far winning bidders' costs were from the published ones.
  PyPSA-GB's own calibration (data/public_ownership/financing/private_cost_calibration.csv) gives the
  same kind of factor by round: offshore 0.90 (AR2), 0.52 (AR3), 0.34 (AR4), 0.85 (AR6), 0.90 (AR7).
  It is not stable across rounds, so it is reported here and not built into the model;
* the T-4 clearing price against the 2029-30 auction.
"""
from __future__ import annotations

import logging
import subprocess
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ukabm import GBMarketModel, get_scenario  # noqa: E402
from ukabm.config import CPI_2012_TO_2024, TECHS, capex_kw, fom_kw, hurdle_rate  # noqa: E402
from ukabm.costs import crf  # noqa: E402

warnings.filterwarnings("ignore")
logging.disable(logging.WARNING)
# cleared strikes, GBP/MWh in 2012 prices (DESNZ allocation round results; data/pypsagb_snapshot/
# cfd_strike_prices_by_round.csv): AR6 (Sept 2024) and AR7 / AR7a (Jan-Feb 2026)
ACTUAL_2012 = {"wind_offshore": {"AR6": 58.87, "AR7": 65.45}, "wind_onshore": {"AR6": 50.90, "AR7": 51.85},
               "solar": {"AR6": 50.07, "AR7": 46.82}}
T4_2029_30 = 27.10          # GBP/kW/yr, T-4 auction for delivery 2029-30 (NESO auction results)


def implied_cost_factor(m, tech: str, model_strike: float, actual: float) -> float:
    """Factor on capital cost that moves the model's strike to *actual*: the strike is linear in the
    capital charge, so k = 1 - (model - actual) x output / capital charge per MW (reference firm)."""
    t = TECHS[tech]
    online = m.start + t.lead_time
    r = hurdle_rate(tech)
    capital = capex_kw(tech, online, r) * 1000 * crf(r, t.life)          # GBP/MW/yr
    output = 8760 * m.capacity_factor(tech, online)
    return 1 - (model_strike - actual) * output / capital


def main(seeds=(1, 2, 3, 4, 5)):
    rows = []
    for seed in seeds:
        m = GBMarketModel(get_scenario("baseline"), seed=seed, end=2025, network_every=0)
        m.run()
        a = m.auctions()
        for tech in ACTUAL_2012:
            r = a[(a.auction == "cfd") & (a.tech == tech)].iloc[0]
            rows.append(dict(seed=seed, item=tech, model=r.clearing, accepted_mw=r.accepted_mw))
        cm = a[(a.auction == "cm_t4") & (a.tech == "all")].iloc[0]
        rows.append(dict(seed=seed, item="cm_t4", model=cm.clearing, accepted_mw=cm.accepted_mw))
    df = pd.DataFrame(rows)
    med = df.groupby("item").model.agg(["median", "min", "max"])
    f = lambda v: f"{v:.1f}"
    md = ["| auction | model, median [range] | held | difference | implied cost factor |", "|---|---|---|---|---|"]
    names = {"wind_offshore": "offshore wind", "wind_onshore": "onshore wind", "solar": "solar"}
    for tech, name in names.items():
        ar7 = ACTUAL_2012[tech]["AR7"] * CPI_2012_TO_2024
        ar6 = ACTUAL_2012[tech]["AR6"] * CPI_2012_TO_2024
        mm = med.loc[tech]
        k = implied_cost_factor(m, tech, mm["median"], ar7)
        md.append(f"| CfD strike, {name} (£/MWh, 2024 prices) | {f(mm['median'])} [{f(mm['min'])}–{f(mm['max'])}] | "
                  f"AR7 {f(ar7)} (AR6 {f(ar6)}) | {100 * (mm['median'] / ar7 - 1):+.0f} % | {k:.2f} |")
    mm = med.loc["cm_t4"]
    md.append(f"| Capacity Market T-4, delivery 2029 (£/kW/yr) | {f(mm['median'])} [{f(mm['min'])}–{f(mm['max'])}] | "
              f"{f(T4_2029_30)} | {100 * (mm['median'] / T4_2029_30 - 1):+.0f} % | – |")
    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    except Exception:
        commit = "unknown"
    text = (f"# Auction check: the model's first auctions against the auctions held\n\nBaseline, seeds {list(seeds)}, "
            f"code at {commit}. No model parameter was set to reproduce these results.\n\n" + "\n".join(md) +
            "\n\nImplied cost factor: the factor on capital cost at which the model's clearing strike would equal the AR7 "
            "strike\n(reference firm, the technology's hurdle rate). Below 1: winning bidders priced in lower costs, "
            "a higher yield or a\nlower return than the published assumptions; above 1: the opposite.\n")
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results" / "auction_check.md").write_text(text, encoding="utf-8")
    df.round(2).to_csv(ROOT / "results" / "auction_check.csv", index=False)
    print(text)


if __name__ == "__main__":
    main()
