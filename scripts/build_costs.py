"""Build the model's technology cost table from DESNZ's published generation cost assumptions.

    python scripts/build_costs.py        # -> data/parameters/cost_paths.csv, prints the table

Source: data/history/desnz_generation_costs.csv, a tidy extract of the central, low and high
assumptions of DECC/BEIS/DESNZ *Electricity Generation Costs* 2013, 2016, 2020, 2023 and 2025
(Open Government Licence v3.0). Only the 2025 edition (2024 prices; projects commissioning 2030-2050)
is used for the model's costs; the earlier editions are kept for hindcasts and for the record of what
was expected at the time.

Mapping to the model (nothing here is fitted to auction results):

    capex (GBP/kW)     = pre-development + construction + infrastructure / reference plant size
    fom   (GBP/kW/yr)  = fixed O&M + insurance + connection and use-of-system charges
    hurdle rate        = the edition's technology hurdle rate (pre-tax real; CEPA 2025 for DESNZ)
    load factor, life  = as published (the load factor is reported, not used: capacity factors of new
                         wind and solar come from measured output, config.NEW_BUILD_CF)

Connection and use-of-system charges are the largest part of an offshore wind farm's fixed cost
(GBP 87/kW/yr of GBP 142/kW/yr) and were missing from the model's earlier fixed cost of GBP 60/kW/yr,
which is why its offshore bids were GBP 25-40/MWh below the AR7 result. A negative charge
(embedded gas engines, which are paid for avoiding transmission use) is set to zero.
Costs for years before 2030 are held at the 2030 value: the 2025 edition gives no earlier year.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "history" / "desnz_generation_costs.csv"
OUT = ROOT / "data" / "parameters" / "cost_paths.csv"
EDITION = "DESNZ EGC 2025"
# model technology -> technology label in the 2025 edition
LABEL = {
    "wind_offshore": "Fixed Offshore Wind",
    "wind_onshore": "Onshore Wind",
    "solar": "Large Scale Solar PV",
    "ccgt": "Gas CCGT 93% Load Factor",
    "ocgt": "Gas OCGT 300MW 5% Load Factor",
    "gas_ccs": "Gas CCUS 900MW 88% Load Factor",
    "h2_turbine": "CCHT 900MW 30% Load Factor",
}
CAPEX = ("predevelopment_cost", "construction_cost")
FOM = ("fixed_om", "insurance", "connection_use_of_system")


def build(scenario: str = "central") -> pd.DataFrame:
    d = pd.read_csv(SRC)
    d = d[(d.publication == EDITION) & (d.scenario == scenario)]
    rows = []
    for tech, label in LABEL.items():
        x = d[d.technology_label == label]
        if x.empty:
            raise SystemExit(f"{label!r} not found in {EDITION}")
        t = x.pivot_table(index="commissioning_year", columns="metric", values="value", aggfunc="first")
        size = t["reference_plant_size"] if "reference_plant_size" in t else None
        for year, r in t.iterrows():
            capex = sum(float(r.get(k, 0.0) or 0.0) for k in CAPEX)
            if size is not None and pd.notna(r.get("infrastructure_cost")) and pd.notna(size.get(year)) and size[year] > 0:
                capex += float(r["infrastructure_cost"]) / float(size[year])        # GBP thousand / MW = GBP/kW
            fom = sum(max(float(r.get(k, 0.0) or 0.0), 0.0) for k in FOM) / 1000.0  # GBP/MW/yr -> GBP/kW/yr
            rows.append(dict(tech=tech, online=int(year), capex=round(capex, 1), fom=round(fom, 2),
                             vom=float(r.get("variable_om", 0.0) or 0.0),
                             hurdle_rate=float(r["hurdle_rate"]) / 100 if pd.notna(r.get("hurdle_rate")) else float("nan"),
                             life=int(r["operating_lifetime"]) if pd.notna(r.get("operating_lifetime")) else 0,
                             load_factor=float(r["load_factor"]) / 100 if pd.notna(r.get("load_factor")) else float("nan"),
                             efficiency=float(r["efficiency"]) / 100 if pd.notna(r.get("efficiency")) else float("nan"),
                             source=f"{EDITION}, {label}, {scenario}"))
    return pd.DataFrame(rows)


def main():
    df = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    pd.set_option("display.width", 200)
    print(df.drop(columns="source").to_string(index=False))


if __name__ == "__main__":
    main()
