"""Operating back-cast: run single historical years and compare them with GB outturn.

    python scripts/run_backcast.py                 # 2021-2025 -> results/backcast.md, results/backcast.csv
    python scripts/run_backcast.py 2024 2025 --no-network

Each year is run on its own weather (data/profiles/profiles_<year>.csv), its own fleet
(ukabm.config.fleet_mw: GB capacity by technology that year), its own interconnectors and neighbour
prices (data/external/neighbour_prices_<year>.csv) and its own fuel and carbon prices in money of the
day (data/history/annual_inputs.csv), so that prices compare with outturn prices.

No parameter is set per year. The parameters fitted to an operating year (interconnector price
levels and spread, availability of nuclear, biomass and hydro, the existing CCGT efficiency range)
were set on 2025 (and nuclear on 2024-25); the other years are a check of them, not a fit.
"""
from __future__ import annotations

import argparse
import logging
import subprocess
import sys
import warnings
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ukabm import GBMarketModel, get_scenario  # noqa: E402
from ukabm.data import PyPSAGBData  # noqa: E402
from ukabm.outturn import compare, load_outturn  # noqa: E402

warnings.filterwarnings("ignore")
logging.disable(logging.WARNING)
CALIBRATION_YEAR = 2025


def run_year(year: int, seed: int = 42, network: bool = True) -> pd.DataFrame:
    sc = get_scenario("baseline")
    sc.setdefault("policy", {})["history_basis"] = "nominal"
    sc.setdefault("fuels", {})["history_basis"] = "nominal"
    m = GBMarketModel(sc, data=PyPSAGBData(profile_year=year), start=year, end=year, seed=seed,
                      network_every=1 if network else 0)
    return compare(m.run().loc[year], year)


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("years", type=int, nargs="*", default=[2021, 2022, 2023, 2024, 2025])
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--no-network", action="store_true", help="skip the network (redispatch) stage")
    a = p.parse_args()
    have = set(load_outturn().index)
    rows = []
    for y in a.years:
        if y not in have:
            print(f"{y}: no outturn (run scripts/fetch_outturn.py {y})")
            continue
        t = run_year(y, a.seed, not a.no_network).reset_index()
        t.insert(0, "year", y)
        rows.append(t)
        print(y, "done", flush=True)
    df = pd.concat(rows, ignore_index=True)
    res = ROOT / "results"
    res.mkdir(exist_ok=True)
    df.round(3).to_csv(res / "backcast.csv", index=False)
    years = sorted(df.year.unique())
    wide = df.pivot(index="metric", columns="year", values=["model", "outturn"]).reindex(df.metric.unique())
    f = (lambda v: "–" if v != v else f"{v:,.1f}")
    md = ["| metric | " + " | ".join(f"{y} model / outturn" for y in years) + " |", "|---|" + "---|" * len(years)]
    for metric, r in wide.iterrows():
        md.append(f"| {metric} | " + " | ".join(f"{f(r[('model', y)])} / {f(r[('outturn', y)])}" for y in years) + " |")
    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    except Exception:
        commit = "unknown"
    head = (f"# Operating back-cast: model against GB outturn\n\nBaseline, seed {a.seed}; each year on its own weather, "
            f"fleet and prices (money of the day); code at {commit}.\nParameters fitted to an operating year were set on "
            f"{CALIBRATION_YEAR}; the other years check them.\n\n")
    foot = ("\n\nOutturn: NESO historic generation mix and carbon intensity (GB, incl. embedded wind and solar); "
            "Ofgem day-ahead baseload price;\nElexon MID price and FUELHH interconnector flows; constraint cost and "
            "curtailment: data/outturn/gb_constraints.csv.\n'Wind and solar, available' adds the wind turned down in the "
            "Balancing Mechanism to outturn generation.\nRows 'after BM redispatch' add the network stage's redispatch "
            "to the wholesale result.\n")
    (res / "backcast.md").write_text(head + "\n".join(md) + foot, encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
