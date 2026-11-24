"""Multi-energy coupling modules: heat (heat pumps vs gas boilers), gas network cost recovery,
transport (EV charging) and hydrogen (electrolysers).

Each module exposes `hourly_load(year, price_forecast)` (MW, 8760) and `update(year, signals)`.
The electricity model is the hub; these modules exchange prices and volumes with it:

    electricity price + policy levies --> retail tariffs --> household heat choice
    heat-pump stock --> electricity load (temperature-shaped)   gas-boiler stock --> gas throughput
    gas throughput (incl. power-sector gas burn) --> gas network tariff --> gas retail price
    EV stock --> charging load (unmanaged evening peak or price-responsive smart charging)
    electrolyser fleet --> price-responsive load (runs below H2 willingness-to-pay)
"""
from __future__ import annotations

import numpy as np

from .market import valley_fill


def synthetic_temperature(doy: np.ndarray, hour: np.ndarray, seed: int = 1) -> np.ndarray:
    """ASSUMPTION: synthetic GB population-weighted temperature (deg C). Replace with
    ERA5/atlite cutouts already used by PyPSA-GB for weather-consistent heat demand."""
    rng = np.random.default_rng(seed)
    seasonal = 10.5 - 6.5 * np.cos(2 * np.pi * (doy - 20) / 365)
    diurnal = 2.5 * np.sin(2 * np.pi * (hour - 9) / 24)
    days = int(doy.max()) + 1
    weather = np.repeat(np.convolve(rng.normal(0, 2.5, days + 6), np.ones(7) / 7 * 2.0, "same")[:days],
                        1)[doy - 1]
    return seasonal + diurnal + weather


class HeatModule:
    """Household agents (each a cohort of homes) choosing heating at boiler replacement.

    Decision: lifecycle cost (capex - grant + 15y discounted running cost) plus a hassle cost that
    falls with local adoption share (social influence / installer maturity). Logit choice.
    """

    def __init__(self, model, n_agents=2000, homes=28e6, hp_homes_2025=0.6e6, rng=None):
        self.m = model
        self.rng = rng or np.random.default_rng(0)
        self.n = n_agents
        self.homes_per_agent = homes / n_agents
        r = self.rng
        self.heat_mwh = r.lognormal(np.log(11.5), 0.35, n_agents)   # annual heat demand
        self.discount = r.uniform(0.04, 0.20, n_agents)             # implicit discount rates
        self.hassle0 = r.lognormal(np.log(4000), 0.6, n_agents)      # GBP non-financial barrier
        self.boiler_age = r.integers(0, 15, n_agents)
        self.on_gas = r.random(n_agents) < 0.85
        self.has_hp = np.zeros(n_agents, bool)
        self.has_hp[r.choice(n_agents, int(hp_homes_2025 / self.homes_per_agent), replace=False)] = True
        self.cop = 2.9
        self.shape = None

    @property
    def hp_homes(self):
        return self.has_hp.sum() * self.homes_per_agent

    @property
    def gas_homes(self):
        return (~self.has_hp & self.on_gas).sum() * self.homes_per_agent

    def heat_shape(self, prof):
        if self.shape is None:
            T = synthetic_temperature(prof.doy.values, prof.hour.values)
            hdd = np.maximum(15.5 - T, 0.0)
            daily = 1 + 0.35 * np.isin(prof.hour.values, [6, 7, 8, 17, 18, 19, 20])
            s = hdd * daily + 0.08 * hdd.mean()   # + hot water baseline
            self.shape = s / s.sum()
        return self.shape

    def hourly_load(self, year, prof):
        elec_mwh = (self.heat_mwh * self.has_hp).sum() * self.homes_per_agent / self.cop
        return elec_mwh * self.heat_shape(prof)

    def update(self, year, elec_retail, gas_retail, grant):
        r = self.rng
        self.boiler_age += 1
        replace = (self.boiler_age >= 15) | (r.random(self.n) < 0.02)
        idx = np.where(replace & ~self.has_hp)[0]
        share = self.has_hp.mean()
        hp_capex, boiler_capex = 11000.0 - grant, 3000.0
        for i in idx:
            ann = (1 - (1 + self.discount[i]) ** -15) / self.discount[i]
            run_hp = self.heat_mwh[i] / self.cop * elec_retail
            run_gb = self.heat_mwh[i] / 0.88 * (gas_retail if self.on_gas[i] else gas_retail * 1.6)
            hassle = self.hassle0[i] * (1 - 0.8 * min(share / 0.3, 1.0))
            u_hp = -(hp_capex + hassle + ann * run_hp)
            u_gb = -(boiler_capex + ann * run_gb)
            p_hp = 1 / (1 + np.exp(-(u_hp - u_gb) / 1500.0))
            if r.random() < p_hp:
                self.has_hp[i] = True
            self.boiler_age[i] = 0
        return {"hp_homes": self.hp_homes, "gas_homes": self.gas_homes}


class GasNetworkModule:
    """Gas distribution/transmission cost recovery: a fixed allowed revenue spread over a
    shrinking throughput (the 'utility death spiral' feedback). Hydrogen blending hook."""

    def __init__(self, allowed_revenue_gbp=5.5e9, nondomestic_twh=230.0):
        self.R = allowed_revenue_gbp
        self.nondomestic_twh = nondomestic_twh
        self.tariff = None

    def update(self, year, gas_homes, heat_mwh_per_home, power_gas_twh, h2_blend=0.0):
        # ASSUMPTION: allowed revenue declines 1%/yr after 2030 (some decommissioning)
        R = self.R * (0.99 ** max(year - 2030, 0))
        dom_twh = gas_homes * heat_mwh_per_home / 0.88 / 1e6
        throughput = dom_twh + self.nondomestic_twh * (0.985 ** (year - 2025)) + power_gas_twh
        self.tariff = R / (throughput * 1e6)   # GBP/MWh
        return {"gas_throughput_twh": throughput, "gas_network_tariff": self.tariff}


class EVModule:
    """EV fleet with unmanaged and smart (price-responsive) charging. Stock path ~ FES-like
    logistic (ASSUMPTION)."""

    def __init__(self, stock_2025=1.5e6, stock_sat=30e6, mid_year=2036, k=0.35,
                 mwh_per_ev=2.6, smart_share_2025=0.1, smart_share_2040=0.6):
        self.__dict__.update(locals())
        del self.__dict__["self"]

    def stock(self, year):
        s = self.stock_sat / (1 + np.exp(-self.k * (year - self.mid_year)))
        return max(s, self.stock_2025 if year >= 2025 else 0)

    def smart_share(self, year):
        f = min(max((year - 2025) / 15, 0), 1)
        return self.smart_share_2025 + f * (self.smart_share_2040 - self.smart_share_2025)

    def hourly_load(self, year, prof, price_forecast=None):
        H = len(prof)
        e_total = self.stock(year) * self.mwh_per_ev
        hour = prof.hour.values
        shape = np.interp(hour, [0, 6, 8, 16, 18, 20, 22, 24], [0.6, 0.3, 0.4, 0.8, 1.6, 1.8, 1.2, 0.6])
        shape = shape / shape.sum()
        smart = self.smart_share(year)
        load = e_total * (1 - smart) * shape
        if price_forecast is not None and smart > 0:
            per_day = np.full(H // 24, e_total * smart / (H // 24))
            cap = self.stock(year) * smart * 0.007 * 0.5   # 7 kW, 50% plugged-in
            # price_forecast here is a residual-load signal (demand - VRE) from pass 1
            load = load + valley_fill(per_day, price_forecast, cap,
                                      hours_window=list(range(0, 8)) + [21, 22, 23])
        else:
            load = load + e_total * smart * shape
        return load


class HydrogenModule:
    """Grid-connected electrolysers: run when price < willingness-to-pay (H2 value * efficiency).
    Capacity path exogenous (ASSUMPTION, FES-like). Hook for H2 storage/turbines and gas blending."""

    def __init__(self, gw_2030=1.0, gw_2050=10.0, eff=0.7, h2_value=80.0):
        self.gw_2030, self.gw_2050, self.eff, self.h2_value = gw_2030, gw_2050, eff, h2_value

    def capacity_mw(self, year):
        if year < 2027:
            return 0.0
        f = min(max((year - 2030) / 20, 0), 1)
        return 1000 * (self.gw_2030 * min((year - 2026) / 4, 1) + f * (self.gw_2050 - self.gw_2030))

    def wtp(self):
        return self.h2_value * self.eff

    def hourly_load(self, year, price_forecast):
        cap = self.capacity_mw(year)
        return np.where(price_forecast < self.wtp(), cap, 0.0)
