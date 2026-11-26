"""Decision interface: every choice a generation company makes goes through a DecisionMaker.

The model asks the owning GenCo, and the GenCo asks its decision maker. Inputs are the agent itself
(its traits, and through ``agent.model`` the year, fleet, policy and forecasting helpers) plus the
arguments of each call (price forecasts, plants, technologies). Outputs are plain decisions: an offer
price, an expected carbon price, a merchant investment, a CfD strike bid or a CM bid.

``RuleBased`` holds the model's original rules. Other implementations (government and system-operator
rules, Q-learning, LLM agents; README roadmap items 2, 5, 6, 24, 25) subclass ``DecisionMaker``,
override the decisions they make, inherit the rest, and are registered by name:

    register("my_logic", MyLogic)
    scenario["decision_logic"] = "my_logic"                          # every GenCo
    scenario["decision_logic"] = {"MerchantIPP": "my_logic"}         # named GenCos; others "rules"

Implementations must draw random numbers only from ``agent.model.rng`` so runs stay reproducible.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from .config import STORAGE_TECHS, TECHS, VRE_TECHS  # noqa: F401  (STORAGE_TECHS for subclasses)

if TYPE_CHECKING:  # pragma: no cover
    from .agents import GenCo, Plant


class DecisionMaker:
    """Interface. Each method is one decision; see ``RuleBased`` for the reference behaviour."""

    name = "base"

    def offer_price(self, agent: "GenCo", plant: "Plant", srmc: float, year: int) -> float:
        """Day-ahead offer price (GBP/MWh) for *plant* in *year*, given its short-run marginal cost."""
        raise NotImplementedError

    def expected_carbon(self, agent: "GenCo", year: int) -> float:
        """The carbon price (GBP/t) the agent expects in *year*."""
        raise NotImplementedError

    def merchant_investment(self, agent: "GenCo", forecast) -> tuple[str, float, float] | None:
        """One merchant investment (tech, MW, NPV GBP/MW) on the hourly *forecast* price, or None."""
        raise NotImplementedError

    def cfd_bid(self, agent: "GenCo", tech: str, forecast) -> float:
        """Strike-price bid (GBP/MWh) for one block of *tech* in this year's CfD round."""
        raise NotImplementedError

    def cm_bid(self, agent: "GenCo", plant_or_tech, expected_margin_per_kw: float, new: bool) -> float:
        """Capacity Market bid (GBP/kW/yr, de-rated) for an existing plant or one new-build block."""
        raise NotImplementedError


class RuleBased(DecisionMaker):
    """The model's original decision rules (heterogeneous through the GenCo's traits)."""

    name = "rules"

    def offer_price(self, agent, plant, srmc, year):
        p = agent.model.policy
        if plant.tech in VRE_TECHS or plant.tech == "hydro":
            if plant.support == "ro":
                return -p.ro_value          # RO units bid negative up to the ROC value
            if plant.support == "cfd" and year <= plant.cfd_end:
                return -0.01                # CfD (post-AR4 negative-price rule simplified)
            return 0.0
        if plant.tech == "nuclear":
            return srmc - 15.0              # inflexible: bids below cost to stay on
        return srmc * (1.0 + agent.markup)

    def expected_carbon(self, agent, year):
        p = agent.model.policy
        c = p.carbon_price(year)
        if agent.expectation == "carbon_optimist":
            return c * 1.3
        if agent.expectation == "myopic":
            return p.carbon_price(agent.model.year)  # assumes today's price persists
        return c

    def merchant_investment(self, agent, forecast):
        """Evaluate candidate techs on the forecast price series; build one block of the best."""
        m = agent.model
        best = None
        for tech in agent.tech_preference:
            t = TECHS[tech]
            if not t.investable or tech in m.scenario.get("banned_techs", []):
                continue
            if tech in VRE_TECHS and m.policy.cfd_enabled:
                continue  # VRE goes via CfD auction when CfD is available
            if tech == "nuclear":
                continue  # nuclear only via government-led CfD/RAB route
            margin = m.expected_margin_per_mw(tech, forecast, agent)
            # cannibalisation haircut for VRE capture price and for own price impact
            npv = agent.npv_per_mw(tech, margin * (1 - agent.risk_aversion))
            if npv > 0 and (best is None or npv > best[1]):
                best = (tech, npv)
        if best is None:
            return None
        tech = best[0]
        mw = TECHS[tech].chunk_mw
        cost = TECHS[tech].capex * 1000 * mw
        if cost > agent.budget:
            return None
        return tech, mw, best[1]

    def cfd_bid(self, agent, tech, forecast):
        """Strike-price bid = levelised cost at a de-risked (CfD) WACC."""
        t = TECHS[tech]
        r = max(agent.wacc - 0.025, 0.035)
        crf = r / (1 - (1 + r) ** -t.life)
        cf = agent.model.capacity_factor(tech)
        lcoe = (t.capex * 1000 * crf + t.fom * 1000) / (8760 * cf) + t.vom
        return lcoe * (1 + 0.05 * agent.model.rng.standard_normal())

    def cm_bid(self, agent, plant_or_tech, expected_margin_per_kw, new):
        """Net missing money."""
        if new:
            t = TECHS[plant_or_tech]
            crf = agent.wacc / (1 - (1 + agent.wacc) ** -15)  # 15-year CM agreement
            missing = t.capex * crf + t.fom - expected_margin_per_kw
            return max(missing, 0.0) / t.derating
        t = TECHS[plant_or_tech.tech]
        return max(t.fom - expected_margin_per_kw, 0.0) / t.derating


REGISTRY: dict[str, type[DecisionMaker]] = {"rules": RuleBased}


def register(name: str, cls: type[DecisionMaker]) -> None:
    """Make *cls* selectable as ``scenario["decision_logic"] = name``."""
    if not (isinstance(cls, type) and issubclass(cls, DecisionMaker)):
        raise TypeError(f"{cls!r} is not a DecisionMaker subclass")
    REGISTRY[name] = cls


def make(spec) -> DecisionMaker:
    """A decision maker from a registered name, a DecisionMaker subclass or an instance."""
    if isinstance(spec, DecisionMaker):
        return spec
    if isinstance(spec, type) and issubclass(spec, DecisionMaker):
        return spec()
    if spec not in REGISTRY:
        raise KeyError(f"unknown decision logic {spec!r}; registered: {sorted(REGISTRY)}")
    return REGISTRY[spec]()


def for_genco(scenario: dict, genco_name: str) -> DecisionMaker:
    """The decision maker *scenario* assigns to the GenCo called *genco_name* (default: rules)."""
    spec = scenario.get("decision_logic", "rules")
    if isinstance(spec, dict):
        spec = spec.get(genco_name, "rules")
    return make(spec)
