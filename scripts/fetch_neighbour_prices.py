"""Hourly day-ahead prices of GB's continental interconnector neighbours for the profile year.

Source: Energy-Charts API (Fraunhofer ISE), https://api.energy-charts.info/price — for the zones
used here the data is Bundesnetzagentur | SMARD.de, licensed CC BY 4.0. Quarter-hourly values
(from Oct 2025) are averaged to hours. Ireland (SEM) is not available under an open licence there,
so the model uses a wind-shaped proxy for it (see ukabm.data.pypsagb).

Writes data/external/neighbour_prices_<year>.csv (EUR/MWh, hourly, UTC, aligned with the hourly
profile of the same year in data/profiles/). Run:
    python scripts/fetch_neighbour_prices.py 2024
"""
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pandas as pd

ZONES = ["FR", "NL", "BE", "NO2", "DK1", "DE-LU"]
OUT = Path(__file__).resolve().parents[1] / "data" / "external"


def zone_prices(zone: str, year: int) -> pd.Series:
    url = f"https://api.energy-charts.info/price?bzn={zone}&start={year}-01-01&end={year}-12-31"
    for attempt in range(8):                 # the API limits request rates: wait and try again
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                d = json.loads(r.read())
            break
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == 7:
                raise
            time.sleep(30 * (attempt + 1))
    time.sleep(5)
    s = pd.Series(d["price"], index=pd.to_datetime(d["unix_seconds"], unit="s", utc=True), dtype=float)
    return s.resample("h").mean()


def main(year: int):
    idx = pd.date_range(f"{year}-01-01", periods=8760, freq="h", tz="UTC")
    df = pd.DataFrame({z.replace("-", "_"): zone_prices(z, year).reindex(idx) for z in ZONES})
    df = df.interpolate(limit_direction="both").round(2)
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT / f"neighbour_prices_{year}.csv", index=False)
    print(df.describe().T[["mean", "min", "max"]])


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 2024)
