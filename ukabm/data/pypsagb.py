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
# Hourly demand, wind and solar profiles built from NESO and Elexon open data by
# scripts/build_profiles.py (onshore and offshore wind separately). Used when the file for the profile
# year exists; otherwise the profile in the PyPSA-GB snapshot (ESPENI, one wind shape) is used.
PROFILES = Path(__file__).resolve().parents[2] / "data" / "profiles"
# Starting fleet (vintages, zones, support) and contracted pipeline built from the DUKES station list
# and the CfD register by scripts/build_fleet.py.
FLEET = Path(__file__).resolve().parents[2] / "data" / "fleet"
# Without separate shapes (ESPENI profile), onshore and offshore wind are the one GB wind shape scaled
# by these factors (the model's original assumption).
SINGLE_WIND_SHAPE_SCALE = {"wind_onshore_cf": 0.75, "wind_offshore_cf": 1.10}
# Weights of the onshore and offshore shapes in the GB wind index `wind_cf` (c. 2024 capacities, GW),
# which the network stage uses for its wind strata and the SEM price proxy for its shape.
GB_WIND_WEIGHTS = {"wind_onshore_cf": 15.0, "wind_offshore_cf": 15.5}


def complete_profiles(prof: pd.DataFrame) -> pd.DataFrame:
    """Make sure a profile table has `wind_onshore_cf`, `wind_offshore_cf` and the GB index `wind_cf`:
    a table with one wind shape gets the two scaled copies; a table with separate shapes gets the
    capacity-weighted index."""
    prof = prof.copy()
    if "wind_onshore_cf" not in prof or "wind_offshore_cf" not in prof:
        for col, k in SINGLE_WIND_SHAPE_SCALE.items():
            prof[col] = np.clip(prof["wind_cf"].values * k, 0, 1)
    if "wind_cf" not in prof:
        w = GB_WIND_WEIGHTS
        prof["wind_cf"] = sum(prof[c].values * w[c] for c in w) / sum(w.values())
    return prof

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

# Inter-zonal capacities. The PyPSA-GB zonal network carries future (HND-era) values, e.g. 22 GW
# across the Scotland-England boundary, so the Scottish boundaries are rebuilt from boundary
# capabilities (MW, incl. HVDC) under NESO's Holistic Transition network build-out as tabulated by
# LCP Delta, "From Bottlenecks to Balance" (Mar 2026, p.58), linearly interpolated between
# 2025/2030/2035 and held after. Each boundary's AC part is carried by one zonal link = boundary
# minus the HVDC links that cross it (floor 500 MW); HVDC links are steps at target energisation:
# Caithness-Moray 1.2 GW (2019), Shetland 0.6 GW (2024), Western HVDC Hunterston-Deeside 2.25 GW
# (2018), EGL1 Torness-Hawthorn Pit 2 GW (2027), EGL2 Peterhead-Drax 2 GW (2029), EGL3/4 to
# Lincolnshire 2 x 2 GW (2031) (SSEN Transmission 2022; Ofgem ASTI 2024). EGL2-4 use the PyPSA-GB
# Z2-Z7 DC corridor.
# HVDC landings are placed by which side of each boundary they lie on, not by nearest bus.
# Hunterston and Torness are south of B5 and north of B6: the Kintyre-Hunterston cable crosses B5,
# and the Western HVDC and EGL1 reinforce B6 (SP Energy Networks, RIIO-T2 Business Plan Annex 4,
# 2019, s.4.1.1 and s.6.2). So the Western HVDC (moved from the PyPSA-GB Z3-Z9 corridor, north of
# B4) and EGL1 run from Z6, south of the modelled B5 cut, and cross B6 only.
# The Western Isles HVDC (1.8 GW, 2030) lands at Beauly, south of B0. It is represented by the
# radial PyPSA-GB Z1_4-Z1_2 link (2 GW, never binding: Z1_2 has ~50 MW of hydro and no demand).
# The PyPSA-GB Z1_3-Z1_2 corridor is closed: it would open a route around B0.
# BOUNDARY_NORTH lists the zones north of each boundary. tests/test_network.py checks that the
# links crossing each cut are exactly the AC link plus the HVDC links in BOUNDARY_LINKS.
# English links keep their PyPSA-GB capacities.
BOUNDARY_MW = {"B0": [(2025, 1800), (2030, 4700), (2035, 4600)],
               "B2": [(2025, 3500), (2030, 6000), (2035, 12000)],
               "B4": [(2025, 4000), (2030, 7300), (2035, 12000)],
               "B5": [(2025, 4300), (2030, 8300), (2035, 11700)],
               "B6": [(2025, 7000), (2030, 10200), (2035, 16800)]}
BOUNDARY_LINKS = {"B0": ("Z1_4-Z1_3", ["Z2-Z1_3"]), "B2": ("Z3-Z2", ["Z7-Z2"]), "B4": ("Z5-Z3", ["Z7-Z2"]),
                  "B5": ("Z6-Z5", ["Z7-Z2"]), "B6": ("Z7-Z6", ["Z7-Z2", "EGL1", "WesternHVDC"])}
_N2 = {"Z1_1", "Z1_2", "Z1_3", "Z1_4", "Z2"}
BOUNDARY_NORTH = {"B0": {"Z1_1", "Z1_3"}, "B2": _N2, "B4": _N2 | {"Z3", "Z4"}, "B5": _N2 | {"Z3", "Z4", "Z5"},
                  "B6": _N2 | {"Z3", "Z4", "Z5", "Z6"}}
HVDC_STEPS = {"Z2-Z1_3": [(2019, 1200)], "Z1_3-Z1_1": [(2024, 600)], "Z1_3-Z1_2": [(2018, 0)],
              "WesternHVDC": [(2018, 2250)], "EGL1": [(2025, 0), (2027, 2000)],
              "Z7-Z2": [(2025, 0), (2029, 2000), (2031, 6000)], "Z9-Z3": [(2018, 0)]}
NEW_LINKS = [dict(name="EGL1", bus0="Z6", bus1="Z7", carrier="DC", p_nom=0.0, p_min_pu=-1),
             dict(name="WesternHVDC", bus0="Z6", bus1="Z9", carrier="DC", p_nom=0.0, p_min_pu=-1)]
# Average available share of boundary capability by month (planned outages/maintenance), read from
# LCP Delta (2026, p.59; NESO day-ahead constraint flows & limits 2019-24): Scottish boundaries
# (B5 separately, it runs much lower) and English & Welsh links.
AVAIL_SCOT = [0.85, 0.86, 0.82, 0.77, 0.69, 0.67, 0.65, 0.63, 0.69, 0.77, 0.74, 0.86]
AVAIL_B5 = [0.55, 0.65, 0.54, 0.51, 0.50, 0.48, 0.52, 0.43, 0.62, 0.47, 0.48, 0.54]
AVAIL_EW = [0.93, 0.92, 0.85, 0.80, 0.80, 0.70, 0.70, 0.62, 0.83, 0.85, 0.83, 0.92]
# Year-specific extra derating of Scottish boundaries: in 2025 average availability on B2, B4 and B6
# was ~25 % below 2023 because of upgrade outages (LCP Delta 2026, p.18; NESO 2025 Annual
# Balancing Costs Report). Other years: normal availability.
SCOT_OUTAGE_DERATE = {2025: 0.76}

DUKES_TO_TECH = {"Fossil Fuel": "ccgt", "Nuclear": "nuclear", "Bioenergy": "biomass", "Hydro": "hydro",
                 "Pumped Hydro": "pumped_hydro", "Pumped hydro": "pumped_hydro", "Solar": "solar",
                 "Wind": "wind"}


class PyPSAGBData:
    def __init__(self, root: str | os.PathLike | None = None, profile_year: int = 2024,
                 profiles: str | os.PathLike | None = None):
        """*profiles*: an hourly profile file to use instead of the default for *profile_year*
        ("espeni" = the PyPSA-GB/ESPENI profile with one wind shape, the model's original input)."""
        self.root = Path(root) if root else None
        self.profile_year = profile_year
        if self.root is None:
            self._load_snapshot()
        else:
            self._load_raw()
        open_file = PROFILES / f"profiles_{profile_year}.csv"
        self.profile_source = "pypsagb"
        if profiles is not None and str(profiles) != "espeni":
            self.profiles, self.profile_source = pd.read_csv(profiles), str(profiles)
        elif profiles is None and open_file.exists():
            self.profiles, self.profile_source = self._open_profiles(open_file), "open"
        if self.profiles is None:
            raise FileNotFoundError(f"no hourly profile for {profile_year}: run scripts/build_profiles.py {profile_year}")
        self.profiles = complete_profiles(self.profiles)
        self.neighbour_price_shape = self._neighbour_shapes()

    def _open_profiles(self, path) -> pd.DataFrame:
        """The open NESO/Elexon profile of the profile year, with wind per MW of installed capacity.
        The file's wind capacity factors are per MW that a wind farm has shown it can produce; the model
        multiplies them by DESNZ's installed (nameplate) capacity, which is 2-6 % higher, so each wind
        column is scaled by that year's ratio (data/profiles/validation.csv, nameplate_factor_*)."""
        prof = pd.read_csv(path)
        check = PROFILES / "validation.csv"
        if check.exists():
            v = pd.read_csv(check).set_index("year")
            if self.profile_year in v.index:
                for kind in ("offshore", "onshore"):
                    k = float(v.loc[self.profile_year, f"nameplate_factor_{kind}"])
                    for col in [c for c in prof.columns if c.startswith(f"wind_{kind}") and c.endswith("_cf")]:
                        prof[col] = prof[col] * k
        return prof

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
        old = path / f"profiles_{self.profile_year}.csv"       # ESPENI-derived; only some years
        self.profiles = pd.read_csv(old) if old.exists() else None
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
        self.neighbour_prices_eur = prices          # observed day-ahead prices of the profile year, EUR/MWh
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

    def links_for_year(self, year: int) -> pd.DataFrame:
        """Inter-zonal links with capacities for *year* (see BOUNDARY_MW, HVDC_STEPS)."""
        links = pd.concat([self.links, pd.DataFrame(NEW_LINKS)], ignore_index=True).set_index("name")
        step = lambda pts, t=year: float(([m for y, m in pts if y <= t] or [0.0])[-1])
        for name, pts in HVDC_STEPS.items():
            links.loc[name, "p_nom"] = step(pts)
        for bnd, pts in BOUNDARY_MW.items():
            ac, hvdc = BOUNDARY_LINKS[bnd]
            ys, mw = zip(*pts)
            # AC part never shrinks when a new HVDC link energises ahead of the interpolated boundary
            links.loc[ac, "p_nom"] = max(max(float(np.interp(t, ys, mw)) - sum(step(HVDC_STEPS[h], t) for h in hvdc)
                                             for t in range(min(ys), max(year, min(ys)) + 1)), 500.0)
        return links.reset_index()

    def link_availability(self, year: int, links: pd.DataFrame, hours) -> pd.DataFrame:
        """Available share of each link's capacity in the given hours (rows) of the profile year.

        Scottish boundary links (AC and HVDC) follow AVAIL_SCOT. B5 runs lower (AVAIL_B5) but shares
        the Z7-Z2 HVDC corridor with B2/B4/B6, so its AC link is derated further until the
        available capacity across the whole B5 cut equals AVAIL_B5 x its total capability.
        """
        month = (pd.Timestamp(f"{self.profile_year}-01-01")
                 + pd.to_timedelta(self.profiles.doy.values[hours] - 1, unit="D")).month.values - 1
        scot = {ac for ac, _ in BOUNDARY_LINKS.values()} | {h for _, hv in BOUNDARY_LINKS.values() for h in hv}
        derate = SCOT_OUTAGE_DERATE.get(year, 1.0)
        out = {}
        for name in links.name:
            out[name] = np.asarray(AVAIL_SCOT)[month] * derate if name in scot else np.asarray(AVAIL_EW)[month]
        cap = links.set_index("name").p_nom
        ac, hvdc = BOUNDARY_LINKS["B5"]
        if cap[ac] > 0:
            target = np.asarray(AVAIL_B5)[month] * derate * (cap[ac] + sum(cap[h] for h in hvdc))
            out[ac] = np.clip((target - sum(out[h] * cap[h] for h in hvdc)) / cap[ac], 0.0, 1.0)
        return pd.DataFrame(out)

    def interconnector_mw(self, year: int) -> float:
        return float(self._ic_in_service(year).p_nom.sum())

    def interconnector_mw_by_market(self, year: int) -> dict:
        ic = self._ic_in_service(year)
        return ic.groupby(ic.country.map(IC_MARKET)).p_nom.sum().astype(float).to_dict()

    def interconnector_landing_share(self, year: int) -> dict:
        """Per neighbour market, the split of its in-service capacity across GB landing zones (register
        `zone` column, e.g. IFA/ElecLink/BritNed/Nemo Z15, NSL Z7, Moyle Z5)."""
        ic = self._ic_in_service(year)
        out = {}
        for mkt, g in ic.groupby(ic.country.map(IC_MARKET)):
            s = g.groupby("zone").p_nom.sum()
            out[mkt] = s / s.sum()
        return out

    def fleet_table(self, year: int) -> pd.DataFrame | None:
        """Shares of each technology's capacity by zone, vintage and support for a model starting in
        *year* (data/fleet/fleet_<year>.csv), or None if there is no table for that year."""
        f = FLEET / f"fleet_{year}.csv"
        if f.exists():
            return pd.read_csv(f, keep_default_na=False)
        later = sorted(int(p.stem.split("_")[1]) for p in FLEET.glob("fleet_*.csv") if int(p.stem.split("_")[1]) > year)
        if not later:
            return None
        # an earlier start: the plant of the next table that was already there, shares re-based
        t = pd.read_csv(FLEET / f"fleet_{later[0]}.csv", keep_default_na=False)
        t = t[t.online <= year].copy()
        t["share"] = t.mw / t.groupby("tech").mw.transform("sum")
        return t

    def pipeline_table(self, year: int) -> pd.DataFrame | None:
        """Capacity contracted but not yet built at the start of *year* (data/fleet/pipeline_<year>.csv)."""
        f = FLEET / f"pipeline_{year}.csv"
        return pd.read_csv(f) if f.exists() else None

    def zone_share(self, tech: str) -> pd.Series:
        key = "wind" if tech.startswith("wind") else tech
        if key in self.zone_tech_share.index:
            return self.zone_tech_share.loc[key]
        if key in ("ocgt", "gas_ccs", "h2_turbine"):
            return self.zone_tech_share.loc["ccgt"]
        if key == "battery":
            return self.zone_demand_share
        return self.zone_demand_share
