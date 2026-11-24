"""Scenario definitions (dicts are merged into Policy/Fuels/module kwargs)."""
import copy

SCENARIOS = {
    "baseline": {},
    "high_carbon": {"policy": {"carbon_price_2050": 300.0}},
    "no_cfd": {"policy": {"cfd_enabled": False}},
    "heat_push": {"policy": {"hp_grant": 11500.0, "gas_levy_rebalancing": 25.0}},
    "no_capacity_market": {"policy": {"cm_enabled": False}},
    "high_gas": {"fuels": {"gas_2025": 45.0, "gas_2050": 45.0}},
}


def get_scenario(name: str) -> dict:
    return copy.deepcopy(SCENARIOS[name])
