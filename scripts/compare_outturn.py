"""Compare the model's 2025 with GB outturn and write results/calibration_2025.md.

    python scripts/compare_outturn.py            # baseline, seed 42
"""
import logging
import sys
import warnings
from pathlib import Path

from ukabm import GBMarketModel, get_scenario
from ukabm.outturn import compare

warnings.filterwarnings("ignore")
logging.disable(logging.WARNING)
OUT = Path(__file__).resolve().parents[1] / "results" / "calibration_2025.md"


def main(year=2025, seed=42):
    m = GBMarketModel(get_scenario("baseline"), start=year, end=year, seed=seed, network_every=1)
    tab = compare(m.run().loc[year], year)
    md = ["| metric | model | outturn | model - outturn |", "|---|---|---|---|"]
    for k, r in tab.iterrows():
        f = (lambda v: "–" if v != v else f"{v:,.1f}")
        md.append(f"| {k} | {f(r.model)} | {f(r.outturn)} | {f(r['diff'])} |")
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(f"# Model {year} (baseline, seed {seed}) vs GB outturn\n\n" + "\n".join(md) + "\n\n"
                   "Outturn: NESO historic generation mix and carbon intensity (GB, incl. embedded wind/solar);\n"
                   "Elexon MID price (APXMIDP) and FUELHH interconnector flows (scripts/fetch_outturn.py);\n"
                   "constraint cost and curtailment: data/outturn/gb_constraints.csv (LCP Delta 2026, from NESO data).\n"
                   "Rows 'after BM redispatch' add the network stage's annualised redispatch to the wholesale result.\n")
    print("\n".join(md))


if __name__ == "__main__":
    main(*(int(a) for a in sys.argv[1:]))
