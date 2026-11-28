"""Agents: generation companies (operate, bid, invest) and their plants.

Generation companies are Mesa agents (https://mesa.readthedocs.io): they are registered with the
model, and a Mesa ``DataCollector`` records a panel of every firm in every year
(``GBMarketModel.firm_panel``). The model, not a Mesa scheduler, orders the phases of the year.
Households are held as arrays in ``ukabm.multienergy.HeatModule`` for speed, not as Mesa agents;
the government and the system operator are in ``ukabm.institutions``.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import mesa

from . import decisions
from .config import MERCHANT_UPLIFT, TECHS, hurdle_rate
from .observations import PlantView, validate

AgentBase = mesa.Agent


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
    cm_start: int = 0            # first delivery year of the CM agreement (paid cm_start..cm_end)
    cm_end: int = 0
    ro_end: int = 0              # last year of Renewables Obligation support
    cm_legacy: dict = field(default_factory=dict)        # {delivery year: GBP/kW} agreements pre-dating the model
    loss_years: int = 0
    history: list = field(default_factory=list)          # (year, profit incl. support and CM)
    energy_history: list = field(default_factory=list)   # (year, profit excl. CM payments)
    availability: float | None = None   # overrides Tech.availability (e.g. legacy AGR fleet)
    efficiency: float | None = None     # overrides Tech.efficiency (e.g. older CCGT fleet)
    route: str = "initial"              # how it came about: initial | pipeline | cfd | cm | merchant
    cfd_paid_negative: bool = False     # CfD of the investment contracts or rounds 1-3: paid at negative prices

    def active(self, year):
        return self.online <= year <= self.retire

    def cm_held(self, year):
        """True if a Capacity Market agreement covers delivery *year*."""
        return year in self.cm_legacy or (self.cm_start <= year <= self.cm_end and self.cm_end > 0)

    def cm_payment_price(self, year):
        """GBP/kW de-rated paid for delivery *year* (0 without an agreement)."""
        if year in self.cm_legacy:
            return self.cm_legacy[year]
        return self.cm_price if self.cm_held(year) else 0.0


class GenCo(AgentBase):
    """A generation company.

    Heterogeneity: hurdle rate (WACC), expectation strategy (myopic / adaptive / carbon-optimist),
    strategic bid mark-up on thermal plant, risk aversion (NPV haircut), annual capex budget.
    Decisions are delegated to a ``decisions.DecisionMaker`` (default: the original rules).
    """

    def __init__(self, model, name, wacc=0.08, expectation="myopic", markup=0.0,
                 risk_aversion=0.1, budget_gbp=3e9, tech_preference=None, decider=None, tech_hurdle=True):
        super().__init__(model)
        self.name = name
        self.wacc = wacc
        # required return by technology (config.HURDLE_RATE shifted by the firm's cost of capital) and
        # the uplift for merchant revenue; tech_hurdle False: one rate, the firm's WACC (idealised capital)
        self.hurdle = {t: hurdle_rate(t, wacc) for t in TECHS} if tech_hurdle else {}
        self.merchant_uplift = MERCHANT_UPLIFT if tech_hurdle else 0.0
        self.expectation = expectation
        self.markup = markup
        self.risk_aversion = risk_aversion
        self.budget = budget_gbp
        self.tech_preference = tech_preference or list(TECHS)
        self.profit_history = []
        self.decider = decisions.make(decider or "rules")
        self.panel = {}        # this year's row of the firm panel (GBMarketModel._firm_rows)

    # ------------------------------------------- decisions (see ukabm.decisions)
    # The GenCo builds an Observation (ukabm.observations) of what it may know, asks its decision maker,
    # and checks the answer against the decision's action space. The decision maker never sees the model.
    def _decide(self, kind, **fields):
        obs = self.model.observation(self, kind, **fields)
        return validate(kind, getattr(self.decider, kind)(obs), obs)

    def offer_price(self, plant: Plant, srmc: float, year: int) -> float:
        return self._decide("offer_price", plant=PlantView.of(plant, with_history=False), srmc=srmc, year=year)

    def expected_carbon(self, year):
        return self._decide("expected_carbon", year=year)

    def decide_investment(self, forecast):
        """Merchant investment: (tech, MW, NPV per MW) or None."""
        return self._decide("merchant_investment", forecast=forecast)

    def cfd_bid(self, tech: str, forecast) -> float | None:
        return self._decide("cfd_bid", tech=tech, forecast=forecast)

    def cm_bid(self, plant_or_tech, expected_margin_per_kw: float, new: bool) -> float:
        if new:
            return self._decide("cm_bid", tech=plant_or_tech, margin_per_kw=expected_margin_per_kw, new=True)
        return self._decide("cm_bid", plant=PlantView.of(plant_or_tech), tech=plant_or_tech.tech,
                            margin_per_kw=expected_margin_per_kw, new=False)

    # ------------------------------------------------------------- helpers
    def npv_per_mw(self, tech: str, margin_per_mw_yr: float, rate: float | None = None) -> float:
        r = self.hurdle.get(tech, self.wacc) + self.merchant_uplift if rate is None else rate
        return decisions.npv_per_mw(tech, margin_per_mw_yr, r, self.model.year + TECHS[tech].lead_time)

    def step(self):  # Mesa hook; model orchestrates phases explicitly
        pass
