"""Build the model's starting fleet from the official station list and the CfD register.

    python scripts/build_fleet.py            # -> data/fleet/fleet_2025.csv, data/fleet/pipeline_2025.csv

Sources (see data/fleet/README.md for licences):

* DESNZ, Digest of UK Energy Statistics 2026, Table 5.11 "Power stations in the United Kingdom", sheet
  "5.11 Full list": company, site, technology, fuel, installed capacity, coordinates and year
  commissioned of every major power producer's station operating at the end of 2025.
* The CfD register extract already in data/pypsagb_snapshot/cfd_strike_prices_by_round.csv (LCCC and
  DESNZ allocation round results): capacity and strike price by round, technology and delivery year.

* data/history/gb_capacity.csv: GB installed capacity by technology at the end of each year
  (DESNZ, DUKES 2026 Tables 5.12 and 5.16).

What is taken from these is the *distribution* of each technology's capacity over commissioning years,
zones and support schemes. The GB totals stay in ukabm.config.INITIAL_FLEET_MW, which the model
multiplies the shares by. The station list covers major power producers only (6.5 GW of 21.5 GW of
solar, mostly recent), so for wind and solar it gives the zones, and the vintages come from the yearly
additions to GB capacity; for thermal plant and hydro it gives both.

Rules (all in this file, none hand-tuned to model output):

* technology: CCGT -> ccgt; single-cycle and conventional-steam gas, and gas-oil engines -> ocgt;
  biomass stations of 100 MW or more -> biomass (the transmission-metered conversions; smaller
  bioenergy is embedded and netted off demand); hydro -> hydro; pumped hydro -> pumped_hydro; wind and
  solar as listed. Nuclear is set by ukabm.model.NUCLEAR_UNITS. Northern Ireland is excluded.
* zone: the PyPSA-GB zone whose bus is nearest to the station's coordinates.
* vintage: thermal plant and hydro: the year commissioned, in 5-year bands. Wind and solar: the yearly
  additions to GB capacity 2012-2025, in 3-year bands, with the 2011 stock placed at FIRST_VINTAGE.
  A band is represented by its capacity-weighted mean year.
* support of wind, solar and biomass in the starting fleet:
    - CfD: offshore wind commissioned from 2017 takes the register's offshore contracts in round order
      (investment contracts, AR1, AR2, ...), at the contract's strike; onshore wind and solar
      commissioned from 2023 take the AR4 and AR5 contracts in the same way. A station can only take a
      contract whose delivery year starts no more than EARLY years after it was commissioned (a 2018
      station cannot hold an AR3 contract for 2023-24). Contracts run 15 years from commissioning.
    - RO: other wind commissioned by 2018, solar by 2016 and biomass by 2018 (the scheme closed to new
      capacity on 31 March 2017, with grace periods), for 20 years, at most to March 2037. Small solar
      on feed-in tariffs (closed 2019) is counted with RO solar: both are paid per MWh whatever the
      wholesale price. Check: this gives 12.1 GW of RO onshore wind and 11.8 GW of RO or FiT solar;
      Ofgem's RO annual report 2024-25 has 12.3 GW of accredited onshore wind and 5.8 GW of solar.
    - merchant: everything else.
* pipeline: register capacity for wind and solar not matched to a commissioned station is contracted
  but not yet built. It comes online in the calendar year in which its delivery year ends
  (2026-27 -> 2027), or the year after the fleet year if that has passed (late projects), at its
  strike; the model places it in the technology's zones. Capacity known to have been withdrawn is
  removed (WITHDRAWN below, with sources). No further attrition or delay is assumed.
* batteries are not in the station list: their vintages are the yearly additions to grid-scale battery
  capacity in DUKES 2026 Table 5.16 (BATTERY_MW below), without a zone (the model places them).
* owner: the station list names the company of every station; data/fleet/owners.csv maps the 54
  companies to the model's twelve firms (seven named companies and five groups, data/fleet/firms.csv).
  Thermal plant and hydro take their station's firm. Wind and solar in a zone are shared among the
  firms in proportion to their listed capacity in that zone; capacity beyond the station list (small
  and unlisted sites: 2.7 GW of onshore wind, 15 GW of solar) belongs to the firm "Independents", as do
  firms with less than MIN_OWNER_SHARE of a zone. Batteries are split between Independents and
  InfrastructureFunds (ASSUMPTION: no owner data in the sources used).
"""
from __future__ import annotations

import argparse
import math
import re
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "fleet"
RAW = OUT / "raw"
DUKES_511 = "https://assets.publishing.service.gov.uk/media/6a6a365b0ddb7e4831c629f3/DUKES_5.11.xlsx"
REGISTER = ROOT / "data" / "pypsagb_snapshot" / "cfd_strike_prices_by_round.csv"
BUSES = ROOT / "data" / "pypsagb_snapshot" / "zonal_buses.csv"
NATIONAL = ROOT / "data" / "history" / "gb_capacity.csv"
VRE = ("wind_onshore", "wind_offshore", "solar")
FIRST_VINTAGE = {"wind_onshore": 2006, "wind_offshore": 2009, "solar": 2011}   # year standing for the 2011 stock
MIN_ZONE_SHARE = 0.03      # wind and solar: zones with less than this share of the listed capacity are dropped
OWNERS = OUT / "owners.csv"
FRINGE = "Independents"
MIN_OWNER_SHARE = 0.05     # wind and solar: a firm with less than this share of a zone is merged into the fringe
BATTERY_OWNERS = {"Independents": 0.5, "InfrastructureFunds": 0.5}

BAND = {"wind_onshore": 4, "wind_offshore": 4, "solar": 4}      # years per vintage band; others 5
RO_LAST = {"wind_onshore": 2018, "wind_offshore": 2018, "solar": 2016, "biomass": 2018}
RO_YEARS, RO_SCHEME_END, CFD_YEARS = 20, 2037, 15
ROUND_ORDER = ["Investment Contract", "AR1", "AR2", "AR3", "AR4", "AR5", "AR6", "AR7", "AR7a"]
REGISTER_TECH = {"offshore": "wind_offshore", "offshore_scotland": "wind_offshore",
                 "offshore_permitted_reduction": "wind_offshore", "onshore": "wind_onshore",
                 "remote_island_wind": "wind_onshore", "solar": "solar"}
CFD_FROM = {"wind_offshore": 2017, "wind_onshore": 2023, "solar": 2023}   # first commissioning year on a CfD
# contracts paid at negative prices (investment contracts always; rounds 2-3 unless six hours run negative)
PAID_NEGATIVE = {"Investment Contract", "AR1", "AR2", "AR3"}
# a station may be commissioned at most this many years before its contract's delivery year starts
EARLY = {"wind_offshore": 1, "wind_onshore": 0, "solar": 0}
# UK grid-scale battery power capacity at the end of each year, MW (DESNZ, DUKES 2026 Table 5.16)
BATTERY_MW = {2016: 0.0, 2017: 140.4, 2018: 633.0, 2019: 879.3, 2020: 1097.1, 2021: 1536.1, 2022: 2319.4,
              2023: 3820.2, 2024: 5209.9, 2025: 7511.6}
# Awarded capacity that will not be built under the listed contract (MW removed from the round):
# * AR4 offshore: Norfolk Boreas (1,396 MW) ceased in July 2023 (Vattenfall interim report, 20 July
#   2023); and 1,578.5 MW of AR4 projects moved to AR6 contracts under the "permitted reduction" rule
#   (DESNZ AR6 results, 3 Sept 2024), which the register lists again under AR6.
WITHDRAWN = {("AR4", "wind_offshore"): 1396.0 + 1578.5}


# --------------------------------------------------------------------------------------- reading
def _download(url: str, path: Path) -> Path:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers={"User-Agent": "ukabm-build-fleet"})
        with urllib.request.urlopen(req, timeout=120) as r:
            path.write_bytes(r.read())
    return path


def read_xlsx_sheet(path: Path, sheet: str) -> list[dict]:
    """Rows of one worksheet as {column letters: value}, without openpyxl (zip + XML)."""
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    rns = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
    with zipfile.ZipFile(path) as z:
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            for si in ET.parse(z.open("xl/sharedStrings.xml")).getroot().iter(ns + "si"):
                shared.append("".join(t.text or "" for t in si.iter(ns + "t")))
        wb = ET.parse(z.open("xl/workbook.xml")).getroot()
        rels = {r.get("Id"): r.get("Target") for r in ET.parse(z.open("xl/_rels/workbook.xml.rels")).getroot()}
        target = next(rels[s.get(rns + "id")] for s in wb.iter(ns + "sheet") if s.get("name") == sheet).lstrip("/")
        target = target if target.startswith("xl/") else "xl/" + target
        out = []
        for row in ET.parse(z.open(target)).getroot().iter(ns + "row"):
            d = {}
            for c in row.iter(ns + "c"):
                col = re.sub(r"\d", "", c.get("r") or "")
                v = c.find(ns + "v")
                if c.get("t") == "inlineStr":
                    d[col] = "".join(t.text or "" for t in c.iter(ns + "t"))
                elif v is not None and v.text is not None:
                    d[col] = shared[int(v.text)] if c.get("t") == "s" else v.text
            out.append(d)
    return out


def stations(path: Path) -> pd.DataFrame:
    rows = read_xlsx_sheet(path, "5.11 Full list")
    i = next(k for k, d in enumerate(rows) if "Site Name" in d.values())
    hdr = rows[i]
    df = pd.DataFrame([{hdr[c].split("[")[0].strip(): v for c, v in d.items() if c in hdr} for d in rows[i + 1:]])
    df = df.rename(columns={"InstalledCapacity (MW)": "mw", "Year Commissioned": "year", "X-Coordinate": "x",
                            "Y-Coordinate": "y", "Site Name": "site", "Company Name": "company"})
    for c in ("mw", "year", "x", "y"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df[(df.Country != "Northern Ireland") & df.mw.notna()].reset_index(drop=True)


def model_tech(r) -> str | None:
    t, typ, fuel = r["Technology"], r["Type"], r["Primary Fuel"]
    if t == "Fossil Fuel":
        return "ccgt" if typ == "CCGT" else "ocgt"
    if t == "Bioenergy":
        return "biomass" if fuel == "Biomass" and r["mw"] >= 100 else None
    if t == "Wind":
        return "wind_offshore" if typ == "Offshore" else "wind_onshore"
    return {"Solar": "solar", "Hydro": "hydro", "Pumped Hydro": "pumped_hydro"}.get(t)


# ------------------------------------------------------------------------------------ geography
def osgb_to_lonlat(e, n):
    """National Grid easting/northing (m) to longitude/latitude (degrees) on the Airy ellipsoid.
    The OSGB36-WGS84 datum shift (about 100 m) is ignored: irrelevant for a nearest-of-20-zones match."""
    a, b, f0 = 6377563.396, 6356256.909, 0.9996012717
    lat0, lon0, n0, e0 = math.radians(49), math.radians(-2), -100000.0, 400000.0
    e2 = 1 - (b * b) / (a * a)
    nn = (a - b) / (a + b)
    lat, m = lat0, 0.0
    while abs(n - n0 - m) >= 1e-5:
        lat = (n - n0 - m) / (a * f0) + lat
        m = b * f0 * ((1 + nn + 1.25 * nn ** 2 + 1.25 * nn ** 3) * (lat - lat0)
                      - (3 * nn + 3 * nn ** 2 + 2.625 * nn ** 3) * math.sin(lat - lat0) * math.cos(lat + lat0)
                      + (1.875 * nn ** 2 + 1.875 * nn ** 3) * math.sin(2 * (lat - lat0)) * math.cos(2 * (lat + lat0))
                      - 35 / 24 * nn ** 3 * math.sin(3 * (lat - lat0)) * math.cos(3 * (lat + lat0)))
    s = math.sin(lat)
    nu = a * f0 / math.sqrt(1 - e2 * s * s)
    rho = a * f0 * (1 - e2) / (1 - e2 * s * s) ** 1.5
    eta2 = nu / rho - 1
    t = math.tan(lat)
    de = e - e0
    vii = t / (2 * rho * nu)
    viii = t / (24 * rho * nu ** 3) * (5 + 3 * t * t + eta2 - 9 * t * t * eta2)
    x = 1 / (math.cos(lat) * nu)
    xi = x / (6 * nu ** 2) * (nu / rho + 2 * t * t)
    xii = x / (120 * nu ** 4) * (5 + 28 * t * t + 24 * t ** 4)
    return math.degrees(lon0 + x * de - xi * de ** 3 + xii * de ** 5), math.degrees(lat - vii * de ** 2 + viii * de ** 4)


def nearest_zone(df: pd.DataFrame) -> pd.Series:
    buses = pd.read_csv(BUSES)
    ll = np.array([osgb_to_lonlat(x, y) if np.isfinite(x) and np.isfinite(y) else (np.nan, np.nan)
                   for x, y in zip(df.x, df.y)])
    d2 = (ll[:, 1][:, None] - buses.y.values[None]) ** 2 + ((ll[:, 0][:, None] - buses.x.values[None]) * 0.6) ** 2
    d2 = np.where(np.isnan(d2), np.inf, d2)
    return pd.Series(np.where(np.isfinite(d2.min(1)), buses.name.values[d2.argmin(1)], ""), index=df.index)


# -------------------------------------------------------------------------------------- support
def register(fleet_year: int) -> pd.DataFrame:
    r = pd.read_csv(REGISTER)
    r = r[r.technology.isin(REGISTER_TECH) & r.cfd_round.isin(ROUND_ORDER) & (r.capacity_mw > 0)].copy()
    r["tech"] = r.technology.map(REGISTER_TECH)
    r["delivery_start"] = r.delivery_year.astype(str).str[:4].astype(int)
    r["online"] = r.delivery_start + 1                                    # 2026-27 -> 2027
    r["order"] = r.cfd_round.map(ROUND_ORDER.index)
    r = r.rename(columns={"capacity_mw": "mw", "strike_price_gbp_per_mwh_2012": "strike_2012"})
    r = r.sort_values(["order", "online"]).reset_index(drop=True)
    for (rnd, tech), cut in WITHDRAWN.items():          # remove withdrawn capacity from the round
        for i in r.index[(r.cfd_round == rnd) & (r.tech == tech)]:
            take = min(cut, r.at[i, "mw"])
            r.at[i, "mw"] -= take
            cut -= take
    return r[r.mw > 0][["cfd_round", "tech", "online", "delivery_start", "mw", "strike_2012", "order"]].reset_index(drop=True)


def assign_support(st: pd.DataFrame, reg: pd.DataFrame, fleet_year: int):
    """Give every station row a support scheme; split rows that are part CfD. Returns (stations,
    register with the capacity left unmatched = the pipeline)."""
    reg = reg.copy()
    out = []
    for tech, g in st.groupby("tech", sort=False):
        contracts = reg[reg.tech == tech] if tech in CFD_FROM else reg.iloc[0:0]
        for _, s in g.sort_values("year").iterrows():
            left = s.mw
            if tech in CFD_FROM and s.year >= CFD_FROM[tech]:
                for i in contracts.index:
                    if left <= 1e-6:
                        break
                    if s.year < reg.at[i, "delivery_start"] - EARLY[tech]:
                        continue
                    take = min(left, reg.at[i, "mw"])
                    if take > 0:
                        out.append({**s, "mw": take, "support": "cfd", "strike_2012": reg.at[i, "strike_2012"],
                                    "support_end": int(s.year) + CFD_YEARS - 1,
                                    "paid_negative": int(reg.at[i, "cfd_round"] in PAID_NEGATIVE)})
                        reg.at[i, "mw"] -= take
                        left -= take
            if left > 1e-6:
                if tech in RO_LAST and s.year <= RO_LAST[tech]:
                    out.append({**s, "mw": left, "support": "ro", "strike_2012": 0.0, "paid_negative": 0,
                                "support_end": min(int(s.year) + RO_YEARS - 1, RO_SCHEME_END - 1)})
                else:
                    out.append({**s, "mw": left, "support": "merchant", "strike_2012": 0.0, "support_end": 0,
                                "paid_negative": 0})
    return pd.DataFrame(out), reg[reg.mw > 1e-6]


# ---------------------------------------------------------------------------------------- build
def build(fleet_year: int = 2025):
    st = stations(_download(DUKES_511, RAW / "DUKES_5.11.xlsx"))
    st["tech"] = st.apply(model_tech, axis=1)
    st = st[st.tech.notna() & (st.year <= fleet_year)].copy()
    st["year"] = st.year.fillna(st.groupby("tech").year.transform("median")).astype(int)
    st["zone"] = nearest_zone(st)
    firm_of = pd.read_csv(OWNERS).set_index("company").firm
    st["owner"] = st.company.map(firm_of).fillna(FRINGE)
    listed = st[st.tech.isin(VRE)].groupby(["tech", "zone", "owner"]).mw.sum()     # station list, by firm
    # wind and solar: national vintages, zones from the station list
    nat = pd.read_csv(NATIONAL)
    vre_rows = []
    for tech in VRE:
        s = nat[nat.tech == tech].set_index("year").mw.sort_index()
        s = s[s.index <= fleet_year]
        add = s.diff().clip(lower=0)
        add.iloc[0] = s.iloc[0]
        zs = st[st.tech == tech].groupby("zone").mw.sum()
        zs = zs[zs / zs.sum() >= MIN_ZONE_SHARE]
        zs = zs / zs.sum()
        for year, mw in add.items():
            y = FIRST_VINTAGE[tech] if year == add.index[0] else int(year)
            vre_rows.append(dict(tech=tech, year=y, mw=float(mw), zshare=zs))
    vre = pd.DataFrame(vre_rows)
    st = pd.concat([st[~st.tech.isin(VRE)][["tech", "year", "mw", "zone", "owner"]], vre[vre.mw > 0]], ignore_index=True)
    st, left = assign_support(st, register(fleet_year), fleet_year)
    # spread the wind and solar rows over their zones
    parts = [st[~st.tech.isin(VRE)]]
    for _, r in st[st.tech.isin(VRE)].iterrows():
        for zone, share in r.zshare.items():
            parts.append(pd.DataFrame([{**r.drop("zshare"), "zone": zone, "mw": r.mw * share}]))
    st = pd.concat(parts, ignore_index=True).drop(columns="zshare", errors="ignore")
    # owners of wind and solar: each zone's capacity shared among the firms listed there, the rest to the fringe
    parts = [st[~st.tech.isin(VRE)]]
    for (tech, zone), g in st[st.tech.isin(VRE)].groupby(["tech", "zone"]):
        total = g.mw.sum()
        q = listed.get((tech, zone), pd.Series(dtype=float)) if (tech, zone) in listed.index.droplevel(2) else pd.Series(dtype=float)
        q = q * min(1.0, total / q.sum()) if len(q) and q.sum() > 0 else q
        share = (q / total).to_dict()
        small = [o for o, s in share.items() if s < MIN_OWNER_SHARE and o != FRINGE]
        for o in small:
            share.pop(o)
        share[FRINGE] = 1.0 - sum(s for o, s in share.items() if o != FRINGE)
        for owner, s in share.items():
            if s > 1e-9:
                parts.append(g.assign(owner=owner, mw=g.mw * s))
    st = pd.concat(parts, ignore_index=True)
    width = st.tech.map(BAND).fillna(5).astype(int)
    st["band"] = (st.year // width) * width
    rows = []
    for (tech, zone, band, support, neg, owner), g in st.groupby(["tech", "zone", "band", "support", "paid_negative", "owner"]):
        mw = g.mw.sum()
        rows.append(dict(tech=tech, zone=zone, owner=owner, online=int(round((g.year * g.mw).sum() / mw)), mw=mw, support=support,
                         paid_negative=int(neg),
                         strike_2012=round((g.strike_2012 * g.mw).sum() / mw, 2),
                         support_end=int(round((g.support_end * g.mw).sum() / mw)) if support != "merchant" else 0))
    years = sorted(BATTERY_MW)
    for y0, y1 in zip(years[:-1], years[1:]):
        if y1 <= fleet_year and BATTERY_MW[y1] > BATTERY_MW[y0]:
            for owner, s in BATTERY_OWNERS.items():
                rows.append(dict(tech="battery", zone="", owner=owner, online=y1, mw=(BATTERY_MW[y1] - BATTERY_MW[y0]) * s,
                                 support="merchant", paid_negative=0, strike_2012=0.0, support_end=0))
    fleet = pd.DataFrame(rows)
    fleet["share"] = fleet.mw / fleet.groupby("tech").mw.transform("sum")
    fleet = fleet.sort_values(["tech", "online", "zone"]).reset_index(drop=True)
    # contracted pipeline: unmatched register capacity, placed like the existing fleet of its technology
    left = left.assign(online=left.online.clip(lower=fleet_year + 1))     # late projects: next year
    pipe = left.groupby(["tech", "online", "cfd_round"], as_index=False).agg(
        mw=("mw", "sum"), strike_2012=("strike_2012", lambda s: float(np.average(s, weights=left.loc[s.index, "mw"]))))
    pipe["support_end"] = pipe.online + CFD_YEARS - 1
    pipe["paid_negative"] = pipe.cfd_round.isin(PAID_NEGATIVE).astype(int)
    return fleet, pipe.round({"mw": 1, "strike_2012": 2}), st


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--year", type=int, default=2025)
    a = p.parse_args()
    fleet, pipe, st = build(a.year)
    OUT.mkdir(parents=True, exist_ok=True)
    fleet.round({"mw": 1, "share": 6}).to_csv(OUT / f"fleet_{a.year}.csv", index=False)
    pipe.to_csv(OUT / f"pipeline_{a.year}.csv", index=False)
    pd.set_option("display.width", 200)
    print("station list, GB MW by technology and support:")
    print(st.pivot_table(index="tech", columns="support", values="mw", aggfunc="sum", fill_value=0).round(0))
    print("\nby commissioning period:")
    st["period"] = pd.cut(st.year, [0, 1999, 2009, 2014, 2019, 2030], labels=["<2000", "2000-09", "2010-14", "2015-19", "2020-"])
    print(st.pivot_table(index="tech", columns="period", values="mw", aggfunc="sum", fill_value=0, observed=False).round(0))
    print("\nfleet by firm, GW (station list scaled to shares; totals are set in ukabm.config):")
    print((fleet.pivot_table(index="owner", columns="tech", values="mw", aggfunc="sum", fill_value=0) / 1e3).round(1).to_string())
    print(f"\n{len(fleet)} fleet rows; contracted pipeline (MW):")
    print(pipe.to_string(index=False))


if __name__ == "__main__":
    main()
