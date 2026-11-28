# Parameter register

Every constant in `ukabm/config.py`, the module-level constants of `ukabm/model.py`, the class
constants of `ExpectationBids` in `ukabm/decisions.py`, the constants of `ukabm/institutions.py` and
`ukabm/planner.py`, and the constructor defaults of the modules in `ukabm/multienergy.py`, as they are
on the branch `foundations/implementation` (commit a47ec5f). A last section lists numbers that are written inline in
the code rather than named, and the constants of the data adapter `ukabm/data/pypsagb.py`, because
they act as parameters too.

## How to read the status

Each row has exactly one status, taken from the comment next to the value in the code:

| Status | Meaning |
|---|---|
| `sourced` | A published value. The code comment names the publisher or document; the register repeats it. |
| `measured` | Computed from data kept in the repository; the register says which file. |
| `calibrated` | Set so that the model reproduces an observed quantity; the register says which, and in which year. |
| `assumed` | The authors' judgement. Used wherever the comment says ASSUMPTION, "indicative" or "illustrative", and wherever the comment gives no source, even if the value looks like a well-known published figure. Nothing has been upgraded: where a published figure exists but the code does not cite it, the row says so in the basis column and keeps `assumed`. |

A row may group several values that share one status and one basis (for example the capital costs of
seven technologies from the same DESNZ table). The counts at the end count rows. Values are real 2024
pounds unless stated. "Table: <file>" means the value is read from a data file at import time.

Some constants are not model parameters: file paths, keys used inside the code, lists that name which
technologies a function treats as wind or storage, and solver options. They are listed once, at the
end, without a status and outside the counts.

## 1. Technologies (`config.TECHS`)

`TECHS` holds one `Tech` record per technology. Fields: capital cost `capex` (£/kW, overnight),
fixed O&M `fom` (£/kW/yr), variable O&M `vom` (£/MWh), `efficiency` (electrical; round trip for
storage), economic `life` (years), `lead_time` from decision to operation (years), `availability`
(share of capacity available, thermal and firm plant), Capacity Market `derating`, project size
`chunk_mw` (MW), emissions `co2_t_per_mwh_fuel`.

| Name | Value | Unit | Status | Basis | Used in |
|---|---|---|---|---|---|
| `TECHS[...]`.capex, fom, vom, efficiency, life for wind_onshore, wind_offshore, solar, ccgt, ocgt, gas_ccs, h2_turbine | e.g. offshore 2670 £/kW, 141.6 £/kW/yr, life 30; CCGT 1034.6, 22.9, 5, 0.54, 25 | as fields | sourced | DESNZ *Electricity Generation Costs 2025*, projects commissioning 2030, central (= 2030 row of `data/parameters/cost_paths.csv`; `tests/test_costs.py` checks equality) | costs, bids, NPVs, planner, settlement |
| `TECHS["nuclear"]`.capex, fom, vom, efficiency, life | 7000, 120, 8, 0.33, 60 | as fields | assumed | "indicative (ASSUMPTION)": not in the 2025 edition | settlement, planner (no new nuclear can be built) |
| `TECHS[...]`.capex, fom, vom, efficiency, life for biomass, hydro, pumped_hydro, coal, other | biomass 2500/90/6/0.38/25; hydro 3000/40/0/1/60; pumped hydro 2500/25/1/0.75/60; coal 1800/40/4/0.36/45; other 0/0/0/1/60 | as fields | assumed | "indicative (ASSUMPTION)"; none is investable, so capex matters only for sunk-cost accounting | settlement, dispatch |
| `TECHS["battery"]`.capex, fom, vom, efficiency, life | 600, 10, 1, 0.85, 15 | as fields | assumed | "indicative (ASSUMPTION)"; `docs/assumptions.md` notes £600/kW looks high against 2025 projects | bids, NPVs, planner |
| `TECHS[...]`.availability for ccgt, ocgt, gas_ccs, h2_turbine, nuclear (new), battery, pumped_hydro, coal | 0.90, 0.92, 0.88, 0.92, 0.80, 0.95, 0.95, 0.85 | share | assumed | no source in the code | offers (available MW), margins |
| `TECHS["biomass"]`.availability | 0.78 | share | calibrated | GB biomass output 2025 (19.9 TWh, NESO) on the 3.0 GW of transmission-connected conversions | dispatch |
| `TECHS["hydro"]`.availability | 0.26 | share | calibrated | NESO mix 3.4–3.6 TWh of hydro a year (2024–25) on 1.5 GW | dispatch |
| `TECHS["other"]`.availability | 0.65 | share | calibrated | NESO mix "OTHER" 3.3 TWh (2024) and 4.7 TWh (2025) on about 0.7 GW | dispatch |
| `TECHS[...]`.derating for ccgt, ocgt, nuclear, biomass, hydro, coal, battery (2 h), pumped_hydro (8 h) | 0.9048, 0.9297, 0.7566, 0.8908, 0.906, 0.804, 0.2231, 0.9075 | share | sourced | NESO de-rating factors, 2030-31 T-4 auction (coal: 2026-27), via PyPSA-GB `neso_cm_derating_factors.csv` | CM auction, SO target, scarcity margin |
| `TECHS[...]`.derating for gas_ccs, h2_turbine | 0.9048 | share | assumed | CCGT factor applied by analogy; no own source | CM auction |
| `TECHS[...]`.derating for wind_onshore, wind_offshore, solar, other | 0.08, 0.10, 0.03, 0.50 | share | assumed | no source in the code | `formula` CM target, long-horizon forecasts |
| `TECHS[...]`.lead_time | nuclear 10, ccgt 3, ocgt 2, gas_ccs 6, h2 3, biomass 4, onshore 3, offshore 5, solar 1, hydro 5, battery 1, pumped hydro 8, coal 6, other 3 | years | assumed | no source in the code | online year of every new plant; which technologies can enter a T-4 or T-1 auction |
| `TECHS[...]`.chunk_mw | nuclear 1600, ccgt 800, ocgt 300, gas_ccs 800, h2 300, onshore 500, offshore 1000, solar 500, battery 500 (others 500) | MW | assumed | no source; sets project lumpiness | CfD, CM, merchant and tender blocks |
| `GAS_T_PER_MWH` | 0.184 | tCO2/MWh fuel | assumed | no source in the code (a standard factor for natural gas) | emissions, carbon cost |
| `TECHS["gas_ccs"]`.co2 | 0.1 × `GAS_T_PER_MWH` (90 % capture) | tCO2/MWh fuel | assumed | no source | emissions |
| `TECHS["coal"]`.co2 | 0.34 | tCO2/MWh fuel | assumed | "Indicative values" | emissions (historical years) |
| `TECHS[...]`.investable | False for biomass, hydro, pumped_hydro, coal, other | – | assumed | modelling choice: these cannot be built by anyone | options of firms and planner |

## 2. Who decides, by default

| Name | Value | Unit | Status | Basis | Used in |
|---|---|---|---|---|---|
| `DEFAULTS` | decision_logic "expectations", government "targets", system_operator "standard" | – | assumed | authors' choice of the default rule set (since November 2026); `legacy_rules` keeps the earlier one | `decisions.for_genco`, `institutions` |

## 3. Market offers, scarcity, interconnectors and storage

| Name | Value | Unit | Status | Basis | Used in |
|---|---|---|---|---|---|
| `MUST_RUN_OFFER` | −50 | £/MWh | assumed | no source | offers of nuclear and "other" |
| `RO_BANDS` | onshore 0.9, offshore 2.0, solar 1.2, hydro 1.0, biomass 1.0 | ROC/MWh | sourced | Ofgem bandings via PyPSA-GB `support_schemes.csv`; biomass conversions from the Ofgem banding table | offers and settlement of RO plant |
| `MERCHANT_RENEWABLE_OFFER` | 0.5 | £/MWh | assumed | rule taken from PyPSA-GB's wholesale stage ("a small variable cost"); the number is a convention | offers of merchant wind, solar, hydro |
| `CFD_FROM_AR4_OFFER` | 0.0 | £/MWh | sourced | CfD terms from allocation round 4: no difference payment at negative prices (as coded in PyPSA-GB) | offers of CfD plant from AR4 |
| `SCARCITY_STEPS` | (20 GW, 6.81), (15, 7.99), (12, 10.15), (10, 12.56), (8, 17.16), (6, 38.46), (4, 86.66), (2, 229.49), (1, 1357.2) | GW de-rated margin; £/MWh | calibrated | by PyPSA-GB, to the 2024 gap between N2EX day-ahead prices and its model price, binned on NESO's de-rated margin; the last step is the BSC reserve scarcity price | market clearing (`scarcity_adder` true) |
| `INTERCONNECTOR_DERATING` | 0.6 | share | sourced | median of NESO's interconnector de-rating factors, 2030-31 T-4 | scarcity margin |
| `STORAGE_TECHS` | battery 2.0, pumped_hydro 8.0 | hours | assumed | no source | storage dispatch, planner, de-rating choice |
| `STORAGE_TRANCHES` (model) | battery 3, pumped_hydro 1 | – | assumed | no source; limits the fleet's price impact on itself | `run_market` |
| `IC_PRICE_LEVEL` (model) | continent 0.68, SEM 1.10 | × SRMC of an existing GB CCGT | calibrated | 2025 ratios of neighbour to GB day-ahead prices (Energy-Charts/SMARD, Ember) | foreign prices in future years |
| `IC_SPREAD` (model) | 12.0 | £/MWh | calibrated | 2025 gross flows (imports 44.0 TWh, exports 14.8 TWh; Elexon FUELHH) | import offers and export bids |
| `IC_AVAILABILITY` (model) | 0.9 | share | measured | 2025 peak import 9.2 GW on 10.5 GW (`data/outturn/gb_annual_outturn.csv`, `fuelhh_ic_peak_import_gw`) | interconnector blocks |
| `NET_STRATA` (model) | 8 | strata | assumed | no source | network-stage hour sample |
| `NUCLEAR_BM_BID` (model) | −300 | £/MWh | assumed | no source ("effectively never turned down") | network stage |
| `Policy.voll` | 6000 | £/MWh | assumed | no source in the code (the 3 h standard was derived from £16,950/MWh; see `docs/assumptions.md`) | clearing cap, unserved-energy cost, planner |

## 4. Costs, finance and discounting

| Name | Value | Unit | Status | Basis | Used in |
|---|---|---|---|---|---|
| `COST_PATHS` | table: `data/parameters/cost_paths.csv` | £/kW, £/kW/yr by online year 2030–2050 | sourced | DESNZ *Electricity Generation Costs 2025*, central; years before 2030 held at 2030 | `capex_kw`, `fom_kw` everywhere |
| `BUILD_LAG` for offshore, onshore, solar, ccgt, ocgt, gas_ccs, h2_turbine | 1.8, 1.2, 0.6, 1.5, 1.0, 1.5, 1.6 | years | sourced | capital-weighted mid-points of pre-development and construction periods, DESNZ EGC 2025 | financing during construction |
| `BUILD_LAG` for nuclear, battery | 4.0, 0.5 | years | assumed | no source; neither technology is in EGC 2025 | financing during construction |
| `HURDLE_RATE` | onshore, solar, nuclear 0.076; offshore, ccgt, ocgt, gas_ccs, h2, battery 0.089 | real pre-tax | sourced | CEPA (2025) for DESNZ, as used in EGC 2025 | bids and NPVs (shifted by firm WACC) |
| `HURDLE_DEFAULT` | 0.089 | real pre-tax | assumed | default for technologies without a rate | `hurdle_rate` |
| `MERCHANT_UPLIFT` | 0.015 | added to rate | sourced | CEPA central estimate 1.5 points (survey range 1.5–3) | merchant NPVs, CfD merchant tail |
| `REFERENCE_WACC` | 0.077 | share | assumed | mean WACC of the five firm types, which are assumed; comment refers to `GENCO_SPECS` | shifts every firm's hurdle rates |
| `SOCIAL_DISCOUNT_RATE` | 0.035 | share | sourced | HM Treasury Green Book STPR 3.5 %. The README and assumptions note that the Green Book rate has been 3.0 % since October 2026 | system cost, planner, ideal agents |
| `Policy.carbon_price_2025` | 65.0 | £/tCO2 | sourced | UK ETS + Carbon Price Support, 2025 outturn £67.4 = £65.1 in 2024 prices | carbon path |
| `Policy.carbon_price_2050` | 180.0 | £/tCO2 | assumed | no source; linear from 2025 | carbon path |

## 5. Fuel prices (`config.Fuels`, `GAS_PATH_CENTRAL`)

| Name | Value | Unit | Status | Basis | Used in |
|---|---|---|---|---|---|
| `GAS_PATH_CENTRAL[2025]` | 29.4 | £/MWh_th | sourced | NBP day-ahead outturn 89.2 p/therm (Ofgem), in 2024 prices | SRMC, forecasts |
| `GAS_PATH_CENTRAL[2026]` | 55.0 | £/MWh_th | assumed | annual mean of the 2026 spike "is an ASSUMPTION" (spot 218–234 p/therm in November 2026, Trading Economics) | SRMC |
| `GAS_PATH_CENTRAL[2027]` | 63.0 | £/MWh_th | sourced | forward curve 25 Nov 2026, Q1-27 and Summer-27 (Catalyst Commercial); Q4-27 assumed between them | SRMC |
| `GAS_PATH_CENTRAL[2028]`, `[2030]` | 45.0, 35.0 | £/MWh_th | assumed | ASSUMPTION, easing as the spike unwinds | SRMC |
| `GAS_PATH_CENTRAL[2035]`, `[2050]` | 29.2, 25.0 | £/MWh_th | assumed | "the pre-spike central path"; no source given | SRMC |
| `Fuels.coal` | 14.0 | £/MWh_th | sourced | DESNZ QEP Table 3.2.1, 2024: 13.99 (used where there is no outturn) | coal SRMC |
| `Fuels.uranium`, `biomass`, `hydrogen`, `waste` | 2.5, 25.0, 80.0, 0.0 | £/MWh_th | assumed | no source | SRMC |
| `Fuels.gas_adder`, `gas_2025`, `gas_2050` | 0, None, None | £/MWh_th | assumed | scenario levers (`high_gas` sets the adder to 15) | gas path |

## 6. Battery revenue outside the hourly market

| Name | Value | Unit | Status | Basis | Used in |
|---|---|---|---|---|---|
| `BATTERY_ANCILLARY_POT` | 128e6 | £/yr | calibrated | £20k/MW/yr of frequency response on the 2025 fleet (Modo Energy monthly reports, 2025), re-based to 6.4 GW | battery settlement, NPVs, CM bids |
| `BATTERY_TRADING_PER_MW_VRE` | 4780 | £/yr per MW of wind and solar | calibrated | 2025 GB 2-hour battery revenue (Modo ME BESS GB index £73k/MW/yr, 12 months to April 2026, ~60 % from trading) | as above |
| `BATTERY_FLEET_FLOOR_MW` | 6400 | MW | sourced | 2025 fleet in `INITIAL_FLEET_MW` (DUKES 2026 Table 5.16) | per-MW revenue cap for small fleets |

## 7. Reserve and response in the planner and evaluator (`config.RESERVE`)

| Name | Value | Unit | Status | Basis | Used in |
|---|---|---|---|---|---|
| `RESERVE["response_mw"]` | 1800 | MW | sourced | largest infrequent infeed loss of the GB SQSS | `planner._add_reserve` |
| `RESERVE["vre_share"]` | 0.10 | share of available wind and solar | assumed | stylised, matched to the battery trading pot | `planner._add_reserve` |
| `RESERVE["load_share"]` | 0.0 | share of load | assumed | stylised | `planner._add_reserve` |
| `RESERVE["hours"]` | 1.0 | h of stored energy per MW held | assumed | stylised | `planner._add_reserve` |
| `RESERVE["shortfall_cost"]` | 1000 | £/MWh | assumed | stylised; makes a shortfall costly rather than infeasible | planner objective, evaluator cost |
| `RESERVE["generators"]`, `["storage"]` | CCGT, OCGT, gas CCS, H2, biomass, hydro; battery, pumped hydro | – | assumed | which plant may hold reserve | `planner._add_reserve` |

## 8. Wind and solar capacity factors of new build (`config.NEW_BUILD_CF`)

| Name | Value | Unit | Status | Basis | Used in |
|---|---|---|---|---|---|
| `NEW_BUILD_CF["wind_offshore"][2026]` | 0.445 | annual CF | measured | mean 2021–2025 CF (with turn-down added back) of GB offshore farms commissioned since 2020, `data/profiles/wind_cf_by_vintage_<year>.csv` | `cf_profile` of new plant |
| `NEW_BUILD_CF["wind_onshore"][2026]` | 0.315 | annual CF | measured | as above, onshore | `cf_profile` |
| `NEW_BUILD_CF["wind_offshore"][2030, 2035, 2040]` | 0.48, 0.49, 0.50 | annual CF | sourced | DESNZ EGC 2025 load factors for projects commissioning in those years | `cf_profile` |
| `NEW_BUILD_CF["wind_onshore"][2030, 2035]` | 0.36, 0.37 | annual CF | sourced | DESNZ EGC 2025 | `cf_profile` |
| `NEW_BUILD_CF["solar"][2026]` | 0.11 | annual CF | sourced | DESNZ UK solar load factor 2022–2025, Energy Trends 6.1 | `cf_profile` |
| `NEW_BUILD_CF["solar"][2030]` | 0.12 | annual CF | sourced | DESNZ 2025 assumption for large-scale solar | `cf_profile` |

## 9. Starting fleet and existing plant

| Name | Value | Unit | Status | Basis | Used in |
|---|---|---|---|---|---|
| `INITIAL_FLEET_MW` for wind_offshore, wind_onshore, solar, battery, nuclear, pumped_hydro | 16400, 14800, 20300, 6400, 5900, 2900 | MW | sourced | DESNZ DUKES 2026 Tables 5.12 and 5.16, mean of end-2024 and end-2025 (nuclear is then set by `NUCLEAR_UNITS`) | `_init_fleet` |
| `INITIAL_FLEET_MW["ocgt"]` | 3700 | MW | sourced | DUKES 2026: OCGT, engines and other gas 3,663 MW (oil left out) | `_init_fleet` |
| `INITIAL_FLEET_MW["biomass"]` | 3000 | MW | sourced | DUKES 2026: transmission-connected conversions 3,035 MW | `_init_fleet` |
| `INITIAL_FLEET_MW["other"]` | 700 | MW | sourced | DUKES 2026 Table 5.12, other fuels, about 0.7 GW | `_init_fleet` |
| `INITIAL_FLEET_MW["ccgt"]` | 30000 | MW | assumed | chosen between 28.8 GW transmission-connected and 31.2 GW in all | `_init_fleet` |
| `INITIAL_FLEET_MW["hydro"]` | 1500 | MW | assumed | chosen between 775 MW transmission-connected and 1,884 MW in DUKES | `_init_fleet` |
| `GB_CAPACITY` | table: `data/history/gb_capacity.csv` | MW by technology, 2011–2025 | sourced | DUKES 2026 Tables 5.12, 5.16 | `fleet_mw` for start years before 2025 |
| `HISTORY` | table: `data/history/annual_inputs.csv` | prices 2010–2025 | sourced | Ofgem, DESNZ, UK ETS Authority, ECB (`scripts/build_history.py`) | fuel and carbon prices before 2025, back-casts |
| `EXISTING_LIFE` | ccgt 40, ocgt 45 | years | assumed | ASSUMPTION (11.4 GW of pre-2000 CCGT still operates, DUKES Table 5.11) | retirement age of the starting fleet |
| `EXISTING_MIN_YEARS` | 5 | years | assumed | ASSUMPTION | plant already past that age |
| `EXISTING_FLEET_EFFICIENCY` | ccgt (0.54 new, 0.46 oldest) | efficiency (GCV) | calibrated | fleet mean ~0.50 (DUKES Table 5.10, 2023–24) and the 2025 merit order | starting CCGT fleet; foreign price reference |
| `NUCLEAR_UNITS`: capacity and closure year of existing units | AGRs 2300 + 1200 + 1200 MW to 2029; Sizewell B 1200 MW to 2035; Hunterston B 985 and Hinkley Point B 965 MW to 2021 | MW, year | sourced | EDF fleet update (January 2026), Centrica (July 2026), DUKES 2026 Table 5.11 | `_init_fleet` |
| `NUCLEAR_UNITS`: availability | AGRs 0.62, Sizewell B 0.88 | share | calibrated | GB nuclear output 38.4 TWh (2024) and 34.2 TWh (2025), NESO; EDF fleet update | dispatch |
| `NUCLEAR_UNITS`: Hinkley Point C and Sizewell C | 2 × 1630 MW online 2030, 2031; 2 × 1600 MW online 2038, 2039 | MW, year | assumed | "indicative public dates"; no source in the code | committed fleet of both runs |
| `NUCLEAR_UNITS`: zones | Z9, Z6, Z12, Z17, Z5 | zone | sourced | station locations; Torness's position south of boundary B5 from SP Energy Networks RIIO-T2 Business Plan Annex 4 (2019) | network stage only |
| `NUCLEAR_OWNER` | "EDF" | – | assumed | no source (Centrica's 20 % of the AGRs is not represented) | owner of nuclear units |
| `LEGACY_CM_PRICE` | 2025 30.59, 2026 63.00, 2027 65.00, 2028 60.00 | £/kW/yr nominal | assumed | marked "ASSUMPTION to confirm against the published results". The values agree with the T-4 clearing prices in `data/history/sources/cm_auctions.csv` | agreements of existing plant before the first modelled T-4 |
| `CPI_2012_TO_2024` | 1.393 | factor | sourced | AR7 offshore £65.45 (2012) = £91.20 (2024), DESNZ 2025 | CfD strikes of existing plant and pipeline |
| `RO_LAST_ONLINE`, `RO_YEARS`, `RO_SCHEME_END` | 2017, 20, 2037 | year, years, year | assumed | scheme rules stated without a source in the code (`data/history/sources/ro_fit.csv` holds Ofgem sources) | random-fleet rule; RO end years |

## 10. Emission factors for reporting (`config.NESO_CI_FACTORS`)

| Name | Value | Unit | Status | Basis | Used in |
|---|---|---|---|---|---|
| `NESO_CI_FACTORS` ccgt, ocgt, biomass | 394, 651, 120 | g/kWh | sourced | NESO Carbon Intensity API methodology | `intensity_neso_g_kwh` |
| `NESO_CI_FACTORS["other"]` | 300 | g/kWh | sourced | NESO carbon intensity counts "other" at 300 g/kWh (comment on `TECHS["other"]`; also `scripts/fetch_outturn.py`) | as above |
| `NESO_CI_FACTORS["imports"]` | 65 | g/kWh | measured | average implied by NESO's 2024–25 half-hourly CI after removing gas, biomass and other (57 in 2024, 74 in 2025), computed from data/outturn source data | as above |
| `NESO_CI_FACTORS["coal"]` | 937 | g/kWh | assumed | no source in the code | as above |

## 11. Policy instruments (`config.Policy`)

| Name | Value | Unit | Status | Basis | Used in |
|---|---|---|---|---|---|
| `Policy.cfd_budget_gw_per_year` | 6.0 | GW per round | assumed | the original fixed rule | `government: "fixed"` only |
| `Policy.cfd_admin_strike_cap` | offshore 113, onshore 89, solar 85, nuclear 110 | £/MWh (2024) | assumed | no source in the code | initial caps of every government |
| `Policy.cm_net_cone` | 49.0 | £/kW/yr | sourced | PyPSA-GB `cm_auction_parameters` (DESNZ letters). **Not used anywhere in the code** | – |
| `Policy.cm_price_cap` | 75.0 | £/kW/yr | assumed | no source in the code (equals the price cap in `data/pypsagb_snapshot/cm_auction_parameters.csv`) | CM demand curve and bids |
| `Policy.cm_reliability_margin` | 0.06 | share of peak | assumed | no source | `formula` CM target, long-horizon forecasts |
| `Policy.ro_value` | 65.0 | £/ROC | sourced | buy-out price 2024-25 £64.73 (Ofgem) | RO offers, settlement, BM bids |
| `Policy.hp_grant` | 7500 | £ | sourced | Boiler Upgrade Scheme grant | household choice |
| `Policy.gas_levy_rebalancing` | 0.0 | £/MWh | assumed | scenario lever (`heat_push` sets 25) | retail prices |
| `CFD_TARGET_GW` 2025 points | offshore 15.5, onshore 15.0, solar 18.0 | GW | assumed | comment says "the model's starting fleet", but the values differ from `INITIAL_FLEET_MW` (16.4, 14.8, 20.3 GW) | government targets when `fes_pathway = "none"` |
| `CFD_TARGET_GW` 2030 points | offshore 43, onshore 27, solar 45 | GW | sourced | lower ends of the Clean Power 2030 Action Plan ranges (DESNZ, December 2024) | as above |
| `CFD_TARGET_GW` 2035 and 2050 points | offshore 60, 90; onshore 32, 40; solar 60, 80 | GW | assumed | ASSUMPTION, "FES-like" | as above |
| `GOVERNMENT_TARGETS["levy_threshold"]` | 30.0 | £/MWh | assumed | no source | budget squeeze |
| `GOVERNMENT_TARGETS["levy_budget_scale"]` | 0.6 | factor | assumed | no source | budget squeeze |
| `GOVERNMENT_TARGETS["cap_step"]` | 0.15 | share | assumed | no source | cap rise after a failed round |
| `GOVERNMENT_TARGETS["cap_ceiling"]` | 2.0 | × initial cap | assumed | no source | cap limit |
| `GOVERNMENT_TARGETS["budget_headroom"]` | 1.1 | factor | assumed | no source | round budget |
| `GOVERNMENT_BILLS` | levy_threshold 20, levy_budget_scale 0.4, cap_step 0.05 | as above | assumed | ASSUMPTION, illustrative | `government: "bills"` |
| `GOVERNMENT_POLITICAL` | first_election 2029, election_every 5, pre_election_years 2, pre_election_scale 0.3, post_election_scale 1.3, target_ambition 1.15 | years, factors | assumed | ASSUMPTION, illustrative | `government: "political"` |
| `SYSTEM_OPERATOR["lole_h"]` | 3 | h/yr | sourced | GB reliability standard, 3 hours loss of load expectation | `standard` CM target |
| `SYSTEM_OPERATOR["weather_margin"]` | 0.0 | share | assumed | no source | `standard` CM target |
| `SYSTEM_OPERATOR["t1_holdback"]` | 0.025 | share | sourced | ~1.0 of 40.1 GW held back for T-1, delivery 2029/30 (DESNZ parameters letter) | T-4 / T-1 split |
| `PLANNER_BUILD_MW_PER_YEAR` | offshore 6000, onshore 2500, solar 6000, battery 5000, ccgt 3000, ocgt 2000, gas_ccs 1500, h2 1500, nuclear 0 | MW/yr | assumed | ASSUMPTION, "of the order of" the fastest FES 2025 / Clean Power 2030 rates. Scenario key `build_limits` overrides any entry for the planner and the firms alike (`scripts/run_gap.py` uses onshore 1,240 and solar 2,900 MW/yr in its "pathway limits" sensitivity) | planner; firms' build room (`agent_build_limits`); government tender |
| `PLANNER_EXTREME_DAYS` | 8 | days per criterion and period | assumed | no source | planner day sample |

## 12. Firms (`ukabm/model.py`)

| Name | Value | Unit | Status | Basis | Used in |
|---|---|---|---|---|---|
| `FIRM_TYPES` wacc | utility 0.07, generator 0.10, major 0.08, fund 0.06, developer 0.075 | share | assumed | ASSUMPTION; the spread is of the size of CEPA's (2025) uncertainty on hurdle rates | hurdle-rate shift |
| `FIRM_TYPES` expectation | utility, major, fund "adaptive"; generator "myopic"; developer "carbon_optimist" | – | assumed | ASSUMPTION | carbon and capture-price expectations |
| `FIRM_TYPES` markup | 0.03, 0.08, 0.02, 0.0, 0.0 | share of SRMC | assumed | ASSUMPTION | thermal offers |
| `FIRM_TYPES` risk_aversion | 0.0 for all | share | assumed | zero because risk is already in the hurdle rates | NPV haircut, CfD premium |
| `FIRM_TYPES` budget_gbp | 2e9, 1e9, 4e9, 3e9, 2e9 | £/yr | assumed | ASSUMPTION | merchant budget per year |
| `FIRM_TYPES` tech_preference | utility: all; generator: gas, CCS, H2, battery; major: offshore, solar, CCS, H2, battery; fund: wind, solar, battery; developer: onshore, solar, battery, OCGT | – | assumed | ASSUMPTION | which auctions and projects a firm enters |
| `GENCO_SPECS` | five stylised firms with the same trait values (budgets 4e9, 1.5e9, 6e9, 3e9, 2e9) | as above | assumed | used with scenario `firms = "stylised"` | `legacy_rules`, `competitive_benchmark` |
| `DPA_TECHS` | gas_ccs, h2_turbine | – | assumed | technologies built only under a government contract | `dpa_round` |

## 13. Firms' decision rules (`ukabm/decisions.py`, class `ExpectationBids`)

| Name | Value | Unit | Status | Basis | Used in |
|---|---|---|---|---|---|
| `ExpectationBids.CONTRACT_YEARS` | 20 | years | assumed | no source (the model's CfD awards also run 20 years) | CfD bid |
| `ExpectationBids.BASIS` | 0.02 | share of output | assumed | no source | CfD bid |
| `ExpectationBids.HAIRCUT` | 0.15 | share | assumed | no source | adaptive firms' tail capture price |
| `ExpectationBids.PPA_YEARS` | 15 | years | assumed | no source | PPA option |
| `ExpectationBids.PPA_DISCOUNT` | 0.10 | share below capture price | assumed | "the offtaker's margin and risk"; no source | PPA option |
| `ExpectationBids.PPA_RATE_CUT` | 0.015 | rate | sourced | equal to `MERCHANT_UPLIFT` (CEPA 2025): contracted revenue removes the merchant uplift | PPA option |

## 14. Institutions (`ukabm/institutions.py`)

| Name | Value | Unit | Status | Basis | Used in |
|---|---|---|---|---|---|
| `CFD_TECHS` | wind_offshore, wind_onshore, solar | – | assumed | the CfD pots modelled (tidal, floating wind and others are left out) | CfD rounds, government |
| `FixedRules` pot shares (default of scenario key `cfd_pots`) | offshore 0.6, onshore 0.2, solar 0.2 | share | assumed | the original fixed rule | `government: "fixed"` |

## 15. Multi-energy modules (`ukabm/multienergy.py`, constructor defaults)

With the default `fes_pathway`, the EV stock, EV energy and electrolyser capacity come from FES 2025
and the EV and hydrogen defaults marked † are not used.

| Name | Value | Unit | Status | Basis | Used in |
|---|---|---|---|---|---|
| `HeatModule.n_agents` | 2000 | agents | assumed | no source | household cohorts |
| `HeatModule.homes` | 28e6 | homes | assumed | no source in the code | homes per agent |
| `HeatModule.hp_homes_2025` | 0.6e6 | homes | assumed | no source in the code | initial heat pumps |
| `GasNetworkModule.allowed_revenue_gbp` | 5.5e9 | £/yr | assumed | no source | gas network tariff |
| `GasNetworkModule.nondomestic_twh` | 230.0 | TWh/yr | assumed | no source | gas throughput |
| `EVModule.stock_2025` † | 1.5e6 | vehicles | assumed | ASSUMPTION ("FES-like") | EV demand |
| `EVModule.stock_sat`, `mid_year`, `k` † | 30e6, 2036, 0.35 | vehicles, year, 1/yr | assumed | logistic path, ASSUMPTION | EV stock |
| `EVModule.mwh_per_ev` † | 2.6 | MWh/vehicle/yr | assumed | no source | EV demand |
| `EVModule.smart_share_2025`, `smart_share_2040` | 0.1, 0.6 | share | assumed | no source (used with or without FES) | smart charging |
| `HydrogenModule.gw_2030`, `gw_2050` † | 1.0, 10.0 | GW | assumed | ASSUMPTION ("FES-like") | electrolyser capacity |
| `HydrogenModule.eff` | 0.7 | share | assumed | no source | willingness to pay |
| `HydrogenModule.h2_value` | 80.0 | £/MWh H2 | assumed | no source (equals `Fuels.hydrogen`) | willingness to pay |

## 16. Planner (`ukabm/planner.py`)

| Name | Value | Unit | Status | Basis | Used in |
|---|---|---|---|---|---|
| `NEW_TECHS` | offshore, onshore, solar, battery, ccgt, ocgt, gas_ccs, h2_turbine, nuclear | – | assumed | the planner's option set (nuclear limited to 0 MW/yr by the build limits) | `plan` |
| `plan(every_nth_day=7)` | 7 | days | assumed | one ordinary day in seven sampled | `sample_days` |

## 17. Numbers written inline in the code

These are not named constants but change results. All are `assumed` unless stated.

| Where | Value | Unit | Status | Basis | Effect |
|---|---|---|---|---|---|
| `model.GBMarketModel.__init__`: `base_demand_growth` default | 0.003 | 1/yr | assumed | no source | base demand to 2025, or always with `fes_pathway = "none"` |
| `model.__init__`: initial `levy`, `cm_clearing` | 20, 30 | £/MWh, £/kW/yr | assumed | starting values | first government round, first bids |
| `model.cm_auction`, `forecast_horizons`; `institutions.SystemOperator.cm_target` (T-1) | 0.45 × interconnector capacity | share | assumed | no source; differs from `INTERCONNECTOR_DERATING` (0.6) used in the scarcity margin | CM supply and targets |
| `model.cm_auction`: demand curve width | target ± 1500 | MW | sourced | equal to the published 2030/31 curve (DESNZ July 2026 letter, `cm_auction_parameters.csv`); code comment says "PyPSA-GB parameters style" | CM clearing |
| `model.cm_auction`: new-build agreement length; existing plant | 15 years (cm_end = dy + 14); 1 year | years | assumed | no source | CM payments |
| `model.cm_auction`: `cm_new_chunks` default; bid step per extra project | 4; +3 % | projects; share | assumed | no source | CM new-build supply |
| `model.cfd_round`: blocks bid per firm and technology; contract length | 2; 20 years (cfd_end = online + 19) | blocks; years | assumed | no source | CfD supply |
| `model._init_fleet`: CfD of Hinkley Point C and Sizewell C | strike £92.50 (2012 prices) × CPI; 35 years | £/MWh; years | assumed | no source in the code. £92.50 is the 2016 HPC strike (NAO 2017, in `data/history/sources/closures_openings.csv`); the snapshot register gives £89.50 since Sizewell C's financial close | nuclear revenue, CfD cost |
| `model._pathway_fleet`: minimum block | 400 | MW | assumed | no source | committed nuclear and pumped hydro from FES |
| `model.invest`: `max_merchant_decisions` default | 6 | decisions/yr | assumed | no source | merchant investment |
| `model.step`: retirement rule | 2 loss years in a row, no CM agreement in the next 4 years | – | assumed | no source | closures of gas, biomass, batteries, CCS, H2 |
| `model.step`: retail adders | electricity +70 network +25 supplier; gas +12; 35 % of rebalancing on gas | £/MWh | assumed | no source | household heat choice |
| `model.demand`: heat pumps and EVs already in base demand | 0.6 m heat pumps; 1.2 m EVs (without FES) | homes, vehicles | assumed | no source | added demand |
| `model.interconnector_blocks`: decline of foreign prices | −25 % relative to the GB CCGT by 2050 | share | assumed | ASSUMPTION (continental decarbonisation) | imports, exports |
| `model.expected_margin_per_mw`: `vre_haircut` | 0.15 | share | assumed | stands for cannibalisation | wind and solar margins (rules) |
| `model.forecast_horizons`: horizons; VRE trend window | t+8, t+13; 5 years | years | assumed | no source | lifetime NPVs |
| `decisions.RuleBased.expected_carbon`: optimist factor | 1.3 | × carbon path | assumed | no source | carbon belief |
| `decisions.RuleBased.cfd_bid`, `ExpectationBids.cfd_bid`: noise | ±5 % (rules), ±2 % (expectations), normal | share | assumed | project-specific costs | CfD bids |
| `decisions.ExpectationBids`: risk premium; minimum PPA rate | strike / max(1 − 0.5 × risk aversion, 0.5); 0.03 | –; rate | assumed | no source | CfD bids, PPA NPV |
| `decisions.RuleBased.cm_bid`: annuity period | 15 years | years | assumed | CM agreement length | CM bids |
| `institutions.TargetTracking.observe`: failed round | accepted < 50 % of the limit, with bids over the cap | share | assumed | no source | cap rise |
| `market.clear`: `scarcity_sigma` | 2500 | MW | assumed | no source | ORDC mode (`scarcity_adder = "ordc"`) only |
| `market.storage_arbitrage`: `min_spread` | 5.0 | £/MWh | assumed | no source | storage dispatch |
| `network.redispatch`: load shed price | 6000 | £/MWh | assumed | hard-coded VoLL | network stage |
| `multienergy.HeatModule`: household attributes | heat demand lognormal (median 11.5 MWh, σ 0.35); discount rate U(0.04, 0.20); hassle cost lognormal (median £4,000, σ 0.6); boiler age U(0, 14); 85 % on the gas grid | various | assumed | no source | heat choice |
| `multienergy.HeatModule`: technology and choice | COP 2.9; boiler efficiency 0.88; off-grid fuel 1.6 × gas; heat pump £11,000 − grant; boiler £3,000; replacement at 15 years or 2 %/yr; 15-year horizon; hassle falls by 80 % at 30 % adoption; logit scale £1,500 | various | assumed | no source | heat choice |
| `multienergy.synthetic_temperature`, `heat_shape` | seasonal 10.5 ± 6.5 °C, diurnal ± 2.5 °C, 7-day noise; base 15.5 °C; peak hours × 1.35; hot water 8 % | °C, shares | assumed | ASSUMPTION ("replace with ERA5/atlite") | heat-pump load shape |
| `multienergy.GasNetworkModule.update` | allowed revenue −1 %/yr after 2030; non-domestic gas −1.5 %/yr | 1/yr | assumed | ASSUMPTION | gas network tariff |
| `multienergy.EVModule.hourly_load` | unmanaged profile points; charger 7 kW; 50 % plugged in; smart window 21:00–08:00 | kW, share, hours | assumed | no source | EV load |
| `multienergy.HydrogenModule.capacity_mw` (without FES) | none before 2027; ramp to `gw_2030` by 2030 | – | assumed | no source | electrolyser capacity |

## 18. Data adapter (`ukabm/data/pypsagb.py`)

| Name | Value | Unit | Status | Basis | Used in |
|---|---|---|---|---|---|
| `BOUNDARY_MW` | B0, B2, B4, B5, B6 capability for 2025, 2030, 2035 | MW | sourced | NESO Holistic Transition build-out as tabulated by LCP Delta, *From Bottlenecks to Balance* (March 2026), p. 58 | network stage |
| `HVDC_STEPS` | Caithness–Moray 1.2 GW (2019), Shetland 0.6 GW (2024), Western HVDC 2.25 GW (2018), EGL1 2 GW (2027), EGL2 2 GW (2029), EGL3/4 4 GW (2031) | MW, year | sourced | SSEN Transmission (2022); Ofgem ASTI (2024) | network stage |
| `AVAIL_SCOT`, `AVAIL_B5`, `AVAIL_EW` | monthly available share of boundary capability | share | sourced | LCP Delta (2026), p. 59 (NESO day-ahead constraint limits 2019–24) | network stage |
| `SCOT_OUTAGE_DERATE` | 2025: 0.76 | factor | sourced | LCP Delta (2026), p. 18; NESO 2025 Annual Balancing Costs Report | network stage |
| `IC_COMMISSIONING_OVERRIDES` | NeuConnect 2028, GridLink 2030, FAB Link 2031, NorthConnect never, Greenlink 2025 | year | sourced | NeuConnect; Ofgem cap-and-floor handbook (December 2024); Ofgem (November 2022); DESNZ Energy Trends (December 2025) | interconnector capacity |
| `SINGLE_WIND_SHAPE_SCALE` | onshore 0.75, offshore 1.10 × GB shape | factor | assumed | the model's original assumption; used only with the ESPENI profile | profiles |
| `GB_WIND_WEIGHTS` | onshore 15.0, offshore 15.5 | GW | assumed | "c. 2024 capacities"; no source | wind strata, SEM proxy |
| `_profiles_from_espeni` normalisation | wind: 99.9th percentile = CF 0.90; solar: = CF 0.80 | CF | assumed | ASSUMPTION; raw PyPSA-GB mode only | profiles |

## Not model parameters (listed for completeness, no status)

| Name | Where | What it is |
|---|---|---|
| `PARAMETERS`, `HISTORY_DIR` | config | data folders |
| `VRE_TECHS`, `VRE_PROFILE` | config | which technologies use an hourly profile, and its column |
| `PANEL_ROUTES`, `MERGED_KEY` | model | firm-panel column names; key offset of merged offer blocks |
| `HIGHS_OPTIONS` | planner | solver output and thread settings |
| `Policy.cfd_enabled`, `cm_enabled`, `dpa_enabled`, `history_basis`; `Fuels.history_basis`, `gas_path` (holds `GAS_PATH_CENTRAL`) | config | scenario switches |
| `GOVERNMENTS`, `REGISTRY` | institutions, decisions | registries of named rule sets |

## Counts

The counts are of rows (a row can group several values with the same status), counted on the tables
above.

| Status | Named constants (sections 1–16) | Inline numbers (section 17) | Data adapter (section 18) | All |
|---|---|---|---|---|
| sourced | 38 | 1 | 5 | 44 |
| measured | 4 | 0 | 0 | 4 |
| calibrated | 10 | 0 | 0 | 10 |
| assumed | 89 | 29 | 3 | 121 |
| total | 141 | 30 | 8 | 179 |

About two thirds of the rows are `assumed`. Most of the values that set operation and costs in the
first years (costs, hurdle rates, fleet, de-rating, support terms, profiles) are `sourced` or
`measured`; most of the values that set behaviour (firm traits, government and household rules,
lead times, build limits) and the long-run paths (gas after 2027, carbon in 2050) are `assumed`.

## Where sensitivity tests should start

No sensitivity analysis of these parameters has been run (foundations review F21; README roadmap
item 46). The assumed and calibrated values below are the ones most likely to move the headline
results, chiefly the gap between the least-cost plan and the agents' system and the 2050 fleet.

| Parameter | Status | Why test it |
|---|---|---|
| `PLANNER_BUILD_MW_PER_YEAR` | assumed | binds both runs; the planner's wind mix followed it in the foundations review (investment gap £17–45bn across the limits tried, before the separate wind profiles) |
| `FIRM_TYPES` (wacc, expectation, markup, tech_preference) | assumed | the five types set every firm's behaviour; the tech sets decide who can bid in which auction |
| `Policy.voll` and `RESERVE["shortfall_cost"]` | assumed | value unserved energy and reserve in the yardstick; the reliability standard used £16,950/MWh |
| `SOCIAL_DISCOUNT_RATE` | sourced, but superseded | the Green Book rate is 3.0 % since October 2026; it weights capex against fuel in the gap |
| `GAS_PATH_CENTRAL` after 2027 and `Policy.carbon_price_2050` | assumed | drive all SRMCs, forecasts and the value of low-carbon plant |
| `BATTERY_TRADING_PER_MW_VRE` and `BATTERY_ANCILLARY_POT` | calibrated | the 2050 battery fleet scales with the trading pot (15 / 24 / 33 GW at × 0.5 / 1 / 1.5 in an earlier model version, `docs/assumptions.md`) |
| `IC_PRICE_LEVEL`, `IC_SPREAD` and the −25 % decline of foreign prices | calibrated / assumed | set future trade on one year's ratios; net trade was worth about £17bn PV in the optimum (README roadmap item 28) |
| `ExpectationBids.HAIRCUT`, `PPA_DISCOUNT`, `BASIS` | assumed | set CfD strikes and whether merchant or PPA wind and solar is built |
| `Policy.cfd_admin_strike_cap` and `GOVERNMENT_TARGETS` | assumed | caps and budgets limit what the default government buys |
| `TECHS` lead times and `chunk_mw` | assumed | decide which plant can enter the T-4 auction and how lumpy entry is |
| Heat-pump choice parameters (hassle cost, logit scale, discount rates, retail adders) | assumed | heat-pump uptake is a result, not an input, and the main one outside the published pathways (`docs/calibration.md`) |
| `TECHS["battery"]`.capex | assumed | marked as looking high against 2025 project costs; sets battery entry in the CM |
| `SCARCITY_STEPS` | calibrated | fitted by PyPSA-GB on one year (2024); sets peak prices and so the margins of peaking plant |
| `EXISTING_LIFE` | assumed | sets when the 1990s CCGT fleet closes and so the need for new firm capacity in the 2030s |
| 0.45 interconnector de-rating in the CM | assumed | inconsistent with the 0.6 used elsewhere; moves the CM target and clearing |
