"""System-cost accounting shared by the agent-based run, the planner benchmark and the evaluator.

System cost is a resource cost for GB, in GBP/yr, the same definition for every run:

    capex     annuity of new-build capital (units online after the model start year) at the social
              discount rate, while the unit is active; the pre-2025 fleet is sunk and excluded
    fom       fixed O&M of every active unit
    fuel      fuel burnt (incl. VOM of thermal and storage plant)
    carbon    CO2 emitted x carbon price (the carbon price stands in for the social cost of carbon)
    trade     imports x import offer price - exports x export bid price
    unserved  unserved energy x VoLL
    h2_value  minus electrolyser consumption x its willingness to pay (value of the hydrogen made)

Transfers (CfD and RO payments, Capacity Market payments, scarcity rents, mark-ups) are not costs and
cancel out. Constraint (redispatch) cost is not included yet: both runs are costed copperplate.
"""
from __future__ import annotations

from dataclasses import dataclass

from .config import TECHS, SOCIAL_DISCOUNT_RATE

COMPONENTS = ("capex", "fom", "fuel", "carbon", "trade", "unserved", "h2_value")


def crf(rate: float, life: int) -> float:
    """Capital recovery factor."""
    return rate / (1 - (1 + rate) ** -life) if rate > 0 else 1.0 / life


@dataclass
class Unit:
    """Minimal plant description used by the planner and evaluator (ukabm.agents.Plant also fits)."""
    tech: str
    mw: float
    online: int
    retire: int
    efficiency: float | None = None
    availability: float | None = None

    def active(self, year):
        return self.online <= year <= self.retire


def fixed_costs(units, year: int, start: int, rate: float = SOCIAL_DISCOUNT_RATE) -> dict:
    """Capex annuity (new build only) and fixed O&M of the units active in *year* (GBP/yr)."""
    capex = fom = 0.0
    for u in units:
        t = TECHS[u.tech]
        if u.active(year):
            fom += t.fom * 1000 * u.mw
        # capital is sunk: the annuity runs over the economic life even if the plant closes early
        if u.online > start and u.online <= year <= u.online + t.life - 1:
            capex += t.capex * 1000 * u.mw * crf(rate, t.life)
    return {"capex": capex, "fom": fom}


def variable_cost(tech: str, efficiency: float | None, mwh: float, year: int, fuels, policy) -> dict:
    """Fuel (incl. VOM) and carbon cost of *mwh* of output (GBP)."""
    t = TECHS[tech]
    if t.fuel is None:
        return {"fuel": t.vom * mwh, "carbon": 0.0}
    eff = efficiency or t.efficiency
    return {"fuel": (fuels.price(t.fuel, year) / eff + t.vom) * mwh,
            "carbon": t.co2_t_per_mwh_fuel * policy.carbon_price(year) / eff * mwh}


def total(costs: dict) -> float:
    return float(sum(costs.get(k, 0.0) for k in COMPONENTS))


def present_value(annual: dict, rate: float = SOCIAL_DISCOUNT_RATE, base: int = 2025, step: int = 1) -> float:
    """PV at *base* of {year: GBP/yr}. With step > 1 each value stands for *step* years from its year."""
    return float(sum(v * sum((1 + rate) ** -(y + k - base) for k in range(step)) for y, v in annual.items()))
