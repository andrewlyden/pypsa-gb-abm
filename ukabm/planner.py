"""The optimum (Run 1) and the shared evaluator, both on a single GB bus in PyPSA.

* `plan`: least-cost capacity expansion with perfect foresight over 5-year investment periods
  (PyPSA multi-investment-period LP). Same technologies, costs, fuel and carbon paths, weather
  profiles, interconnector markets, electrolysers and starting fleet as the agent-based model, and the
  agent run's realised inflexible demand (base + heat pumps + EVs) in each period, so that only the
  decisions differ. Build rates are limited (config.PLANNER_BUILD_MW_PER_YEAR) and nothing new can
  come online before its lead time.
* `evaluate`: least-cost hourly dispatch (8760 h, perfect foresight) of a given fleet in one year,
  costed with ukabm.costs. Both capacity pathways (the planner's and the agents') go through it, so the
  difference between them is due to what was built, not to two different dispatch models.

Both are copperplate, like the wholesale market in the agent model.
"""
from __future__ import annotations

import logging
import warnings
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .config import TECHS, STORAGE_TECHS, VRE_TECHS, SOCIAL_DISCOUNT_RATE, PLANNER_BUILD_MW_PER_YEAR
from .costs import COMPONENTS, Unit, crf, fixed_costs, variable_cost

log = logging.getLogger(__name__)
# one thread per solve: gap runs are parallelised across processes
HIGHS_OPTIONS = {"output_flag": False, "threads": 1}
NEW_TECHS = ("wind_offshore", "wind_onshore", "solar", "battery", "ccgt", "ocgt", "gas_ccs",
             "h2_turbine", "nuclear")


def _quiet():
    for name in ("pypsa", "linopy", "highspy"):
        logging.getLogger(name).setLevel(logging.ERROR)


def _avail(model, u, hours):
    cf = model.cf_profile(u.tech)
    if cf is not None:
        return cf[hours]
    a = TECHS[u.tech].availability if u.availability is None else u.availability
    return np.full(len(hours), a)


def _groups(units):
    """Aggregate units with identical cost/availability characteristics: {(tech, eff, avail): mw}."""
    g = {}
    for u in units:
        eff = None if u.efficiency is None else round(u.efficiency, 2)
        k = (u.tech, eff, u.availability)
        g[k] = g.get(k, 0.0) + u.mw
    return g


def _trade_and_h2(model, year, hours):
    """Interconnector import offers / export bids and electrolysers as (name, p_nom, price, sign)."""
    imports, exports, _, _ = model.interconnector_blocks(year)
    out = []
    for b in imports:
        out.append((f"import{b.key}", float(np.max(b.avail)), np.broadcast_to(b.price, (model.H,))[hours], 1))
    for b in exports:
        out.append((f"export{b.key}", float(np.max(b.avail)), np.broadcast_to(b.price, (model.H,))[hours], -1))
    h2 = model.h2.capacity_mw(year)
    if h2 > 0:
        out.append(("electrolyser", h2, np.full(len(hours), model.h2.wtp()), -1))
    return out


# --------------------------------------------------------------------------------------- evaluator
def evaluate(model, year: int, units, load: np.ndarray, hours=None) -> dict:
    """Least-cost dispatch of *units* (active in *year*) against *load* (MW, hourly). Returns
    {'costs': {component: GBP/yr}, 'gen': {tech: MWh}, 'unserved_mwh', 'emissions_t'}."""
    import pypsa
    _quiet()
    hours = np.arange(model.H) if hours is None else np.asarray(hours)
    w = model.H / len(hours)
    units = [u for u in units if u.active(year)]
    n = pypsa.Network()
    n.set_snapshots(pd.RangeIndex(len(hours)))
    n.snapshot_weightings = n.snapshot_weightings.astype(float).assign(**{c: w for c in n.snapshot_weightings.columns})
    n.add("Bus", "GB")
    n.add("Load", "load", bus="GB", p_set=load[hours])
    n.add("Generator", "shed", bus="GB", p_nom=1e6, marginal_cost=model.policy.voll)
    info = {}
    for i, ((tech, eff, av), mw) in enumerate(_groups(units).items()):
        name = f"{tech}_{i}"
        if tech in STORAGE_TECHS:
            e = np.sqrt(TECHS[tech].efficiency)
            n.add("StorageUnit", name, bus="GB", p_nom=mw, max_hours=STORAGE_TECHS[tech], efficiency_store=e,
                  efficiency_dispatch=e, marginal_cost=TECHS[tech].vom, cyclic_state_of_charge=True)
        else:
            u = Unit(tech, mw, year, year, eff, av)
            mc = model.srmc(tech, year, efficiency=eff)
            n.add("Generator", name, bus="GB", p_nom=mw, p_max_pu=_avail(model, u, hours), marginal_cost=mc)
        info[name] = (tech, eff)
    trade = {}
    for name, p_nom, price, sign in _trade_and_h2(model, year, hours):
        if sign > 0:
            n.add("Generator", name, bus="GB", p_nom=p_nom, marginal_cost=price)
        else:
            n.add("Generator", name, bus="GB", p_nom=p_nom, p_max_pu=0.0, p_min_pu=-1.0, marginal_cost=price)
        trade[name] = price
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        status, cond = n.optimize(solver_name="highs", solver_options=HIGHS_OPTIONS, progress=False)
    if status != "ok":
        raise RuntimeError(f"evaluator dispatch failed in {year}: {status} {cond}")
    gp, sp = n.generators_t.p, n.storage_units_t.p
    c = dict.fromkeys(COMPONENTS, 0.0)
    c.update(fixed_costs(units, year, model.start))
    gen, em = {}, 0.0
    for name, (tech, eff) in info.items():
        if tech in STORAGE_TECHS:
            dis = float(sp[name].clip(lower=0).sum()) * w
            c["fuel"] += TECHS[tech].vom * dis
            gen[tech] = gen.get(tech, 0.0) + dis
            continue
        e = float(gp[name].sum()) * w
        for k, v in variable_cost(tech, eff, e, year, model.fuels, model.policy).items():
            c[k] += v
        gen[tech] = gen.get(tech, 0.0) + e
        t = TECHS[tech]
        if t.fuel is not None:
            em += e / (eff or t.efficiency) * t.co2_t_per_mwh_fuel
    for name, price in trade.items():
        val = float((gp[name].values * price).sum()) * w
        if name == "electrolyser":
            c["h2_value"] += val
        else:
            c["trade"] += val
            if name.startswith("import"):
                gen["imports"] = gen.get("imports", 0.0) + float(gp[name].sum()) * w
    shed = float(gp["shed"].sum()) * w
    c["unserved"] = shed * model.policy.voll
    return {"costs": c, "gen": gen, "unserved_mwh": shed, "emissions_t": em}


# ----------------------------------------------------------------------------------------- planner
@dataclass
class Plan:
    periods: list
    built_mw: pd.DataFrame                     # index period, columns tech: new capacity built in period
    units: list = field(default_factory=list)  # new-build Units (online = period)
    objective: float = float("nan")
    hours: np.ndarray | None = None


def sample_hours(model, loads: dict, every: int = 7) -> np.ndarray:
    """Every *every*-th day plus, for each period, the day with the highest load net of wind."""
    days = model.H // 24
    keep = set(range(every // 2, days, every))
    wind = model.cf_profile("wind_offshore")
    for load in loads.values():
        net = load[:days * 24] - 30000 * wind[:days * 24]
        keep.add(int(np.argmax(net)) // 24)
    return np.concatenate([np.arange(d * 24, d * 24 + 24) for d in sorted(keep)])


def plan(model, loads: dict, rate: float = SOCIAL_DISCOUNT_RATE, build_limits: dict | None = None,
         every_nth_day: int = 7) -> Plan:
    """Least-cost capacity expansion over investment periods = sorted(loads) (e.g. 2025, 2030, ...),
    starting from model.initial_fleet. loads: {period: hourly inflexible load (MW)}."""
    import pypsa
    _quiet()
    limits = dict(PLANNER_BUILD_MW_PER_YEAR if build_limits is None else build_limits)
    periods = sorted(loads)
    step = periods[1] - periods[0] if len(periods) > 1 else 5
    hours = sample_hours(model, loads, every_nth_day)
    w = model.H / len(hours)
    n = pypsa.Network()
    snaps = pd.MultiIndex.from_product([periods, range(len(hours))], names=["period", "timestep"])
    n.set_snapshots(snaps)
    n.investment_periods = periods
    n.snapshot_weightings = n.snapshot_weightings.astype(float).assign(**{c: w for c in n.snapshot_weightings.columns})
    start = periods[0]
    n.investment_period_weightings["years"] = float(step)
    n.investment_period_weightings["objective"] = [
        sum((1 + rate) ** -(p - start + k) for k in range(step)) for p in periods]
    n.add("Bus", "GB")
    n.add("Load", "load", bus="GB", p_set=pd.Series(np.concatenate([loads[p][hours] for p in periods]), index=snaps))
    n.add("Generator", "shed", bus="GB", p_nom=1e6, marginal_cost=model.policy.voll, build_year=start, lifetime=1000)

    def per_period(f):   # time series over all snapshots from a per-period function of the period
        return pd.Series(np.concatenate([np.broadcast_to(f(p), (len(hours),)) for p in periods]), index=snaps)

    # existing and committed fleet, aggregated by (tech, efficiency, availability, active periods)
    agg = {}
    for u in model.initial_fleet:
        act = [p for p in periods if u.active(p)]
        if not act:
            continue
        eff = None if u.efficiency is None else round(u.efficiency, 2)
        k = (u.tech, eff, u.availability, act[0], act[-1] - act[0] + step)
        agg[k] = agg.get(k, 0.0) + u.mw
    for i, ((tech, eff, av, by, life), mw) in enumerate(agg.items()):
        name = f"old_{tech}_{i}"
        u = Unit(tech, mw, by, by, eff, av)
        if tech in STORAGE_TECHS:
            e = np.sqrt(TECHS[tech].efficiency)
            n.add("StorageUnit", name, bus="GB", p_nom=mw, max_hours=STORAGE_TECHS[tech], efficiency_store=e,
                  efficiency_dispatch=e, marginal_cost=TECHS[tech].vom, build_year=by, lifetime=life,
                  cyclic_state_of_charge=True, cyclic_state_of_charge_per_period=True)
        else:
            n.add("Generator", name, bus="GB", p_nom=mw, build_year=by, lifetime=life,
                  p_max_pu=per_period(lambda p: _avail(model, u, hours)),
                  marginal_cost=per_period(lambda p: model.srmc(tech, p, efficiency=eff)))
    # new build: one extendable asset per technology and period
    for p in periods:
        for tech in NEW_TECHS:
            t = TECHS[tech]
            # years of decisions that can be online by period p: decisions from the start year onwards,
            # online after the lead time, within this period's step (offshore: only 2025 decisions reach 2030)
            years = min(step, p - start - t.lead_time + 1)
            cap = limits.get(tech, 0) * years
            if p == start or p < start + t.lead_time or cap <= 0 or not t.investable:
                continue
            if tech in model.scenario.get("banned_techs", []):
                continue
            cc = t.capex * 1000 * crf(rate, t.life) + t.fom * 1000
            name = f"new_{tech}_{p}"
            if tech in STORAGE_TECHS:
                e = np.sqrt(t.efficiency)
                n.add("StorageUnit", name, bus="GB", p_nom_extendable=True, p_nom_max=cap, capital_cost=cc,
                      max_hours=STORAGE_TECHS[tech], efficiency_store=e, efficiency_dispatch=e,
                      marginal_cost=t.vom, build_year=p, lifetime=t.life,
                      cyclic_state_of_charge=True, cyclic_state_of_charge_per_period=True)
            else:
                u = Unit(tech, 1.0, p, p)
                n.add("Generator", name, bus="GB", p_nom_extendable=True, p_nom_max=cap, capital_cost=cc,
                      build_year=p, lifetime=t.life, p_max_pu=per_period(lambda q: _avail(model, u, hours)),
                      marginal_cost=per_period(lambda q: model.srmc(tech, q)))
    # trade and electrolysers: one asset per period (capacity and prices change by period)
    for p in periods:
        for name, p_nom, price, sign in _trade_and_h2(model, p, hours):
            mc = per_period(lambda q: price if q == p else 0.0)
            kw = dict(p_max_pu=0.0, p_min_pu=-1.0) if sign < 0 else {}
            n.add("Generator", f"{name}_{p}", bus="GB", p_nom=p_nom, marginal_cost=mc, build_year=p,
                  lifetime=step, **kw)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        status, cond = n.optimize(multi_investment_periods=True, solver_name="highs",
                                  solver_options=HIGHS_OPTIONS, progress=False)
    if status != "ok":
        raise RuntimeError(f"planner failed: {status} {cond}")
    built = pd.DataFrame(0.0, index=periods, columns=list(NEW_TECHS))
    units = []
    for df in (n.generators, n.storage_units):
        for name, row in df[df.index.str.startswith("new_")].iterrows():
            tech, p = name[4:].rsplit("_", 1)
            mw = float(row.p_nom_opt)
            if mw < 1.0:
                continue
            built.loc[int(p), tech] += mw
            units.append(Unit(tech, mw, int(p), int(p) + TECHS[tech].life - 1))
    return Plan(periods, built, units, float(n.objective), hours)
