"""The gap between the optimal and the emergent system (deck slides 5, 10, 11).

For one scenario and seed:

1. Run 2, many actors: the agent-based model runs 2025-2050 (`GBMarketModel`).
2. Run 1, one planner: `planner.plan` builds the least-cost pathway from the same starting fleet,
   against the agent run's realised inflexible demand, in 5-year investment periods.
3. Both capacity pathways are dispatched at least cost by the same evaluator (`planner.evaluate`)
   in each period year, and costed with the same definition (`ukabm.costs`).

The gap in year y is split into
    investment gap = evaluator(agents' fleet) - evaluator(planner's fleet)   what was built
    operation gap  = agents' realised cost    - evaluator(agents' fleet)     how it was run (mark-ups,
                     heuristic storage/EV/electrolyser dispatch)
    total gap      = agents' realised cost    - evaluator(planner's fleet)
and summarised as a present value 2025-2054 at the social discount rate, each period year standing
for the five years from it.

`run_ladder` repeats Run 2 with agent traits idealised (scenarios.LADDER) to attribute the gap to its
candidate sources. Each rung has its own planner run against its own demand, so every gap is like-for-like.
"""
from __future__ import annotations

import logging
import warnings
from concurrent.futures import ProcessPoolExecutor

import pandas as pd

from .config import SOCIAL_DISCOUNT_RATE
from .costs import COMPONENTS, present_value, total
from .model import GBMarketModel
from .planner import evaluate, plan
from .scenarios import LADDER, get_scenario, with_ideal

KINDS = ("planner", "agents_eval", "agents_realised")


def gap_run(scenario: str = "baseline", seed: int = 42, ideal=(), label: str = "", start: int = 2025,
            end: int = 2050, step: int = 5, network_every: int = 0, overrides: dict | None = None,
            **model_kw) -> dict:
    """One optimal-vs-emergent comparison; *overrides* are merged into the scenario (e.g.
    ``{"reserve": {"scale": 0}}``). Returns {'costs', 'capacity', 'annual'} DataFrames:
    costs: one row per (year, kind) with cost components and total (GBP bn/yr);
    capacity: one row per (year, pathway, tech) in GW; annual: the agent run's annual results."""
    prev = logging.root.manager.disable
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        logging.disable(logging.INFO)
        try:
            sc = with_ideal(get_scenario(scenario), ideal)
            sc.update(overrides or {})
            m = GBMarketModel(sc, seed=seed, start=start, end=end, network_every=network_every, **model_kw)
            annual = m.run()
            years = list(range(start, end + 1, step))
            loads = {y: m.hourly[y]["load"].values for y in years}
            p = plan(m, loads)
            rows, cap = [], []
            for y in years:
                fleets = {"planner": list(m.initial_fleet) + p.units, "agents": m.plants}
                ev = {k: evaluate(m, y, f, loads[y]) for k, f in fleets.items()}
                realised = {k: annual.loc[y, f"syscost_{k}_bn"] * 1e9 for k in COMPONENTS}
                for kind, c, extra in (("planner", ev["planner"]["costs"], ev["planner"]),
                                       ("agents_eval", ev["agents"]["costs"], ev["agents"]),
                                       ("agents_realised", realised, None)):
                    row = dict(year=y, kind=kind, **{k: v / 1e9 for k, v in c.items()}, total=total(c) / 1e9)
                    if extra is not None:
                        row["emissions_mt"] = extra["emissions_t"] / 1e6
                        row["unserved_gwh"] = extra["unserved_mwh"] / 1e3
                        row["reserve_short_gwh"] = extra.get("reserve_shortfall_mwh", 0.0) / 1e3
                    else:
                        row["emissions_mt"] = annual.loc[y, "emissions_mt"]
                        row["unserved_gwh"] = annual.loc[y, "unserved_gwh"]
                    rows.append(row)
                for path, f in fleets.items():
                    by = {}
                    for u in f:
                        if u.active(y):
                            by[u.tech] = by.get(u.tech, 0.0) + u.mw / 1e3
                    cap += [dict(year=y, pathway=path, tech=t, gw=v) for t, v in by.items()]
        finally:
            logging.disable(prev)
    costs = pd.DataFrame(rows)
    capacity = pd.DataFrame(cap)
    for df in (costs, capacity, annual):
        df.insert(0, "seed", seed)
        df.insert(0, "run", label or scenario)
    return {"costs": costs, "capacity": capacity, "annual": annual.reset_index()}


def summarise(costs: pd.DataFrame, rate: float = SOCIAL_DISCOUNT_RATE) -> pd.DataFrame:
    """Per (run, seed): PV 2025-2054 (GBP bn) of each kind, and the gap split. Assumes 5-year steps."""
    out = []
    for (run, seed), g in costs.groupby(["run", "seed"], sort=False):
        years = sorted(g.year.unique())
        step = years[1] - years[0] if len(years) > 1 else 1
        pv = {k: present_value(g[g.kind == k].set_index("year")["total"].to_dict(), rate, years[0], step)
              for k in KINDS}
        out.append(dict(run=run, seed=seed, pv_planner_bn=pv["planner"], pv_agents_eval_bn=pv["agents_eval"],
                        pv_agents_realised_bn=pv["agents_realised"],
                        gap_total_bn=pv["agents_realised"] - pv["planner"],
                        gap_investment_bn=pv["agents_eval"] - pv["planner"],
                        gap_operation_bn=pv["agents_realised"] - pv["agents_eval"],
                        gap_total_pct=100 * (pv["agents_realised"] - pv["planner"]) / pv["planner"]))
    return pd.DataFrame(out)


def _task(args):
    scenario, seed, ideal, label, overrides, kw = args
    try:
        return gap_run(scenario, seed, ideal, label, overrides=overrides, **kw)
    except Exception as e:          # one failed run (e.g. a solver status) must not discard the batch
        logging.getLogger(__name__).error("gap run %s seed %s failed: %r", label or scenario, seed, e)
        return {"failed": (label or scenario, seed, repr(e))}


def run_many(tasks, jobs: int = 1, **kw) -> dict:
    """tasks: iterable of (scenario, seed, ideal_groups, label[, scenario overrides]). Returns
    concatenated DataFrames, plus 'failed': a list of (label, seed, error) for runs that raised."""
    args = [(t[0], int(t[1]), list(t[2]), t[3], t[4] if len(t) > 4 else None, kw) for t in tasks]
    if jobs > 1:
        with ProcessPoolExecutor(max_workers=jobs) as ex:
            res = list(ex.map(_task, args))
    else:
        res = [_task(a) for a in args]
    ok = [r for r in res if "failed" not in r]
    out = {k: pd.concat([r[k] for r in ok], ignore_index=True) if ok else pd.DataFrame()
           for k in ("costs", "capacity", "annual")}
    out["failed"] = [r["failed"] for r in res if "failed" in r]
    return out


def ladder_tasks(scenario: str = "baseline", seeds=(1, 2, 3)):
    return [(scenario, s, ideal, label) for label, ideal in LADDER for s in seeds]
