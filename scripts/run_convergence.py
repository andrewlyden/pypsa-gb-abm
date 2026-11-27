"""Convergence test (README roadmap item 7): under textbook conditions the agents should reproduce the
least-cost plan. Runs the competitive_benchmark scenario through ukabm.gap and writes
results/convergence_summary.md (and results/convergence_*.csv).

    python scripts/run_convergence.py                  # seeds 1-3, 2025-2050, 3 jobs (~1 h)
    python scripts/run_convergence.py --seeds 1 --end 2035 --jobs 1
"""
import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ukabm.gap import run_many, summarise  # noqa: E402

TARGET_PCT = 3.0     # the roadmap's aim for the convergence gap


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3])
    p.add_argument("--end", type=int, default=2050)
    p.add_argument("--jobs", type=int, default=3)
    a = p.parse_args()
    t0 = time.time()
    tasks = [("competitive_benchmark", s, [], "competitive_benchmark") for s in a.seeds]
    out = run_many(tasks, jobs=a.jobs, end=a.end)
    res = ROOT / "results"
    for k, df in out.items():
        df.to_csv(res / f"convergence_{k}.csv", index=False)
    s = summarise(out["costs"])
    cap = out["capacity"]
    last = cap[cap.year == cap.year.max()].pivot_table(index="tech", columns="pathway", values="gw", aggfunc="median")
    lines = [
        f"# Convergence test: competitive benchmark vs the least-cost plan ({min(a.seeds)}–{max(a.seeds)} seeds, 2025–{a.end})",
        "",
        "Energy-only market, scarcity at VoLL only, idealised firms investing merchant on lifetime forecasts",
        f"(scenario `competitive_benchmark`). Aim: gap below {TARGET_PCT:.0f} % of the optimum's PV system cost.",
        "",
        "| seed | optimal PV (£bn) | agents PV (£bn) | gap (£bn) | investment | operation | gap (%) |",
        "|---|---|---|---|---|---|---|",
    ]
    for _, r in s.iterrows():
        lines.append(f"| {r.seed:.0f} | {r.pv_planner_bn:.0f} | {r.pv_agents_realised_bn:.0f} | {r.gap_total_bn:.1f} | "
                     f"{r.gap_investment_bn:.1f} | {r.gap_operation_bn:.1f} | {r.gap_total_pct:.1f} |")
    lines += ["", f"Capacity in {cap.year.max()} (GW, median of seeds):", "", "| tech | optimal | agents |", "|---|---|---|"]
    for tech, r in last.fillna(0).iterrows():
        lines.append(f"| {tech} | {r.get('planner', 0):.1f} | {r.get('agents', 0):.1f} |")
    (res / "convergence_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"{len(tasks)} runs in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
