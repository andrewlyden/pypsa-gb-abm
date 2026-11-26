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
                     NESO_CI_FACTORS, Policy, Fuels)
from .data import PyPSAGBData
from .market import Block, clear, storage_arbitrage
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

# Existing / committed nuclear: (mw, online, retire, zone, availability). Indicative public dates.
# Availability of the legacy fleet calibrated to outturn: GB nuclear 38.4 TWh (2024) and 34.2 TWh
# (2025, NESO); Sizewell B ran at 99 % in 2025 (10.4 TWh) while the AGRs averaged ~58 % with an
# extended Hartlepool outage (EDF UK nuclear fleet update, Jan 2026; EDF plans ~36-37 TWh in
# 2026-27). AGRs 0.62, Sizewell B 0.88 (18-month refuelling cycle); new EPRs use Tech default.
NUCLEAR_UNITS = [(2300, 1983, 2027, "Z9", 0.62), (2400, 1988, 2030, "Z5", 0.62),   # AGRs
                 (1200, 1995, 2035, "Z12", 0.88),                                   # Sizewell B
                 (1630, 2030, 2089, "Z17", None), (1630, 2031, 2090, "Z17", None),  # Hinkley Point C
                 (1600, 2038, 2097, "Z12", None), (1600, 2039, 2098, "Z12", None)]  # Sizewell C

GENCO_SPECS = [
    dict(name="IntegratedUtility", wacc=0.07, expectation="adaptive", markup=0.03, risk_aversion=0.10, budget_gbp=4e9),
    dict(name="MerchantIPP", wacc=0.10, expectation="myopic", markup=0.08, risk_aversion=0.15, budget_gbp=1.5e9),
    dict(name="OilMajor", wacc=0.08, expectation="adaptive", markup=0.02, risk_aversion=0.05, budget_gbp=6e9),
    dict(name="InfraFund", wacc=0.06, expectation="adaptive", markup=0.0, risk_aversion=0.20, budget_gbp=3e9),
    dict(name="GreenDeveloper", wacc=0.075, expectation="carbon_optimist", markup=0.0, risk_aversion=0.10, budget_gbp=2e9),
]


class GBMarketModel(ModelBase):
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
        self.gencos = [GenCo(self, **s) for s in GENCO_SPECS]
        self.plants: list[Plant] = []
        self._pid = 0
        self._init_fleet()
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
        base, heat, ev0, _ = self.demand(year)
        d1 = base + heat + ev0
        p1, _, _ = clear(d1 + x_max, allb, self.policy.voll)
        # flexibility reacts to pass-1 prices
        vre = sum(np.broadcast_to(b.avail, (self.H,)) for b in blocks
                  if self._tech_of.get(b.key) in VRE_TECHS)
        base, heat, ev, h2 = self.demand(year, p1, residual=d1 - vre)
        stor = {}
        net_st = np.zeros(self.H)
        for tech, hrs in STORAGE_TECHS.items():
            mw = sum(p.mw for p in plants if p.tech == tech)
            if mw > 0:
                stor[tech] = storage_arbitrage(p1, mw, hrs, TECHS[tech].efficiency)
                net_st += stor[tech]
        d2 = base + heat + ev + h2 - net_st
        price, disp, uns = clear(d2 + x_max, allb, self.policy.voll)
        # pass 3: electrolysers withdraw where the pass-2 price is above their willingness to pay
        # (avoids flexibility-induced scarcity from a one-shot response)
        bad_h = price > self.h2.wtp()
        if np.any(bad_h & (h2 > 0)):
            h2 = np.where(bad_h, 0.0, h2)
            d2 = base + heat + ev + h2 - net_st
            price, disp, uns = clear(d2 + x_max, allb, self.policy.voll)
        xj = [j for j, b in enumerate(allb) if b.key <= -11]
        export = x_max - disp[:, xj].sum(1)              # bought-back volume = export not taken
        return dict(price=price, disp=disp, unserved=uns, blocks=allb, demand=d2 + export, export=export,
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
        for tech, net in res["storage"].items():
            sp = [p for p in plants if p.tech == tech]
            tot = sum(p.mw for p in sp)
            rev = float((price * net).sum())
            anc = 20000 * max(1 - (year - 2025) / 12, 0.25) if tech == "battery" else 0.0
            for p in sp:
                rev_p = rev * p.mw / tot + anc * p.mw   # ASSUMPTION: ancillary-service revenue
                cm = p.cm_price * 1000 * p.mw * TECHS[tech].derating if year <= p.cm_end else 0.0
                cm_cost += cm
                acc.append((p, rev_p + cm - TECHS[tech].fom * 1000 * p.mw, rev_p, 0))
            gen_by_tech[tech] = float(np.clip(net, 0, None).sum())
        for p, profit, rev, e in acc:
            p.history.append((year, profit))
            p.loss_years = p.loss_years + 1 if profit < 0 else 0
        return dict(cfd_cost=cfd_cost, ro_cost=ro_cost, cm_cost=cm_cost, gen=gen_by_tech,
                    emissions_t=em, gas_burn_twh=gas_burn / 1e6)

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

    def expected_margin_per_mw(self, tech, price, agent, include_cm=True):
        t = TECHS[tech]
        yr = self.year + t.lead_time
        if tech in STORAGE_TECHS:
            net = storage_arbitrage(price, 1.0, STORAGE_TECHS[tech], t.efficiency)
            m = float((price * net).sum()) - t.vom * np.clip(net, 0, None).sum()
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
        if not self.policy.cfd_enabled:
            return []
        target = self.policy.cfd_budget_gw_per_year * 1000
        pots = self.scenario.get("cfd_pots", {"wind_offshore": 0.6, "wind_onshore": 0.2, "solar": 0.2})
        bids = []
        for g in self.gencos:
            for tech in ("wind_offshore", "wind_onshore", "solar"):
                if tech in self.scenario.get("banned_techs", []):
                    continue
                for _ in range(2):
                    s = g.cfd_bid(tech, price_fc)
                    if s <= self.policy.cfd_admin_strike_cap[tech]:
                        bids.append((s, g, tech))
        bids.sort(key=lambda x: x[0])
        won, mw = [], {k: 0.0 for k in pots}
        for s, g, tech in bids:   # technology pots (AR-style ring-fenced budgets)
            if mw.get(tech, 0) >= target * pots.get(tech, 0):
                continue
            won.append((s, g, tech))
            mw[tech] += TECHS[tech].chunk_mw
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
        return built

    def cm_auction(self, year):
        if not self.policy.cm_enabled:
            return []
        dy = year + 4
        base, heat, ev, _ = self.demand(dy)
        peak = float((base + heat + ev).max())
        target = peak * (1 + self.policy.cm_reliability_margin)
        # supported (CfD/RO) plant is outside the CM but still contributes to security of supply
        target -= sum(p.mw * TECHS[p.tech].derating for p in self.plants
                      if p.active(dy) and p.support in ("cfd", "ro"))
        offers = []   # (price, derated_mw, plant or (genco, tech))
        _, _, ic_cap, _ = self.interconnector_blocks(dy)
        offers.append((0.0, 0.45 * ic_cap, None))
        for p in self.plants:
            if p.active(dy) and p.support not in ("cfd", "ro"):
                if p.tech in VRE_TECHS:
                    continue
                t = TECHS[p.tech]
                margin_kw = max(np.mean([h for _, h in p.history[-2:]]) / (p.mw * 1000), 0) if p.history else 0
                bid = p.owner.cm_bid(p, margin_kw + t.fom, new=False)   # history is net of FOM
                offers.append((min(bid, self.policy.cm_price_cap), p.mw * t.derating, p))
        price_fc = self.last_price if self.last_price is not None else np.full(self.H, 60.0)
        for g in self.gencos:
            for tech in ("ocgt", "battery", "ccgt", "h2_turbine", "gas_ccs"):
                if tech in self.scenario.get("banned_techs", []) or TECHS[tech].lead_time > 4:
                    continue
                t = TECHS[tech]
                m = self.expected_margin_per_mw(tech, price_fc, g, include_cm=False) / 1000
                bid = g.cm_bid(tech, m, new=True)
                if bid <= self.policy.cm_price_cap:
                    for k in range(self.scenario.get("cm_new_chunks", 4)):   # up to 4 projects each
                        offers.append((bid * (1 + 0.03 * k), t.chunk_mw * t.derating, (g, tech)))
        offers.sort(key=lambda x: x[0])
        lo, hi, cap = target - 1500, target + 1500, self.policy.cm_price_cap

        def demand_price(q):  # linear sloping demand curve (PyPSA-GB parameters style)
            return float(np.clip(cap * (hi - q) / (hi - lo), 0, cap))
        q, clearing, accepted = 0.0, 0.0, []
        for pr, mw, who in offers:
            if pr > demand_price(q + mw):
                clearing = max(pr, demand_price(q)) if not accepted else max(clearing, min(demand_price(q), pr))
                break
            q += mw
            accepted.append(who)
            clearing = max(clearing, pr)
        else:
            clearing = max(clearing, demand_price(q))
        clearing = float(np.clip(max(clearing, demand_price(q)), 0, cap))
        new = []
        for who in accepted:
            if isinstance(who, Plant):
                who.cm_price, who.cm_end = clearing, dy
            elif isinstance(who, tuple):
                g, tech = who
                new.append(self.new_plant(g, tech, self.choose_zone(tech), TECHS[tech].chunk_mw, dy,
                                          cm_price=clearing, cm_end=dy + 14))
        self.cm_clearing = clearing
        self.cm_log = getattr(self, "cm_log", [])
        self.cm_log.append(dict(year=dy, clearing=clearing, procured_mw=q, target_mw=target, peak=peak, n_offers=len(offers), offered=sum(o[1] for o in offers)))
        self.cm_last = dict(year=dy, clearing=clearing, procured_mw=q, target_mw=target, new_mw=sum(p.mw for p in new))
        return new

    def choose_zone(self, tech):
        """Locational choice: resource share (PyPSA-GB DUKES split) x network signal (zonal price
        from the last PyPSA-GB redispatch; higher zonal price => more attractive)."""
        share = self.data.zone_share(tech).copy()
        zp = self.network_results.get("zonal_price") if self.network_results else None
        if zp is not None and self.scenario.get("locational_signal", True):
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
        price = res["price"]
        self.last_price = price
        dem = res["demand"].sum()
        # policy cost pass-through to consumers (GBP/MWh)
        self.levy = (st["cfd_cost"] + st["ro_cost"] + st["cm_cost"]) / dem
        # network stage
        constraint_cost = np.nan
        if self.network_every and (y - self.start) % self.network_every == 0:
            constraint_cost = self.network_stage(y, plants, res)
        # multi-energy feedbacks
        twavg = float((price * res["demand"]).sum() / dem)
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
                   retired_mw=retired, invested_mw=invested)
        for tech in TECHS:
            rec[f"cap_{tech}"] = sum(p.mw for p in plants if p.tech == tech) / 1e3
            rec[f"gen_{tech}"] = gen.get(tech, 0.0) / 1e6
        rec["gen_imports"] = gen.get("imports", 0.0) / 1e6
        rec["gen_total"] = sum(gen.values()) / 1e6
        for q in (5, 50, 95):
            rec[f"price_p{q:02d}"] = float(np.percentile(price, q))
        rec["cap_interconnector"] = res["ic_cap"] / 1e3
        self.records.append(rec)
        self.hourly[y] = pd.DataFrame({"price": price, "demand": res["demand"], "heat": res["heat"],
                                       "ev": res["ev"], "h2": res["h2"], "export": res["export"]})
        self.year += 1

    def invest(self, y):
        before = sum(p.mw for p in self.plants if p.online > y)
        price_fc = self.forecast(y + 3)
        self.cfd_round(y, price_fc)
        self.cm_auction(y)
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

    def network_stage(self, y, plants, res):
        rng = np.random.default_rng(y)
        hours = np.sort(rng.choice(self.H, self.network_hours, replace=False))
        # interconnector & storage handled as fixed injections folded into zonal demand
        blocks = [b for b in res["blocks"] if b.key > 0]
        ic_disp = res["disp"][:, [j for j, b in enumerate(res["blocks"]) if -10 < b.key < 0]].sum(1)
        net_demand = res["demand"] - ic_disp
        try:
            out = netmod.redispatch(self.data, plants, blocks, net_demand, hours)
        except Exception as e:  # keep the annual loop robust for the workshop
            log.warning("network stage failed: %s", e)
            return np.nan
        if out is None:
            return np.nan
        self.network_results = {"zonal_price": out["zonal_price_mean"], "flows": out["flows"], "year": y}
        cost_cu = 0.0
        for j, b in enumerate(res["blocks"]):
            if b.key > 0:
                cost_cu += float((res["disp"][hours, j] * b.price).sum())
        cc = max(out["cost_constrained"] - cost_cu, 0.0)
        self.network_results["constraint_cost_sample"] = cc
        return cc * self.H / len(hours) / 1e9

    def run(self):
        while self.year <= self.end:
            self.step()
        return self.results()

    def results(self):
        return pd.DataFrame(self.records).set_index("year")
