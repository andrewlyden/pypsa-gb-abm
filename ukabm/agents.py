"""Agents: generation companies (operate, bid, invest), plants, and a government/policy agent.

Built on Mesa (https://mesa.readthedocs.io) when installed; falls back to a tiny shim so the
model also runs without Mesa.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import decisions
from .config import TECHS

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
    Decisions are delegated to a ``decisions.DecisionMaker`` (default: the original rules).
    """

    def __init__(self, model, name, wacc=0.08, expectation="myopic", markup=0.0,
                 risk_aversion=0.1, budget_gbp=3e9, tech_preference=None, decider=None):
        super().__init__(model)
        self.name = name
        self.wacc = wacc
        self.expectation = expectation
        self.markup = markup
        self.risk_aversion = risk_aversion
        self.budget = budget_gbp
        self.tech_preference = tech_preference or list(TECHS)
        self.profit_history = []
        self.decider = decisions.make(decider or "rules")

    # ------------------------------------------- decisions (see ukabm.decisions)
    def offer_price(self, plant: Plant, srmc: float, year: int) -> float:
        return self.decider.offer_price(self, plant, srmc, year)

    def expected_carbon(self, year):
        return self.decider.expected_carbon(self, year)

    def decide_investment(self, forecast):
        """Merchant investment: (tech, MW, NPV per MW) or None."""
        return self.decider.merchant_investment(self, forecast)

    def cfd_bid(self, tech: str, forecast) -> float:
        return self.decider.cfd_bid(self, tech, forecast)

    def cm_bid(self, plant_or_tech, expected_margin_per_kw: float, new: bool) -> float:
        return self.decider.cm_bid(self, plant_or_tech, expected_margin_per_kw, new)

    # ------------------------------------------------------------- helpers
    def npv_per_mw(self, tech: str, margin_per_mw_yr: float, rate: float | None = None) -> float:
        t = TECHS[tech]
        r = rate if rate is not None else self.wacc
        annuity = (1 - (1 + r) ** -t.life) / r
        return (margin_per_mw_yr - t.fom * 1000) * annuity - t.capex * 1000

    def step(self):  # Mesa hook; model orchestrates phases explicitly
        pass
