"""Compare the model's future years with published pathways.

    python scripts/compare_pathways.py [results/annual_baseline.csv]   # -> results/pathways_comparison.md

Published numbers: data/fes/published_pathways.csv (NESO FES 2025, the CCC's Seventh Carbon Budget
Balanced Pathway, the Clean Power 2030 Action Plan and NESO's advice for it), every value read from
the source's own workbook or tables (data/fes/NOTES.md gives sheets, pages and definitions).

For each quantity and year the table gives the model's value, the range of the four FES 2025
pathways, the CCC value and the Clean Power 2030 range, and says whether the model is inside the FES
range. "Role" says what the quantity is in the model, because being inside the range means different
things for an input and for a result:

    driver   taken from the FES pathway the scenario follows (ukabm.drivers): inside by construction
    target   decided by the model's government, whose target path is the pathway's capacity
    result   decided by firms, households or the market

Not like for like (see NOTES.md): FES and Clean Power 2030 are GB, the CCC is UK; FES demand includes
losses and networked electrolysis; FES peak is after smart charging; FES unabated gas includes CHP.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PUBLISHED = ROOT / "data" / "fes" / "published_pathways.csv"
FES = ["Holistic Transition", "Electric Engagement", "Hydrogen Evolution", "Falling Behind"]
YEARS = [2030, 2035, 2040, 2050]
# (label, role, model column or function of the annual row, published metric, technology, unit)
ROWS = [
    ("offshore wind (GW)", "target", "cap_wind_offshore", "capacity", "offshore_wind", "GW"),
    ("onshore wind (GW)", "target", "cap_wind_onshore", "capacity", "onshore_wind", "GW"),
    ("solar (GW)", "target", "cap_solar", "capacity", "solar", "GW"),
    ("batteries (GW)", "result", "cap_battery", "capacity", "battery", "GW"),
    ("unabated gas (GW)", "result", lambda r: r["cap_ccgt"] + r["cap_ocgt"], "capacity", "gas_unabated", "GW"),
    ("gas CCS (GW)", "result", "cap_gas_ccs", "capacity", "gas_ccs", "GW"),
    ("hydrogen power (GW)", "result", "cap_h2_turbine", "capacity", "hydrogen_power", "GW"),
    ("nuclear (GW)", "driver", "cap_nuclear", "capacity", "nuclear", "GW"),
    ("interconnectors (GW)", "driver", "cap_interconnector", "capacity", "interconnector", "GW"),
    ("electrolysers (GW)", "driver", "cap_electrolyser", "capacity", "electrolyser", "GW"),
    ("electricity demand (TWh)", "result", "demand_twh", "demand", "", "TWh"),
    ("peak demand (GW)", "result", "peak_demand_gw", "peak_demand", "", "GW"),
    ("heat pumps (million)", "result", "hp_homes_m", "heat_pumps", "", "million units"),
    ("battery electric vehicles (million)", "driver", "ev_stock_m", "evs", "", "million cars+vans"),
    ("carbon intensity (gCO2/kWh)", "result", "intensity_g_kwh", "carbon_intensity", "", "gCO2/kWh excl BECCS"),
]
WHY = {   # what is known about a row that falls outside the published range
    "heat pumps (million)": "Households choose on running cost at today's grant and price ratio, and the levy that pays for "
                            "CfDs and capacity sits on electricity bills; the pathways assume policy that closes the gap",
    "electricity demand (TWh)": "Follows from fewer heat pumps than the pathways assume",
    "peak demand (GW)": "Not like for like: the model's peak is the highest hour of the measured 2024 demand shape scaled up "
                        "(48 GW in 2024); FES gives an average-cold-spell peak that includes demand met by embedded plant (58 GW in 2025)",
    "batteries (GW)": "Built through the Capacity Market and merchant decisions on revenue the model can see; Capacity Market "
                      "agreements already held by batteries not yet built are not in the starting pipeline",
    "unabated gas (GW)": "Existing plant closes on age (40 years) or after two loss-making years without an agreement",
    "gas CCS (GW)": "Tendered to the pathway, limited by the build rate of 1.5 GW a year",
    "hydrogen power (GW)": "Tendered to the pathway, limited by the build rate of 1.5 GW a year",
    "offshore wind (GW)": "A round held in 2025 delivers in 2030 (five-year lead time) and no more than 6 GW can come online "
                          "in a year; the contracted pipeline alone gives 36 GW by 2031",
    "onshore wind (GW)": "The build-rate limit of 2.5 GW a year",
    "interconnectors (GW)": "The project register (with NeuConnect in 2028 and GridLink in 2030) is ahead of the pathway in 2030",
    "battery electric vehicles (million)": "The driver is every battery electric vehicle in the pathway (with HGVs, buses and "
                                           "motorbikes); the published row here is cars and vans",
    "carbon intensity (gCO2/kWh)": "Direct emissions over generation including imports; definitions differ",
}


def published(p, source, pathway, metric, tech, unit, year):
    x = p[(p.source == source) & (p.pathway == pathway) & (p.metric == metric) & (p.technology == tech)
          & (p.unit == unit) & (p.year == year)]
    return float(x.value.iloc[0]) if len(x) else float("nan")


def main(path=None):
    annual = pd.read_csv(path or ROOT / "results" / "annual_baseline.csv").set_index("year")
    p = pd.read_csv(PUBLISHED, keep_default_na=False)
    p["year"] = pd.to_numeric(p.year, errors="coerce")
    p["value"] = pd.to_numeric(p.value, errors="coerce")
    f = lambda v: "–" if v != v else (f"{v:.0f}" if abs(v) >= 100 else f"{v:.1f}")
    md = ["| quantity | role | year | model | FES 2025, four pathways | CCC Balanced | Clean Power 2030 | in FES range |",
          "|---|---|---|---|---|---|---|---|"]
    outside = []
    for label, role, col, metric, tech, unit in ROWS:
        for y in YEARS:
            if y not in annual.index:
                continue
            r = annual.loc[y]
            m = col(r) if callable(col) else r.get(col, float("nan"))
            fes = [published(p, "NESO FES", w, metric, tech, unit, y) for w in FES]
            fes = [v for v in fes if v == v]
            ccc = published(p, "CCC Seventh Carbon Budget", "Balanced Pathway", metric, tech, unit, y)
            cp = [published(p, "DESNZ Clean Power 2030 Action Plan", f"Clean Power Capacity Range ({k})", metric, tech, unit, y)
                  for k in ("low", "high")]
            lo, hi = (min(fes), max(fes)) if fes else (float("nan"), float("nan"))
            tol = 0.05 * max(abs(hi), 1.0)
            verdict = "–" if not fes else ("yes" if lo - tol <= m <= hi + tol else ("below" if m < lo else "above"))
            if verdict in ("below", "above"):
                outside.append((label, y, verdict))
            cp_txt = f"{f(cp[0])}–{f(cp[1])}" if cp[0] == cp[0] else "–"
            md.append(f"| {label} | {role} | {y} | {f(m)} | {f(lo)}–{f(hi)} | {f(ccc)} | {cp_txt} | {verdict} |")
    notes = ["", "## Where the model is outside the FES range", ""]
    for label in dict.fromkeys(l for l, _, _ in outside):
        ys = ", ".join(f"{y} ({v})" for l, y, v in outside if l == label)
        notes.append(f"* **{label}**: {ys}. {WHY.get(label, 'Not yet explained')}.")
    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    except Exception:
        commit = "unknown"
    head = ("# The model's future years against published pathways\n\nBaseline, one seed (the file's), code at "
            f"{commit}. Published values: NESO FES 2025 (GB), CCC Seventh Carbon Budget Balanced Pathway (UK), Clean Power "
            "2030 Action Plan capacity range (GB).\nRole: *driver* = taken from the FES pathway the scenario follows; "
            "*target* = the government's target path is the pathway's capacity;\n*result* = decided in the model. "
            "\"In FES range\" allows 5 % either side.\n\n")
    out = ROOT / "results" / "pathways_comparison.md"
    out.write_text(head + "\n".join(md + notes) + "\n", encoding="utf-8")
    print(head + "\n".join(md + notes))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
