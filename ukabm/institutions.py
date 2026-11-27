"""Institutions as agents: the government that runs CfD allocation rounds.

Each year the government sets the round: for every technology pot, a £ budget, a volume limit and an
administrative strike price (the cap). The auction (``GBMarketModel.cfd_round``) then clears the firms'
bids pay-as-clear per pot within those limits, and the government observes the result before the next
round. Volumes therefore come from the interaction of the government's settings and the firms' bids.

Governments are selected by ``scenario["government"]`` (default ``"fixed"``):

* ``"fixed"`` reproduces the model's original rule: 6 GW a year split 60/20/20 (``Policy`` and the
  ``cfd_pots`` scenario key), the policy caps, no £ budget.
* ``"targets"`` tracks a capacity target path per technology (``config.CFD_TARGET_GW``): it asks for the
  capacity still missing at the delivery year, funds it at the strike it expects (last clearing, else
  the cap), raises a pot's cap after a
  round that failed for lack of bids under the cap, and scales budgets down when the policy levy passes a
  bill threshold. Parameters: ``config.GOVERNMENT_TARGETS`` and ``scenario["government_params"]``.

Further objectives (least cost, bills, political; README roadmap item 6) subclass ``Government`` and
register a name, like decision makers in ``ukabm.decisions``.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .config import CFD_TARGET_GW, GOVERNMENT_TARGETS, TECHS

CFD_TECHS = ("wind_offshore", "wind_onshore", "solar")


@dataclass
class PotSettings:
    """One technology pot in one allocation round."""
    max_mw: float                  # volume limit: accept blocks while accepted MW is below this
    cap: float                     # administrative strike price (GBP/MWh): bids above it are excluded
    budget_gbp: float | None = None    # annual support cost limit at the clearing price (None: no £ budget)
    reference_price: float = 0.0   # forecast capture price used to value support (GBP/MWh)
    mwh_per_mw: float = 0.0        # expected annual generation per MW (MWh)

    def support_per_mw(self, strike: float) -> float:
        """Expected annual CfD support per MW at *strike*, floored at zero (GBP/MW/yr)."""
        return max(strike - self.reference_price, 0.0) * self.mwh_per_mw


class Government:
    """Interface. ``round_settings`` sets each pot; ``observe`` sees the result of the round."""

    name = "base"

    def __init__(self, model):
        self.model = model
        self.log: list[dict] = []

    def round_settings(self, year: int, price_fc) -> dict[str, PotSettings]:
        raise NotImplementedError

    def observe(self, year: int, result: dict[str, dict]) -> None:
        """*result*: per technology, offered/accepted MW, bids excluded by the cap, clearing strike."""

    # helpers shared by implementations
    def capture_price(self, tech: str, price_fc) -> float:
        cf = self.model.cf_profile(tech)
        return float((price_fc * cf).sum() / max(cf.sum(), 1e-9))

    def capacity_mw(self, tech: str, year: int) -> float:
        return sum(p.mw for p in self.model.plants if p.tech == tech and p.active(year))


class FixedRules(Government):
    """The original rule: a fixed GW volume per round split by fixed pot shares; policy caps; no £ budget."""

    name = "fixed"

    def round_settings(self, year, price_fc):
        m = self.model
        volume = m.policy.cfd_budget_gw_per_year * 1000
        pots = m.scenario.get("cfd_pots", {"wind_offshore": 0.6, "wind_onshore": 0.2, "solar": 0.2})
        return {tech: PotSettings(max_mw=volume * share, cap=m.policy.cfd_admin_strike_cap[tech])
                for tech, share in pots.items()}


class TargetTracking(Government):
    """Buy the capacity still missing from a target path, within a £ budget, adapting caps and budgets."""

    name = "targets"

    def __init__(self, model):
        super().__init__(model)
        self.params = {**GOVERNMENT_TARGETS, **model.scenario.get("government_params", {})}
        self.targets = {**CFD_TARGET_GW, **model.scenario.get("cfd_targets_gw", {})}
        self.cap0 = {t: model.policy.cfd_admin_strike_cap[t] for t in CFD_TECHS}
        self.cap = dict(self.cap0)
        self.last_clearing: dict[str, float] = {}

    def target_mw(self, tech: str, year: float) -> float:
        path = self.targets[tech]
        ys = sorted(path)
        return 1000 * float(np.interp(year, ys, [path[y] for y in ys]))

    def round_settings(self, year, price_fc):
        m, P = self.model, self.params
        squeeze = m.levy > P["levy_threshold"]          # bills too high: fund less this round
        out = {}
        for tech in CFD_TECHS:
            dy = year + TECHS[tech].lead_time
            need = max(self.target_mw(tech, dy) - self.capacity_mw(tech, dy), 0.0)
            s = PotSettings(max_mw=need, cap=self.cap[tech], reference_price=self.capture_price(tech, price_fc),
                            mwh_per_mw=8760 * m.capacity_factor(tech))
            # enough to buy the missing capacity at the strike it expects (last clearing, else the cap),
            # with headroom; less when bills are too high
            expect = min(self.last_clearing.get(tech, s.cap), s.cap)
            s.budget_gbp = (need * s.support_per_mw(expect) * P["budget_headroom"]
                            * (P["levy_budget_scale"] if squeeze else 1.0))
            out[tech] = s
            self.log.append(dict(year=year, tech=tech, delivery=dy, target_mw=self.target_mw(tech, dy),
                                 need_mw=need, cap=s.cap, budget_gbp=s.budget_gbp,
                                 reference_price=s.reference_price, levy_squeeze=squeeze))
        return out

    def observe(self, year, result):
        P = self.params
        for tech, r in result.items():
            if tech not in self.cap:
                continue
            if r.get("clearing") is not None:
                self.last_clearing[tech] = r["clearing"]
            short = r["accepted_mw"] < 0.5 * r["max_mw"] and r["max_mw"] > 0
            if short and r["over_cap"] > 0:          # bids existed, but above the cap: raise it
                self.cap[tech] = min(self.cap[tech] * (1 + P["cap_step"]), self.cap0[tech] * P["cap_ceiling"])
        for row in self.log[-len(CFD_TECHS):]:
            r = result.get(row["tech"], {})
            row.update(accepted_mw=r.get("accepted_mw", 0.0), clearing=r.get("clearing"),
                       over_cap=r.get("over_cap", 0), next_cap=self.cap[row["tech"]])


GOVERNMENTS: dict[str, type[Government]] = {"fixed": FixedRules, "targets": TargetTracking}


def register(name: str, cls: type[Government]) -> None:
    if not (isinstance(cls, type) and issubclass(cls, Government)):
        raise TypeError(f"{cls!r} is not a Government subclass")
    GOVERNMENTS[name] = cls


def make_government(model) -> Government:
    spec = model.scenario.get("government", "fixed")
    if isinstance(spec, type) and issubclass(spec, Government):
        return spec(model)
    if spec not in GOVERNMENTS:
        raise KeyError(f"unknown government {spec!r}; registered: {sorted(GOVERNMENTS)}")
    return GOVERNMENTS[spec](model)
