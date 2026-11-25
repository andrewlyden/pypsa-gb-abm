"""Technology, fuel and policy assumptions.

All values are *indicative* and in real 2024 GBP. They are placeholders chosen to be in the
range of public sources (DESNZ Electricity Generation Costs 2023, NESO FES 2025, UK ETS prices)
and MUST be reviewed before quantitative use. See docs/assumptions.md.
"""
from dataclasses import dataclass, field


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

TECHS: dict[str, Tech] = {t.name: t for t in [
    Tech("nuclear", 7000, 120, 8, 0.33, "uranium", 0.0, 60, 10, 0.80, 0.78, investable=True, chunk_mw=1600),
    Tech("ccgt", 750, 20, 3, 0.55, "gas", GAS_T_PER_MWH, 25, 3, 0.90, 0.88, chunk_mw=800),
    Tech("ocgt", 550, 12, 5, 0.38, "gas", GAS_T_PER_MWH, 25, 2, 0.92, 0.94, chunk_mw=300),
    Tech("gas_ccs", 1800, 45, 6, 0.48, "gas", GAS_T_PER_MWH * 0.1, 25, 6, 0.88, 0.88, chunk_mw=800),
    Tech("h2_turbine", 650, 15, 5, 0.40, "hydrogen", 0.0, 25, 3, 0.92, 0.94, chunk_mw=300),
    # biomass availability 0.70: GB biomass output 19.9 TWh in 2025 (NESO) = 60 % load factor on the
    # 3.8 GW fleet; Drax flexes its RO units seasonally and has long outages (Drax FY2025 results)
    Tech("biomass", 2500, 90, 6, 0.38, "biomass", 0.0, 25, 4, 0.70, 0.84, investable=False),
    Tech("wind_onshore", 1400, 30, 0, 1.0, None, 0.0, 25, 3, 1.0, 0.08, profile="wind_onshore", chunk_mw=500),
    Tech("wind_offshore", 2500, 60, 0, 1.0, None, 0.0, 30, 5, 1.0, 0.10, profile="wind_offshore", chunk_mw=1000),
    Tech("solar", 600, 10, 0, 1.0, None, 0.0, 30, 1, 1.0, 0.03, profile="solar", chunk_mw=500),
    Tech("hydro", 3000, 40, 0, 1.0, None, 0.0, 60, 5, 0.40, 0.37, investable=False),
    Tech("battery", 600, 10, 1, 0.85, None, 0.0, 15, 1, 0.95, 0.20, chunk_mw=500),   # 2h; round-trip eff
    Tech("pumped_hydro", 2500, 25, 1, 0.75, None, 0.0, 60, 8, 0.95, 0.80, investable=False),
]}

STORAGE_TECHS = {"battery": 2.0, "pumped_hydro": 8.0}   # duration hours

# Battery revenues beyond the model's hourly day-ahead arbitrage (stylised; see docs/assumptions.md).
# Each stream is a pot (GBP/yr) shared across the battery fleet, so revenue per MW falls as the fleet
# grows (saturation). Calibrated to the 2025 GB 2-hour BESS revenue stack: Modo Energy ME BESS GB index
# GBP 73k/MW/yr over the 12 months to April 2026, ~60 % from wholesale + Balancing Mechanism trading;
# frequency response ~GBP 20-25k/MW/yr through 2025 (Modo monthly reports).
# * ancillary (frequency response + reserve): fixed-size market. GBP 100m/yr = GBP 20k/MW on the
#   model's 5 GW 2025 fleet.
# * intraday + BM trading the hourly day-ahead clearing does not see: pot proportional to wind+solar
#   capacity (forecast-error and balancing volume). 4100 GBP/yr per MW of VRE tops the fleet's modelled
#   2025 day-ahead arbitrage (~GBP 4k/MW) up to ~GBP 44k/MW of trading revenue on 48.5 GW of VRE.
# Per-MW revenue is not extrapolated above its 2025 level for fleets smaller than the 2025 fleet.
BATTERY_ANCILLARY_POT = 100e6            # GBP/yr
BATTERY_TRADING_PER_MW_VRE = 4100.0      # GBP/yr per MW of wind + solar capacity
BATTERY_FLEET_FLOOR_MW = 5000.0          # 2025 fleet in INITIAL_FLEET_MW
VRE_TECHS = {"wind_onshore", "wind_offshore", "solar"}

# Initial GB fleet c. 2025 (MW). Indicative, consistent in magnitude with DUKES 2025 / NESO.
INITIAL_FLEET_MW = {
    "nuclear": 5900, "ccgt": 30000, "ocgt": 2000, "biomass": 3800,
    "wind_onshore": 15000, "wind_offshore": 15500, "solar": 18000, "hydro": 1500,
    "battery": 5000, "pumped_hydro": 2900,
}
# Existing-fleet performance that differs from new-build Tech values (calibration to 2025 outturn).
# CCGT: GB fleet thermal efficiency ~50 % (GCV) — DUKES Table 5.10 (CCGT stations, 2023-24); the
# 0.55 in TECHS is new-build. Initial-fleet CCGTs get an efficiency that falls linearly with age
# from 0.54 (new) to 0.46 (end of life), fleet mean ~0.50, which gives the merit order a realistic
# slope instead of one cost step. (newest, oldest) per tech:
EXISTING_FLEET_EFFICIENCY = {"ccgt": (0.54, 0.46)}

# Emission factors (gCO2/kWh) used by NESO's carbon-intensity methodology, so that model output can
# be compared like-for-like with NESO's published CI (which counts biomass at 120 and imports at
# per-country factors). Source: NESO Carbon Intensity API methodology (CCGT 394, OCGT 651, biomass
# 120). Imports: 65 = average implied by NESO's 2024-25 half-hourly CI after removing gas, biomass
# and "other" (57 in 2024, 74 in 2025; computed from data/outturn source data). Technologies not
# listed count as zero (gas_ccs uses its direct factor in the model).
NESO_CI_FACTORS = {"ccgt": 394.0, "ocgt": 651.0, "biomass": 120.0, "imports": 65.0}

# Existing nuclear retirements (MW, year) - indicative AGR closures; Hinkley C first unit
NUCLEAR_SCHEDULE = [(2028, -2300), (2030, -1200), (2030, 1600), (2031, 1600), (2035, -1200)]


@dataclass
class Policy:
    carbon_price_2025: float = 60.0      # GBP/t (UK ETS + Carbon Price Support)
    carbon_price_2050: float = 180.0
    cfd_enabled: bool = True
    cfd_budget_gw_per_year: float = 6.0  # capacity procured per allocation round
    cfd_admin_strike_cap: dict = field(default_factory=lambda: {
        "wind_offshore": 113.0, "wind_onshore": 89.0, "solar": 85.0, "nuclear": 110.0})
    cm_enabled: bool = True
    cm_net_cone: float = 49.0            # GBP/kW/yr (PyPSA-GB cm_auction_parameters)
    cm_price_cap: float = 75.0
    cm_reliability_margin: float = 0.06  # target derated margin over peak
    ro_value: float = 55.0               # GBP/MWh renewables obligation (legacy fleet)
    hp_grant: float = 7500.0             # Boiler Upgrade Scheme GBP
    gas_levy_rebalancing: float = 0.0    # GBP/MWh moved from electricity to gas bills
    voll: float = 6000.0

    def carbon_price(self, year: int) -> float:
        f = min(max((year - 2025) / 25, 0), 1)
        return self.carbon_price_2025 + f * (self.carbon_price_2050 - self.carbon_price_2025)


@dataclass
class Fuels:
    gas_2025: float = 32.0        # GBP/MWh_th wholesale
    gas_2050: float = 25.0
    uranium: float = 2.5          # GBP/MWh_th
    biomass: float = 25.0
    hydrogen: float = 80.0        # GBP/MWh_th delivered (hook: could be endogenous)

    def price(self, fuel: str | None, year: int) -> float:
        if fuel is None:
            return 0.0
        if fuel == "gas":
            f = min(max((year - 2025) / 25, 0), 1)
            return self.gas_2025 + f * (self.gas_2050 - self.gas_2025)
        return getattr(self, fuel)
