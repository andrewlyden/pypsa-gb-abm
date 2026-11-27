"""Decision interface: every choice a generation company makes goes through a DecisionMaker.

The model asks the owning GenCo, and the GenCo asks its decision maker with an ``Observation``
(``ukabm.observations``): the firm's traits and own plants, public market information and analysis
tools, and the fields of the decision (forecast, technology, plant ...). A decision maker never sees the
model. Outputs are plain decisions (an offer price, an expected carbon price, a merchant investment, a
CfD strike bid or a CM bid), checked against the declared action space (``observations.ACTIONS``).
After settlement each year ``learn`` receives the firm's realised profit (the reward for learning agents).

``RuleBased`` holds the model's original rules. Other implementations (government and system-operator
rules, Q-learning, LLM agents; README roadmap items 2, 5, 6, 24, 25) subclass ``DecisionMaker``,
override the decisions they make, inherit the rest, and are registered by name:

    register("my_logic", MyLogic)
    scenario["decision_logic"] = "my_logic"                          # every GenCo
    scenario["decision_logic"] = {"MerchantIPP": "my_logic"}         # named GenCos; others "rules"

Implementations must draw random numbers only from ``obs.market.rng`` so runs stay reproducible.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from .config import STORAGE_TECHS, TECHS, VRE_TECHS, capex_kw, fom_kw  # noqa: F401  (STORAGE_TECHS for subclasses)

if TYPE_CHECKING:  # pragma: no cover
    from .observations import Observation, Outcome


def npv_per_mw(tech: str, margin_per_mw_yr: float, rate: float, online: int | None = None) -> float:
    """NPV per MW of *tech* earning a flat annual margin (before FOM) over its life at *rate*, at the
    costs of a plant coming online in *online* (config.COST_PATHS; None: the reference costs)."""
    t = TECHS[tech]
    annuity = (1 - (1 + rate) ** -t.life) / rate
    return (margin_per_mw_yr - fom_kw(tech, online) * 1000) * annuity - capex_kw(tech, online) * 1000


class DecisionMaker:
    """Interface. Each method is one decision; see ``RuleBased`` for the reference behaviour."""

    name = "base"

    def offer_price(self, obs: "Observation") -> float:
        """Day-ahead offer price (GBP/MWh) for ``obs.plant`` in ``obs.year``, given ``obs.srmc``."""
        raise NotImplementedError

    def expected_carbon(self, obs: "Observation") -> float:
        """The carbon price (GBP/t) the firm expects in ``obs.year``."""
        raise NotImplementedError

    def merchant_investment(self, obs: "Observation") -> tuple[str, float, float] | None:
        """One merchant investment (tech, MW, NPV GBP/MW) with tech in ``obs.options``, on the hourly
        ``obs.forecast`` price (t+3), or None."""
        raise NotImplementedError

    def cfd_bid(self, obs: "Observation") -> float | None:
        """Strike-price bid (GBP/MWh) for one block of ``obs.tech`` in this year's CfD round, or None."""
        raise NotImplementedError

    def cm_bid(self, obs: "Observation") -> float:
        """Capacity Market bid (GBP/kW/yr, de-rated): an existing plant (``obs.plant``, gross margin
        ``obs.margin_per_kw``) or one new-build block of ``obs.tech`` (``obs.new``)."""
        raise NotImplementedError

    def learn(self, outcome: "Outcome") -> None:
        """Called once a year after settlement with the firm's realised profit. Default: nothing."""


class RuleBased(DecisionMaker):
    """The model's original decision rules (heterogeneous through the GenCo's traits)."""

    name = "rules"

    def offer_price(self, obs):
        p, plant, srmc, year = obs.market.policy, obs.plant, obs.srmc, obs.year
        if plant.tech in VRE_TECHS or plant.tech == "hydro":
            if plant.support == "ro" and year <= plant.ro_end:
                return -p.ro_value          # RO units bid negative up to the ROC value
            if plant.support == "cfd" and year <= plant.cfd_end:
                return -0.01                # CfD (post-AR4 negative-price rule simplified)
            return 0.0
        if plant.tech == "nuclear":
            return srmc - 15.0              # inflexible: bids below cost to stay on
        return srmc * (1.0 + obs.traits.markup)

    def expected_carbon(self, obs):
        p = obs.market.policy
        c = p.carbon_price(obs.year)
        if obs.traits.expectation == "carbon_optimist":
            return c * 1.3
        if obs.traits.expectation == "myopic":
            return p.carbon_price(obs.market.year)   # assumes today's price persists
        return c

    def merchant_investment(self, obs):
        """Evaluate the candidate techs (``obs.options``: investable, allowed, affordable) on the forecast
        price series; build one block of the best."""
        tr = obs.traits
        best = None
        for tech in obs.options:
            if tech in VRE_TECHS and obs.market.policy.cfd_enabled:
                continue  # VRE goes via CfD auction when CfD is available
            margin = obs.market.expected_margin(tech, obs.forecast)
            # cannibalisation haircut for VRE capture price and for own price impact
            npv = npv_per_mw(tech, margin * (1 - tr.risk_aversion), tr.wacc,
                             obs.market.year + TECHS[tech].lead_time)
            if npv > 0 and (best is None or npv > best[1]):
                best = (tech, npv)
        if best is None:
            return None
        return best[0], TECHS[best[0]].chunk_mw, best[1]

    def cfd_bid(self, obs):
        """Strike-price bid = levelised cost at a de-risked (CfD) WACC."""
        t = TECHS[obs.tech]
        online = obs.market.year + t.lead_time
        r = max(obs.traits.wacc - 0.025, 0.035)
        crf = r / (1 - (1 + r) ** -t.life)
        cf = obs.market.capacity_factor(obs.tech)
        lcoe = (capex_kw(obs.tech, online) * 1000 * crf + fom_kw(obs.tech, online) * 1000) / (8760 * cf) + t.vom
        return lcoe * (1 + 0.05 * obs.market.rng.standard_normal())

    def cm_bid(self, obs):
        """Net missing money."""
        if obs.new:
            t = TECHS[obs.tech]
            w = obs.traits.wacc
            crf = w / (1 - (1 + w) ** -15)  # 15-year CM agreement
            online = obs.market.year + 4    # T-4 delivery year
            missing = capex_kw(obs.tech, online) * crf + fom_kw(obs.tech, online) - obs.margin_per_kw
            return max(missing, 0.0) / t.derating
        t = TECHS[obs.plant.tech]
        return max(fom_kw(obs.plant.tech, obs.plant.online) - obs.margin_per_kw, 0.0) / t.derating


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


class ExpectationBids(RuleBased):
    """Forward-looking firms: CfD bids from their own expectations (README roadmap item 3), and merchant
    or PPA investment, wind and solar included, on forecasts over the asset's life (item 4).

    The bid is the lowest strike at which the project meets the firm's hurdle rate:

        capex = PV_contract(strike x gen x (1 - basis) - FOM)  +  PV_tail(capture x gen - FOM)

    over a 20-year two-way CfD at the de-risked rate (WACC - 2.5 points, floor 3.5 %), then a merchant
    tail to the end of the asset's life at the firm's WACC. The tail capture price is the firm's view:
    *myopic* firms take this year's capture price, *adaptive* firms the t+3 forecast less a 15 %
    cannibalisation haircut, *carbon optimists* the t+3 forecast without the haircut. Risk aversion adds
    a premium on the required revenue, and ±2 % noise (from ``model.rng``) stands for project-specific
    costs. A firm whose required strike is above the cap is excluded by the auction (it abstains).
    Withdrawal after winning needs cost uncertainty, which arrives with cost trajectories (item 19).
    """

    name = "expectations"
    CONTRACT_YEARS = 20
    BASIS = 0.02          # share of contracted output not paid the strike (curtailment, negative hours)
    HAIRCUT = 0.15        # adaptive firms' cannibalisation haircut on the forecast capture price

    def tail_capture(self, obs, tech=None, forecast=None):
        tech = tech or obs.tech
        forecast = obs.forecast if forecast is None else forecast
        cf = obs.market.cf_profile(tech)
        if obs.traits.expectation == "myopic" and obs.market.last_price is not None:
            price, haircut = obs.market.last_price, 0.0
        else:
            price = forecast
            haircut = 0.0 if obs.traits.expectation == "carbon_optimist" else self.HAIRCUT
        return float((price * cf).sum() / max(cf.sum(), 1e-9)) * (1 - haircut)

    def cfd_bid(self, obs):
        tech = obs.tech
        t = TECHS[tech]
        tr = obs.traits
        gen = 8760 * obs.market.capacity_factor(tech)             # MWh per MW per year
        n = min(self.CONTRACT_YEARS, t.life)
        rc = max(tr.wacc - 0.025, 0.035)                          # contracted years
        rm = tr.wacc                                              # merchant tail
        a_contract = (1 - (1 + rc) ** -n) / rc
        a_tail = ((1 - (1 + rm) ** -t.life) / rm - (1 - (1 + rm) ** -n) / rm) if t.life > n else 0.0
        online = obs.market.year + t.lead_time
        capex = capex_kw(tech, online) * 1000
        fom = fom_kw(tech, online) * 1000
        tail = max(self.tail_capture(obs) - t.vom, 0.0) * gen - fom
        need = capex + fom * a_contract - tail * a_tail          # PV the contract must cover
        strike = need / (a_contract * gen * (1 - self.BASIS)) + t.vom
        strike /= max(1 - 0.5 * tr.risk_aversion, 0.5)           # risk premium
        return strike * (1 + 0.02 * obs.market.rng.standard_normal())

    # ------------------------------------------------ merchant and PPA investment (roadmap item 4)
    PPA_YEARS = 15
    PPA_DISCOUNT = 0.10    # PPA price below the expected capture price (the offtaker's margin and risk)
    PPA_RATE_CUT = 0.015   # contracted revenue lowers the cost of capital by this much

    def margin_path(self, obs, tech, forecast=None):
        """Expected annual margin per MW at each forecast year: t+3 (the model's forecast) and the long
        horizons of ``market.forecast_horizons``. Battery services use the fleet in the pipeline."""
        mk = obs.market
        forecast = obs.forecast if forecast is None else forecast
        prices = {mk.year + 3: forecast, **mk.forecast_horizons()}
        online = mk.year + TECHS[tech].lead_time
        fleet = max(mk.year + 3, online)        # battery services: the fleet in the pipeline, not a horizon
        return {y: mk.expected_margin(tech, p, fleet_year=fleet, price_year=y, vre_haircut=0.0)
                for y, p in sorted(prices.items())}

    @staticmethod
    def path_npv(tech, path, online, rate, haircut=0.0, first=None):
        """NPV per MW of building *tech* coming online in *online*: margins interpolated linearly
        between the forecast years of *path* (flat outside), less FOM, over the asset life. *first*:
        optional (years, revenue per MW per year, rate) for a contracted first period."""
        t = TECHS[tech]
        ys = sorted(path)
        fom = fom_kw(tech, online) * 1000
        npv, df = -capex_kw(tech, online) * 1000, 1.0
        for k in range(1, t.life + 1):
            year = online + k - 1
            if first is not None and k <= first[0]:
                df /= 1 + first[2]
                npv += (first[1] - fom) * df
            else:
                df /= 1 + rate
                margin = float(np.interp(year, ys, [path[y] for y in ys]))
                npv += (margin * (1 - haircut) - fom) * df
        return npv

    def merchant_investment(self, obs):
        """The best positive-NPV block on forecasts over the asset's life. Wind and solar may be built
        merchant or on a PPA alongside CfDs; other technologies as in RuleBased."""
        tr, year = obs.traits, obs.market.year
        best = None
        for tech in obs.options:
            t = TECHS[tech]
            path = self.margin_path(obs, tech)
            online = year + t.lead_time
            npv = self.path_npv(tech, path, online, tr.wacc, tr.risk_aversion)
            if tech in VRE_TECHS:          # PPA: a fixed price on the t+3 capture value, then merchant
                ppa = path[year + 3] * (1 - self.PPA_DISCOUNT)
                npv = max(npv, self.path_npv(tech, path, online, tr.wacc, tr.risk_aversion,
                                             first=(self.PPA_YEARS, ppa, max(tr.wacc - self.PPA_RATE_CUT, 0.03))))
            if npv > 0 and (best is None or npv > best[1]):
                best = (tech, npv)
        if best is None:
            return None
        return best[0], TECHS[best[0]].chunk_mw, best[1]


REGISTRY["expectations"] = ExpectationBids
