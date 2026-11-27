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

Both are copperplate, like the wholesale market in the agent model. Both hold the same reserve and
response requirement (config.RESERVE, README item 9), the services the agents' batteries are paid for
outside the hourly market.
"""
from __future__ import annotations

import logging
import warnings
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .config import TECHS, STORAGE_TECHS, VRE_TECHS, SOCIAL_DISCOUNT_RATE, PLANNER_BUILD_MW_PER_YEAR, RESERVE
from .costs import COMPONENTS, Unit, crf, fixed_costs, variable_cost

log = logging.getLogger(__name__)
# one thread per solve: gap runs are parallelised across processes
HIGHS_OPTIONS = {"output_flag": False, "threads": 1}
NEW_TECHS = ("wind_offshore", "wind_onshore", "solar", "battery", "ccgt", "ocgt", "gas_ccs",
             "h2_turbine", "nuclear")


def _quiet():
    for name in ("pypsa", "linopy", "highspy"):
        logging.getLogger(name).setLevel(logging.ERROR)


def _avail(model, u, hours, weights=None):
    """Availability of *u* in the sampled *hours*. With *weights* (a sample), wind and solar profiles
    are rescaled so their weighted sample mean equals the annual mean (sampling noise removed).
    ``u.online`` selects the fleet or the new-build profile (GBMarketModel.cf_profile)."""
    cf = model.cf_profile(u.tech, u.online)
    if cf is not None:
        x = cf[hours]
        if weights is not None:
            x = np.clip(x * cf.mean() / max(float((x * weights).sum() / weights.sum()), 1e-9), 0, 1)
        return x
    a = TECHS[u.tech].availability if u.availability is None else u.availability
    return np.full(len(hours), a)


def _groups(model, units):
    """Aggregate units with identical cost, availability and profile: {(tech, eff, avail, online): mw},
    where *online* is the first year of one unit of the group (it selects the group's profile)."""
    g, rep = {}, {}
    for u in units:
        eff = None if u.efficiency is None else round(u.efficiency, 2)
        k = (u.tech, eff, u.availability, model.cf_key(u.tech, u.online))
        g[k] = g.get(k, 0.0) + u.mw
        rep.setdefault(k, u.online)
    return {(k[0], k[1], k[2], rep[k]): mw for k, mw in g.items()}


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


# ----------------------------------------------------------------------------- reserve and response
def reserve_settings(model) -> dict | None:
    """config.RESERVE with the scenario's ``reserve`` overrides; None when switched off (scale 0)."""
    s = dict(RESERVE)
    s.update(model.scenario.get("reserve", {}) or {})
    k = float(s.pop("scale", 1.0))
    for key in ("response_mw", "vre_share", "load_share"):
        s[key] = float(s[key]) * k
    if s["response_mw"] <= 0 and s["vre_share"] <= 0 and s["load_share"] <= 0:
        return None
    return s


def _zeros(a):
    """Zeros shaped like DataArray *a* (variable bounds can be -inf, so not a * 0)."""
    return a.copy(data=np.zeros(a.shape))


def _active(n, c, names):
    """(snapshots x names) array: 1 where the asset exists in the snapshot's investment period."""
    if len(n.investment_periods) == 0:
        return np.ones((len(n.snapshots), len(names)))
    out = np.zeros((len(n.snapshots), len(names)))
    per = n.snapshots.get_level_values(0)
    for p in n.investment_periods:
        out[per == p] = n.get_active_assets(c, p).reindex(names).fillna(False).astype(float).values
    return out


def _capacity(m, n, c, names, factor):
    """Sum over *names* of factor (snapshots x names) x p_nom, as (constant, expression or None) by
    snapshot; extendable assets contribute through their p_nom variable."""
    df = n.static(c) if hasattr(n, "static") else getattr(n, {"Generator": "generators",
                                                              "StorageUnit": "storage_units"}[c])
    ext = df.loc[names, "p_nom_extendable"].values.astype(bool)
    const = (factor[:, ~ext] * df.loc[names, "p_nom"].values[~ext]).sum(axis=1)
    expr = None
    if ext.any():
        en = list(np.asarray(names)[ext])
        tmpl = m[f"{c}-p"].lower.sel(name=en) if c == "Generator" else m[f"{c}-p_dispatch"].lower.sel(name=en)
        expr = (m[f"{c}-p_nom"].sel(name=en) * tmpl.copy(data=factor[:, ext])).sum("name")
    return const, expr


def _add_reserve(n, s):
    """Reserve and response constraints (see config.RESERVE) on a PyPSA network being optimised.
    Assets are identified by their carrier (= ukabm technology)."""
    m = n.model
    gens = n.generators.index[n.generators.carrier.isin(s["generators"])]
    stor = n.storage_units.index[n.storage_units.carrier.isin(s["storage"])]
    vre = n.generators.index[n.generators.carrier.isin(VRE_TECHS)]
    snap = m["Generator-p"].lower.isel(name=0, drop=True)        # template with the snapshot coordinate
    ns = len(n.snapshots)
    load = n.loads_t.p_set.sum(axis=1).values if len(n.loads) else np.zeros(ns)

    held = 0
    held_storage_response = 0
    if len(gens):
        p = m["Generator-p"].sel(name=list(gens))
        r = m.add_variables(lower=_zeros(p.lower), name="Generator-reserve")
        pmax = n.get_switchable_as_dense("Generator", "p_max_pu")[gens].values * _active(n, "Generator", gens)
        ext = n.generators.loc[gens, "p_nom_extendable"].values.astype(bool)
        if (~ext).any():
            fx = list(gens[~ext])
            rhs = p.lower.sel(name=fx).copy(data=pmax[:, ~ext] * n.generators.loc[fx, "p_nom"].values)
            m.add_constraints(r.sel(name=fx) + p.sel(name=fx) <= rhs, name="Generator-reserve-headroom-fix")
        if ext.any():
            ex = list(gens[ext])
            f = p.lower.sel(name=ex).copy(data=pmax[:, ext])
            m.add_constraints(r.sel(name=ex) + p.sel(name=ex) - f * m["Generator-p_nom"].sel(name=ex) <= 0,
                              name="Generator-reserve-headroom-ext")
        held = r.sum("name")
    if len(stor):
        pdis = m["StorageUnit-p_dispatch"].sel(name=list(stor))
        psto = m["StorageUnit-p_store"].sel(name=list(stor))
        soc = m["StorageUnit-state_of_charge"].sel(name=list(stor))
        rf = m.add_variables(lower=_zeros(pdis.lower), name="StorageUnit-response")
        rr = m.add_variables(lower=_zeros(pdis.lower), name="StorageUnit-reserve")
        act = _active(n, "StorageUnit", stor)
        ext = n.storage_units.loc[stor, "p_nom_extendable"].values.astype(bool)
        if (~ext).any():
            fx = list(stor[~ext])
            rhs = pdis.lower.sel(name=fx).copy(data=act[:, ~ext] * n.storage_units.loc[fx, "p_nom"].values)
            m.add_constraints(rf.sel(name=fx) + rr.sel(name=fx) + pdis.sel(name=fx) - psto.sel(name=fx) <= rhs,
                              name="StorageUnit-reserve-headroom-fix")
        if ext.any():
            ex = list(stor[ext])
            f = pdis.lower.sel(name=ex).copy(data=act[:, ext])
            m.add_constraints(rf.sel(name=ex) + rr.sel(name=ex) + pdis.sel(name=ex) - psto.sel(name=ex)
                              - f * m["StorageUnit-p_nom"].sel(name=ex) <= 0, name="StorageUnit-reserve-headroom-ext")
        m.add_constraints(s["hours"] * (rf + rr) - soc <= 0, name="StorageUnit-reserve-energy")
        held = held + rr.sum("name")
        held_storage_response = rf.sum("name")

    # requirements, each with a penalised shortfall
    w = n.snapshot_weightings.objective.values.astype(float)
    if len(n.investment_periods):
        w = w * n.investment_period_weightings.objective.reindex(n.snapshots.get_level_values(0)).values
    cost = 0
    if s["response_mw"] > 0:
        short = m.add_variables(lower=_zeros(snap), name="Reserve-response-shortfall")
        m.add_constraints(held_storage_response + short >= snap.copy(data=np.full(ns, s["response_mw"])),
                          name="Reserve-response")
        cost = cost + (short * snap.copy(data=w * s["shortfall_cost"])).sum()
    if s["vre_share"] > 0 or s["load_share"] > 0:
        req = s["load_share"] * load
        lhs = held
        if s["vre_share"] > 0 and len(vre):
            pmax = n.get_switchable_as_dense("Generator", "p_max_pu")[vre].values * _active(n, "Generator", vre)
            const, expr = _capacity(m, n, "Generator", list(vre), pmax)
            req = req + s["vre_share"] * const
            if expr is not None:
                lhs = lhs - s["vre_share"] * expr
        short = m.add_variables(lower=_zeros(snap), name="Reserve-reserve-shortfall")
        m.add_constraints(lhs + short >= snap.copy(data=req), name="Reserve-reserve")
        cost = cost + (short * snap.copy(data=w * s["shortfall_cost"])).sum()
    m.add_objective(m.objective.expression + cost, overwrite=True)


def _shortfall_mwh(n, weights) -> float:
    """Reserve not held over the solved snapshots, MWh (weighted to the year)."""
    tot = 0.0
    for k in ("Reserve-response-shortfall", "Reserve-reserve-shortfall"):
        if k in n.model.variables:
            tot += float((n.model[k].solution.values * weights).sum())
    return tot


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
    # objective and generator energy scale with the sampling weight; storage steps one hour per snapshot
    n.snapshot_weightings = n.snapshot_weightings.astype(float).assign(objective=w, generators=w, stores=1.0)
    n.add("Bus", "GB")
    n.add("Load", "load", bus="GB", p_set=load[hours])
    n.add("Generator", "shed", bus="GB", p_nom=1e6, marginal_cost=model.policy.voll)
    info = {}
    for i, ((tech, eff, av, online), mw) in enumerate(_groups(model, units).items()):
        name = f"{tech}_{i}"
        if tech in STORAGE_TECHS:
            e = np.sqrt(TECHS[tech].efficiency)
            n.add("StorageUnit", name, bus="GB", carrier=tech, p_nom=mw, max_hours=STORAGE_TECHS[tech],
                  efficiency_store=e, efficiency_dispatch=e, marginal_cost=TECHS[tech].vom,
                  cyclic_state_of_charge=True)
        else:
            u = Unit(tech, mw, online, year, eff, av)
            mc = model.srmc(tech, year, efficiency=eff)
            n.add("Generator", name, bus="GB", carrier=tech, p_nom=mw, p_max_pu=_avail(model, u, hours),
                  marginal_cost=mc)
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
        rs = reserve_settings(model)
        status, cond = n.optimize(solver_name="highs", solver_options=HIGHS_OPTIONS, progress=False,
                                  extra_functionality=(lambda n_, s_: _add_reserve(n_, rs)) if rs else None)
    if status != "ok":
        raise RuntimeError(f"evaluator dispatch failed in {year}: {status} {cond}")
    short = _shortfall_mwh(n, w) if rs else 0.0
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
    # reserve not held is costed with unserved energy (it is a reliability shortfall)
    c["unserved"] = shed * model.policy.voll + (short * rs["shortfall_cost"] if rs else 0.0)
    return {"costs": c, "gen": gen, "unserved_mwh": shed, "emissions_t": em, "reserve_shortfall_mwh": short}


# ----------------------------------------------------------------------------------------- planner
@dataclass
class Plan:
    periods: list
    built_mw: pd.DataFrame                     # index period, columns tech: new capacity built in period
    units: list = field(default_factory=list)  # new-build Units (online = period)
    objective: float = float("nan")
    hours: np.ndarray | None = None


def sample_days(model, loads: dict, every: int = 7):
    """One day in every *every* days, the position within each block rotating so that every weekday is
    sampled equally often, plus for each period the day with the highest load net of wind. Returns
    (ordinary days, peak days), each sorted."""
    days = model.H // 24
    ordinary = {b + (k % every) for k, b in enumerate(range(0, days - every + 1, every))}
    wind = model.cf_profile("wind_offshore")
    peak = set()
    for load in loads.values():
        net = load[:days * 24] - 30000 * wind[:days * 24]
        peak.add(int(np.argmax(net)) // 24)
    return sorted(ordinary), sorted(peak - ordinary)


def sample_hours(model, loads: dict, every: int = 7) -> np.ndarray:
    ordinary, peak = sample_days(model, loads, every)
    return np.concatenate([np.arange(d * 24, d * 24 + 24) for d in sorted(ordinary + peak)])


def sample_weights(model, loads: dict, every: int = 7) -> np.ndarray:
    """Hours represented by each sampled hour (same order as ``sample_hours``): a peak day stands for
    itself (weight 1); the ordinary days share the rest of the year. Sums to model.H."""
    ordinary, peak = sample_days(model, loads, every)
    w_ord = (model.H - 24 * len(peak)) / (24 * len(ordinary))
    return np.concatenate([np.full(24, 1.0 if d in peak else w_ord) for d in sorted(ordinary + peak)])


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
    w = sample_weights(model, loads, every_nth_day)      # hours each sampled hour represents
    n = pypsa.Network()
    snaps = pd.MultiIndex.from_product([periods, range(len(hours))], names=["period", "timestep"])
    n.set_snapshots(snaps)
    n.investment_periods = periods
    # objective and generator energy scale with the sampling weight; storage steps one hour per snapshot
    wt = np.tile(w, len(periods))
    n.snapshot_weightings = n.snapshot_weightings.astype(float).assign(objective=wt, generators=wt, stores=1.0)
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
    agg, online = {}, {}
    for u in model.initial_fleet:
        act = [p for p in periods if u.active(p)]
        if not act:
            continue
        eff = None if u.efficiency is None else round(u.efficiency, 2)
        k = (u.tech, eff, u.availability, act[0], act[-1] - act[0] + step, model.cf_key(u.tech, u.online))
        agg[k] = agg.get(k, 0.0) + u.mw
        online.setdefault(k, u.online)
    for i, (k, mw) in enumerate(agg.items()):
        tech, eff, av, by, life, _ = k
        name = f"old_{tech}_{i}"
        u = Unit(tech, mw, online[k], by, eff, av)       # online: selects the fleet or new-build profile
        if tech in STORAGE_TECHS:
            e = np.sqrt(TECHS[tech].efficiency)
            n.add("StorageUnit", name, bus="GB", carrier=tech, p_nom=mw, max_hours=STORAGE_TECHS[tech],
                  efficiency_store=e, efficiency_dispatch=e, marginal_cost=TECHS[tech].vom, build_year=by, lifetime=life,
                  cyclic_state_of_charge=True, cyclic_state_of_charge_per_period=True)
        else:
            n.add("Generator", name, bus="GB", carrier=tech, p_nom=mw, build_year=by, lifetime=life,
                  p_max_pu=per_period(lambda p: _avail(model, u, hours, w)),
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
                n.add("StorageUnit", name, bus="GB", carrier=tech, p_nom_extendable=True, p_nom_max=cap,
                      capital_cost=cc,
                      max_hours=STORAGE_TECHS[tech], efficiency_store=e, efficiency_dispatch=e,
                      marginal_cost=t.vom, build_year=p, lifetime=t.life,
                      cyclic_state_of_charge=True, cyclic_state_of_charge_per_period=True)
            else:
                u = Unit(tech, 1.0, p, p)
                n.add("Generator", name, bus="GB", carrier=tech, p_nom_extendable=True, p_nom_max=cap,
                      capital_cost=cc,
                      build_year=p, lifetime=t.life, p_max_pu=per_period(lambda q: _avail(model, u, hours, w)),
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
        rs = reserve_settings(model)
        status, cond = n.optimize(multi_investment_periods=True, solver_name="highs",
                                  solver_options=HIGHS_OPTIONS, progress=False,
                                  extra_functionality=(lambda n_, s_: _add_reserve(n_, rs)) if rs else None)
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
