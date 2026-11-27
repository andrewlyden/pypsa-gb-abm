"""Build the GB annual outturn reference used to calibrate / validate the ABM.

Sources (all public, no key needed):
  * NESO "Historic generation mix & carbon intensity" (df_fuel_ckan.csv, half-hourly, GB,
    transmission + NESO-estimated embedded wind/solar; CI on NESO's operational basis:
    CCGT 394, OCGT 651, biomass 120, other 300 g/kWh, imports per-country factors)
    https://www.neso.energy/data-portal/historic-generation-mix
  * Elexon Insights API, Market Index Data (MID, APXMIDP provider) -> day-ahead/within-day price
  * Elexon Insights API, FUELHH -> signed interconnector flows (imports +, exports -) and the
    CCGT / OCGT split of gas generation

Writes data/outturn/gb_annual_outturn.csv (one row per year). Run:
    python scripts/fetch_outturn.py 2024 2025
"""
from __future__ import annotations

import io
import json
import sys
import urllib.request
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

NESO_MIX = ("https://api.neso.energy/dataset/88313ae5-94e4-4ddc-a790-593554d8c6b9/resource/"
            "f93d1835-75bc-43e5-84ad-12472b180a98/download/df_fuel_ckan.csv")
ELEXON = "https://data.elexon.co.uk/bmrs/api/v1"
OUT = Path(__file__).resolve().parents[1] / "data" / "outturn" / "gb_annual_outturn.csv"


def _get(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=120) as r:
        return r.read()


def _chunks(year: int, days: int):
    d = date(year, 1, 1)
    while d.year == year:
        e = min(d + timedelta(days=days), date(year + 1, 1, 1))
        yield d, e
        d = e


def neso_mix(years) -> pd.DataFrame:
    d = pd.read_csv(io.BytesIO(_get(NESO_MIX)), parse_dates=["DATETIME"])
    rows = []
    for y in years:
        x = d[d.DATETIME.dt.year == y]
        twh = lambda c: x[c].sum() / 2 / 1e6   # half-hourly MW -> TWh
        rows.append(dict(
            year=y, gen_gas=twh("GAS"), gen_coal=twh("COAL"), gen_nuclear=twh("NUCLEAR"),
            gen_wind=twh("WIND") + twh("WIND_EMB"), gen_wind_embedded=twh("WIND_EMB"),
            gen_hydro=twh("HYDRO"), gen_imports=twh("IMPORTS"), gen_biomass=twh("BIOMASS"),
            gen_other=twh("OTHER"), gen_solar=twh("SOLAR"), gen_storage=twh("STORAGE"),
            gen_total=twh("GENERATION"),
            ci_neso_mean=x.CARBON_INTENSITY.mean(),
            ci_neso_genweighted=(x.CARBON_INTENSITY * x.GENERATION).sum() / x.GENERATION.sum(),
            peak_generation_gw=x.GENERATION.max() / 1e3))
    return pd.DataFrame(rows).set_index("year")


def elexon_mid(year: int) -> dict:
    recs = []
    for a, b in _chunks(year, 7):
        url = (f"{ELEXON}/balancing/pricing/market-index?from={a}T00:00Z&to={b}T00:00Z"
               f"&dataProviders=APXMIDP&format=json")
        recs += json.loads(_get(url))["data"]
    m = pd.DataFrame(recs).drop_duplicates("startTime")
    m = m[pd.to_datetime(m.startTime).dt.year == year]
    m = m[m.volume > 0]   # MID periods with no trades are reported as price 0
    q = m.price.quantile([0.05, 0.25, 0.5, 0.75, 0.95])
    return dict(price_mid_mean=m.price.mean(),
                price_mid_volume_weighted=(m.price * m.volume).sum() / m.volume.sum(),
                price_mid_negative_hours=(m.price < 0).sum() / 2, price_mid_max=m.price.max(),
                price_mid_p05=q[0.05], price_mid_p25=q[0.25], price_mid_p50=q[0.5],
                price_mid_p75=q[0.75], price_mid_p95=q[0.95])


def elexon_fuelhh(year: int) -> dict:
    recs = []
    for a, b in _chunks(year, 7):   # API limit: 7 days inclusive
        url = (f"{ELEXON}/datasets/FUELHH?settlementDateFrom={a}&settlementDateTo={b - timedelta(days=1)}"
               f"&format=json")
        recs += json.loads(_get(url))["data"]
    f = pd.DataFrame(recs).drop_duplicates(["startTime", "fuelType"])
    f = f[pd.to_datetime(f.settlementDate).dt.year == year]
    ic = f[f.fuelType.str.startswith("INT")].pivot(index="startTime", columns="fuelType", values="generation")
    twh = lambda s: s.sum() / 2 / 1e6
    by = f.groupby("fuelType").generation.sum() / 2 / 1e6
    return dict(ic_imports_twh=twh(ic.clip(lower=0).sum(axis=1)), ic_exports_twh=twh((-ic).clip(lower=0).sum(axis=1)),
                ic_net_imports_twh=twh(ic.sum(axis=1)),
                fuelhh_ccgt_twh=by.get("CCGT", 0.0), fuelhh_ocgt_twh=by.get("OCGT", 0.0),
                fuelhh_ic_peak_import_gw=ic.clip(lower=0).sum(axis=1).max() / 1e3)


def main(years):
    df = neso_mix(years)
    for y in years:
        for k, v in {**elexon_mid(y), **elexon_fuelhh(y)}.items():
            df.loc[y, k] = v
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.round(3).to_csv(OUT)
    print(df.T)


if __name__ == "__main__":
    main([int(a) for a in sys.argv[1:]] or [2024, 2025])
