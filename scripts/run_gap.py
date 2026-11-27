"""Optimal vs emergent: planner benchmark, agent runs and the gap between them (ukabm.gap).

    python scripts/run_gap.py                      # ladder (baseline, 4 rungs) + levers, seeds 1-3
    python scripts/run_gap.py --only ladder --seeds 1 --jobs 4
Writes results/gap_costs.csv, gap_capacity.csv, gap_annual.csv and gap_summary.csv.
"""
import argparse
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ukabm.gap import ladder_tasks, run_many, summarise  # noqa: E402

# market-design and policy levers, full model (deck slide 13)
LEVERS = ["no_cfd", "no_capacity_market", "heat_push", "high_carbon", "high_gas"]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3])
    p.add_argument("--only", choices=["ladder", "levers"], default=None)
    p.add_argument("--jobs", type=int, default=max((os.cpu_count() or 2) - 2, 1))
    p.add_argument("--end", type=int, default=2050)
    a = p.parse_args()
    tasks = []
    if a.only in (None, "ladder"):
        tasks += ladder_tasks("baseline", a.seeds)
    if a.only in (None, "levers"):
        tasks += [(s, seed, [], s) for s in LEVERS for seed in a.seeds]
    t0 = time.time()
    out = run_many(tasks, jobs=a.jobs, end=a.end)
    res = ROOT / "results"
    for k in ("costs", "capacity", "annual"):
        out[k].to_csv(res / f"gap_{k}.csv", index=False)
    for label, seed, err in out["failed"]:
        print(f"FAILED: {label} seed {seed}: {err}")
    s = summarise(out["costs"])
    s.to_csv(res / "gap_summary.csv", index=False)
    print(f"{len(tasks)} runs in {time.time() - t0:.0f}s")
    print(s.groupby("run", sort=False)[["gap_total_bn", "gap_investment_bn", "gap_operation_bn",
                                        "gap_total_pct"]].median().round(1).to_string())


if __name__ == "__main__":   # required: worker processes re-import this file
    main()
