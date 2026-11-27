"""GB electricity-market ABM: annual investment/policy loop around an hourly market.

Yearly sequence (each step = one delivery year):
  1. commission pipeline / retire plants
  2. build hourly demand: base (PyPSA-GB ESPENI shape) + heat pumps + EVs + electrolysers
  3. market: GenCo offers -> pass-1 clearing -> storage, smart EV, electrolysers react -> pass-2
  4. settlement: energy, CfD difference payments, RO, Capacity Market; emissions; gas burn
  5. network stage (PyPSA-GB zonal redispatch) on sample hours  [every *network_every* years]
  6. multi-energy feedbacks: retail prices -> heat choice; gas throughput -> gas network tariff
  7. retirement decisions (persistent losses, end of life)
  8. investment: CfD allocation round, T-4 Capacity Market, merchant decisions on forecasts
"""
from __future__ import annotations

import copy
import logging

import numpy as np
import pandas as pd

from .agents import GenCo, Plant
from .config import (TECHS, VRE_TECHS, STORAGE_TECHS, INITIAL_FLEET_MW, EXISTING_FLEET_EFFICIENCY,
                     NESO_CI_FACTORS, Policy, Fuels, BATTERY_ANCILLARY_POT, BATTERY_TRADING_PER_MW_VRE,
                     BATTERY_FLEET_FLOOR_MW)
from .data import PyPSAGBData
from .costs import COMPONENTS as COST_COMPONENTS, fixed_costs, variable_cost
from . import decisions
from .institutions import CFD_TECHS, SystemOperator, make_government
from .market import Block, clear, merit_order, storage_arbitrage
from .scenarios import IDEAL_TRAITS
from .multienergy import HeatModule, GasNetworkModule, EVModule, HydrogenModule
from . import network as netmod

log = logging.getLogger(__name__)

try:
    import mesa
    ModelBase = mesa.Model
except Exception:  # pragma: no cover
    class ModelBase:
        def __init__(self, seed=None):
            pass

# Interconnector trade (see interconnector_blocks). Price levels are foreign mean price / SRMC of an
# existing GB CCGT, calibrated to 2025: capacity-weighted FR/NL/BE/NO2/DK1 day-ahead averaged
# 0.74 x the GB price (EUR 70.3 vs 94.4/MWh; Energy-Charts/SMARD, Ember) and SEM 1.21 x GB
# (EUR 114.4/MWh, Ember), with the GB price at 0.91 x the modelled CCGT SRMC in 2025 (MID
# GBP 80.9/MWh vs 89.1). The spread is calibrated so that 2025 gross flows match outturn (imports
# 44.0 TWh, exports 14.8 TWh; Elexon FUELHH): it stands for losses, post-Brexit explicit capacity
# allocation (flows respond sluggishly to day-ahead spreads) and GB internal constraints that keep
# Scottish surplus from reaching the southern links.
IC_PRICE_LEVEL = {"continent": 0.68, "SEM": 1.10}
IC_SPREAD = 12.0         # GBP/MWh
IC_AVAILABILITY = 0.9    # GB peak import 2025 was 9.2 GW on 10.5 GW (Elexon FUELHH)

# Storage fleet dispatched in this many sequential tranches (price impact of the fleet's own trading)
STORAGE_TRANCHES = {"battery": 3, "pumped_hydro": 1}

# Network stage: wind-CF strata for representative hours; nuclear BM bid (inflexible plant).
NET_STRATA = 8
NUCLEAR_BM_BID = -300.0

# Existing / committed nuclear: (mw, online, retire, zone, availability). Indicative public dates.
# Availability of the legacy fleet calibrated to outturn: GB nuclear 38.4 TWh (2024) and 34.2 TWh
# (2025, NESO); Sizewell B ran at 99 % in 2025 (10.4 TWh) while the AGRs averaged ~58 % with an
# extended Hartlepool outage (EDF UK nuclear fleet update, Jan 2026; EDF plans ~36-37 TWh in
# 2026-27). AGRs 0.62, Sizewell B 0.88 (18-month refuelling cycle); new EPRs use Tech default.
# Zones matter only for the network stage: Heysham 1 + Hartlepool in England (Z9); Torness in Z6
# (south of B5, like the Western HVDC and EGL1 landings, see ukabm/data/pypsagb.py); Heysham 2 in
# England (Z9), listed last so the owner assignment (i % 2) of the other units is unchanged.
NUCLEAR_UNITS = [(2300, 1983, 2027, "Z9", 0.62), (1200, 1988, 2030, "Z6", 0.62),   # AGRs
                 (1200, 1995, 2035, "Z12", 0.88),                                   # Sizewell B
                 (1630, 2030, 2089, "Z17", None), (1630, 2031, 2090, "Z17", None),  # Hinkley Point C
                 (1600, 2038, 2097, "Z12", None), (1600, 2039, 2098, "Z12", None),  # Sizewell C
                 (1200, 1988, 2030, "Z9", 0.62)]                                    # Heysham 2 (AGR)

GENCO_SPECS = [
    dict(name="IntegratedUtility", wacc=0.07, expectation="adaptive", markup=0.03, risk_aversion=0.10, budget_gbp=4e9),
    dict(name="MerchantIPP", wacc=0.10, expectation="myopic", markup=0.08, risk_aversion=0.15, budget_gbp=1.5e9),
    dict(name="OilMajor", wacc=0.08, expectation="adaptive", markup=0.02, risk_aversion=0.05, budget_gbp=6e9),
    dict(name="InfraFund", wacc=0.06, expectation="adaptive", markup=0.0, risk_aversion=0.20, budget_gbp=3e9),
    dict(name="GreenDeveloper", wacc=0.075, expectation="carbon_optimist", markup=0.0, risk_aversion=0.10, budget_gbp=2e9),
]


def _weighted_median(x, w):
    o = np.argsort(x)
    c = np.cumsum(w[o])
    return float(x[o][np.searchsorted(c, 0.5 * c[-1])])


class GBMarketModel(ModelBase):
    # Mesa >= 3.5 defines Model.scenario (a mesa Scenario object, set in Model.__init__). This model
    # uses `scenario` for its own dict of overrides, so keep Mesa's object in `_scenario` and the
    # dict in `_ukabm_scenario`.
    @property
    def scenario(self) -> dict:
        return self.__dict__.get("_ukabm_scenario", {})

    @scenario.setter
    def scenario(self, value):
        if isinstance(value, dict):
            self._ukabm_scenario = value
        else:
            self._scenario = value

    def __init__(self, scenario: dict | None = None, data: PyPSAGBData | None = None,
                 start: int = 2025, end: int = 2050, seed: int = 42,
                 network_every: int = 5, network_hours: int = 96):
        super().__init__(seed=seed)
        self.scenario = scenario or {}
        self.rng = np.random.default_rng(seed)
        self.data = data or PyPSAGBData()
        self.prof = self.data.profiles
        self.H = len(self.prof)
        self.policy = Policy(**self.scenario.get("policy", {}))
        self.fuels = Fuels(**self.scenario.get("fuels", {}))
        self.start, self.end, self.year = start, end, start
        self.network_every, self.network_hours = network_every, network_hours
        specs = [dict(s) for s in GENCO_SPECS]
        for grp in self.scenario.get("agents_ideal", []):   # idealised trait groups (scenarios.IDEAL_TRAITS)
            for s in specs:
                s.update(IDEAL_TRAITS[grp])
        # decisions go through ukabm.decisions (scenario 'decision_logic': a name, or {genco: name})
        self.gencos = [GenCo(self, decider=decisions.for_genco(self.scenario, s["name"]), **s) for s in specs]
        self.government = make_government(self)   # runs the CfD rounds (scenario "government")
        self.operator = SystemOperator(self)       # sets the CM target (scenario "system_operator")
        self.scarcity_on = self.scenario.get("scarcity_adder", True)   # ORDC adder in market clearing
        self.cfd_last = dict(awarded_mw=0.0, budget_gbp=np.nan)
        self.plants: list[Plant] = []
        self._pid = 0
        self._init_fleet()
        # the fleet as it stood at the start (incl. committed nuclear), before any agent decision:
        # the planner benchmark starts from the same fleet
        self.initial_fleet = [copy.copy(p) for p in self.plants]
        me = self.scenario.get("multienergy", {})
        self.heat = HeatModule(self, rng=np.random.default_rng(seed + 1), **me.get("heat", {}))
        self.gas = GasNetworkModule(**me.get("gas", {}))
        self.ev = EVModule(**me.get("ev", {}))
        self.h2 = HydrogenModule(**me.get("h2", {}))
        self.base_growth = self.scenario.get("base_demand_growth", 0.003)
        self.levy = 20.0            # GBP/MWh policy cost pass-through (updated endogenously)
        self.last_price = None
        self.cm_clearing = 30.0
        self.records, self.hourly = [], {}
        self.network_results = {}

    # ------------------------------------------------------------------ fleet
    def new_plant(self, owner, tech, zone, mw, online, retire=None, **kw):
        self._pid += 1
        p = Plant(self._pid, owner, tech, zone, mw, online,
                  retire if retire is not None else online + TECHS[tech].life - 1, **kw)
        self.plants.append(p)
        return p

    def _init_fleet(self):
        strikes = self.data.cfd_strikes
        infl = 1.45  # ASSUMPTION: 2012 -> 2024 prices
        mean_strike = {t: strikes[strikes.technology == k].strike_price_gbp_per_mwh_2012.mean() * infl
                       for t, k in [("wind_offshore", "offshore"), ("wind_onshore", "onshore"), ("solar", "solar")]}
        for tech, total in INITIAL_FLEET_MW.items():
            if tech == "nuclear":
                continue
            share = self.data.zone_share(tech)
            share = share[share > 0.02]
            share = share / share.sum()
            life = TECHS[tech].life
            for k, (zone, s) in enumerate(share.items()):
                owner = self.gencos[k % len(self.gencos)]
                for v in range(2):   # two vintages per zone
                    age = int(self.rng.integers(0, life))
                    online = self.start - age
                    kw = {}
                    if tech in VRE_TECHS:
                        if self.rng.random() < 0.5:
                            kw = dict(support="ro")
                        else:
                            kw = dict(support="cfd", strike=mean_strike.get(tech, 80.0), cfd_end=online + 15)
                    retire = 2100 if tech in ("hydro", "pumped_hydro") else online + life - 1
                    if tech in EXISTING_FLEET_EFFICIENCY:
                        new, old = EXISTING_FLEET_EFFICIENCY[tech]
                        kw["efficiency"] = new + (old - new) * age / (life - 1)
                    self.new_plant(owner, tech, zone, total * s / 2, online, retire, **kw)
        for i, (mw, on, ret, zone, av) in enumerate(NUCLEAR_UNITS):
            kw = dict(support="cfd", strike=128.0, cfd_end=on + 35) if on >= 2030 else {}
            self.new_plant(self.gencos[i % 2], "nuclear", zone, mw, on, ret, availability=av, **kw)

    def active(self, year):
        return [p for p in self.plants if p.active(year)]

    # ---------------------------------------------------------------- physics
    def cf_profile(self, tech):
        w, s = self.prof.wind_cf.values, self.prof.solar_cf.values
        if tech == "wind_onshore":
            return np.clip(w * 0.75, 0, 1)
        if tech == "wind_offshore":
            return np.clip(w * 1.10, 0, 1)
        if tech == "solar":
            return s
        return None

    def capacity_factor(self, tech):
        cf = self.cf_profile(tech)
        return float(cf.mean()) if cf is not None else TECHS[tech].availability

    def srmc(self, tech, year, carbon=None, efficiency=None):
        t = TECHS[tech]
        c = self.policy.carbon_price(year) if carbon is None else carbon
        if t.fuel is None:
            return t.vom
        eff = efficiency or t.efficiency
        return (self.fuels.price(t.fuel, year) + t.co2_t_per_mwh_fuel * c) / eff + t.vom

    def plant_srmc(self, p, year, carbon=None):
        return self.srmc(p.tech, year, carbon, p.efficiency)

    def interconnector_blocks(self, year):
        """Interconnector trade, one import offer and one export bid per neighbouring market.

        Foreign price per market = reference CCGT SRMC x level x hourly shape (observed 2024
        day-ahead prices for continental borders, same weather year as the GB profile; wind proxy for
        SEM). Imports are offered at foreign price + spread. Exports are bids at foreign price - spread,
        modelled as "buy-back" blocks: the export volume is added to demand and offered back at the
        bid price, so it is curtailed exactly when the GB price exceeds the bid (uniform-price
        equivalent of a price-responsive export bid). Returns (imports, exports, cap, ref).
        """
        g = self.scenario.get("ic_growth", 1.0) ** max(year - 2025, 0)
        caps = {k: v * g for k, v in self.data.interconnector_mw_by_market(year).items()}
        # ASSUMPTION: foreign prices are anchored on the SRMC of an existing-fleet GB CCGT and fall
        # 25 % relative to it by 2050 (continental decarbonisation).
        ref = self.srmc("ccgt", year, efficiency=float(np.mean(EXISTING_FLEET_EFFICIENCY["ccgt"])))
        decarb = 1 - 0.25 * min(max((year - 2025) / 25, 0), 1)
        shape = self.data.neighbour_price_shape
        imports, exports = [], []
        for k, (mkt, mw) in enumerate(sorted(caps.items())):
            fp = ref * decarb * IC_PRICE_LEVEL[mkt if mkt in IC_PRICE_LEVEL else "continent"] * shape[mkt].values
            imports.append(Block(-1 - k, fp + IC_SPREAD, IC_AVAILABILITY * mw))
            exports.append(Block(-11 - k, fp - IC_SPREAD, IC_AVAILABILITY * mw, demand_bid=True))
        return imports, exports, sum(caps.values()), ref

    def blocks(self, plants, year, carbon=None):
        out = []
        for p in plants:
            if p.tech in STORAGE_TECHS:
                continue
            t = TECHS[p.tech]
            prof = self.cf_profile(p.tech)
            if prof is None:
                prof = t.availability if p.availability is None else p.availability
            avail = p.mw * prof
            out.append(Block(p.pid, p.owner.offer_price(p, self.plant_srmc(p, year, carbon), year), avail))
        return out

    def demand(self, year, price_forecast=None, residual=None):
        base = self.prof.demand_mw.values * (1 + self.base_growth) ** (year - 2024)
        heat = self.heat.hourly_load(year, self.prof) - self.heat.hourly_load(year, self.prof) * 0  # explicit
        heat_extra = heat * max(1 - 0.6e6 / max(self.heat.hp_homes, 1), 0)  # 2024 HPs already in base
        ev_sig = residual if residual is not None else price_forecast
        ev_extra = self.ev.hourly_load(year, self.prof, ev_sig) * max(1 - 1.2e6 / self.ev.stock(year), 0)
        h2 = self.h2.hourly_load(year, price_forecast) if price_forecast is not None else 0 * base
        return base, heat_extra, ev_extra, h2

    def run_market(self, year, plants, record=True):
        self._tech_of = {p.pid: p.tech for p in plants}
        blocks = self.blocks(plants, year)
        ic_blocks, x_blocks, ic_cap, ref = self.interconnector_blocks(year)
        allb = blocks + ic_blocks + x_blocks
        x_max = sum(b.avail for b in x_blocks)          # export bids enter demand at full volume
        curve = merit_order(allb, self.H)                # offers are fixed within the year
        base, heat, ev0, _ = self.demand(year)
        d1 = base + heat + ev0
        p1, _, _ = clear(d1 + x_max, allb, self.policy.voll, scarcity_on=self.scarcity_on, curve=curve)
        # flexibility reacts to pass-1 prices
        vre = sum(np.broadcast_to(b.avail, (self.H,)) for b in blocks
                  if self._tech_of.get(b.key) in VRE_TECHS)
        base, heat, ev, h2 = self.demand(year, p1, residual=d1 - vre)
        # storage: the fleet is dispatched in tranches, each a price-taker on the price left by the flexible
        # demand and the tranches before it; a tranche skips days on which its own trades would lose money
        # at the price they produce, so the fleet does not trade away its own spread
        stor = {}
        net_st = np.zeros(self.H)
        flex = base + heat + ev + h2 + x_max
        for tech, hrs in STORAGE_TECHS.items():
            mw = sum(p.mw for p in plants if p.tech == tech)
            k = STORAGE_TRANCHES.get(tech, 1)
            for _ in range(k if mw > 0 else 0):
                pk, _, _ = clear(flex - net_st, allb, self.policy.voll, scarcity_on=self.scarcity_on, curve=curve)
                nk = storage_arbitrage(pk, mw / k, hrs, TECHS[tech].efficiency)
                after, _, _ = clear(flex - net_st - nk, allb, self.policy.voll, scarcity_on=self.scarcity_on, curve=curve)
                daily = (after * nk)[:self.H // 24 * 24].reshape(-1, 24).sum(1)
                nk[:len(daily) * 24] *= np.repeat(daily > 0, 24)
                stor[tech] = stor.get(tech, 0.0) + nk
                net_st += nk
        d2 = base + heat + ev + h2 - net_st
        price, disp, uns = clear(d2 + x_max, allb, self.policy.voll, scarcity_on=self.scarcity_on, curve=curve)
        # pass 3: electrolysers withdraw where the pass-2 price is above their willingness to pay
        # (avoids flexibility-induced scarcity from a one-shot response)
        bad_h = price > self.h2.wtp()
        if np.any(bad_h & (h2 > 0)):
            h2 = np.where(bad_h, 0.0, h2)
            d2 = base + heat + ev + h2 - net_st
            price, disp, uns = clear(d2 + x_max, allb, self.policy.voll, scarcity_on=self.scarcity_on, curve=curve)
        xj = [j for j, b in enumerate(allb) if b.key <= -11]
        export = x_max - disp[:, xj].sum(1)              # bought-back volume = export not taken
        # demand = everything GB generation/imports serve (incl. exports, net storage), for the network
        # stage; demand_domestic = GB final consumption, the volume policy costs are recovered from
        return dict(price=price, disp=disp, unserved=uns, blocks=allb, demand=d2 + export, export=export,
                    demand_domestic=base + heat + ev + h2,
                    base=base, heat=heat, ev=ev, h2=h2, storage=stor, ic_cap=ic_cap)

    # ------------------------------------------------------------ settlement
    def settle(self, year, plants, res):
        price = res["price"]
        pmap = {p.pid: p for p in plants}
        acc = []
        cfd_cost = ro_cost = cm_cost = 0.0
        gen_by_tech, em = {}, 0.0
        gas_burn = 0.0
        for j, b in enumerate(res["blocks"]):
            q = res["disp"][:, j]
            if b.key < 0:
                if b.key > -10:   # import tranches; export buy-back blocks (<= -11) are not generation
                    gen_by_tech["imports"] = gen_by_tech.get("imports", 0) + q.sum()
                continue
            p = pmap[b.key]
            t = TECHS[p.tech]
            e = q.sum()
            rev = float((price * q).sum())
            var = self.plant_srmc(p, year) * e
            extra = 0.0
            if p.support == "cfd" and year <= p.cfd_end:
                diff = float(((p.strike - price) * q).sum())
                extra += diff
                cfd_cost += diff
            elif p.support == "ro":
                extra += self.policy.ro_value * e
                ro_cost += self.policy.ro_value * e
            cm = p.cm_price * 1000 * p.mw * t.derating if year <= p.cm_end else 0.0
            cm_cost += cm
            profit = rev + extra + cm - var - t.fom * 1000 * p.mw
            acc.append((p, profit, rev, e))
            gen_by_tech[p.tech] = gen_by_tech.get(p.tech, 0) + e
            if t.fuel is not None:
                fuel_mwh = e / (p.efficiency or t.efficiency)
                em += fuel_mwh * t.co2_t_per_mwh_fuel
                if t.fuel == "gas":
                    gas_burn += fuel_mwh
        batt = dict(arbitrage=0.0, services=0.0, cm=0.0)   # GBP/MW/yr, battery fleet average
        for tech, net in res["storage"].items():
            sp = [p for p in plants if p.tech == tech]
            tot = sum(p.mw for p in sp)
            rev = float((price * net).sum())
            svc = self.battery_services_per_mw(plants) if tech == "battery" else 0.0
            cm_t = 0.0
            for p in sp:
                rev_p = rev * p.mw / tot + svc * p.mw
                cm = p.cm_price * 1000 * p.mw * TECHS[tech].derating if year <= p.cm_end else 0.0
                cm_cost += cm
                cm_t += cm
                acc.append((p, rev_p + cm - TECHS[tech].fom * 1000 * p.mw, rev_p, 0))
            gen_by_tech[tech] = float(np.clip(net, 0, None).sum())
            if tech == "battery" and tot > 0:
                batt = dict(arbitrage=rev / tot, services=svc, cm=cm_t / tot)
        for p, profit, rev, e in acc:
            p.history.append((year, profit))
            p.loss_years = p.loss_years + 1 if profit < 0 else 0
        return dict(cfd_cost=cfd_cost, ro_cost=ro_cost, cm_cost=cm_cost, gen=gen_by_tech,
                    emissions_t=em, gas_burn_twh=gas_burn / 1e6, battery=batt)

    def system_cost(self, year, plants, res):
        """Annual system cost (GBP) of the realised market outcome, by component (ukabm.costs)."""
        c = dict.fromkeys(COST_COMPONENTS, 0.0)
        c.update(fixed_costs(plants, year, self.start))
        pmap = {p.pid: p for p in plants}
        for j, b in enumerate(res["blocks"]):
            q = res["disp"][:, j]
            price = np.broadcast_to(b.price, q.shape)
            if b.key > 0:
                p = pmap[b.key]
                for k, v in variable_cost(p.tech, p.efficiency, float(q.sum()), year, self.fuels, self.policy).items():
                    c[k] += v
            elif b.key > -10:                                   # import tranche
                c["trade"] += float((price * q).sum())
            else:                                               # export bid: exported = offered - bought back
                c["trade"] -= float((price * (np.broadcast_to(b.avail, q.shape) - q)).sum())
        for tech, net in res["storage"].items():
            c["fuel"] += TECHS[tech].vom * float(np.clip(net, 0, None).sum())
        c["unserved"] = float(res["unserved"].sum()) * self.policy.voll
        c["h2_value"] = -float(np.sum(res["h2"])) * self.h2.wtp()
        return c

    @staticmethod
    def battery_services_per_mw(plants, extra_mw=0.0):
        """Battery revenue (GBP/MW/yr) from ancillary services and intraday/BM trading that the hourly
        day-ahead clearing does not capture: two pots (config.BATTERY_*) shared across the battery fleet
        of *plants* plus *extra_mw* (a candidate project). The fleet is floored at its 2025 size."""
        fleet = sum(p.mw for p in plants if p.tech == "battery") + extra_mw
        vre = sum(p.mw for p in plants if p.tech in VRE_TECHS)
        pot = BATTERY_ANCILLARY_POT + BATTERY_TRADING_PER_MW_VRE * vre
        return pot / max(fleet, BATTERY_FLEET_FLOOR_MW)

    def neso_basis_ci(self, gen, st):
        """Carbon intensity (g/kWh) on NESO's accounting basis: NESO factors for CCGT/OCGT/biomass/
        imports, model direct emissions for gas_ccs, zero otherwise. Denominator = generation incl.
        imports and storage discharge, as in NESO's historic generation mix."""
        g = sum(NESO_CI_FACTORS.get(k, 0.0) * v for k, v in gen.items())   # MWh * g/kWh = kg
        ccs = gen.get("gas_ccs", 0.0)
        g += ccs / TECHS["gas_ccs"].efficiency * TECHS["gas_ccs"].co2_t_per_mwh_fuel * 1e3
        return g / max(sum(gen.values()), 1)

    # ------------------------------------------------------------- forecasts
    def forecast(self, target_year, extra=()):
        plants = [p for p in self.plants if p.active(target_year)] + list(extra)
        return self.run_market(target_year, plants)["price"]

    def forecast_horizons(self, offsets=(8, 13)):
        """Long-horizon price forecasts for investment decisions, cached per model year. Fleet: the
        pipeline at t+3 held, plus wind and solar growing at their recent build rate (cannibalisation),
        plus peaking capacity that keeps the de-rated margin at the CM target (investors expect the system
        to stay adequate). Fuel, carbon and demand are those of the horizon year."""
        cache = getattr(self, "_horizon_cache", None)
        if cache is not None and cache[0] == (self.year, offsets):
            return cache[1]
        y0 = self.year + 3
        base = [p for p in self.plants if p.active(y0)]
        out = {}
        for off in offsets:
            h = self.year + off
            extra = []
            for tech in sorted(VRE_TECHS):
                now = sum(p.mw for p in base if p.tech == tech)
                before = sum(p.mw for p in self.plants if p.tech == tech and p.active(y0 - 5))
                add = max(now - before, 0.0) / 5 * (h - y0)
                if add > 0:
                    extra.append(Plant(-1 - len(extra), self.gencos[0], tech, "GB", add, self.year, h + 50,
                                       support="cfd", cfd_end=h + 50))
            b, heat, ev, _ = self.demand(h)
            peak = float((b + heat + ev).max())
            _, _, ic_cap, _ = self.interconnector_blocks(h)
            firm = sum(p.mw * TECHS[p.tech].derating for p in base + extra) + 0.45 * ic_cap
            short = peak * (1 + self.policy.cm_reliability_margin) - firm
            if short > 0:
                extra.append(Plant(-1 - len(extra), self.gencos[0], "ocgt", "GB", short / TECHS["ocgt"].derating,
                                   self.year, h + 50))
            out[h] = self.run_market(h, base + extra)["price"]
        self._horizon_cache = ((self.year, offsets), out)
        return out

    def expected_margin_per_mw(self, tech, price, agent, include_cm=True, fleet_year=None, extra_mw=None):
        """Expected annual margin per MW. *fleet_year*: year whose (pipeline) battery fleet shares the
        battery service pots; default = first operating year (CM new build passes its delivery year).
        *extra_mw*: new battery MW added to that fleet (default: the candidate chunk itself)."""
        t = TECHS[tech]
        yr = self.year + t.lead_time
        if tech in STORAGE_TECHS:
            net = storage_arbitrage(price, 1.0, STORAGE_TECHS[tech], t.efficiency)
            m = float((price * net).sum()) - t.vom * np.clip(net, 0, None).sum()
            if tech == "battery":   # services at the fleet expected when the project comes online
                fy = fleet_year or yr
                extra = t.chunk_mw if extra_mw is None else extra_mw
                m += self.battery_services_per_mw([p for p in self.plants if p.active(fy)], extra)
        elif tech in VRE_TECHS:
            m = float((price * self.cf_profile(tech)).sum()) * 0.85   # capture-price haircut
        else:
            srmc = self.srmc(tech, yr, agent.expected_carbon(yr))
            m = float(np.clip(price - srmc, 0, None).sum()) * t.availability
        if include_cm and self.policy.cm_enabled and tech not in VRE_TECHS:
            m += self.cm_clearing * 1000 * t.derating
        return m

    # ----------------------------------------------------------- policy auctions
    def cfd_round(self, year, price_fc):
        """CfD allocation round. The government (ukabm.institutions) sets each technology pot's volume
        limit, administrative strike price and GBP budget; bids clear pay-as-clear per pot within them."""
        self.cfd_last = dict(awarded_mw=0.0, budget_gbp=np.nan)
        if not self.policy.cfd_enabled:
            return []
        pots = self.government.round_settings(year, price_fc)
        bids, over_cap = [], {}
        for g in self.gencos:
            for tech in CFD_TECHS:
                if tech in self.scenario.get("banned_techs", []):
                    continue
                for _ in range(2):
                    s = g.cfd_bid(tech, price_fc)
                    cap = pots[tech].cap if tech in pots else self.policy.cfd_admin_strike_cap[tech]
                    if s <= cap:
                        bids.append((s, g, tech))
                    elif tech in pots:
                        over_cap[tech] = over_cap.get(tech, 0) + 1
        bids.sort(key=lambda x: x[0])
        won, mw = [], {k: 0.0 for k in pots}
        for s, g, tech in bids:   # technology pots (AR-style ring-fenced)
            pot = pots.get(tech)
            if pot is None or mw[tech] >= pot.max_mw:
                continue
            chunk = TECHS[tech].chunk_mw
            # pay-as-clear: with this bid as the clearing strike, all accepted MW are paid it
            if pot.budget_gbp is not None and (mw[tech] + chunk) * pot.support_per_mw(s) > pot.budget_gbp + 1e-6:
                continue
            won.append((s, g, tech))
            mw[tech] += chunk
        clearing = {}
        for s, g, tech in won:
            clearing[tech] = max(clearing.get(tech, 0), s)
        built = []
        for s, g, tech in won:
            t = TECHS[tech]
            zone = self.choose_zone(tech)
            on = year + t.lead_time
            built.append(self.new_plant(g, tech, zone, t.chunk_mw, on, support="cfd",
                                        strike=clearing[tech], cfd_end=on + 19))
        self.last_cfd = clearing
        result = {tech: dict(max_mw=pot.max_mw, accepted_mw=mw[tech], over_cap=over_cap.get(tech, 0),
                             clearing=clearing.get(tech), cap=pot.cap, budget_gbp=pot.budget_gbp)
                  for tech, pot in pots.items()}
        self.government.observe(year, result)
        budgets = [pot.budget_gbp for pot in pots.values() if pot.budget_gbp is not None]
        self.cfd_last = dict(awarded_mw=sum(mw.values()), budget_gbp=sum(budgets) if budgets else np.nan)
        return built

    def cm_auction(self, year, price_fc=None, ahead=4):
        """T-4 (ahead=4) or T-1 (ahead=1) Capacity Market auction. The system operator
        (ukabm.institutions.SystemOperator) sets the target; supported (CfD/RO) plant is outside the CM
        but counts towards security of supply."""
        if not self.policy.cm_enabled:
            return []
        dy = year + ahead
        target, peak = self.operator.cm_target(year, dy, ahead)
        offers = []   # (price, derated_mw, plant or (genco, tech))
        if ahead == 4:
            _, _, ic_cap, _ = self.interconnector_blocks(dy)
            offers.append((0.0, 0.45 * ic_cap, None))
        for p in self.plants:
            if p.active(dy) and p.support not in ("cfd", "ro"):
                if p.tech in VRE_TECHS:
                    continue
                if ahead == 1 and p.cm_end >= dy:      # already holds an agreement covering dy
                    continue
                t = TECHS[p.tech]
                margin_kw = max(np.mean([h for _, h in p.history[-2:]]) / (p.mw * 1000), 0) if p.history else 0
                bid = p.owner.cm_bid(p, margin_kw + t.fom, new=False)   # history is net of FOM
                offers.append((min(bid, self.policy.cm_price_cap), p.mw * t.derating, p))
        # new-build bids are priced on the investment forecast (t+3, known fuel and carbon paths) when
        # given, not on the latest outturn year, which mis-prices plant delivered 4 years later after a
        # fuel-price spike
        if price_fc is None:
            price_fc = self.last_price if self.last_price is not None else np.full(self.H, 60.0)
        n_chunks = self.scenario.get("cm_new_chunks", 4)   # up to 4 projects per GenCo and technology
        batt = []
        for g in self.gencos:
            for tech in ("ocgt", "battery", "ccgt", "h2_turbine", "gas_ccs"):
                if tech in self.scenario.get("banned_techs", []) or TECHS[tech].lead_time > ahead:
                    continue
                if tech == "battery":
                    batt += [(g, k) for k in range(n_chunks)]
                    continue
                t = TECHS[tech]
                m = self.expected_margin_per_mw(tech, price_fc, g, include_cm=False, fleet_year=dy) / 1000
                bid = g.cm_bid(tech, m, new=True)
                if bid <= self.policy.cm_price_cap:
                    for k in range(n_chunks):
                        offers.append((bid * (1 + 0.03 * k), t.chunk_mw * t.derating, (g, tech)))
        offers += self._cm_battery_supply(batt, price_fc, dy)
        offers.sort(key=lambda x: x[0])
        lo, hi, cap = target - 1500, target + 1500, self.policy.cm_price_cap

        def demand_price(q):  # linear sloping demand curve (PyPSA-GB parameters style)
            return float(np.clip(cap * (hi - q) / (hi - lo), 0, cap))
        q, clearing, accepted = 0.0, 0.0, []
        for pr, mw, who in offers:
            # stop at the first offer above the demand curve, and at the end of the curve: zero-priced
            # offers are not accepted beyond the quantity at which the demand curve reaches zero
            if pr > demand_price(q + mw) or q + mw > hi:
                clearing = max(pr, demand_price(q)) if not accepted else max(clearing, min(demand_price(q), pr))
                break
            q += mw
            accepted.append(who)
            clearing = max(clearing, pr)
        else:
            clearing = max(clearing, demand_price(q))
        clearing = float(np.clip(max(clearing, demand_price(q)), 0, cap))
        new, batt_svc = [], None
        for who in accepted:
            if isinstance(who, Plant):
                who.cm_price, who.cm_end = clearing, dy
            elif isinstance(who, tuple):
                g, tech = who[:2]
                if tech == "battery":
                    batt_svc = who[2]      # expected services of the marginal accepted battery chunk
                new.append(self.new_plant(g, tech, self.choose_zone(tech), TECHS[tech].chunk_mw, dy,
                                          cm_price=clearing, cm_end=dy + 14))
        self.cm_log = getattr(self, "cm_log", [])
        self.cm_log.append(dict(year=dy, clearing=clearing, procured_mw=q, target_mw=target, peak=peak, n_offers=len(offers), offered=sum(o[1] for o in offers), ahead=ahead))
        if ahead != 4:
            return new
        self.cm_clearing = clearing
        self.cm_last = dict(year=dy, clearing=clearing, procured_mw=q, target_mw=target, new_mw=sum(p.mw for p in new),
                            battery_new_mw=sum(p.mw for p in new if p.tech == "battery"),
                            battery_marginal_services=batt_svc)
        return new

    def _cm_battery_supply(self, candidates, price_fc, dy):
        """New-build battery CM offers as a stepwise supply curve. Batteries share the service pots, so
        each chunk's expected services revenue counts all battery MW ranked ahead of it in this auction
        plus itself (chunks are added cheapest bid first; bids rise as the expected fleet grows).
        Accepted chunks are a prefix of this curve, so the marginal accepted chunk expects exactly the
        per-MW services the delivery-year fleet will share. *candidates*: (GenCo, project index k)."""
        if not candidates:
            return []
        t = TECHS["battery"]
        fleet = [p for p in self.plants if p.active(dy)]
        g0 = candidates[0][0]
        arb = (self.expected_margin_per_mw("battery", price_fc, g0, include_cm=False, fleet_year=dy, extra_mw=0.0)
               - self.battery_services_per_mw(fleet))      # GenCo-independent arbitrage margin, GBP/MW/yr
        out, cum, left = [], 0.0, list(candidates)
        while left:
            svc = self.battery_services_per_mw(fleet, cum + t.chunk_mw)
            bids = [g.cm_bid("battery", (arb + svc) / 1000, new=True) * (1 + 0.03 * k) for g, k in left]
            i = int(np.argmin(bids))
            if bids[i] > self.policy.cm_price_cap:
                break
            g, _ = left.pop(i)
            out.append((bids[i], t.chunk_mw * t.derating, (g, "battery", svc)))
            cum += t.chunk_mw
        return out

    def choose_zone(self, tech):
        """Locational choice by resource share (PyPSA-GB DUKES split). GB keeps national wholesale
        pricing (REMA decision, July 2025), so by default generators see no zonal price signal.
        Sensitivity `locational_signal=True` (zonal pricing): share x zonal price / mean, clipped to
        [0.2, 2], with zonal prices from the last network-stage redispatch."""
        share = self.data.zone_share(tech).copy()
        zp = self.network_results.get("zonal_price") if self.network_results else None
        if zp is not None and self.scenario.get("locational_signal", False):
            rel = (zp.reindex(share.index).fillna(zp.mean()) / max(zp.mean(), 1.0)).clip(0.2, 2.0)
            share = share * rel
        share = share.clip(lower=0) + 1e-9
        return self.rng.choice(share.index, p=(share / share.sum()).values)

    # ------------------------------------------------------------ main step
    def step(self):
        y = self.year
        plants = self.active(y)
        res = self.run_market(y, plants)
        st = self.settle(y, plants, res)
        sc = self.system_cost(y, plants, res)
        price = res["price"]
        self.last_price = price
        dem_d = res["demand_domestic"]
        dem = dem_d.sum()
        # policy cost pass-through to consumers (GBP/MWh): CfD/RO/CM are recovered from GB supplier
        # volumes only, not from interconnector exports
        self.levy = (st["cfd_cost"] + st["ro_cost"] + st["cm_cost"]) / dem
        # network stage
        net = {}
        if self.network_every and (y - self.start) % self.network_every == 0:
            net = self.network_stage(y, plants, res)
        constraint_cost = net.get("constraint_cost_bn", np.nan)
        # multi-energy feedbacks
        twavg = float((price * dem_d).sum() / dem)
        hp_price = float((price * self.heat.heat_shape(self.prof)).sum())
        reb = self.policy.gas_levy_rebalancing
        elec_retail = hp_price + 70 + self.levy + 25 - reb
        gasr = self.gas.update(y, self.heat.gas_homes, float(np.mean(self.heat.heat_mwh)), st["gas_burn_twh"])
        gas_retail = self.fuels.price("gas", y) + gasr["gas_network_tariff"] + 12 + reb * 0.35
        hr = self.heat.update(y, elec_retail, gas_retail, self.policy.hp_grant)
        # retirements
        retired = 0.0
        for p in plants:
            t = TECHS[p.tech]
            if p.tech in ("ccgt", "ocgt", "biomass", "battery") and p.loss_years >= 2 and p.cm_end < y + 1:
                p.retire = y
                retired += p.mw
        # investment
        invested = self.invest(y)
        gen = st["gen"]
        rec = dict(year=y, price_twa=twavg, price_mean=float(price.mean()), price_max=float(price.max()),
                   hours_negative=int((price < 0).sum()), unserved_gwh=float(res["unserved"].sum() / 1e3),
                   lole_h=int((res["unserved"] > 1).sum()),
                   demand_twh=dem / 1e6, heat_twh=res["heat"].sum() / 1e6, ev_twh=res["ev"].sum() / 1e6,
                   h2_twh=float(np.sum(res["h2"])) / 1e6, export_twh=res["export"].sum() / 1e6,
                   emissions_mt=st["emissions_t"] / 1e6,
                   intensity_g_kwh=st["emissions_t"] / max(sum(gen.values()), 1) * 1e3,
                   intensity_neso_g_kwh=self.neso_basis_ci(gen, st),
                   cfd_cost_bn=st["cfd_cost"] / 1e9, ro_cost_bn=st["ro_cost"] / 1e9, cm_cost_bn=st["cm_cost"] / 1e9,
                   levy_gbp_mwh=self.levy, cm_clearing=self.cm_clearing, constraint_cost_bn=constraint_cost,
                   carbon_price=self.policy.carbon_price(y), gas_price=self.fuels.price("gas", y),
                   elec_retail=elec_retail, gas_retail=gas_retail, gas_network_tariff=gasr["gas_network_tariff"],
                   gas_throughput_twh=gasr["gas_throughput_twh"], power_gas_twh=st["gas_burn_twh"],
                   hp_homes_m=hr["hp_homes"] / 1e6, ev_stock_m=self.ev.stock(y) / 1e6,
                   retired_mw=retired, invested_mw=invested,
                   cfd_awarded_mw=self.cfd_last["awarded_mw"], cfd_budget_bn=self.cfd_last["budget_gbp"] / 1e9)
        for k, v in sc.items():               # system cost by component, GBP bn/yr (ukabm.costs)
            rec[f"syscost_{k}_bn"] = v / 1e9
        rec["syscost_bn"] = sum(sc.values()) / 1e9
        for k, v in st["battery"].items():   # battery revenue stack, kGBP/MW/yr (fleet average)
            rec[f"battery_{k}_k_per_mw"] = v / 1e3
        # services pots paid to batteries (system cost; not yet passed to retail prices or the levy)
        rec["battery_services_bn"] = st["battery"]["services"] * sum(p.mw for p in plants if p.tech == "battery") / 1e9
        for tech in TECHS:
            rec[f"cap_{tech}"] = sum(p.mw for p in plants if p.tech == tech) / 1e3
            rec[f"gen_{tech}"] = gen.get(tech, 0.0) / 1e6
        rec["gen_imports"] = gen.get("imports", 0.0) / 1e6
        rec["gen_total"] = sum(gen.values()) / 1e6
        # Balancing Mechanism redispatch from the network stage (NaN in years without it):
        # net change by technology (TWh, + = turned up) and the post-redispatch NESO-basis CI
        rec["curtailment_twh"] = net.get("curtailment_twh", np.nan)
        rec["network_shed_twh"] = net.get("shed_twh", np.nan)   # demand behind constraints not met
        for tech in TECHS:
            rec[f"bm_net_{tech}"] = net["bm_net"].get(tech, 0.0) / 1e6 if net else np.nan
        post = {k: gen.get(k, 0.0) + (net["bm_net"].get(k, 0.0) if net else 0.0) for k in set(gen) | set(TECHS)}
        rec["intensity_neso_post_bm_g_kwh"] = self.neso_basis_ci(post, st) if net else np.nan
        for q in (5, 50, 95):
            rec[f"price_p{q:02d}"] = float(np.percentile(price, q))
        rec["cap_interconnector"] = res["ic_cap"] / 1e3
        self.records.append(rec)
        self.hourly[y] = pd.DataFrame({"price": price, "demand": res["demand"], "heat": res["heat"],
                                       "ev": res["ev"], "h2": res["h2"], "export": res["export"],
                                       "load": res["base"] + res["heat"] + res["ev"]})   # inflexible load
        self.year += 1

    def invest(self, y):
        before = sum(p.mw for p in self.plants if p.online > y)
        price_fc = self.forecast(y + 3)
        self.cfd_round(y, price_fc)
        self.cm_auction(y, price_fc)
        if self.operator.t1:
            self.cm_auction(y, price_fc, ahead=1)
        # merchant: sequential, re-forecast after each decision (captures others' pipeline)
        order = list(self.rng.permutation(len(self.gencos)))
        budgets = {g.name: g.budget for g in self.gencos}
        for _ in range(self.scenario.get("max_merchant_decisions", 6)):
            price_fc = self.forecast(y + 3)
            done = False
            for i in order:
                g = self.gencos[i]
                d = g.decide_investment(price_fc)
                if d and budgets[g.name] > 0:
                    tech, mw, npv = d
                    t = TECHS[tech]
                    self.new_plant(g, tech, self.choose_zone(tech), mw, y + t.lead_time)
                    budgets[g.name] -= t.capex * 1000 * mw
                    done = True
                    break
            if not done:
                break
        return sum(p.mw for p in self.plants if p.online > y) - before

    def interconnector_injection(self, y, res, hours):
        """Net interconnector injection (imports - exports, MW) by GB landing zone for the sample hours,
        from the market's per-market import offers (keys -1-k) and export buy-back bids (-11-k); each
        market's flow is split across its landing zones by capacity."""
        disp = res["disp"][hours]
        col = {b.key: j for j, b in enumerate(res["blocks"]) if b.key < 0}
        share = self.data.interconnector_landing_share(y)
        inj = pd.DataFrame(0.0, index=range(len(hours)), columns=list(self.data.buses.name))
        for k, mkt in enumerate(sorted(self.data.interconnector_mw_by_market(y))):   # as interconnector_blocks
            net = disp[:, col[-1 - k]].copy()
            xb = res["blocks"][col[-11 - k]]
            net -= np.broadcast_to(xb.avail, (self.H,))[hours] - disp[:, col[-11 - k]]   # export taken
            for z, s in share[mkt].items():
                inj[z] += net * s
        return inj

    def network_sample(self, y):
        """Representative hours for the network stage: stratified by GB wind CF (constraint costs
        are driven by wind), equal hours per stratum, with weights = stratum size / sampled hours."""
        rng = np.random.default_rng(y)
        w = self.prof.wind_cf.values
        edges = np.quantile(w, np.linspace(0, 1, NET_STRATA + 1))
        strata = np.clip(np.searchsorted(edges, w, side="right") - 1, 0, NET_STRATA - 1)
        per = max(self.network_hours // NET_STRATA, 1)
        hours, weights = [], []
        for s in range(NET_STRATA):
            idx = np.flatnonzero(strata == s)
            if len(idx) == 0:      # repeated quantile edges (e.g. many zero-wind hours) leave strata empty
                continue
            k = min(per, len(idx))
            hours += list(rng.choice(idx, k, replace=False))
            weights += [len(idx) / k] * k
        order = np.argsort(hours)
        return np.asarray(hours)[order], np.asarray(weights)[order]

    def bm_bids(self, plants, blocks, price, year):
        """Balancing Mechanism bid prices (GBP/MWh paid by the plant to be turned down; negative =
        the system pays it). Thermal: SRMC (fuel saved). RO renewables: -ROC value. CfD renewables:
        -(strike - market price), the difference payment lost on curtailed output (positive above the
        strike, where turning down saves the generator's payback). Merchant VRE/hydro: 0.
        Nuclear: NUCLEAR_BM_BID (inflexible, effectively never turned down)."""
        pmap = {p.pid: p for p in plants}
        bids = np.zeros((len(price), len(blocks)))
        for j, b in enumerate(blocks):
            p = pmap[b.key]
            if p.tech == "nuclear":
                bids[:, j] = NUCLEAR_BM_BID
            elif p.tech in VRE_TECHS or p.tech == "hydro":
                if p.support == "ro":
                    bids[:, j] = -self.policy.ro_value
                elif p.support == "cfd" and year <= p.cfd_end:
                    bids[:, j] = -(p.strike - price)     # > 0 above the strike: turn-down saves the payback
            else:
                bids[:, j] = self.plant_srmc(p, year)
        return bids

    def network_stage(self, y, plants, res):
        """BM-style zonal redispatch on representative hours. Returns annualised constraint cost,
        curtailment and net redispatch volume by technology (empty dict if the stage fails)."""
        hours, wts = self.network_sample(y)
        cols = [j for j, b in enumerate(res["blocks"]) if b.key > 0]
        blocks = [res["blocks"][j] for j in cols]
        bc = lambda v: np.broadcast_to(v, (self.H,))[hours]
        inj = self.interconnector_injection(y, res, hours)
        sched = res["disp"][np.ix_(hours, cols)]
        avail = np.stack([bc(b.avail) for b in blocks], 1)
        offers = np.stack([bc(b.price) for b in blocks], 1)
        bids = self.bm_bids(plants, blocks, res["price"][hours], y)
        # BSC rule: a unit's offer may not be below its bid, so the redispatch cannot turn the same
        # unit down and up for profit. Binds only for CfD plant above the strike, whose turn-up would
        # add payback: their offer is raised to the bid (price - strike).
        offers = np.maximum(offers, bids)
        links = self.data.links_for_year(y)
        try:
            out = netmod.redispatch(self.data, plants, blocks, (res["demand"] - res["export"])[hours], sched, avail,
                                    offers, bids, links, self.data.link_availability(y, links, hours), injection=inj)
        except Exception as e:  # keep the annual loop robust
            log.warning("network stage failed: %s", e)
            return {}
        if out is None:
            return {}
        tech = {p.pid: p.tech for p in plants}
        up, down = wts @ out["up"], wts @ out["down"]          # MWh/yr per block
        bm_net, curtail = {}, 0.0
        for j, b in enumerate(blocks):
            t = tech[b.key]
            bm_net[t] = bm_net.get(t, 0.0) + up[j] - down[j]
            curtail += down[j] if t in VRE_TECHS else 0.0
        zp = out["zonal_price"].apply(lambda c: _weighted_median(c.values, wts))   # robust to shedding hours
        self.network_results = {"zonal_price": zp, "flows": out["flows"], "year": y,
                                "hours": hours, "weights": wts}
        return dict(constraint_cost_bn=float(wts @ out["cost_h"]) / 1e9, curtailment_twh=curtail / 1e6,
                    shed_twh=float(wts @ out["shed"]) / 1e6, bm_net=bm_net)

    def run(self):
        while self.year <= self.end:
            self.step()
        return self.results()

    def results(self):
        return pd.DataFrame(self.records).set_index("year")
