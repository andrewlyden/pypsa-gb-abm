"""Exogenous drivers from a named NESO Future Energy Scenarios 2025 pathway (README roadmap item 12a).

What the model does not decide follows a published pathway, chosen by the scenario key ``fes_pathway``
(default "Holistic Transition"; "none" keeps the model's earlier assumptions):

* demand other than road transport, residential heat pumps and electrolysis (industry, commerce,
  appliances, data centres, losses): its growth from 2025;
* road transport: battery electric vehicles and their electricity demand;
* electrolyser capacity connected to the grid;
* interconnector, nuclear and pumped-hydro capacity (decisions of governments and regulated schemes);
* the capacity of gas CCS and hydrogen power that the government contracts for (Dispatchable Power
  Agreements, hydrogen to power): the target of the model's tender, not committed plant.

Heat pumps are not taken from the pathway: households choose them in the model, and how far that choice
is from the pathway is a result (scripts/compare_pathways.py). Wind, solar, gas and battery capacity are
what firms, the government and the planner decide; the pathway's values are only compared with.

Data: data/fes/fes2025_drivers.csv, read from the FES 2025 Data Workbook (V005), one value per pathway
and year 2025-2050. The Ten Year Forecast ends in 2035 and is held flat after.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

FILE = Path(__file__).resolve().parents[1] / "data" / "fes" / "fes2025_drivers.csv"
DEFAULT = "Holistic Transition"
PATHWAYS = ("Holistic Transition", "Electric Engagement", "Hydrogen Evolution", "Falling Behind", "Ten Year Forecast")


@lru_cache(maxsize=1)
def _table() -> pd.DataFrame:
    return pd.read_csv(FILE, keep_default_na=False)


class Drivers:
    """One pathway's series, interpolated by year (flat before the first and after the last year)."""

    def __init__(self, pathway: str = DEFAULT):
        if pathway not in PATHWAYS:
            raise KeyError(f"unknown FES pathway {pathway!r}; available: {list(PATHWAYS)} or 'none'")
        self.pathway = pathway
        t = _table()
        t = t[t.pathway == pathway]
        self._s = {name: g.set_index("year").value.astype(float).sort_index() for name, g in t.groupby("series")}

    def value(self, series: str, year: float) -> float:
        s = self._s[series]
        return float(np.interp(year, s.index.values, s.values))

    # ------------------------------------------------------------------ demand
    def other_demand_twh(self, year: float) -> float:
        """System demand less road transport, residential heat pumps and networked electrolysis."""
        return (self.value("demand_total_system", year) - self.value("demand_road_transport", year)
                - self.value("demand_residential_heat_pumps", year) - self.value("demand_networked_electrolysis", year))

    def other_demand_index(self, year: float, base: int = 2025) -> float:
        """Growth of that demand since *base* (1.0 in the base year and before it)."""
        return 1.0 if year <= base else self.other_demand_twh(year) / self.other_demand_twh(base)

    def ev_twh(self, year: float) -> float:
        return self.value("demand_road_transport", year)

    def ev_stock(self, year: float) -> float:
        return self.value("ev_bev_total", year)

    # ---------------------------------------------------------------- capacity, MW
    def electrolyser_mw(self, year: float) -> float:
        return 1000 * self.value("capacity_electrolyser_grid", year)

    def interconnector_mw(self, year: float) -> float:
        return 1000 * self.value("capacity_interconnector", year)

    def nuclear_mw(self, year: float) -> float:
        return 1000 * self.value("capacity_nuclear", year)

    def pumped_hydro_mw(self, year: float) -> float:
        return 1000 * self.value("capacity_pumped_hydro", year)

    def dispatchable_mw(self, tech: str, year: float) -> float:
        """The pathway's gas CCS or hydrogen power capacity (model technologies gas_ccs, h2_turbine)."""
        return 1000 * self.value({"gas_ccs": "capacity_gas_ccs", "h2_turbine": "capacity_hydrogen_power"}[tech], year)

    def target_gw(self, tech: str) -> dict:
        """The pathway's capacity of wind_offshore, wind_onshore or solar by year (the government's target path)."""
        name = {"wind_offshore": "capacity_offshore_wind", "wind_onshore": "capacity_onshore_wind", "solar": "capacity_solar"}[tech]
        s = self._s[name]
        return {int(y): float(v) for y, v in s.items()}


def make(scenario: dict) -> Drivers | None:
    """The drivers of *scenario* (``fes_pathway``), or None for "none"."""
    name = scenario.get("fes_pathway", DEFAULT)
    return None if name in (None, "none") else Drivers(name)
