"""Adapter between the ABM and PyPSA-GB (https://github.com/andrewlyden/PyPSA-GB).

Two modes:
  * `PyPSAGBData(root='/path/to/PyPSA-GB')` reads raw PyPSA-GB data files directly;
  * `PyPSAGBData()` reads the small snapshot bundled in data/pypsagb_snapshot (built by
    scripts/extract_pypsagb_snapshot.py from the same raw files), so the ABM runs without the
    5 GB PyPSA-GB clone.

What is taken from PyPSA-GB:
  - Zonal network (20 buses, 31 internal transfer links with ETYS-like capacities) -> ukabm.network
  - Interconnector register (links_future.csv) -> interconnector capacity by year
  - ESPENI half-hourly outturn -> hourly demand shape and wind/solar capacity-factor shapes
  - DUKES station coordinates -> zonal split of capacity by technology
  - GSP->zone population weights -> zonal demand split
  - Capacity Market auction parameters, CfD strike prices by round, emissions intensities
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd

SNAPSHOT = Path(__file__).resolve().parents[2] / "data" / "pypsagb_snapshot"
EXTERNAL = Path(__file__).resolve().parents[2] / "data" / "external"

# Interconnector register country -> neighbour price zone (data/external/neighbour_prices_<y>.csv).
# Ireland (SEM) has no openly licensed hourly series there; it gets a GB-wind-shaped proxy.
IC_MARKET = {"France1": "FR", "France2": "FR", "Netherlands": "NL", "Belgium": "BE", "Norway": "NO2",
             "Denmark": "DK1", "Germany": "DE_LU", "Ireland": "SEM", "Ireland2": "SEM", "N. Ireland": "SEM"}

# Corrections to commissioning years in the PyPSA-GB interconnector register (links_future.csv),
# which lists several projects as operating by 2024/25 that were not (GB peak import in 2025 was
# 9.2 GW per Elexon FUELHH vs 16.1 GW in the register). None = not expected to be built.
#   NeuConnect (DE, 1.4 GW): under construction, operation 2028 (NeuConnect; Ofgem IC cap & floor
#     handbook, Dec 2024).  GridLink (FR): "under development", 2030 (same Ofgem handbook).
#   FAB Link (FR): connection date end-2030 (Ofgem needs-case reassessment, Nov 2022).
#   NorthConnect (NO): Ofgem withdrew cap & floor in Dec 2022; Norway not approving new links.
#   Greenlink (IE): opened January 2025 (DESNZ Energy Trends, Dec 2025).
IC_COMMISSIONING_OVERRIDES = {"NeuConnect": 2028, "GridLink": 2030, "FAB Link": 2031,
                              "NorthConnect": None, "Greenlink": 2025}

DUKES_TO_TECH = {"Fossil Fuel": "ccgt", "Nuclear": "nuclear", "Bioenergy": "biomass", "Hydro": "hydro",
                 "Pumped Hydro": "pumped_hydro", "Pumped hydro": "pumped_hydro", "Solar": "solar",
                 "Wind": "wind"}


class PyPSAGBData:
    def __init__(self, root: str | os.PathLike | None = None, profile_year: int = 2024):
        self.root = Path(root) if root else None
        self.profile_year = profile_year
        if self.root is None:
            self._load_snapshot()
        else:
            self._load_raw()
        self.neighbour_price_shape = self._neighbour_shapes()

    # ------------------------------------------------------------------ raw
    def _load_raw(self):
        d = self.root / "data"
        self.buses = pd.read_csv(d / "network/zonal/buses.csv")
        links = pd.read_csv(d / "network/zonal/links.csv")
        zones = set(self.buses.name)
        self.links = links[links.bus0.isin(zones) & links.bus1.isin(zones)].reset_index(drop=True)
        ic = pd.read_csv(d / "network/zonal/links_future.csv")
        ic["year"] = pd.to_datetime(ic["installed date"], dayfirst=True).dt.year
        self.interconnectors = ic[["name", "bus0", "bus1", "p_nom", "year", "marginal_cost"]].rename(
            columns={"bus0": "country", "bus1": "zone"})
        zd = pd.read_csv(d / "network/zonal/zone_definitions.csv")
        share = zd.groupby("target_bus").population_weight.sum()
        self.zone_demand_share = (share / share.sum()).reindex(self.buses.name).fillna(0.0)
        self.profiles = self._profiles_from_espeni(d / "demand/espeni.csv")
        self.zone_tech_share = self._zone_shares(d / "generators/dukes_power_station_coordinates.csv")
        self.cm_params = pd.read_csv(d / "market/capacity_market/cm_auction_parameters.csv")
        self.cfd_strikes = pd.read_csv(d / "market/lccc/cfd_strike_prices_by_round.csv")
        self.emissions = pd.read_csv(d / "generators/emissions_intensity_by_types.csv")

    def _profiles_from_espeni(self, path) -> pd.DataFrame:
        cols = {"ELEC_elex_startTime[utc](datetime)": "t",
                "ELEC_POWER_TOTAL_ESPENI[MW](float32)": "demand",
                "ELEC_POWER_TOTAL_WIND[MW](float32)": "wind",
                "ELEC_POWER_NGEM_EMBEDDED_SOLAR_GENERATION[MW](float32)": "solar"}
        e = pd.read_csv(path, usecols=list(cols)).rename(columns=cols)
        e["t"] = pd.to_datetime(e["t"], utc=True)
        e = e[e.t.dt.year == self.profile_year].set_index("t").astype(float)
        h = e.resample("h").mean().interpolate().iloc[:8760]
        out = pd.DataFrame(index=range(len(h)))
        out["demand_mw"] = h["demand"].values
        # ASSUMPTION: capacity factors = output / (high quantile / reference CF at that quantile).
        # ESPENI has no installed-capacity series, so this normalisation is approximate.
        out["wind_cf"] = np.clip(h["wind"].values / (np.nanquantile(h["wind"], 0.999) / 0.90), 0, 1)
        out["solar_cf"] = np.clip(h["solar"].values / (np.nanquantile(h["solar"], 0.999) / 0.80), 0, 1)
        out["hour"] = h.index.hour
        out["doy"] = h.index.dayofyear
        return out

    def _zone_shares(self, path) -> pd.DataFrame:
        from pyproj import Transformer
        st = pd.read_csv(path).dropna(subset=["x_coordinate", "y_coordinate"])
        tr = Transformer.from_crs("EPSG:27700", "EPSG:4326", always_xy=True)
        lon, lat = tr.transform(st.x_coordinate.values, st.y_coordinate.values)
        b = self.buses
        d2 = (lat[:, None] - b.y.values[None]) ** 2 + ((lon[:, None] - b.x.values[None]) * 0.6) ** 2
        st["zone"] = b.name.values[d2.argmin(1)]
        st["tech"] = st.technology.map(DUKES_TO_TECH)
        tab = st.groupby(["tech", "zone"]).capacity_mw.sum().unstack(fill_value=0.0)
        tab = tab.reindex(columns=b.name, fill_value=0.0)
        return tab.div(tab.sum(1), axis=0)

    # ------------------------------------------------------------- snapshot
    def save_snapshot(self, path: Path = SNAPSHOT):
        path.mkdir(parents=True, exist_ok=True)
        self.buses.to_csv(path / "zonal_buses.csv", index=False)
        self.links.to_csv(path / "zonal_links.csv", index=False)
        self.interconnectors.to_csv(path / "interconnectors.csv", index=False)
        self.zone_demand_share.rename("share").to_csv(path / "zone_demand_share.csv", index_label="zone")
        self.profiles.round(4).to_csv(path / f"profiles_{self.profile_year}.csv", index=False)
        self.zone_tech_share.round(5).to_csv(path / "zone_tech_share.csv")
        self.cm_params.to_csv(path / "cm_auction_parameters.csv", index=False)
        self.cfd_strikes.to_csv(path / "cfd_strike_prices_by_round.csv", index=False)
        self.emissions.to_csv(path / "emissions_intensity.csv", index=False)

    def _load_snapshot(self, path: Path = SNAPSHOT):
        self.buses = pd.read_csv(path / "zonal_buses.csv")
        self.links = pd.read_csv(path / "zonal_links.csv")
        self.interconnectors = pd.read_csv(path / "interconnectors.csv")
        self.zone_demand_share = pd.read_csv(path / "zone_demand_share.csv", index_col=0)["share"]
        self.profiles = pd.read_csv(path / f"profiles_{self.profile_year}.csv")
        self.zone_tech_share = pd.read_csv(path / "zone_tech_share.csv", index_col=0)
        self.cm_params = pd.read_csv(path / "cm_auction_parameters.csv")
        self.cfd_strikes = pd.read_csv(path / "cfd_strike_prices_by_round.csv")
        self.emissions = pd.read_csv(path / "emissions_intensity.csv")

    def _neighbour_shapes(self) -> pd.DataFrame:
        """Hourly neighbour price shapes, dimensionless. Continental zones are divided by the
        capacity-weighted continental mean of the profile year (so relative levels between borders
        are kept); the SEM proxy is (1.25 - 0.75 * GB wind CF) normalised to mean 1, since Irish
        and GB wind are strongly correlated and SEM is gas-marginal most hours."""
        prices = pd.read_csv(EXTERNAL / f"neighbour_prices_{self.profile_year}.csv").iloc[:len(self.profiles)]
        caps = self.interconnector_mw_by_market(self.profile_year)
        w = pd.Series({k: v for k, v in caps.items() if k in prices.columns})
        mean = float((prices[w.index].mean() * w).sum() / w.sum())
        shape = prices / mean
        sem = 1.25 - 0.75 * self.profiles.wind_cf.values
        shape["SEM"] = sem / sem.mean()
        return shape

    # -------------------------------------------------------------- helpers
    def _ic_in_service(self, year: int) -> pd.DataFrame:
        ic = self.interconnectors
        first = ic.name.map(IC_COMMISSIONING_OVERRIDES).where(ic.name.isin(list(IC_COMMISSIONING_OVERRIDES)), ic.year)
        return ic[first.notna() & (first <= year)]

    def interconnector_mw(self, year: int) -> float:
        return float(self._ic_in_service(year).p_nom.sum())

    def interconnector_mw_by_market(self, year: int) -> dict:
        ic = self._ic_in_service(year)
        return ic.groupby(ic.country.map(IC_MARKET)).p_nom.sum().astype(float).to_dict()

    def zone_share(self, tech: str) -> pd.Series:
        key = "wind" if tech.startswith("wind") else tech
        if key in self.zone_tech_share.index:
            return self.zone_tech_share.loc[key]
        if key in ("ocgt", "gas_ccs", "h2_turbine"):
            return self.zone_tech_share.loc["ccgt"]
        if key == "battery":
            return self.zone_demand_share
        return self.zone_demand_share
