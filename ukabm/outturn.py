"""Comparison of model output with GB outturn (data/outturn/gb_annual_outturn.csv).

The outturn file is built from NESO's historic generation mix (generation by fuel incl. embedded
wind/solar estimates, NESO carbon intensity) and Elexon (MID price, interconnector flows); see
scripts/fetch_outturn.py.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

OUTTURN = Path(__file__).resolve().parents[1] / "data" / "outturn" / "gb_annual_outturn.csv"

# (label, model column or callable on the annual record, outturn column)
METRICS = [
    ("price, demand-weighted (GBP/MWh)", "price_twa", "price_mid_volume_weighted"),
    ("price, time-weighted mean (GBP/MWh)", "price_mean", "price_mid_mean"),
    ("price p05 (GBP/MWh)", "price_p05", "price_mid_p05"),
    ("price p50 (GBP/MWh)", "price_p50", "price_mid_p50"),
    ("price p95 (GBP/MWh)", "price_p95", "price_mid_p95"),
    ("negative-price hours", "hours_negative", "price_mid_negative_hours"),
    ("carbon intensity, NESO basis (g/kWh)", "intensity_neso_g_kwh", "ci_neso_genweighted"),
    ("carbon intensity, direct combustion (g/kWh)", "intensity_g_kwh", None),
    ("gas (CCGT+OCGT) (TWh)", lambda r: r["gen_ccgt"] + r["gen_ocgt"] + r.get("gen_gas_ccs", 0.0), "gen_gas"),
    ("nuclear (TWh)", "gen_nuclear", "gen_nuclear"),
    ("wind incl. embedded (TWh)", lambda r: r["gen_wind_onshore"] + r["gen_wind_offshore"], "gen_wind"),
    ("solar (TWh)", "gen_solar", "gen_solar"),
    ("biomass (TWh)", "gen_biomass", "gen_biomass"),
    ("hydro (TWh)", "gen_hydro", "gen_hydro"),
    ("storage discharge (TWh)", lambda r: r["gen_battery"] + r["gen_pumped_hydro"], "gen_storage"),
    ("other (CHP, waste, oil) (TWh)", lambda r: 0.0, "gen_other"),
    ("imports (TWh)", "gen_imports", "ic_imports_twh"),
    ("exports (TWh)", "export_twh", "ic_exports_twh"),
    ("net imports (TWh)", lambda r: r["gen_imports"] - r["export_twh"], "ic_net_imports_twh"),
    ("total supply incl. imports (TWh)", "gen_total", "gen_total"),
]


def load_outturn() -> pd.DataFrame:
    return pd.read_csv(OUTTURN, index_col="year")


def compare(record: pd.Series | dict, year: int) -> pd.DataFrame:
    """Table of model vs outturn for one year. *record* is a row of GBMarketModel.results()."""
    r = dict(record)
    out = load_outturn().loc[year]
    rows = []
    for label, mcol, ocol in METRICS:
        mv = mcol(r) if callable(mcol) else r.get(mcol, np.nan)
        ov = out[ocol] if ocol else np.nan
        rows.append(dict(metric=label, model=float(mv), outturn=float(ov), diff=float(mv - ov)))
    return pd.DataFrame(rows).set_index("metric")
