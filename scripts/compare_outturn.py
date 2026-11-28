"""Compare the model's 2025 with GB outturn and write results/calibration_2025.md.

    python scripts/compare_outturn.py            # baseline, seed 42

2025 is the year the operating parameters were calibrated on (docs/calibration.md). The year is run on
its own weather, fleet and prices, exactly as in the five-year back-cast (scripts/run_backcast.py),
which checks the same parameters on 2021-2024.
"""
import logging
import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_backcast import run_year  # noqa: E402

warnings.filterwarnings("ignore")
logging.disable(logging.WARNING)
OUT = Path(__file__).resolve().parents[1] / "results" / "calibration_2025.md"


def main(year=2025, seed=42):
    tab = run_year(year, seed)
    md = ["| metric | model | outturn | model - outturn |", "|---|---|---|---|"]
    for k, r in tab.iterrows():
        f = (lambda v: "–" if v != v else f"{v:,.1f}")
        md.append(f"| {k} | {f(r.model)} | {f(r.outturn)} | {f(r['diff'])} |")
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(f"# Model {year} (baseline, seed {seed}) vs GB outturn\n\n" + "\n".join(md) + "\n\n"
                   "The year on its own weather, fleet, fuel and carbon prices (money of the day) and neighbour prices.\n"
                   "Outturn: NESO historic generation mix and carbon intensity (GB, incl. embedded wind/solar);\n"
                   "Ofgem day-ahead baseload price; Elexon MID price (APXMIDP) and FUELHH interconnector flows\n"
                   "(scripts/fetch_outturn.py); constraint cost and curtailment: data/outturn/gb_constraints.csv\n"
                   "(LCP Delta 2026, from NESO data). 'Wind and solar, available' adds the wind turned down in the\n"
                   "Balancing Mechanism to outturn. Rows 'after BM redispatch' add the network stage's redispatch.\n",
                   encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main(*(int(a) for a in sys.argv[1:]))
