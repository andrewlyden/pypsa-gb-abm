"""Build the hourly GB demand, wind and solar profiles of one or more weather years from open data.

    python scripts/build_profiles.py 2024            # one weather year
    python scripts/build_profiles.py 2021 2022 2023  # several

For each year it prints the checks against independent figures and, if they pass, writes to data/profiles/

    profiles_<year>.csv            the hourly profile (8,760 rows)
    wind_units_<year>.csv          every wind BM unit: type, region, capacity, output, capacity factor
    wind_cf_by_vintage_<year>.csv  capacity factor by type and vintage band of the units complete all year
    validation.csv                 the check figures, one row per year

Sources (public APIs, no key; licences and attribution in data/profiles/README.md):

* NESO "Historic Demand Data" (half-hourly): national demand ND, transmission system demand TSD,
  interconnector flows, NESO's estimates of embedded wind and solar generation and of their capacity.
* NESO "Historic generation mix" (half-hourly): GB generation by fuel including imports and embedded
  wind and solar. Used for the demand level and to check the wind energy.
* Elexon Insights API
  - reference/bmunits/all: the BM units, their fuel type, GSP group, registered generation capacity;
  - IGCPU (B1420) "Installed generation capacity per unit": installed capacity, onshore / offshore;
  - B1610 "Actual generation output per generation unit": half-hourly metered volume of every wind
    BM unit and of the pumped-storage units;
  - BOAV "Bid-offer acceptance volumes" (settlement): the volume by which each unit was turned down
    (or up) in the Balancing Mechanism, per acceptance and half hour.
* Two small files kept with the data: wind_units_manual.csv (hand-made unit classifications and offshore
  commissioning years, a source per row) and benchmarks_desnz.csv (DESNZ Energy Trends table 6.1).

Definitions
-----------
demand_mw
    GENERATION (generation mix: all GB generation + imports, including embedded wind and solar)
    - interconnector exports (negative flows in the demand data)
    - pumped-storage pumping (net metered import of the pumped-storage BM units, B1610).
    This is the demand that the generation in the mix served, so a model calibrated against the mix
    balances; the model adds exports and storage charging itself. The mix counts pumped storage as
    the net output of the fleet floored at zero, so pumping is the fleet's net import. Battery
    charging is not removed: the mix has net battery discharge under OTHER, and no data on the
    charging is used here.
demand_nd_embedded_mw
    ND + embedded wind + embedded solar (the narrower NESO definition; excludes station load).
solar_cf
    embedded solar generation / embedded solar capacity (NESO's own estimates).
wind_*_cf
    *available* output per MW of capacity. For each wind BM unit and half hour

        available = metered output (B1610) + volume turned down in the Balancing Mechanism (BOAV)

    where the turned-down volume is minus the sum of the accepted volumes of the unit's negative
    bid-offer pairs (bids, net of the offers that undo them). Accepted volumes are measured from the
    unit's final physical notification, i.e. the operator's own forecast of its output, so during
    curtailment the available output is that forecast.
wind_offshore_cf, wind_offshore_{scot,ew}_cf
    sum of available output / sum of capacity over the offshore units (of the region).
wind_onshore_cf
    the same over the onshore units together with NESO's embedded wind (wind farms without transmission
    metering): (unit output + embedded generation) / (unit capacity + embedded capacity).
wind_onshore_scot_cf
    the Scottish onshore BM units (most of the Scottish onshore fleet).
wind_onshore_ew_cf
    the onshore BM units in England & Wales together with NESO's embedded wind. Only two or three
    onshore wind farms in England & Wales are BM units, and NESO does not publish embedded wind by
    region, so this series is in effect the GB embedded fleet, part of which is in Scotland. The two
    regional series partition the fleet of wind_onshore_cf.

Capacity of a unit (MW, per half hour) -- see unit_capacity():
    Two capacities are published per unit, IGCPU "installed capacity" and the "generation capacity"
    of the BM unit list. Neither is reliable (Moray East: 1,200 and 900 MW for a 950 MW wind farm;
    Seagreen: 1,130 and 1,773 MW; Thanet: 518 MW for 300 MW), so each is tested against the unit's
    own peak output P, the 99.9th percentile of its half-hourly output since 1 October of the previous
    year. The capacity of a complete unit is the published number closest to P if P is between 90%
    and 103% of it; otherwise P / PEAK_SHARE, where PEAK_SHARE is the median of P / published capacity
    over the units whose published number was kept (about 0.98).
    Commissioning: a unit has no capacity before it first generates. While the highest output it has
    shown so far (in earlier Decembers, since 1 October of the previous year, and looking
    LOOKAHEAD_DAYS ahead) is below COMPLETE_SHARE x P it is taken to be part-built and its capacity is
    that highest output / PEAK_SHARE.

Regions: Scotland = GSP groups North Scotland and South Scotland. Transmission-connected units have no
GSP group; they are placed by their transmission loss factor, which Elexon sets per GSP-group zone, so
a unit belongs to the zone whose embedded units carry the same factor. This is the zone of the grid
connection (Robin Rigg, in Scottish waters, connects in Cumbria and counts as England & Wales).

All series are hourly means of the half hours, in UTC, for the first 8,760 hours of the year.
The raw downloads are cached under data/profiles/raw/ (not committed); delete a file to refresh it.
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "profiles"
RAW = OUT / "raw"
ELEXON = "https://data.elexon.co.uk/bmrs/api/v1"
NESO_DEMAND = "https://api.neso.energy/api/3/action/datapackage_show?id=historic-demand-data"
NESO_MIX = ("https://api.neso.energy/dataset/88313ae5-94e4-4ddc-a790-593554d8c6b9/resource/"
            "f93d1835-75bc-43e5-84ad-12472b180a98/download/df_fuel_ckan.csv")
UA = {"User-Agent": "ukabm-build-profiles"}
PAUSE = 0.25                       # seconds between API requests
FIRST_YEAR = 2020                  # the API has B1610 from 1 Feb 2019; the capacity rule needs a look-back
MANUAL = OUT / "wind_units_manual.csv"
DESNZ = OUT / "benchmarks_desnz.csv"

# capacity rule (see module docstring)
FIRST_MW = 0.5                     # output above which a unit counts as generating
PEAK_QUANTILE = 0.999              # "peak" of a unit = this quantile of its half-hourly output
ACCEPT = (0.90, 1.03)              # peak / published capacity for which the published number is kept
COMPLETE_SHARE = 0.90              # highest output so far / peak above which a unit is complete
LOOKAHEAD_DAYS = 30                # "so far" looks this far ahead

# a year is written only if it passes these checks against independent figures
TOL_ENERGY = 0.05                  # metered wind energy vs NESO generation mix (relative)
TOL_LOAD_FACTOR = 0.03             # metered capacity factor vs DESNZ load factor (absolute)


# ---------------------------------------------------------------------------------------------------
# downloads
# ---------------------------------------------------------------------------------------------------
def _get(url: str, tries: int = 6) -> bytes:
    """GET with retries and exponential back-off (client errors other than 429 are not retried)."""
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=180) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504) or k == tries - 1:
                raise
        except Exception:
            if k == tries - 1:
                raise
        time.sleep(3 * 2 ** k)
    raise RuntimeError(url)


def neso_demand(year: int) -> pd.DataFrame:
    """Half-hourly NESO demand data of *year*, indexed by UTC period start."""
    f = RAW / f"neso_demanddata_{year}.csv"
    if not f.exists():
        pkg = json.loads(_get(NESO_DEMAND))["result"]["resources"]
        url = next(r["path"] for r in pkg if r["name"] == f"historic_demand_data_{year}")
        RAW.mkdir(parents=True, exist_ok=True)
        f.write_bytes(_get(url))
    d = pd.read_csv(f)
    d.columns = [c.upper() for c in d.columns]
    # the files write the date as 01-JAN-2024, 01-Jan-23 or (from 2025) 2025-01-01
    text = d["SETTLEMENT_DATE"].astype(str)
    iso = text.str.match(r"\d{4}-\d{2}-\d{2}").all()
    day = pd.to_datetime(text, format="%Y-%m-%d" if iso else "mixed", dayfirst=not iso)
    if not day.is_monotonic_increasing or day.dt.year.ne(year).any():
        raise SystemExit(f"{f.name}: settlement dates not understood")
    # settlement periods count half hours from local midnight; clock-change days have 46 or 50
    d.index = (day.dt.tz_localize("Europe/London").dt.tz_convert("UTC")
               + pd.to_timedelta((d["SETTLEMENT_PERIOD"] - 1) * 30, "min"))
    return d[~d.index.duplicated()].sort_index()


def neso_mix(year: int) -> pd.DataFrame:
    """Half-hourly NESO generation mix of *year* (MW by fuel, GENERATION = total), UTC index."""
    f = RAW / "neso_generation_mix.csv"
    if not f.exists():
        RAW.mkdir(parents=True, exist_ok=True)
        f.write_bytes(_get(NESO_MIX))
    d = pd.read_csv(f, usecols=lambda c: not c.endswith("_perc"))
    d.index = pd.to_datetime(d.pop("DATETIME"), utc=True)
    return d[d.index.year == year].sort_index()


def elexon_bmunits() -> pd.DataFrame:
    """Elexon's reference list of BM units (current registrations)."""
    f = RAW / "elexon_bmunits.json"
    if not f.exists():
        RAW.mkdir(parents=True, exist_ok=True)
        f.write_bytes(_get(f"{ELEXON}/reference/bmunits/all"))
    return pd.DataFrame(json.loads(f.read_text(encoding="utf-8")))


def elexon_igcpu() -> pd.DataFrame:
    """IGCPU records (installed capacity and production type of units of 100 MW or more)."""
    f = RAW / "elexon_igcpu.csv"
    if not f.exists():
        rows = []
        for y in range(2022, date.today().year + 1):   # nothing is published under earlier dates
            url = (f"{ELEXON}/datasets/IGCPU?publishDateTimeFrom={y}-01-01T00:00:00Z"
                   f"&publishDateTimeTo={y + 1}-01-01T00:00:00Z&format=json")
            rows += json.loads(_get(url))["data"]
            time.sleep(PAUSE)
        RAW.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(rows).drop_duplicates().to_csv(f, index=False)
    return pd.read_csv(f)


def _months(first: date, last: date):
    d = first.replace(day=1)
    while d <= last:
        nxt = (d + timedelta(days=32)).replace(day=1)
        yield d, nxt - timedelta(days=1)
        d = nxt


def _monthly(name: str, first: date, last: date, fetch) -> pd.DataFrame:
    """Concatenate the monthly cache files *name*_YYYY-MM.csv.gz, downloading the missing months."""
    parts = []
    for a, b in _months(first, last):
        f = RAW / f"{name}_{a:%Y-%m}.csv.gz"
        if not f.exists():
            if b > date.today() - timedelta(days=14):
                raise SystemExit(f"{name}: {a:%Y-%m} is not complete yet")
            RAW.mkdir(parents=True, exist_ok=True)
            x = fetch(a, b)
            tmp = f.with_suffix(".part")
            x.to_csv(tmp, index=False, compression="gzip")
            tmp.replace(f)
            print(f"  downloaded {f.name} ({len(x)} rows)", flush=True)
        parts.append(pd.read_csv(f))
    return pd.concat(parts, ignore_index=True)


def _b1610_long(first: date, last: date, units: list[str], name: str = "elexon_b1610_wind") -> pd.DataFrame:
    """B1610 metered volumes (MWh per half hour) of *units* for whole months, long format.

    One request covers a week of all units; the latest settlement run of each period is returned.
    """
    q = "&".join("bmUnit=" + u for u in units)

    def fetch(a: date, b: date) -> pd.DataFrame:
        rows, d = [], a
        while d <= b:
            e = min(d + timedelta(days=6), b)
            url = (f"{ELEXON}/datasets/B1610/stream?settlementDateFrom={d}&settlementDateTo={e}"
                   f"&settlementPeriodFrom=1&settlementPeriodTo=50&{q}")
            rows += [(r["halfHourEndTime"], r["bmUnit"], r["quantity"]) for r in json.loads(_get(url))]
            d = e + timedelta(days=1)
            time.sleep(PAUSE)
        return pd.DataFrame(rows, columns=["half_hour_end_utc", "bm_unit", "mwh"])

    return _monthly(name, first, last, fetch)


def elexon_b1610(year: int, units: list[str]) -> pd.DataFrame:
    """Half-hourly metered output (MW) of *units*, UTC period start x unit, from 1 October of the
    previous year (the look-back of the capacity rule) to the end of *year*."""
    x = _b1610_long(date(year - 1, 10, 1), date(year, 12, 31), units)
    x["t"] = pd.to_datetime(x["half_hour_end_utc"], utc=True) - pd.Timedelta(minutes=30)
    return x.pivot_table(index="t", columns="bm_unit", values="mwh", aggfunc="last") * 2.0


def elexon_pumped_storage(year: int) -> pd.Series:
    """Half-hourly net output (MW) of the pumped-storage fleet from B1610: generation minus pumping.

    The generation mix counts the fleet net and floors it at zero (STORAGE), so the pumping that the
    generation in the mix served is the negative part of this series.
    """
    ref = elexon_bmunits()
    units = sorted(ref.loc[(ref["fuelType"] == "PS") & ref["elexonBmUnit"].notna(), "elexonBmUnit"].unique())
    x = _b1610_long(date(year, 1, 1), date(year, 12, 31), units, name="elexon_b1610_pumped_storage")
    t = pd.to_datetime(x["half_hour_end_utc"], utc=True) - pd.Timedelta(minutes=30)
    return (x["mwh"] * 2.0).groupby(t).sum()


def elexon_boav(year: int, units: list[str]) -> pd.DataFrame:
    """Half-hourly volume (MW, >= 0) by which each unit was turned down in the Balancing Mechanism.

    BOAV gives, per acceptance, the accepted volume in each bid-offer pair. Volumes in the negative
    pairs are below the unit's physical notification: bids (negative) and the offers that undo them
    (positive). Their sum over the "bid" and "offer" endpoints is the net turn-down.
    """
    q = "&".join("bmUnit=" + u for u in units)
    neg = [f"negative{i}" for i in range(1, 7)]

    def fetch(a: date, b: date) -> pd.DataFrame:
        rows, d = [], a
        while d <= b:
            for side in ("bid", "offer"):
                url = f"{ELEXON}/balancing/settlement/acceptance/volumes/all/{side}/{d}?{q}"
                for r in json.loads(_get(url))["data"]:
                    v = sum(r["pairVolumes"].get(k) or 0.0 for k in neg)
                    if v:
                        rows.append((r["startTime"], r["bmUnit"], v))
                time.sleep(PAUSE)
            d += timedelta(days=1)
        x = pd.DataFrame(rows, columns=["start_utc", "bm_unit", "mwh"])
        return x.groupby(["start_utc", "bm_unit"], as_index=False)["mwh"].sum().round(4)

    x = _monthly("elexon_boav_wind", date(year, 1, 1), date(year, 12, 31), fetch)
    x["t"] = pd.to_datetime(x["start_utc"], utc=True)
    return (-x.pivot_table(index="t", columns="bm_unit", values="mwh", aggfunc="sum") * 2.0).clip(lower=0)


# ---------------------------------------------------------------------------------------------------
# wind units
# ---------------------------------------------------------------------------------------------------
def wind_units() -> pd.DataFrame:
    """One row per wind BM unit (index: Elexon id): tech, region, registered MW and where each came from.

    Units: fuel type WIND in Elexon's BM unit list, plus the rows of wind_units_manual.csv.
    Onshore / offshore, in order: the manual file; an id ending "O-<n>" (the convention for offshore
    units); IGCPU production type "Wind Offshore"; otherwise onshore. IGCPU is not used on its own: it
    covers under half of the units and mislabels some (West of Duddon Sands is "Wind Onshore").
    """
    ref = elexon_bmunits()
    ref = ref[ref["elexonBmUnit"].notna()].drop_duplicates("elexonBmUnit").set_index("elexonBmUnit")
    ig = elexon_igcpu().sort_values("publishTime")
    ngc_to_elexon = {n: e for e, n in ref["nationalGridBmUnit"].items() if isinstance(n, str)}
    ig["unit"] = ig["bmUnit"].where(ig["bmUnit"].notna(), ig["registeredResourceName"].map(ngc_to_elexon))
    ig = ig.dropna(subset=["unit"]).drop_duplicates("unit", keep="last").set_index("unit")
    man = pd.read_csv(MANUAL, comment="#").set_index("bm_unit")

    ids = sorted((set(ref.index[ref["fuelType"] == "WIND"]) | set(man.index))
                 - set(man.index[man["tech"] == "exclude"]))
    u = pd.DataFrame(index=pd.Index(ids, name="bm_unit"))
    u["ngc_id"] = ref["nationalGridBmUnit"].reindex(u.index)
    u["name"] = ref["bmUnitName"].reindex(u.index)
    u["lead_party"] = ref["leadPartyName"].reindex(u.index)
    u["bm_unit_type"] = ref["bmUnitType"].reindex(u.index)

    def pick(*options):
        """First non-missing value per unit from (series, label) options; returns values and labels."""
        val = pd.Series(None, index=u.index, dtype=object)
        src = pd.Series(None, index=u.index, dtype=object)
        for s, label in options:
            s = s.reindex(u.index).astype(object)
            use = val.isna() & s.notna()
            val[use], src[use] = s[use], label
        return val, src

    # onshore / offshore
    ids_ = pd.Series(u.index, index=u.index) + " " + u["ngc_id"].fillna("").astype(str)
    suffix = ids_.str.contains(r"O-\d+(?: |$)").map({True: "offshore", False: None})
    psr = ig["psrType"].map({"Wind Offshore": "offshore"})
    u["tech"], u["tech_source"] = pick((man["tech"], "manual"), (suffix, "id ends O-n"),
                                       (psr, "IGCPU Wind Offshore"),
                                       (pd.Series("onshore", index=u.index), "default"))

    # region: GSP group, else the GSP-group zone that carries the same transmission loss factor
    def scot(names: pd.Series) -> pd.Series:
        names = names.dropna().astype(str)
        return names.str.lower().str.contains("scotland").map({True: "scot", False: "ew"})

    everyone = elexon_bmunits().drop_duplicates("elexonBmUnit")
    tlf_all = pd.to_numeric(everyone["transmissionLossFactor"], errors="coerce").round(6)
    known = scot(everyone["gspGroupName"])
    zone = known.groupby(tlf_all.reindex(known.index)).agg(lambda s: s.mode().iloc[0])
    by_zone = pd.to_numeric(ref["transmissionLossFactor"], errors="coerce").round(6).reindex(u.index).map(zone)
    u["region"], u["region_source"] = pick((man["region"], "manual"), (scot(ref["gspGroupName"]), "GSP group"),
                                           (by_zone, "loss-factor zone"))

    # registered capacity
    cap_ig = pd.to_numeric(ig["installedCapacity"], errors="coerce")
    cap_ref = pd.to_numeric(ref["generationCapacity"], errors="coerce")
    u["igcpu_mw"] = cap_ig.where(cap_ig > 0).reindex(u.index)
    u["bmunits_mw"] = cap_ref.where(cap_ref > 0).reindex(u.index)
    u["registered_mw"], u["registered_source"] = pick((u["igcpu_mw"], "IGCPU"), (u["bmunits_mw"], "bmunits"))
    u["registered_mw"] = u["registered_mw"].astype(float)
    u["igcpu_effective_from"] = ig["effectiveFrom"].reindex(u.index)
    u["manual_first_year"] = man["first_year"].reindex(u.index)
    missing = u.index[u["region"].isna()]
    if len(missing):
        raise SystemExit(f"no region for {list(missing)}: add them to {MANUAL.name}")
    return u


def unit_capacity(metered: pd.DataFrame, u: pd.DataFrame, prior: pd.Series) -> tuple[pd.DataFrame, pd.DataFrame, float]:
    """Half-hourly capacity (MW) of each unit, the per-unit numbers behind it, and PEAK_SHARE.

    *metered* is the half-hourly output (MW, >= 0, no gaps) from 1 October of the previous year and
    *prior* the highest output of each unit in the Decembers before that. See the module docstring.
    """
    started = metered.gt(FIRST_MW).cummax() | (prior > FIRST_MW)
    peak = metered.where(started).quantile(PEAK_QUANTILE)            # NaN: never generated
    published = u[["igcpu_mw", "bmunits_mw"]].reindex(metered.columns)
    with np.errstate(invalid="ignore"):
        ratio = published.rdiv(peak, axis=0).to_numpy(dtype=float)    # peak / published
        off = np.where((ratio >= ACCEPT[0]) & (ratio <= ACCEPT[1]), np.abs(ratio - 1), np.inf)
    pick, kept = off.argmin(axis=1), np.isfinite(off.min(axis=1))
    chosen = published.to_numpy(dtype=float)[np.arange(len(pick)), pick]
    share = float(np.median(peak.to_numpy()[kept] / chosen[kept]))    # PEAK_SHARE
    full = np.where(kept, chosen, peak.to_numpy() / share)            # capacity once complete

    ahead = LOOKAHEAD_DAYS * 48
    so_far = np.maximum(metered.cummax().shift(-ahead).ffill().to_numpy(), prior.to_numpy())
    with np.errstate(invalid="ignore"):
        cap = np.where(so_far >= COMPLETE_SHARE * peak.to_numpy(), full, np.minimum(so_far / share, full))
    cap = pd.DataFrame(np.where(started.to_numpy(), cap, 0.0), index=metered.index, columns=metered.columns)
    table = pd.DataFrame({"peak_mw": peak, "capacity_mw": full,
                          "capacity_source": np.where(kept, np.array(["IGCPU", "bmunits"])[pick], "own peak")},
                         index=metered.columns)
    table.loc[peak.isna(), "capacity_source"] = "no output"
    return cap.fillna(0.0), table, share


def december_peaks(year: int, units: list[str]) -> pd.DataFrame:
    """Highest half-hourly output (MW) of each unit in the Decembers from 2019 to the year before *year*.

    A cheap history of the fleet: it tells which units were already running, and how much of them, before
    the look-back window, and the year of first output (the API has no B1610 before February 2019).
    """
    peaks = {}
    for y in range(2019, year):
        dec = _b1610_long(date(y, 12, 1), date(y, 12, 31), units)
        peaks[y] = dec.groupby("bm_unit")["mwh"].max() * 2.0
    return pd.DataFrame(peaks).T.reindex(columns=units).fillna(0.0)


# ---------------------------------------------------------------------------------------------------
# build one year
# ---------------------------------------------------------------------------------------------------
def build(year: int) -> dict:
    """Profiles, unit table, vintage table and validation figures of one weather year."""
    if year < FIRST_YEAR:
        raise SystemExit(f"{year}: the API has B1610 from 1 February 2019 only and the capacity rule "
                         f"needs the last quarter of the previous year; first year is {FIRST_YEAR}")
    half = pd.date_range(f"{year}-01-01", f"{year}-12-31 23:30", freq="30min", tz="UTC")
    hours = len(half) / 2

    def twh(x) -> float:                                          # half-hourly MW -> TWh
        return float(np.nansum(np.asarray(x, dtype=float))) / 2e6

    # --- demand and solar ---------------------------------------------------------------------------
    nd = neso_demand(year).reindex(half)
    mix = neso_mix(year).reindex(half)
    flows = nd[[c for c in nd.columns if c.endswith("_FLOW")]]
    exports = (-flows).clip(lower=0).sum(axis=1)
    storage = elexon_pumped_storage(year).reindex(half).fillna(0.0)
    pumping = (-storage).clip(lower=0)
    pumping_neso = nd["PUMP_STORAGE_PUMPING"]
    f = pd.DataFrame(index=half)
    f["demand_mw"] = mix["GENERATION"] - exports - pumping
    f["demand_nd_embedded_mw"] = nd["ND"] + nd["EMBEDDED_WIND_GENERATION"] + nd["EMBEDDED_SOLAR_GENERATION"]
    f["solar_cf"] = (nd["EMBEDDED_SOLAR_GENERATION"] / nd["EMBEDDED_SOLAR_CAPACITY"]).clip(0, 1)

    # --- wind units ---------------------------------------------------------------------------------
    u = wind_units()
    raw = elexon_b1610(year, list(u.index))
    missing = int(raw.reindex(half).isna().all(axis=1).sum())
    window = pd.date_range(raw.index.min(), half[-1], freq="30min", tz="UTC")
    metered = raw.reindex(window).fillna(0.0).clip(lower=0.0)   # imports of idle wind farms are not output
    dec = december_peaks(year, list(metered.columns))
    prior = dec[dec.index < year - 1].max().fillna(0.0)         # before the look-back window
    cap, table, share = unit_capacity(metered, u, prior)
    metered, cap = metered.loc[half], cap.loc[half]
    turned_down = elexon_boav(year, list(u.index)).reindex(index=half, columns=metered.columns).fillna(0.0)
    available = np.minimum(metered + turned_down, cap)
    metered = np.minimum(metered, cap)

    u = u.reindex(metered.columns).join(table)
    emb_gen, emb_cap = nd["EMBEDDED_WIND_GENERATION"], nd["EMBEDDED_WIND_CAPACITY"]
    groups = {"offshore": u["tech"] == "offshore", "onshore_bm": u["tech"] == "onshore"}
    for tech in ("offshore", "onshore"):
        for region in ("scot", "ew"):
            groups[f"{tech}_{region}"] = (u["tech"] == tech) & (u["region"] == region)
    out_mw = {g: available.loc[:, m].sum(axis=1) for g, m in groups.items()}
    met_mw = {g: metered.loc[:, m].sum(axis=1) for g, m in groups.items()}
    cap_mw = {g: cap.loc[:, m].sum(axis=1) for g, m in groups.items()}
    for g, bm_units in (("onshore", "onshore_bm"), ("onshore_ew_emb", "onshore_ew")):   # + embedded wind
        out_mw[g], met_mw[g] = out_mw[bm_units] + emb_gen, met_mw[bm_units] + emb_gen
        cap_mw[g] = cap_mw[bm_units] + emb_cap
    f["wind_onshore_cf"] = out_mw["onshore"] / cap_mw["onshore"]
    f["wind_offshore_cf"] = out_mw["offshore"] / cap_mw["offshore"]
    f["wind_onshore_scot_cf"] = out_mw["onshore_scot"] / cap_mw["onshore_scot"]
    f["wind_onshore_ew_cf"] = out_mw["onshore_ew_emb"] / cap_mw["onshore_ew_emb"]
    f["wind_offshore_scot_cf"] = out_mw["offshore_scot"] / cap_mw["offshore_scot"]
    f["wind_offshore_ew_cf"] = out_mw["offshore_ew"] / cap_mw["offshore_ew"]
    f["wind_onshore_ew_bm_cf"] = out_mw["onshore_ew"] / cap_mw["onshore_ew"]     # for the report only
    wind_cols = [c for c in f.columns if c.startswith("wind_")]
    f[wind_cols] = f[wind_cols].clip(0, 1)

    # --- hourly profile -----------------------------------------------------------------------------
    h = f.resample("h").mean().interpolate(limit=3).ffill().bfill().iloc[:8760]
    regional = ["wind_onshore_scot_cf", "wind_onshore_ew_cf", "wind_offshore_scot_cf", "wind_offshore_ew_cf"]
    prof = h[["demand_mw", "wind_onshore_cf", "wind_offshore_cf", "solar_cf"]].copy()
    prof["hour"], prof["doy"] = h.index.hour, h.index.day_of_year
    prof[regional + ["demand_nd_embedded_mw"]] = h[regional + ["demand_nd_embedded_mw"]]
    prof = prof.reset_index(drop=True)

    # --- unit table ---------------------------------------------------------------------------------
    u["capacity_start_mw"], u["capacity_end_mw"] = cap.iloc[0], cap.iloc[-1]
    u["capacity_mean_mw"] = cap.mean()
    u["metered_gwh"], u["turned_down_gwh"] = metered.sum() / 2e3, (available - metered).sum() / 2e3
    u["cf_metered"] = metered.sum() / cap.sum()
    u["cf_available"] = available.sum() / cap.sum()
    u["complete_all_year"] = (cap.min() > 0) & (cap.min() == cap.max())
    # year of first output: the first December with output, else this year; 2019 = "by December 2019"
    first = dec.gt(FIRST_MW).idxmax().where(dec.gt(FIRST_MW).any(), float(year))
    by_lookup = u["manual_first_year"].notna()
    u["vintage_year"] = u["manual_first_year"].where(by_lookup, first)
    u["vintage_source"] = np.where(by_lookup, "lookup: project commissioning year",
                                   np.where(first == 2019, "B1610: in operation by Dec 2019",
                                            np.where(first.notna(), "B1610: first output", "")))
    u = u[u["capacity_mean_mw"] > 0]

    # --- validation figures (whole calendar year, half-hourly) ---------------------------------------
    bench = pd.read_csv(DESNZ, comment="#").set_index("year")
    b0, b1 = bench.loc[year - 1], bench.loc[year]

    def desnz_offshore(r) -> float:
        return float(r["offshore_seabed_mw_end"] + r["offshore_floating_mw_end"])

    def desnz_onshore_gb(r) -> float:                             # all Northern Irish wind is onshore
        return float(r["onshore_mw_end"] - r["ni_wind_mw_end"])

    def cf(x: dict, g: str) -> float:
        return float(x[g].sum() / cap_mw[g].sum())

    def lf(g: str) -> float:                                      # DESNZ's load factor definition
        return twh(met_mw[g]) * 1e6 / ((cap_mw[g].iloc[0] + cap_mw[g].iloc[-1]) / 2 * hours)

    def corr(a: str, b: str) -> float:
        return float(np.corrcoef(h[a], h[b])[0, 1])

    ours_twh = twh(met_mw["offshore"]) + twh(met_mw["onshore"])
    neso_twh = twh(mix["WIND"]) + twh(mix["WIND_EMB"])
    desnz_on_gb_twh = float(b1["onshore_gwh"] - b1["ni_wind_gwh"]) / 1e3
    info = {
        "year": year,
        # demand
        "demand_twh": twh(f["demand_mw"]), "demand_nd_embedded_twh": twh(f["demand_nd_embedded_mw"]),
        "demand_peak_gw": float(prof["demand_mw"].max()) / 1e3,
        "mix_generation_twh": twh(mix["GENERATION"]), "exports_twh": twh(exports), "pumping_twh": twh(pumping),
        "pumping_neso_column_twh": twh(pumping_neso),
        "pumped_storage_output_twh": twh(storage.clip(lower=0)), "mix_storage_twh": twh(mix["STORAGE"]),
        "station_load_twh": twh(nd["TSD"] - nd["ND"] - pumping_neso - exports),
        "mix_minus_tsd_twh": twh(mix["GENERATION"] - mix["WIND_EMB"] - mix["SOLAR"] - nd["TSD"]),
        "embedded_basis_twh": twh(mix["WIND_EMB"] + mix["SOLAR"] - nd["EMBEDDED_WIND_GENERATION"]
                                  - nd["EMBEDDED_SOLAR_GENERATION"]),
        # capacity factors: available (the profile) and metered (comparable with DESNZ)
        "cf_offshore": cf(out_mw, "offshore"), "cf_offshore_metered": cf(met_mw, "offshore"),
        "cf_onshore": cf(out_mw, "onshore"), "cf_onshore_metered": cf(met_mw, "onshore"),
        "cf_onshore_bm_units": cf(out_mw, "onshore_bm"), "cf_onshore_bm_units_metered": cf(met_mw, "onshore_bm"),
        "cf_embedded_wind": float(emb_gen.sum() / emb_cap.sum()),
        "cf_offshore_scot": cf(out_mw, "offshore_scot"), "cf_offshore_scot_metered": cf(met_mw, "offshore_scot"),
        "cf_offshore_ew": cf(out_mw, "offshore_ew"), "cf_offshore_ew_metered": cf(met_mw, "offshore_ew"),
        "cf_onshore_scot": cf(out_mw, "onshore_scot"), "cf_onshore_scot_metered": cf(met_mw, "onshore_scot"),
        "cf_onshore_ew": cf(out_mw, "onshore_ew_emb"), "cf_onshore_ew_bm_units_only": cf(out_mw, "onshore_ew"),
        "cf_solar": float(prof["solar_cf"].mean()),
        # the same on DESNZ's definition: energy / (mean of start and end capacity x hours)
        "lf_offshore_metered_desnz_method": lf("offshore"), "lf_onshore_metered_desnz_method": lf("onshore"),
        "desnz_lf_offshore_uk": float(b1["offshore_lf_pct"]) / 100,
        "desnz_lf_onshore_uk": float(b1["onshore_lf_pct"]) / 100,
        "desnz_lf_onshore_gb": desnz_on_gb_twh * 1e6 / ((desnz_onshore_gb(b0) + desnz_onshore_gb(b1)) / 2 * hours),
        "desnz_lf_solar_uk": float(b1["solar_lf_pct"]) / 100,
        # energy (TWh)
        "wind_metered_twh": ours_twh, "neso_mix_wind_twh": neso_twh,
        "offshore_metered_twh": twh(met_mw["offshore"]), "desnz_offshore_twh": float(b1["offshore_gwh"]) / 1e3,
        "onshore_metered_twh": twh(met_mw["onshore"]), "desnz_onshore_gb_twh": desnz_on_gb_twh,
        "turned_down_offshore_twh": twh(out_mw["offshore"] - met_mw["offshore"]),
        "turned_down_onshore_twh": twh(out_mw["onshore"] - met_mw["onshore"]),
        "turned_down_scot_twh": twh(out_mw["offshore_scot"] - met_mw["offshore_scot"]
                                    + out_mw["onshore_scot"] - met_mw["onshore_scot"]),
        "bm_units_scot_metered_twh": twh(met_mw["offshore_scot"]) + twh(met_mw["onshore_scot"]),
        "desnz_scot_wind_twh": float(b1["scot_wind_gwh"]) / 1e3,
        # capacity (MW) at the start and the end of the year
        "offshore_mw_start": float(cap_mw["offshore"].iloc[0]), "offshore_mw_end": float(cap_mw["offshore"].iloc[-1]),
        "desnz_offshore_mw_start": desnz_offshore(b0), "desnz_offshore_mw_end": desnz_offshore(b1),
        "onshore_mw_start": float(cap_mw["onshore"].iloc[0]), "onshore_mw_end": float(cap_mw["onshore"].iloc[-1]),
        "onshore_bm_units_mw_start": float(cap_mw["onshore_bm"].iloc[0]),
        "onshore_bm_units_mw_end": float(cap_mw["onshore_bm"].iloc[-1]),
        "embedded_wind_mw_start": float(emb_cap.iloc[0]), "embedded_wind_mw_end": float(emb_cap.iloc[-1]),
        "desnz_onshore_gb_mw_start": desnz_onshore_gb(b0), "desnz_onshore_gb_mw_end": desnz_onshore_gb(b1),
        "offshore_scot_mw_end": float(cap_mw["offshore_scot"].iloc[-1]),
        "onshore_scot_mw_end": float(cap_mw["onshore_scot"].iloc[-1]),
        "onshore_ew_bm_units_mw_end": float(cap_mw["onshore_ew"].iloc[-1]),
        # capacity the profile was built on / DESNZ installed capacity (means of start and end of year):
        # the factor by which a capacity factor must be scaled when it is applied to DESNZ capacity
        "nameplate_factor_offshore": float(cap_mw["offshore"].iloc[[0, -1]].mean())
        / ((desnz_offshore(b0) + desnz_offshore(b1)) / 2),
        "nameplate_factor_onshore": float(cap_mw["onshore"].iloc[[0, -1]].mean())
        / ((desnz_onshore_gb(b0) + desnz_onshore_gb(b1)) / 2),
        # shape (hourly, the 8,760 hours written)
        "corr_onshore_offshore": corr("wind_onshore_cf", "wind_offshore_cf"),
        "corr_onshore_scot_ew": corr("wind_onshore_scot_cf", "wind_onshore_ew_cf"),
        "corr_offshore_scot_ew": corr("wind_offshore_scot_cf", "wind_offshore_ew_cf"),
        "corr_onshore_ew_with_bm_units_only": corr("wind_onshore_ew_cf", "wind_onshore_ew_bm_cf"),
        "share_hours_onshore_below_10pct": float((prof["wind_onshore_cf"] < 0.1).mean()),
        "share_hours_offshore_below_10pct": float((prof["wind_offshore_cf"] < 0.1).mean()),
        "wind_units": int(len(u)), "peak_share": share, "half_hours_without_b1610": missing,
    }
    checks = {
        f"metered wind energy within {TOL_ENERGY:.0%} of the NESO generation mix":
            abs(ours_twh / neso_twh - 1) <= TOL_ENERGY,
        f"offshore metered load factor within {100 * TOL_LOAD_FACTOR:.0f} points of DESNZ":
            abs(info["lf_offshore_metered_desnz_method"] - info["desnz_lf_offshore_uk"]) <= TOL_LOAD_FACTOR,
        f"onshore metered load factor within {100 * TOL_LOAD_FACTOR:.0f} points of DESNZ (GB)":
            abs(info["lf_onshore_metered_desnz_method"] - info["desnz_lf_onshore_gb"]) <= TOL_LOAD_FACTOR,
        "B1610 has data for (almost) every half hour": missing <= 48,
        "demand data and generation mix aligned in time (embedded solar, correlation > 0.99)":
            float(np.corrcoef(nd["EMBEDDED_SOLAR_GENERATION"].fillna(0), mix["SOLAR"].fillna(0))[0, 1]) > 0.99,
        "8,760 hours without gaps": len(prof) == 8760 and not prof.isna().any().any(),
    }
    return dict(profile=prof, units=u, vintage=vintage_table(u, hours), info=info, checks=checks)


def vintage_table(u: pd.DataFrame, hours: float) -> pd.DataFrame:
    """Capacity-weighted capacity factor of the units complete all year, by technology and vintage band."""
    def band(row) -> str:
        if pd.isna(row["vintage_year"]):
            return "unknown"
        if row["vintage_year"] >= 2020:
            return "2020 or later"
        if row["vintage_source"].startswith("B1610"):
            return "2019 or earlier"                      # no commissioning year for these units
        return "pre-2015" if row["vintage_year"] < 2015 else "2015-2019"

    order = ["pre-2015", "2015-2019", "2019 or earlier", "2020 or later", "unknown"]
    u = u.assign(band=u.apply(band, axis=1))
    rows = []
    for tech in ("offshore", "onshore"):
        for b in order:
            g = u[(u["tech"] == tech) & (u["band"] == b)]
            full = g[g["complete_all_year"]]
            if g.empty:
                continue
            mwh_cap = full["capacity_mean_mw"].sum() * hours
            rows.append({
                "tech": tech, "vintage": b, "units": len(full),
                "capacity_mw": round(full["capacity_mean_mw"].sum(), 1),
                "cf_available": round((full["metered_gwh"] + full["turned_down_gwh"]).sum() * 1e3 / mwh_cap, 4)
                if len(full) else np.nan,
                "cf_metered": round(full["metered_gwh"].sum() * 1e3 / mwh_cap, 4) if len(full) else np.nan,
                "curtailment_added_back": "cf_available: yes; cf_metered: no",
                "units_excluded_commissioning": int((~g["complete_all_year"]).sum()),
                "capacity_excluded_mw": round(g.loc[~g["complete_all_year"], "capacity_end_mw"].sum(), 1),
                "vintage_basis": "; ".join(sorted(set(g["vintage_source"]) - {""})),
            })
    return pd.DataFrame(rows)


def report(i: dict, checks: dict) -> str:
    """The validation figures of one year as text."""
    def pct(x: float) -> str:
        return f"{100 * x:5.1f}%"

    lines = [
        f"=== {i['year']} ===",
        f"demand           {i['demand_twh']:.1f} TWh, peak {i['demand_peak_gw']:.1f} GW  (ND + embedded: "
        f"{i['demand_nd_embedded_twh']:.1f} TWh; difference = station load {i['station_load_twh']:.2f} + mix vs TSD "
        f"{i['mix_minus_tsd_twh']:.2f} + embedded basis {i['embedded_basis_twh']:.2f} - pumping missing from the NESO "
        f"column {i['pumping_twh'] - i['pumping_neso_column_twh']:.2f})",
        "capacity factor  available  metered  metered, DESNZ method   DESNZ ET 6.1",
        f"  offshore        {pct(i['cf_offshore'])}   {pct(i['cf_offshore_metered'])}   "
        f"{pct(i['lf_offshore_metered_desnz_method'])}                {pct(i['desnz_lf_offshore_uk'])} (UK)",
        f"  onshore         {pct(i['cf_onshore'])}   {pct(i['cf_onshore_metered'])}   "
        f"{pct(i['lf_onshore_metered_desnz_method'])}                {pct(i['desnz_lf_onshore_gb'])} (GB = UK - NI; "
        f"UK {pct(i['desnz_lf_onshore_uk'])})",
        f"  solar           {pct(i['cf_solar'])}                                    {pct(i['desnz_lf_solar_uk'])} (UK)",
        f"  regions, available (metered): offshore Scot {pct(i['cf_offshore_scot'])} ({pct(i['cf_offshore_scot_metered'])}), "
        f"offshore E&W {pct(i['cf_offshore_ew'])} ({pct(i['cf_offshore_ew_metered'])}), onshore Scot "
        f"{pct(i['cf_onshore_scot'])} ({pct(i['cf_onshore_scot_metered'])}), onshore E&W {pct(i['cf_onshore_ew'])}",
        f"wind energy      metered {i['wind_metered_twh']:.1f} TWh vs NESO generation mix {i['neso_mix_wind_twh']:.1f} TWh "
        f"({100 * (i['wind_metered_twh'] / i['neso_mix_wind_twh'] - 1):+.1f}%); offshore {i['offshore_metered_twh']:.1f} vs "
        f"DESNZ {i['desnz_offshore_twh']:.1f}; onshore {i['onshore_metered_twh']:.1f} vs DESNZ GB "
        f"{i['desnz_onshore_gb_twh']:.1f}",
        f"turned down      offshore {i['turned_down_offshore_twh']:.2f} TWh, onshore {i['turned_down_onshore_twh']:.2f} TWh "
        f"(Scottish units {i['turned_down_scot_twh']:.2f} TWh)",
        f"capacity (MW)    offshore {i['offshore_mw_start']:.0f} -> {i['offshore_mw_end']:.0f} (DESNZ "
        f"{i['desnz_offshore_mw_start']:.0f} -> {i['desnz_offshore_mw_end']:.0f}); onshore {i['onshore_mw_start']:.0f} -> "
        f"{i['onshore_mw_end']:.0f} (DESNZ GB {i['desnz_onshore_gb_mw_start']:.0f} -> {i['desnz_onshore_gb_mw_end']:.0f}); "
        f"nameplate factor offshore {i['nameplate_factor_offshore']:.3f}, onshore {i['nameplate_factor_onshore']:.3f}",
        f"shape            corr(onshore, offshore) {i['corr_onshore_offshore']:.3f}; hours with CF < 0.1: onshore "
        f"{pct(i['share_hours_onshore_below_10pct'])}, offshore {pct(i['share_hours_offshore_below_10pct'])}",
    ]
    return "\n".join(lines + [f"check            {'ok    ' if ok else 'FAILED'} {name}" for name, ok in checks.items()])


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("years", type=int, nargs="+")
    a = p.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    unit_columns = ["name", "lead_party", "tech", "tech_source", "region", "region_source", "igcpu_mw", "bmunits_mw",
                    "peak_mw", "capacity_mw", "capacity_source", "capacity_start_mw", "capacity_end_mw",
                    "capacity_mean_mw", "metered_gwh", "turned_down_gwh", "cf_metered", "cf_available",
                    "complete_all_year", "vintage_year", "vintage_source"]
    for y in a.years:
        r = build(y)
        print(report(r["info"], r["checks"]), flush=True)
        if not all(r["checks"].values()):
            print(f"{y}: validation failed, nothing written", flush=True)
            continue
        r["profile"].round(4).to_csv(OUT / f"profiles_{y}.csv", index=False)
        r["vintage"].to_csv(OUT / f"wind_cf_by_vintage_{y}.csv", index=False)
        r["units"][unit_columns].round(4).to_csv(OUT / f"wind_units_{y}.csv")
        v = OUT / "validation.csv"
        rows = [pd.read_csv(v)] if v.exists() else []
        rows = [x[x["year"] != y] for x in rows] + [pd.DataFrame([r["info"]])]
        pd.concat(rows).sort_values("year").round(4).to_csv(v, index=False)
        print(r["vintage"].drop(columns="vintage_basis").to_string(index=False), flush=True)


if __name__ == "__main__":
    main()
