"""Scenarios: tables of overrides on the model's defaults, read from TOML and checked on use.

The built-in scenarios and benchmarks are in ``ukabm/data/scenarios.toml``; a user file has the same
layout (``get_scenario("my_case", file="my_scenarios.toml")``). ``validate`` raises on any key the
model does not read, so a misspelt key cannot silently leave a default in place.

Agent traits can be idealised per scenario with ``agents_ideal``: a list of trait groups whose values
are replaced by those of a social planner's agent (see IDEAL_TRAITS). The gap ladder (ukabm.gap)
switches the groups on one at a time to attribute the optimal-vs-emergent gap to its sources.
"""
from __future__ import annotations

import copy
import dataclasses
import tomllib
from pathlib import Path

from .config import RESERVE, SOCIAL_DISCOUNT_RATE, Fuels, Policy

BUILTIN = Path(__file__).resolve().parent / "data" / "scenarios.toml"

# Every scenario key the model reads, with what it does. Sub-tables `policy`, `fuels` and `reserve`
# are checked against config.Policy, config.Fuels and config.RESERVE.
SCENARIO_KEYS = {
    "policy": "overrides of config.Policy fields (carbon path, CfD, Capacity Market, grants, VoLL)",
    "fuels": "overrides of config.Fuels fields (gas path or adder, other fuel prices)",
    "multienergy": "keyword arguments of the heat, gas, ev and h2 modules: {heat: {...}, ...}",
    "agents_ideal": "trait groups replaced by an idealised agent's values (IDEAL_TRAITS)",
    "decision_logic": "decision maker by name, for all firms or {firm: name} (ukabm.decisions)",
    "government": "who sets the CfD rounds: fixed | targets | least_cost | bills | political",
    "government_params": "overrides of the government's rule parameters (config.GOVERNMENT_*)",
    "cfd_pots": "fixed government: share of the round volume per technology",
    "cfd_targets_gw": "target-tracking governments: capacity target path per technology",
    "system_operator": "who sets the Capacity Market target: formula | standard",
    "system_operator_params": "overrides of config.SYSTEM_OPERATOR",
    "scarcity_adder": "ORDC-style scarcity adder in market clearing (default true)",
    "max_merchant_decisions": "merchant investment decisions per year (default 6)",
    "merchant_order": "order of firms in merchant investment: redraw (default) | fixed",
    "cm_new_chunks": "new-build projects per firm and technology offered in a CM auction (default 4)",
    "banned_techs": "technologies nobody may build",
    "base_demand_growth": "annual growth of base demand (default 0.003)",
    "ic_growth": "annual growth factor of interconnector capacity (default 1.0)",
    "locational_signal": "site new plant on zonal prices of the network stage (default false)",
    "reserve": "overrides of config.RESERVE; `scale` multiplies the requirement (0 = off)",
    "new_build_cf": "annual capacity factor of new wind and solar by online year (config.NEW_BUILD_CF)",
    "fleet": "starting fleet: table (default: data/fleet, real vintages and contracted pipeline) | random",
}
_SUBTABLES = {
    "policy": {f.name for f in dataclasses.fields(Policy)},
    "fuels": {f.name for f in dataclasses.fields(Fuels)},
    "multienergy": {"heat", "gas", "ev", "h2"},
    "reserve": set(RESERVE) | {"scale"},
}


def validate(scenario: dict) -> dict:
    """Raise ValueError if *scenario* has a key the model does not read. Returns the scenario."""
    unknown = sorted(set(scenario) - set(SCENARIO_KEYS))
    if unknown:
        raise ValueError(f"unknown scenario key(s) {unknown}; valid keys: {sorted(SCENARIO_KEYS)}")
    for table, allowed in _SUBTABLES.items():
        bad = sorted(set(scenario.get(table) or {}) - allowed)
        if bad:
            raise ValueError(f"unknown key(s) {bad} in scenario['{table}']; valid keys: {sorted(allowed)}")
    return scenario


def _year_keys(x):
    """TOML keys are strings: turn all-digit keys back into years, at any depth."""
    if isinstance(x, dict):
        return {(int(k) if isinstance(k, str) and k.isdigit() else k): _year_keys(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_year_keys(v) for v in x]
    return x


def load_scenarios(file=None) -> tuple[dict, dict]:
    """(scenarios, benchmarks) from a TOML *file* (default: the built-in file), validated."""
    with open(file or BUILTIN, "rb") as f:
        raw = _year_keys(tomllib.load(f))
    out = raw.get("scenarios", {}), raw.get("benchmarks", {})
    for group in out:
        for name, sc in group.items():
            try:
                validate(sc)
            except ValueError as e:
                raise ValueError(f"scenario '{name}' in {file or BUILTIN}: {e}") from None
    return out


SCENARIOS, BENCHMARKS = load_scenarios()

# Trait groups and the values an idealised agent takes. Groups follow the candidate gap sources
# (deck slide 11): expectations ~ limited information, capital ~ risk and cost of capital,
# strategic ~ strategic behaviour. What remains with every group idealised is the market and plan
# design plus the agents' decision procedure itself (t+3 price forecasts, lumpy projects, sequential
# decisions) and path dependence.
IDEAL_TRAITS = {
    "expectations": {"expectation": "adaptive"},              # carbon path known, no myopia/optimism
    "capital": {"wacc": SOCIAL_DISCOUNT_RATE, "risk_aversion": 0.0, "budget_gbp": float("inf"),
                "tech_hurdle": False},     # one rate for every project: the social discount rate
    "strategic": {"markup": 0.0},
}

# Cumulative ladder from idealised agents to the full model (order matters; see docs/gap.md).
LADDER = [
    ("ideal agents", ["expectations", "capital", "strategic"]),
    ("+ expectations", ["capital", "strategic"]),
    ("+ cost of capital and risk", ["strategic"]),
    ("+ strategic mark-ups (full model)", []),
]


def get_scenario(name: str, file=None) -> dict:
    """A copy of the scenario or benchmark called *name*, from the built-in file or from *file*."""
    scenarios, benchmarks = (SCENARIOS, BENCHMARKS) if file is None else load_scenarios(file)
    for group in (scenarios, benchmarks):
        if name in group:
            return copy.deepcopy(group[name])
    raise KeyError(f"unknown scenario {name!r}; available: {sorted(scenarios) + sorted(benchmarks)}")


def with_ideal(scenario: dict, groups) -> dict:
    s = copy.deepcopy(scenario)
    s["agents_ideal"] = list(groups)
    return s
