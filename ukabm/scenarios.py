"""Scenario definitions (dicts are merged into Policy/Fuels/module kwargs).

Agent traits can be idealised per scenario with `agents_ideal`: a list of trait groups whose values are
replaced by those of a social planner's agent (see IDEAL_TRAITS). The gap ladder (ukabm.gap) switches the
groups on one at a time to attribute the optimal-vs-emergent gap to its sources.
"""
import copy

from .config import SOCIAL_DISCOUNT_RATE

SCENARIOS = {
    "baseline": {},
    "high_carbon": {"policy": {"carbon_price_2050": 300.0}},
    "no_cfd": {"policy": {"cfd_enabled": False}},
    "heat_push": {"policy": {"hp_grant": 11500.0, "gas_levy_rebalancing": 25.0}},
    "no_capacity_market": {"policy": {"cm_enabled": False}},
    "high_gas": {"fuels": {"gas_adder": 15.0}},     # central path + GBP 15/MWh_th every year
}

# Trait groups and the values an idealised agent takes. Groups follow the candidate gap sources
# (deck slide 11): expectations ~ limited information, capital ~ risk and cost of capital,
# strategic ~ strategic behaviour. What remains with every group idealised is the market and plan
# design plus the agents' decision procedure itself (t+3 price forecasts, lumpy projects, sequential
# decisions) and path dependence.
IDEAL_TRAITS = {
    "expectations": {"expectation": "adaptive"},              # carbon path known, no myopia/optimism
    "capital": {"wacc": SOCIAL_DISCOUNT_RATE, "risk_aversion": 0.0, "budget_gbp": float("inf")},
    "strategic": {"markup": 0.0},
}

# Cumulative ladder from idealised agents to the full model (order matters; see docs/gap.md).
LADDER = [
    ("ideal agents", ["expectations", "capital", "strategic"]),
    ("+ expectations", ["capital", "strategic"]),
    ("+ cost of capital and risk", ["strategic"]),
    ("+ strategic mark-ups (full model)", []),
]


# Benchmarks: not policy scenarios, so not in SCENARIOS (scripts/run_scenarios.py runs SCENARIOS).
BENCHMARKS = {
    # Convergence test (README roadmap item 7): textbook conditions under which a competitive market
    # should reproduce the least-cost plan. Energy-only market (no CfD, no CM) with scarcity priced only
    # by unserved energy at VoLL (no ORDC adder), idealised firms (unbiased adaptive expectations, social
    # discount rate, no risk aversion or budget limit, no mark-up) that invest merchant in any technology
    # on lifetime price forecasts (decision_logic "expectations"), with enough decisions a year to keep up.
    "competitive_benchmark": {
        "policy": {"cfd_enabled": False, "cm_enabled": False},
        "agents_ideal": ["expectations", "capital", "strategic"],
        "decision_logic": "expectations",
        "scarcity_adder": False,
        "max_merchant_decisions": 40,
    },
}


def get_scenario(name: str) -> dict:
    return copy.deepcopy(SCENARIOS[name] if name in SCENARIOS else BENCHMARKS[name])


def with_ideal(scenario: dict, groups) -> dict:
    s = copy.deepcopy(scenario)
    s["agents_ideal"] = list(groups)
    return s
