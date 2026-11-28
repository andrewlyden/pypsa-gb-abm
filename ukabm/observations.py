"""What a generation company may know when it decides (README roadmap item 34).

A decision maker (``ukabm.decisions``) receives an ``Observation``, not the model. The observation holds

* ``traits``: the firm's own characteristics and the budget it has left this year;
* ``own``: views of the firm's own plants (no link back to the model or to other firms' plants);
* ``market``: public information and analysis tools. Public information is the year, the published
  policy (carbon price path, caps, scheme switches), last year's hourly prices and the latest auction
  results. The tools turn a price series into a technology's expected margin, give capacity factors,
  and give the model's long-horizon price forecasts; they use only public information (published fuel
  and carbon paths, the CfD and CM registers of committed plant). The seeded random generator is passed
  so that decisions stay reproducible;
* decision-specific fields (``forecast``, ``tech``, ``plant``, ``srmc``, ``margin_per_kw``, ``new``,
  ``year``, ``options``).

Each decision also has a declared action space (``ACTIONS``), and ``validate`` checks what a decision
maker returns against it. ``Observation.to_dict`` gives a JSON-safe summary (arrays summarised) for logs
and LLM prompts. Rewards for learning agents come through ``DecisionMaker.learn`` (realised profit per
firm and plant, once a year after settlement).

The tools are a deliberate boundary rather than a sandbox: they are closures over the model, so code
that introspects them could reach it. Decision makers must use only the observation's public fields
and tools. Today's price forecasts are the model's own (perfect knowledge of the committed pipeline and
the published paths); firms' own, imperfect forecasts are roadmap item 36.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Callable

import numpy as np

# ----------------------------------------------------------------------------- views


@dataclass(frozen=True)
class Traits:
    """The firm's own characteristics."""
    name: str
    wacc: float
    expectation: str
    markup: float
    risk_aversion: float
    budget: float
    budget_left: float
    tech_preference: tuple
    hurdle: dict = field(default_factory=dict)   # technology -> required return with contracted revenue
    merchant_uplift: float = 0.0                 # added to the required return of a merchant project

    def rate(self, tech: str, contracted: bool = False) -> float:
        """The firm's required return on a *tech* project: the technology's hurdle rate shifted by the
        firm's own cost of capital, plus the merchant uplift unless the revenue is contracted. Firms
        without technology hurdle rates (idealised capital) use their WACC for everything."""
        return self.hurdle.get(tech, self.wacc) + (0.0 if contracted else self.merchant_uplift)


@dataclass(frozen=True)
class PlantView:
    """One of the firm's own plants, as the firm sees it."""
    pid: int
    tech: str
    zone: str
    mw: float
    online: int
    retire: int
    support: str
    strike: float
    cfd_end: int
    ro_end: int
    cm_price: float
    cm_start: int
    cm_end: int
    efficiency: float | None
    availability: float | None
    history: tuple = ()
    energy_history: tuple = ()
    cfd_paid_negative: bool = False

    @classmethod
    def of(cls, p, with_history: bool = True) -> "PlantView":
        return cls(p.pid, p.tech, p.zone, p.mw, p.online, p.retire, p.support, p.strike, p.cfd_end,
                   p.ro_end, p.cm_price, p.cm_start, p.cm_end, p.efficiency, p.availability,
                   tuple(p.history) if with_history else (), tuple(p.energy_history) if with_history else (),
                   getattr(p, "cfd_paid_negative", False))


@dataclass(frozen=True)
class MarketInfo:
    """Public information and analysis tools (see the module docstring)."""
    year: int
    policy: Any                      # ukabm.config.Policy (published rules; no link to the model)
    banned_techs: tuple
    last_price: np.ndarray | None    # last year's hourly prices (read-only copy)
    cm_clearing: float               # last T-4 clearing price, GBP/kW/yr
    cfd_clearing: dict               # last CfD round's clearing strike per technology
    rng: Any                         # the model's seeded generator (draw only from this)
    capacity_factor: Callable[[str], float]
    cf_profile: Callable[[str], Any]
    expected_margin: Callable[..., float]    # (tech, price, **kw) -> GBP/MW/yr for this firm
    forecast_horizons: Callable[[], dict]    # {year: hourly price} at t+8 and t+13


@dataclass(frozen=True)
class Observation:
    kind: str
    traits: Traits
    market: MarketInfo
    own: tuple = ()                  # PlantView of the firm's plants (investment and auction decisions)
    forecast: np.ndarray | None = None
    tech: str | None = None
    plant: PlantView | None = None
    srmc: float | None = None
    margin_per_kw: float | None = None
    new: bool | None = None
    year: int | None = None
    options: tuple = ()              # candidate actions where the action space is a choice

    def to_dict(self) -> dict:
        """JSON-safe summary: arrays as mean / percentiles, tools and the generator left out."""
        def arr(a):
            if a is None:
                return None
            a = np.asarray(a, dtype=float)
            return dict(mean=float(a.mean()), p05=float(np.percentile(a, 5)), p50=float(np.median(a)),
                        p95=float(np.percentile(a, 95)), max=float(a.max()))
        m = self.market
        return dict(kind=self.kind, traits=asdict(self.traits), year=m.year,
                    market=dict(last_price=arr(m.last_price), cm_clearing=m.cm_clearing,
                                cfd_clearing=dict(m.cfd_clearing), banned_techs=list(m.banned_techs),
                                carbon_price=m.policy.carbon_price(m.year)),
                    own=[dict(tech=p.tech, mw=p.mw, online=p.online, retire=p.retire, support=p.support,
                              last_profit=(p.history[-1][1] if p.history else None)) for p in self.own],
                    forecast=arr(self.forecast), tech=self.tech, srmc=self.srmc,
                    plant=None if self.plant is None else dict(tech=self.plant.tech, mw=self.plant.mw,
                                                               support=self.plant.support),
                    margin_per_kw=self.margin_per_kw, new=self.new, decision_year=self.year,
                    options=list(self.options))


# ----------------------------------------------------------------------------- action spaces


@dataclass(frozen=True)
class Continuous:
    low: float
    high: float
    allow_none: bool = False         # None = abstain


@dataclass(frozen=True)
class Choice:
    """One of the observation's ``options`` (or None for 'do nothing')."""
    allow_none: bool = True


ACTIONS = {
    "offer_price": Continuous(-1e4, 1e5),              # GBP/MWh
    "expected_carbon": Continuous(0.0, 1e4),           # GBP/t
    "merchant_investment": Choice(),                   # (tech, MW, NPV) with tech in options, or None
    "cfd_bid": Continuous(0.0, 1e4, allow_none=True),  # strike GBP/MWh, None = abstain
    "cm_bid": Continuous(0.0, 1e4),                    # GBP/kW/yr de-rated (capped by the auction)
}


def validate(kind: str, action, obs: Observation):
    """Check *action* against the action space of *kind*; return it, or raise ValueError."""
    space = ACTIONS[kind]
    if action is None:
        if space.allow_none:
            return None
        raise ValueError(f"{kind}: None is not allowed")
    if isinstance(space, Choice):
        tech = action[0]
        if tech not in obs.options:
            raise ValueError(f"{kind}: {tech!r} is not one of the options {obs.options}")
        return action
    x = float(action)
    if not np.isfinite(x) or not space.low <= x <= space.high:
        raise ValueError(f"{kind}: {x} outside [{space.low}, {space.high}]")
    return action


@dataclass
class Outcome:
    """What a firm learns after settlement each year (the reward for learning agents)."""
    year: int
    profit: float                                     # GBP, all the firm's plants
    by_plant: dict = field(default_factory=dict)      # pid -> GBP
