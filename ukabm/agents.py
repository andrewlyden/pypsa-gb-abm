"""Agents: generation companies (operate, bid, invest), plants, and a government/policy agent.

Built on Mesa (https://mesa.readthedocs.io) when installed; falls back to a tiny shim so the
model also runs without Mesa.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .config import TECHS, VRE_TECHS, STORAGE_TECHS

try:  # Mesa 3.x
    import mesa
    AgentBase = mesa.Agent
except Exception:  # pragma: no cover
    class AgentBase:  # minimal shim
        _next = 0

        def __init__(self, model):
            self.model = model
            AgentBase._next += 1
            self.unique_id = AgentBase._next


@dataclass
class Plant:
    pid: int
    owner: "GenCo"
    tech: str
    zone: str
    mw: float
    online: int                  # first year of operation
    retire: int                  # last year of operation
    support: str = "merchant"    # merchant | cfd | ro
    strike: float = 0.0          # CfD strike GBP/MWh
    cfd_end: int = 0
    cm_price: float = 0.0        # GBP/kW/yr
    cm_end: int = 0
    loss_years: int = 0
    history: list = field(default_factory=list)
    availability: float | None = None   # overrides Tech.availability (e.g. legacy AGR fleet)
    efficiency: float | None = None     # overrides Tech.efficiency (e.g. older CCGT fleet)

    def active(self, year):
        return self.online <= year <= self.retire


class GenCo(AgentBase):
    """A generation company.

    Heterogeneity: hurdle rate (WACC), expectation strategy (myopic / adaptive / carbon-optimist),
    strategic bid mark-up on thermal plant, risk aversion (NPV haircut), annual capex budget.
    """

    def __init__(self, model, name, wacc=0.08, expectation="myopic", markup=0.0,
                 risk_aversion=0.1, budget_gbp=3e9, tech_preference=None):
        super().__init__(model)
        self.name = name
        self.wacc = wacc
        self.expectation = expectation
        self.markup = markup
        self.risk_aversion = risk_aversion
        self.budget = budget_gbp
        self.tech_preference = tech_preference or list(TECHS)
        self.profit_history = []

    # ---------------------------------------------------------------- bids
    def offer_price(self, plant: Plant, srmc: float, year: int) -> float:
        p = self.model.policy
        if plant.tech in VRE_TECHS or plant.tech == "hydro":
            if plant.support == "ro":
                return -p.ro_value          # RO units bid negative up to the ROC value
            if plant.support == "cfd" and year <= plant.cfd_end:
                return -0.01                # CfD (post-AR4 negative-price rule simplified)
            return 0.0
        if plant.tech == "nuclear":
            return srmc - 15.0              # inflexible: bids below cost to stay on
        return srmc * (1.0 + self.markup)

    # ---------------------------------------------------------- investment
    def expected_carbon(self, year):
        p = self.model.policy
        c = p.carbon_price(year)
        if self.expectation == "carbon_optimist":
            return c * 1.3
        if self.expectation == "myopic":
            return p.carbon_price(self.model.year)  # assumes today's price persists
        return c

    def npv_per_mw(self, tech: str, margin_per_mw_yr: float, rate: float | None = None) -> float:
        t = TECHS[tech]
        r = rate if rate is not None else self.wacc
        annuity = (1 - (1 + r) ** -t.life) / r
        return (margin_per_mw_yr - t.fom * 1000) * annuity - t.capex * 1000

    def decide_investment(self, forecast):
        """Merchant investment: evaluate candidate techs on the forecast price series."""
        m = self.model
        best = None
        for tech in self.tech_preference:
            t = TECHS[tech]
            if not t.investable or tech in m.scenario.get("banned_techs", []):
                continue
            if tech in VRE_TECHS and m.policy.cfd_enabled:
                continue  # VRE goes via CfD auction when CfD is available
            if tech == "nuclear":
                continue  # nuclear only via government-led CfD/RAB route
            margin = m.expected_margin_per_mw(tech, forecast, self)
            # cannibalisation haircut for VRE capture price and for own price impact
            npv = self.npv_per_mw(tech, margin * (1 - self.risk_aversion))
            if npv > 0 and (best is None or npv > best[1]):
                best = (tech, npv)
        if best is None:
            return None
        tech = best[0]
        mw = TECHS[tech].chunk_mw
        cost = TECHS[tech].capex * 1000 * mw
        if cost > self.budget:
            return None
        return tech, mw, best[1]

    def cfd_bid(self, tech: str, forecast) -> float:
        """Strike-price bid = levelised cost at a de-risked (CfD) WACC."""
        t = TECHS[tech]
        r = max(self.wacc - 0.025, 0.035)
        crf = r / (1 - (1 + r) ** -t.life)
        cf = self.model.capacity_factor(tech)
        lcoe = (t.capex * 1000 * crf + t.fom * 1000) / (8760 * cf) + t.vom
        return lcoe * (1 + 0.05 * self.model.rng.standard_normal())

    def cm_bid(self, plant_or_tech, expected_margin_per_kw: float, new: bool) -> float:
        """Capacity Market bid (GBP/kW/yr, de-rated) = net missing money."""
        if new:
            t = TECHS[plant_or_tech]
            crf = self.wacc / (1 - (1 + self.wacc) ** -15)  # 15-year CM agreement
            missing = t.capex * crf + t.fom - expected_margin_per_kw
            return max(missing, 0.0) / t.derating
        t = TECHS[plant_or_tech.tech]
        return max(t.fom - expected_margin_per_kw, 0.0) / t.derating

    def step(self):  # Mesa hook; model orchestrates phases explicitly
        pass
