"""Technology, fuel and policy assumptions.

All values are *indicative* and in real 2024 GBP. They are placeholders chosen to be in the
range of public sources (DESNZ Electricity Generation Costs 2023, NESO FES 2025, UK ETS prices)
and MUST be reviewed before quantitative use. See docs/assumptions.md.
"""
import csv
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

PARAMETERS = Path(__file__).resolve().parents[1] / "data" / "parameters"
HISTORY_DIR = Path(__file__).resolve().parents[1] / "data" / "history"


@dataclass(frozen=True)
class Tech:
    name: str
    capex: float          # GBP/kW (overnight, incl. IDC approx.)
    fom: float            # GBP/kW/yr fixed O&M
    vom: float            # GBP/MWh variable O&M
    efficiency: float     # electrical efficiency (thermal); 1 for VRE
    fuel: str | None      # key into fuel prices
    co2_t_per_mwh_fuel: float  # tCO2 per MWh of fuel burnt (after capture)
    life: int             # economic life, years
    lead_time: int        # years from decision to operation
    availability: float   # average availability for thermal / firm plant
    derating: float       # capacity market de-rating factor
    profile: str | None = None   # 'wind_onshore', 'wind_offshore', 'solar' for VRE
    investable: bool = True
    chunk_mw: float = 500.0


GAS_T_PER_MWH = 0.184  # tCO2 per MWh_th natural gas

# Capital cost, fixed O&M, variable O&M, efficiency and life of wind, solar and gas plant are those of
# DESNZ Electricity Generation Costs 2025 for projects commissioning in 2030 (2024 prices), as built
# into data/parameters/cost_paths.csv by scripts/build_costs.py: capital = pre-development +
# construction + infrastructure (overnight; financing during construction is added by capex_kw);
# fixed O&M includes insurance and connection and use-of-system charges. tests/test_costs.py checks
# that the numbers here equal the table. Nuclear, biomass, hydro and storage are not in that edition:
# their values are indicative (ASSUMPTION).
# Capacity Market de-rating factors: NESO, 2030-31 T-4 auction (PyPSA-GB data/market/scarcity/
# neso_cm_derating_factors.csv): CCGT 0.9048, OCGT and engines 0.9297, nuclear 0.7566, biomass 0.8908,
# hydro 0.906, coal 0.804 (2026-27), storage by duration (2 h 0.2231, 8 h and longer 0.9075).
TECHS: dict[str, Tech] = {t.name: t for t in [
    Tech("nuclear", 7000, 120, 8, 0.33, "uranium", 0.0, 60, 10, 0.80, 0.7566, investable=True, chunk_mw=1600),
    Tech("ccgt", 1034.6, 22.9, 5, 0.54, "gas", GAS_T_PER_MWH, 25, 3, 0.90, 0.9048, chunk_mw=800),
    Tech("ocgt", 664.1, 16.4, 5, 0.35, "gas", GAS_T_PER_MWH, 25, 2, 0.92, 0.9297, chunk_mw=300),
    Tech("gas_ccs", 2242.4, 35.5, 6, 0.47, "gas", GAS_T_PER_MWH * 0.1, 25, 6, 0.88, 0.9048, chunk_mw=800),
    Tech("h2_turbine", 1199.1, 21.4, 5, 0.51, "hydrogen", 0.0, 25, 3, 0.92, 0.9048, chunk_mw=300),
    # biomass availability 0.70: GB biomass output 19.9 TWh in 2025 (NESO) = 60 % load factor on the
    # 3.8 GW fleet; Drax flexes its RO units seasonally and has long outages (Drax FY2025 results)
    # November 2026: 0.78 on the 3.0 GW of transmission-connected conversions gives the same 2025 output
    Tech("biomass", 2500, 90, 6, 0.38, "biomass", 0.0, 25, 4, 0.78, 0.8908, investable=False),
    Tech("wind_onshore", 1695.9, 39.9, 0, 1.0, None, 0.0, 35, 3, 1.0, 0.08, profile="wind_onshore", chunk_mw=500),
    Tech("wind_offshore", 2670.0, 141.6, 0, 1.0, None, 0.0, 30, 5, 1.0, 0.10, profile="wind_offshore", chunk_mw=1000),
    Tech("solar", 647.3, 9.1, 0, 1.0, None, 0.0, 38, 1, 1.0, 0.03, profile="solar", chunk_mw=500),
    # hydro availability 0.26: NESO's mix has 3.4-3.6 TWh of hydro a year (2024-25) on the model's 1.5 GW
    Tech("hydro", 3000, 40, 0, 1.0, None, 0.0, 60, 5, 0.26, 0.906, investable=False),
    Tech("battery", 600, 10, 1, 0.85, None, 0.0, 15, 1, 0.95, 0.2231, chunk_mw=500),   # 2h; round-trip eff
    Tech("pumped_hydro", 2500, 25, 1, 0.75, None, 0.0, 60, 8, 0.95, 0.9075, investable=False),
    # Coal: for historical years only (the last GB station closed in September 2024). Indicative values.
    Tech("coal", 1800, 40, 4, 0.36, "coal", 0.34, 45, 6, 0.85, 0.804, investable=False),
    # "Other": the transmission-metered plant NESO's mix reports as OTHER (energy from waste, CHP, oil):
    # 3.3 TWh in 2024, 4.7 TWh in 2025, on about 0.7 GW (DUKES 2026 Table 5.12, other fuels). It runs
    # whatever the price (MUST_RUN_OFFER). Its emissions are outside the model's carbon cost; NESO's
    # carbon intensity counts it at 300 g/kWh (NESO_CI_FACTORS).
    Tech("other", 0, 0, 0, 1.0, "waste", 0.0, 60, 3, 0.65, 0.50, investable=False),
]}
# Who decides, by default (scenario keys of the same names override; README items 1-6). Since November
# 2026: firms bid and invest on their own expectations over the life of the asset, the government
# tracks its capacity targets within a GBP budget, and the system operator sets the Capacity Market
# target from the reliability standard. The benchmark scenario "legacy_rules" has the earlier defaults
# (rules / fixed / formula).
DEFAULTS = {"decision_logic": "expectations", "government": "targets", "system_operator": "standard"}

MUST_RUN_OFFER = -50.0       # GBP/MWh offer of plant that runs whatever the price ("other", nuclear)

# Day-ahead offers of supported renewables, by the terms of their support. These are the rules of
# PyPSA-GB's wholesale stage (scripts/market/curtailment_order.py, revenue_tracking.py), which follow
# the contract terms:
# * Renewables Obligation plant earns its certificates on every MWh, so it offers at minus the
#   certificate value: banding (ROCs/MWh) x ROC price. Bandings: PyPSA-GB data/market/support/
#   support_schemes.csv (Ofgem); biomass conversions 1.0 (Ofgem banding table).
# * CfDs of the investment contracts and allocation rounds 1-3 are paid through negative prices
#   (rounds 2-3 unless six hours run negative), so they offer at minus the strike.
# * CfDs from round 4 on are paid nothing when the price is negative: they offer at zero and receive
#   no difference payment in hours with a negative price.
# * Merchant wind, solar and hydro offer at a small variable cost and give way first.
RO_BANDS = {"wind_onshore": 0.9, "wind_offshore": 2.0, "solar": 1.2, "hydro": 1.0, "biomass": 1.0}
MERCHANT_RENEWABLE_OFFER = 0.5      # GBP/MWh
CFD_FROM_AR4_OFFER = 0.0            # GBP/MWh

# Scarcity mark-up on the day-ahead price as the de-rated margin falls: the stepped curve PyPSA-GB
# fitted to the 2024 gap between N2EX day-ahead prices and its model price, binned on NESO's de-rated
# margin (PyPSA-GB data/market/scarcity/scarcity_curve_2024.json; the step below 1 GW is the BSC
# reserve scarcity price, LoLP x VoLL). (margin below, MW; GBP/MWh). The margin is available GB
# capacity (thermal plant at its availability, wind and solar at output, storage and interconnectors
# at Capacity Market de-rating factors) less demand. DESNZ's Dynamic Dispatch Model prices scarcity the
# same way. Scenario key `scarcity_adder`: true (this curve) | "ordc" (the earlier formula) | false.
SCARCITY_STEPS = ((20000.0, 6.81), (15000.0, 7.99), (12000.0, 10.15), (10000.0, 12.56), (8000.0, 17.16),
                  (6000.0, 38.46), (4000.0, 86.66), (2000.0, 229.49), (1000.0, 1357.2))
INTERCONNECTOR_DERATING = 0.6       # median of NESO's interconnector de-rating factors, 2030-31 T-4

STORAGE_TECHS = {"battery": 2.0, "pumped_hydro": 8.0}   # duration hours

# Technology cost trajectories (README roadmap item 19): capital cost (GBP/kW) and fixed O&M
# (GBP/kW/yr) by the year a plant comes online, real 2024 prices, linear between points and flat
# outside them. A technology or item without a path keeps its TECHS value in every year. The same
# paths serve the agents, the planner and the system-cost accounting, in hindcasts and in future years.
# Values and sources: data/parameters/cost_paths.csv (loaded below) and docs/assumptions.md.
COST_PATHS: dict[str, dict[str, dict[int, float]]] = {}
# Years between the (capital-weighted) spending of the capital cost and the first year of operation:
# pre-development spent halfway through its period, construction halfway through its own (DESNZ
# Electricity Generation Costs 2025 periods). Capital is carried over this lag at the discount rate of
# whoever values the project, which is the financing cost during construction.
BUILD_LAG = {"wind_offshore": 1.8, "wind_onshore": 1.2, "solar": 0.6, "ccgt": 1.5, "ocgt": 1.0, "gas_ccs": 1.5,
             "h2_turbine": 1.6, "nuclear": 4.0, "battery": 0.5}
# Hurdle rates by technology (pre-tax real) for projects with contracted revenue: CEPA (2025) for DESNZ,
# as used in Electricity Generation Costs 2025 (solar and onshore wind 7.6 %, offshore wind and gas
# 8.9 %, batteries 8.9 %, nuclear under RAB 7.6 %, CCUS and hydrogen power 8.9-10.1 %). A project on
# merchant revenue needs MERCHANT_UPLIFT more (CEPA central estimate 1.5 points; survey range 1.5-3).
# A firm's own cost of capital shifts every rate by (its wacc - REFERENCE_WACC). CEPA puts the
# uncertainty of each rate at 1.1-1.7 points.
HURDLE_RATE = {"wind_offshore": 0.089, "wind_onshore": 0.076, "solar": 0.076, "ccgt": 0.089, "ocgt": 0.089,
               "gas_ccs": 0.089, "h2_turbine": 0.089, "battery": 0.089, "nuclear": 0.076}
HURDLE_DEFAULT = 0.089
MERCHANT_UPLIFT = 0.015
REFERENCE_WACC = 0.077       # mean WACC of the five firm types (ukabm.model.FIRM_TYPES, GENCO_SPECS)


def _load_cost_paths(path: Path = PARAMETERS / "cost_paths.csv") -> None:
    """Fill COST_PATHS from the cost table (scripts/build_costs.py); costs before the first published
    year are held at that year's value."""
    if not path.exists():
        return
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            for item in ("capex", "fom"):
                COST_PATHS.setdefault(r["tech"], {}).setdefault(item, {})[int(r["online"])] = float(r[item])


def _path_value(tech: str, item: str, online: int | None, default: float) -> float:
    path = COST_PATHS.get(tech, {}).get(item)
    if not path or online is None:
        return default
    ys = sorted(path)
    return float(np.interp(online, ys, [path[y] for y in ys]))


def capex_kw(tech: str, online: int | None = None, rate: float | None = None) -> float:
    """Capital cost (GBP/kW) of *tech* coming online in *online* (None: the TECHS reference value).
    With *rate*, the cost includes financing over the build lag at that rate (BUILD_LAG)."""
    c = _path_value(tech, "capex", online, TECHS[tech].capex)
    return c if rate is None else c * (1 + rate) ** BUILD_LAG.get(tech, 0.0)


def hurdle_rate(tech: str, wacc: float | None = None, contracted: bool = True) -> float:
    """Required return on a *tech* project for a firm with cost of capital *wacc* (None: the reference
    firm), with contracted revenue (CfD, Capacity Market agreement, PPA) or merchant."""
    r = HURDLE_RATE.get(tech, HURDLE_DEFAULT) + (0.0 if wacc is None else wacc - REFERENCE_WACC)
    return max(r + (0.0 if contracted else MERCHANT_UPLIFT), 0.01)


def fom_kw(tech: str, online: int | None = None) -> float:
    """Fixed O&M (GBP/kW/yr) of a *tech* plant that came online in *online*."""
    return _path_value(tech, "fom", online, TECHS[tech].fom)

# Battery revenues beyond the model's hourly day-ahead arbitrage (stylised; see docs/assumptions.md).
# Each stream is a pot (GBP/yr) shared across the battery fleet, so revenue per MW falls as the fleet
# grows (saturation). Calibrated to the 2025 GB 2-hour BESS revenue stack: Modo Energy ME BESS GB index
# GBP 73k/MW/yr over the 12 months to April 2026, ~60 % from wholesale + Balancing Mechanism trading;
# frequency response ~GBP 20-25k/MW/yr through 2025 (Modo monthly reports).
# * ancillary (frequency response + reserve): fixed-size market. GBP 100m/yr = GBP 20k/MW on the
#   model's 5 GW 2025 fleet.
# * intraday + BM trading the hourly day-ahead clearing does not see: pot proportional to wind+solar
#   capacity (forecast-error and balancing volume). 3960 GBP/yr per MW of VRE tops the fleet's modelled
#   2025 day-ahead arbitrage (~GBP 5.6k/MW) up to ~GBP 44k/MW of trading revenue on 48.5 GW of VRE.
# Per-MW revenue is not extrapolated above its 2025 level for fleets smaller than the 2025 fleet.
# November 2026: the 2025 fleet is 6.4 GW (DUKES 2026 Table 5.16), not 5 GW, and wind and solar 51.5 GW,
# not 48.5 GW; the pots are re-based so that revenue per MW on the 2025 fleet is unchanged
# (GBP 20k/MW ancillary: 128m on 6.4 GW; GBP 38.4k/MW trading top-up: 246m on 51.5 GW of VRE).
BATTERY_ANCILLARY_POT = 128e6            # GBP/yr
BATTERY_TRADING_PER_MW_VRE = 4780.0      # GBP/yr per MW of wind + solar capacity
BATTERY_FLEET_FLOOR_MW = 6400.0          # 2025 fleet in INITIAL_FLEET_MW

# Reserve and response in the optimum and the evaluator (README roadmap item 9). The agents' batteries
# are paid for services the hourly market does not see (the two pots above); the system needs those
# services whoever builds it, so the planner and the evaluator must hold them too. Stylised, matched
# to the two pots:
# * response (matches the fixed ancillary pot): a fixed MW of headroom on storage every hour, sized to
#   the largest infrequent infeed loss of the GB SQSS (1,800 MW);
# * reserve (matches the trading pot, which scales with wind and solar): headroom on any flexible plant
#   or storage equal to a share of the hour's available wind and solar output (forecast error), plus a
#   share of load.
# Storage needs `hours` of stored energy behind each MW it holds. Reserve not held costs
# `shortfall_cost` per MWh, so a fleet that cannot meet it is costed rather than infeasible.
# A scenario can override any key with `reserve: {...}`; `scale` multiplies the three sizes (0 = off).
RESERVE = dict(
    response_mw=1800.0,
    vre_share=0.10,
    load_share=0.0,
    hours=1.0,
    shortfall_cost=1000.0,
    generators=("ccgt", "ocgt", "gas_ccs", "h2_turbine", "biomass", "hydro"),
    storage=("battery", "pumped_hydro"),
)
VRE_TECHS = {"wind_onshore", "wind_offshore", "solar"}
# Column of the hourly profile table that gives each technology's capacity-factor shape.
VRE_PROFILE = {"wind_onshore": "wind_onshore_cf", "wind_offshore": "wind_offshore_cf", "solar": "solar_cf"}
# Annual capacity factor of new wind and solar by the year a plant comes online (linear between
# points, flat outside). The hourly profiles are measured on the existing fleet; new plant yields more
# (larger rotors, higher hubs, sites further offshore). Empty: new build has the fleet's profile.
# A scenario can override it with `new_build_cf`. Values and sources: docs/assumptions.md.
# Offshore and onshore wind: the first point is measured, the mean 2021-2025 capacity factor (output
# plus turn-down added back) of the GB wind farms commissioned since 2020 (data/profiles/
# wind_cf_by_vintage_<year>.csv: offshore 0.43-0.46, onshore 0.26-0.36); later points are the load
# factors DESNZ Electricity Generation Costs 2025 assumes for projects commissioning in 2030, 2035
# and 2040. Solar: DESNZ's UK load factor of 2022-2025 (0.10-0.11, Energy Trends 6.1), then its 2025
# assumption of 0.12 for large-scale solar.
NEW_BUILD_CF: dict = {
    "wind_offshore": {2026: 0.445, 2030: 0.48, 2035: 0.49, 2040: 0.50},
    "wind_onshore": {2026: 0.315, 2030: 0.36, 2035: 0.37},
    "solar": {2026: 0.11, 2030: 0.12},
}

# GB fleet in 2025 (MW): the mean of installed capacity at the end of 2024 and of 2025 (DESNZ, DUKES
# 2026 Table 5.12, GB, all generators; data/history/gb_capacity.csv), so that the 2025 operating year
# sees the capacity that was there on average. How each total is spread over zones, vintages and
# support schemes comes from data/fleet (scripts/build_fleet.py).
#   wind_offshore 16,140 -> 16,650; wind_onshore 14,728 -> 14,912; solar 19,047 -> 21,517;
#   battery 5,210 -> 7,512 (Table 5.16, UK grid-scale); nuclear 5,883; pumped_hydro 2,900.
# Departures from the table, because generation is compared with NESO's transmission-metered mix
# and embedded thermal plant is netted off NESO demand:
#   ccgt 30,000: between 28.8 GW transmission-connected and 31.2 GW in all;
#   ocgt 3,700: OCGT, gas engines and other gas (3,663); oil-fired plant (1,089) left out;
#   biomass 3,000: the transmission-connected conversions (3,035) of 6.5 GW of bioenergy;
#   hydro 1,500 (1,884 in the table; 775 MW transmission-connected), see Tech availability.
INITIAL_FLEET_MW = {
    "nuclear": 5900, "ccgt": 30000, "ocgt": 3700, "biomass": 3000,
    "wind_onshore": 14800, "wind_offshore": 16400, "solar": 20300, "hydro": 1500,
    "battery": 6400, "pumped_hydro": 2900, "other": 700,
}


def _load_table(path: Path, key: str) -> dict:
    """{key value: {year: number}} from a tidy CSV with a `year` column (empty if the file is missing)."""
    out: dict = {}
    if path.exists():
        with open(path, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if key in r:                      # long format: year, <key>, mw
                    out.setdefault(r[key], {})[int(r["year"])] = float(r["mw"])
                else:                             # wide format: year, col1, col2, ...
                    for k, v in r.items():
                        if k != "year" and v not in ("", "nan"):
                            out.setdefault(k, {})[int(r["year"])] = float(v)
    return out


# GB installed capacity at the end of each year 2011-2025 by technology (DUKES 2026 Tables 5.12, 5.16),
# and annual fuel, carbon and power prices 2010-2025; both built by scripts/build_history.py.
GB_CAPACITY = _load_table(HISTORY_DIR / "gb_capacity.csv", "tech")
HISTORY = _load_table(HISTORY_DIR / "annual_inputs.csv", "")


def history_value(name: str, year: int, basis: str = "real") -> float | None:
    """Historical annual value of *name* (gas, coal, carbon, power_day_ahead) in *year*: in 2024 prices
    (basis "real") or in money of the day ("nominal"); basis "raw" reads a column as it is (e.g.
    gbp_per_eur). None if the year is not in the table."""
    key = name if basis == "raw" else f"{name}_{'2024' if basis == 'real' else 'nominal'}"
    v = HISTORY.get(key, {}).get(year)
    return None if v is None else float(v)


def fleet_mw(year: int) -> dict:
    """GB fleet (MW by technology) for a model that starts in *year*: INITIAL_FLEET_MW for 2025 and
    later; for an earlier year the same definitions applied to that year's capacity table (mean of the
    end of the previous year and of the year). Nuclear is set by ukabm.model.NUCLEAR_UNITS."""
    if year >= 2025 or not GB_CAPACITY:
        return dict(INITIAL_FLEET_MW)

    def mean(k, y=year):
        s = GB_CAPACITY.get(k, {})
        vals = [s[t] for t in (y - 1, y) if t in s]
        return sum(vals) / len(vals) if vals else 0.0
    out = dict(INITIAL_FLEET_MW)
    for k in ("wind_offshore", "wind_onshore", "solar", "ocgt", "coal"):
        out[k] = mean(k)
    out["battery"] = mean("battery_uk")
    out["biomass"] = mean("biomass_transmission")
    out["other"] = mean("other_fuels")
    out["ccgt"] = INITIAL_FLEET_MW["ccgt"] * mean("ccgt") / mean("ccgt", 2025)
    return {k: v for k, v in out.items() if v > 0}
# Technical life (years) of plant in the starting fleet where it differs from the economic life of
# new build in TECHS: GB CCGTs of the 1990s are still operating (DUKES 2026 Table 5.11 lists 11.4 GW
# commissioned before 2000), so existing gas plant closes on age only at 40 (CCGT) or 45 (peaking
# plant) years; before that it closes when it loses money (model retirement rule). A plant already past
# this age at the start stays EXISTING_MIN_YEARS more years. ASSUMPTION.
EXISTING_LIFE = {"ccgt": 40, "ocgt": 45}
EXISTING_MIN_YEARS = 5
# Existing-fleet performance that differs from new-build Tech values (calibration to 2025 outturn).
# CCGT: GB fleet thermal efficiency ~50 % (GCV) — DUKES Table 5.10 (CCGT stations, 2023-24); the
# 0.54 in TECHS is new-build. Initial-fleet CCGTs get an efficiency that falls linearly with age
# from 0.54 (new) to 0.46 (end of life), fleet mean ~0.50, which gives the merit order a realistic
# slope instead of one cost step. (newest, oldest) per tech:
EXISTING_FLEET_EFFICIENCY = {"ccgt": (0.54, 0.46)}

# Emission factors (gCO2/kWh) used by NESO's carbon-intensity methodology, so that model output can
# be compared like-for-like with NESO's published CI (which counts biomass at 120 and imports at
# per-country factors). Source: NESO Carbon Intensity API methodology (CCGT 394, OCGT 651, biomass
# 120). Imports: 65 = average implied by NESO's 2024-25 half-hourly CI after removing gas, biomass
# and "other" (57 in 2024, 74 in 2025; computed from data/outturn source data). Technologies not
# listed count as zero (gas_ccs uses its direct factor in the model).
NESO_CI_FACTORS = {"ccgt": 394.0, "ocgt": 651.0, "biomass": 120.0, "imports": 65.0, "coal": 937.0, "other": 300.0}



# Capacity target path for the target-tracking government (ukabm.institutions, GW installed), used
# only without a FES pathway (scenario fes_pathway "none"); with one, the targets are the pathway's
# capacities (ukabm.drivers). 2025: the starting fleet as it was before November 2026. 2030: lower ends of the Clean Power 2030 Action Plan ranges (DESNZ,
# Dec 2024: offshore 43-50 GW, onshore 27-29 GW, solar 45-47 GW). 2035 and 2050: indicative
# (ASSUMPTION, FES-like; to be sourced from FES 2025). Linear between points, flat after 2050.
CFD_TARGET_GW = {
    "wind_offshore": {2025: 15.5, 2030: 43.0, 2035: 60.0, 2050: 90.0},
    "wind_onshore": {2025: 15.0, 2030: 27.0, 2035: 32.0, 2050: 40.0},
    "solar": {2025: 18.0, 2030: 45.0, 2035: 60.0, 2050: 80.0},
}
# Target-tracking government's rules (override per scenario with "government_params").
GOVERNMENT_TARGETS = dict(
    levy_threshold=30.0,     # GBP/MWh policy levy above which round budgets are cut
    levy_budget_scale=0.6,   # budget multiplier while the levy is above the threshold
    cap_step=0.15,           # cap rise after a round that failed for lack of bids under the cap
    cap_ceiling=2.0,         # caps never exceed this multiple of the policy cap
    budget_headroom=1.1,     # budget = missing MW x expected support x this
)
# Bills-first government: overrides GOVERNMENT_TARGETS (ASSUMPTION, illustrative).
GOVERNMENT_BILLS = dict(levy_threshold=20.0, levy_budget_scale=0.4, cap_step=0.05)
# Political government (ASSUMPTION, illustrative): UK general elections every 5 years, next by 2029.
GOVERNMENT_POLITICAL = dict(
    first_election=2029, election_every=5,
    pre_election_years=2,        # rounds held in the two years before an election are cut back
    pre_election_scale=0.3,      # share of the missing capacity funded before an election
    post_election_scale=1.3,     # budget uplift in the other years (catch-up)
    target_ambition=1.15,        # announced targets above the target path
)
# System operator's reliability standard (ukabm.institutions.SystemOperator, "standard" mode).
SYSTEM_OPERATOR = dict(
    lole_h=3,                # GB reliability standard: 3 hours loss of load expectation a year
    weather_margin=0.0,      # extra de-rated capacity for weather beyond the model's one year (share)
    t1_holdback=0.025,       # share of the target left to the T-1 auction (~1.0 of 40.1 GW, 2029/30)
)


# CPI 2012 -> 2024 prices for CfD strikes: AR7 offshore GBP 65.45 (2012) = GBP 91.20 (2024), DESNZ 2025.
CPI_2012_TO_2024 = 1.393
# T-4 Capacity Market clearing prices (GBP/kW/yr, nominal) for delivery years auctioned before 2025:
# 2024/25 18.00, 2025/26 30.59, 2026/27 63.00, 2027/28 65.00, 2028/29 60.00 (NESO Capacity Market
# auction static data; data/history/sources/cm_auctions.csv). The model gives existing
# dispatchable plant these one-year agreements for the delivery years before its own first T-4 auction.
LEGACY_CM_PRICE = {2025: 30.59, 2026: 63.00, 2027: 65.00, 2028: 60.00}
# Renewables Obligation: closed to new capacity in 2017, support for at most 20 years, scheme ends 2037.
RO_LAST_ONLINE, RO_YEARS, RO_SCHEME_END = 2017, 20, 2037


@dataclass
class Policy:
    carbon_price_2025: float = 65.0      # GBP/t, UK ETS + Carbon Price Support: 2025 outturn GBP 67.4 = 65.1 in 2024 prices
    carbon_price_2050: float = 180.0
    cfd_enabled: bool = True
    cfd_budget_gw_per_year: float = 6.0  # capacity procured per allocation round
    cfd_admin_strike_cap: dict = field(default_factory=lambda: {
        "wind_offshore": 113.0, "wind_onshore": 89.0, "solar": 85.0, "nuclear": 110.0})
    cm_enabled: bool = True
    cm_net_cone: float = 49.0            # GBP/kW/yr (PyPSA-GB cm_auction_parameters)
    cm_price_cap: float = 75.0
    cm_reliability_margin: float = 0.06  # target derated margin over peak
    ro_value: float = 65.0               # GBP per ROC: buy-out price 2024-25 GBP 64.73 (Ofgem); x config.RO_BANDS per MWh
    hp_grant: float = 7500.0             # Boiler Upgrade Scheme GBP
    gas_levy_rebalancing: float = 0.0    # GBP/MWh moved from electricity to gas bills
    voll: float = 6000.0
    dpa_enabled: bool = True             # government tenders gas CCS and hydrogen power to its pathway (with fes_pathway)
    history_basis: str = "real"          # historical years: 2024 prices ("real") or money of the day ("nominal")

    def carbon_price(self, year: int) -> float:
        if year < 2025 or self.history_basis == "nominal":        # outturn (config.HISTORY) where there is one
            h = history_value("carbon", year, self.history_basis)
            if h is not None:
                return h
        f = min(max((year - 2025) / 25, 0), 1)
        return self.carbon_price_2025 + f * (self.carbon_price_2050 - self.carbon_price_2025)


# Central wholesale gas price path (GBP/MWh_th, NBP; 1 p/therm = 0.3412 GBP/MWh_th), linear between
# points and flat after the last. Re-based in November 2026 for the 2026 price spike:
# * 2025 = 29.4: NBP day-ahead outturn 89.2 p/therm = GBP 30.45/MWh, 29.4 in 2024 prices (Ofgem);
# * 2026 = 55: spot rose from ~80 p/therm at the start of the year to 218-234 p/therm in November
#   (Trading Economics, 26 Nov 2026); annual mean is an ASSUMPTION;
# * 2027 = 63: forward curve 25 Nov 2026, Q1-27 ~223 p/therm (GBP 76), Summer-27 ~160 p/therm (GBP 55)
#   (Catalyst Commercial UK wholesale gas prices), Q4-27 assumed between the two;
# * 2028 = 45, 2030 = 35: ASSUMPTION, easing as the spike unwinds (no reliable 2028 quote found);
# * 2035 onwards: the pre-spike central path (32 -> 25 by 2050, interpolated).
GAS_PATH_CENTRAL = {2025: 29.4, 2026: 55.0, 2027: 63.0, 2028: 45.0, 2030: 35.0, 2035: 29.2, 2050: 25.0}

# Social discount rate for system-cost accounting and the planner benchmark (HM Treasury Green Book
# STPR, 3.5 %). Both runs are costed at this rate, so the gap measures misallocation, not who finances it.
SOCIAL_DISCOUNT_RATE = 0.035

# Build-rate limits (MW of new capacity per year, by technology). Supply-chain limits that apply to any
# decision-maker: the planner, and since November 2026 the firms too (auction awards and merchant
# projects coming online in one year; scenario key agent_build_limits). ASSUMPTION, of the order of the
# fastest rates in NESO FES 2025 Holistic Transition / Clean Power 2030. New nuclear is limited to what
# the committed units already give both runs (Hinkley C, Sizewell C), because agents cannot build it.
PLANNER_BUILD_MW_PER_YEAR = {
    "wind_offshore": 6000, "wind_onshore": 2500, "solar": 6000, "battery": 5000,
    "ccgt": 3000, "ocgt": 2000, "gas_ccs": 1500, "h2_turbine": 1500, "nuclear": 0,
}


# The planner is solved on a sample of days: one in seven, plus for every investment period this many
# days with the highest daily peak and this many with the highest daily mean of load net of wind and
# solar (ukabm.planner.sample_days). 0 = the earlier rule (one peak day per period).
PLANNER_EXTREME_DAYS = 8


@dataclass
class Fuels:
    gas_2025: float | None = None   # if both set: linear gas path 2025 -> 2050 instead of the central path
    gas_2050: float | None = None
    gas_adder: float = 0.0          # GBP/MWh_th added to every year of the gas path (high_gas scenario)
    gas_path: dict = field(default_factory=lambda: dict(GAS_PATH_CENTRAL))
    uranium: float = 2.5          # GBP/MWh_th
    biomass: float = 25.0
    hydrogen: float = 80.0        # GBP/MWh_th delivered (hook: could be endogenous)
    coal: float = 14.0            # GBP/MWh_th where there is no outturn (2024: 13.99, DESNZ QEP 3.2.1)
    waste: float = 0.0            # fuel of the must-run "other" plant
    history_basis: str = "real"   # historical years: 2024 prices ("real") or money of the day ("nominal")

    def _history(self, name: str, year: int) -> float | None:
        if year < 2025 or self.history_basis == "nominal":
            return history_value(name, year, self.history_basis)
        return None

    def gas(self, year: int) -> float:
        h = self._history("gas", year)
        if h is not None:
            return h + self.gas_adder
        if self.gas_2025 is not None and self.gas_2050 is not None:
            f = min(max((year - 2025) / 25, 0), 1)
            base = self.gas_2025 + f * (self.gas_2050 - self.gas_2025)
        else:
            ys = sorted(self.gas_path)
            base = float(np.interp(year, ys, [self.gas_path[y] for y in ys]))
        return base + self.gas_adder

    def price(self, fuel: str | None, year: int) -> float:
        if fuel is None:
            return 0.0
        if fuel == "gas":
            return self.gas(year)
        if fuel == "coal":
            h = self._history("coal", year)
            return self.coal if h is None else h
        return getattr(self, fuel)


_load_cost_paths()
