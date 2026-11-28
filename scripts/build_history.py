"""Build the model's annual historical inputs from the sourced series in data/history/sources/.

    python scripts/build_history.py     # -> data/history/annual_inputs.csv, data/history/gb_capacity.csv

gb_capacity.csv: GB installed capacity (MW) at the end of each year by technology, from
sources/capacity_by_year.csv (DESNZ, DUKES 2026 Table 5.12 for GB by network; Table 5.16 for UK
grid-scale batteries; Table 5.13A for interconnectors).

One row per year 2010-2025: wholesale gas (NBP day-ahead), coal (delivered to major power producers),
the carbon price a GB generator paid (EU ETS allowance to 2020, UK ETS from 2021, plus Carbon Price
Support) and the day-ahead baseload electricity price, each in money of the day and in 2024 prices.
The model uses the 2024-price columns for years before its forward paths start (ukabm.config), and the
money-of-the-day columns when one historical year is run to be compared with that year's outturn.

Sources (all read from the primary tables; see data/history/README.md):
* gas, electricity: Ofgem data portal, wholesale market indicators (day-ahead contracts, annual means).
* coal: DESNZ Quarterly Energy Prices table 3.2.1 (fuel purchased by major power producers).
* carbon to 2023: DESNZ Energy and Emissions Projections 2023-2050, Annex M (traded allowance price, and
  the same plus Carbon Price Support, 2023 prices). 2024 and 2025: UK ETS Authority, average December
  futures price over the 12 months to 11 November (the civil-penalty carbon price), plus the Carbon
  Price Support rate of GBP 18/tCO2.
* deflator: the GDP deflator implied by table 3.2.1's nominal and real columns.
* gbp_per_eur: European Central Bank reference rate, annual average (to convert neighbours' prices).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "history" / "sources" / "prices.csv"
OUT = ROOT / "data" / "history" / "annual_inputs.csv"
CPS = 18.0     # GBP/tCO2, Carbon Price Support rate since 2016-17


def series(d, commodity, name, unit, base=None):
    x = d[(d.commodity == commodity) & (d.series == name) & (d.unit == unit)]
    if base is not None:
        x = x[x.price_base.fillna("").str.startswith(base)]
    return x.set_index("year").value.astype(float).sort_index()


def build() -> pd.DataFrame:
    d = pd.read_csv(SRC)
    nominal = series(d, "gas", "purchased_by_major_power_producers", "GBP/MWh_th", "nominal")
    real25 = series(d, "gas", "purchased_by_major_power_producers", "GBP/MWh_th", "real")
    defl = (nominal / real25).dropna()            # GDP deflator, 2025 = 1
    out = pd.DataFrame(index=range(2010, 2026))
    out.index.name = "year"
    out["deflator_2024"] = defl / defl.loc[2024]
    out["gas_nominal"] = series(d, "gas", "nbp_day_ahead", "GBP/MWh_th")
    out["coal_nominal"] = series(d, "coal", "purchased_by_major_power_producers", "GBP/MWh_th", "nominal")
    out["power_day_ahead_nominal"] = series(d, "electricity", "day_ahead_baseload", "GBP/MWh")
    carbon23 = series(d, "carbon", "traded_price_plus_carbon_price_support", "GBP/tCO2")      # 2023 prices
    out["carbon_nominal"] = carbon23 * out["deflator_2024"] / out.loc[2023, "deflator_2024"]
    uka = series(d, "carbon", "uka_dec_futures_average_12m_to_11_nov", "GBP/tCO2")
    for y in (2024, 2025):
        out.loc[y, "carbon_nominal"] = uka.loc[y] + CPS
    for k in ("gas", "coal", "power_day_ahead", "carbon"):
        out[f"{k}_2024"] = out[f"{k}_nominal"] / out["deflator_2024"]
    out = out.round(3)
    out["gbp_per_eur"] = pd.read_csv(SRC.with_name("ecb_gbp_per_eur.csv")).set_index("year").gbp_per_eur.round(4)
    return out


def build_capacity() -> pd.DataFrame:
    c = pd.read_csv(SRC.with_name("capacity_by_year.csv"))
    gb = c[(c.geography == "GB") & (c.connection == "all") & (c.capacity_basis == "installed (end December)")]
    keep = {"wind_offshore": "wind_offshore", "wind_onshore": "wind_onshore", "solar": "solar", "ccgt": "ccgt",
            "ocgt_other_gas": "ocgt", "coal": "coal", "oil": "oil", "biomass": "bioenergy_all", "hydro": "hydro",
            "pumped_hydro": "pumped_hydro", "other_fuels_waste": "other_fuels"}
    x = gb[gb.technology.isin(keep)].copy()
    x["tech"] = x.technology.map(keep)
    x = x.groupby(["year", "tech"], as_index=False).value.sum()
    nuclear = gb[gb.technology == "nuclear"].groupby("year", as_index=False).value.sum().assign(tech="nuclear")
    tb = c[(c.geography == "GB") & (c.connection == "transmission") & (c.technology == "biomass")
           & (c.capacity_basis == "installed (end December)")][["year", "value"]].assign(tech="biomass_transmission")
    battery = c[(c.technology == "battery") & (c.geography == "UK")][["year", "value"]].assign(tech="battery_uk")
    ic = c[(c.technology == "interconnector") & c.source_category.str.contains("incl. Moyle")][["year", "value"]].assign(tech="interconnector")
    out = pd.concat([x, nuclear, tb, battery, ic]).rename(columns={"value": "mw"}).sort_values(["tech", "year"])
    out["mw"] = out.mw.round(1)
    return out[["year", "tech", "mw"]]


def main():
    build_capacity().to_csv(OUT.with_name("gb_capacity.csv"), index=False)
    df = build()
    df.to_csv(OUT)
    pd.set_option("display.width", 200)
    print(df.to_string())


if __name__ == "__main__":
    main()
