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
CONSTRAINTS = OUTTURN.with_name("gb_constraints.csv")   # hand-entered from cited reports

# (label, model column or callable on the annual record, outturn column)
METRICS = [
    # the model clears a day-ahead market: the day-ahead baseload price is its like-for-like comparator
    ("price, mean vs day-ahead baseload (GBP/MWh)", "price_mean", "power_day_ahead_nominal"),
    ("price, time-weighted mean vs MID (GBP/MWh)", "price_mean", "price_mid_mean"),
    # not like-for-like: the model weights by GB demand, MID by its own traded volume
    ("price, model demand-weighted vs MID volume-weighted (GBP/MWh)", "price_twa", "price_mid_volume_weighted"),
    ("price p05 (GBP/MWh)", "price_p05", "price_mid_p05"),
    ("price p50 (GBP/MWh)", "price_p50", "price_mid_p50"),
    ("price p95 (GBP/MWh)", "price_p95", "price_mid_p95"),
    ("negative-price hours", "hours_negative", "price_mid_negative_hours"),
    ("carbon intensity, NESO basis (g/kWh)", "intensity_neso_g_kwh", "ci_neso_genweighted"),
    ("carbon intensity, NESO basis, after BM redispatch (g/kWh)", "intensity_neso_post_bm_g_kwh", "ci_neso_genweighted"),
    ("carbon intensity, direct combustion (g/kWh)", "intensity_g_kwh", None),
    ("constraint cost (GBP bn)", "constraint_cost_bn", "constraint_cost_bn"),
    ("constraint cost excl. BM premia (GBP bn)", "constraint_cost_bn",
     lambda o: o["constraint_cost_bn"] - o["constraint_premia_bn"]),
    ("renewable curtailment in BM (TWh)", "curtailment_twh", "renewable_turndown_twh"),
    ("gas (CCGT+OCGT) (TWh)", lambda r: r["gen_ccgt"] + r["gen_ocgt"] + r.get("gen_gas_ccs", 0.0), "gen_gas"),
    ("wind and solar, available (TWh)", lambda r: r["gen_wind_onshore"] + r["gen_wind_offshore"] + r["gen_solar"],
     lambda o: o["gen_wind"] + o["gen_solar"] + o.get("wind_turned_down_twh", float("nan"))),
    ("nuclear (TWh)", "gen_nuclear", "gen_nuclear"),
    ("wind incl. embedded (TWh)", lambda r: r["gen_wind_onshore"] + r["gen_wind_offshore"], "gen_wind"),
    ("gas after BM redispatch (TWh)", lambda r: r["gen_ccgt"] + r["gen_ocgt"] + r["bm_net_ccgt"] + r["bm_net_ocgt"],
     "gen_gas"),
    ("wind after BM redispatch (TWh)", lambda r: r["gen_wind_onshore"] + r["gen_wind_offshore"]
     + r["bm_net_wind_onshore"] + r["bm_net_wind_offshore"], "gen_wind"),
    ("solar (TWh)", "gen_solar", "gen_solar"),
    ("biomass (TWh)", "gen_biomass", "gen_biomass"),
    ("hydro (TWh)", "gen_hydro", "gen_hydro"),
    # NESO's STORAGE is the pumped-storage fleet only; batteries are not in the mix
    ("pumped storage discharge (TWh)", "gen_pumped_hydro", "gen_storage"),
    ("coal (TWh)", lambda r: r.get("gen_coal", 0.0), "gen_coal"),
    ("other (CHP, waste, oil) (TWh)", lambda r: r.get("gen_other", 0.0), "gen_other"),
    ("imports (TWh)", "gen_imports", "ic_imports_twh"),
    ("exports (TWh)", "export_twh", "ic_exports_twh"),
    ("net imports (TWh)", lambda r: r["gen_imports"] - r["export_twh"], "ic_net_imports_twh"),
    ("total supply incl. imports (TWh)", "gen_total", "gen_total"),
]


def load_outturn() -> pd.DataFrame:
    """Outturn by year: the generation mix, prices and flows (scripts/fetch_outturn.py), constraint
    costs, the day-ahead baseload price (data/history/annual_inputs.csv) and the wind turned down in the
    Balancing Mechanism (data/profiles/validation.csv), which the model's wholesale stage has not yet removed."""
    out = pd.read_csv(OUTTURN, index_col="year")
    con = pd.read_csv(CONSTRAINTS, index_col="year").drop(columns="source")
    out = out.join(con, how="left")
    hist = OUTTURN.parents[1] / "history" / "annual_inputs.csv"
    if hist.exists():
        out = out.join(pd.read_csv(hist, index_col="year")[["power_day_ahead_nominal"]], how="left")
    val = OUTTURN.parents[1] / "profiles" / "validation.csv"
    if val.exists():
        v = pd.read_csv(val, index_col="year")
        out = out.join((v["turned_down_offshore_twh"] + v["turned_down_onshore_twh"]).rename("wind_turned_down_twh"), how="left")
    return out


def compare(record: pd.Series | dict, year: int) -> pd.DataFrame:
    """Table of model vs outturn for one year. *record* is a row of GBMarketModel.results()."""
    r = dict(record)
    out = load_outturn().loc[year]
    rows = []
    for label, mcol, ocol in METRICS:
        mv = mcol(r) if callable(mcol) else r.get(mcol, np.nan)
        ov = ocol(out) if callable(ocol) else out.get(ocol, np.nan) if ocol else np.nan
        rows.append(dict(metric=label, model=float(mv), outturn=float(ov), diff=float(mv - ov)))
    return pd.DataFrame(rows).set_index("metric")
