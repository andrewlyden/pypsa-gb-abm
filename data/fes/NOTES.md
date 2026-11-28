# Notes for pathways.csv

Built 2026-11-27. 1,765 rows, 12 sources. Every `read` row was taken from the primary workbook, official data table or document text; nothing was interpolated or filled from memory. The two `search` rows (Cornwall Insight) come from search-result snippets only.

## Conventions used in the CSV

- Key is unique on `source, edition, pathway, year, metric, technology, unit`. Where one source gives two definitions of the same thing, the `unit` string carries the difference (for example `gCO2/kWh` vs `gCO2/kWh excl BECCS`, `GW` vs `GWh`, `TWh` vs `TWh final`). Filter on `unit` as well as `metric`.
- Ranges are stored as two rows with `(low)` / `(high)` in `pathway`.
- Scalings only: MW to GW, GWh to TWh, units to millions. Price bases and currencies are as published and stated in `unit` (FES gas and carbon prices are in 2025 EUR, not GBP).
- Technology labels outside the requested list, used only where the source does not split a category:
  - `gas_ccs+hydrogen_power` (CCC "low-carbon dispatchable")
  - `biomass_beccs+gas_ccs+hydrogen_power` (DESNZ "Low Carbon Dispatchable Power")
  - `other_generation` (CCC: unabated biomass, energy from waste, hydro, CHP)
  - `renewables_all`, `storage_all` (DESNZ EEP aggregates)
  - `wind+solar`, `hydrogen_storage` (Royal Society)
- `demand` with `technology = electrolyser` is the electrolysis component of electricity demand (TWh).
- `generation` with `technology = interconnector` is net imports (positive = net import).
- `emissions` with `technology = biomass_beccs` (FES) is power-sector BECCS removals (negative).
- Years stored: 2023/2024 (base year or outturn as the source gives it), 2025, 2030, 2035, 2040, 2045, 2050.

## Source by source

### 1. NESO Future Energy Scenarios 2025 (1,166 rows, GB)
- Read: local copy of the official workbook `Future Energy Scenarios 2025 Data Workbook V005_0.xlsx` (version sheet: V5 uploaded 11 Nov 2025) in `PyPSA-GB v0.0.1\data\FES\`. Not modified.
- Pathways: Holistic Transition, Electric Engagement, Hydrogen Evolution, Falling Behind, Ten Year Forecast (to 2035 only).
- Sheets: ES1 (capacity MW, generation TWh, storage GWh, CO2 intensity), ED1 (annual demand, peak), FLX1 (electrolysis capacity), WS2 (emissions), F.44 (heat pumps), ED5 (EVs), CP1 (gas price), CP2 (carbon price). ES3, ED2, WS3 for definitions.
- Capacity sums all connection types (transmission, distributed, micro <1 MW, non-networked) and reproduces figure F.12 exactly (checked for 2030 and 2050, all four pathways). Capacity is stated for 1 December of each year.
- Generation is networked only, as in NESO figure F.13. It comes from an hourly dispatch model with no network constraints and a single weather year (2013).
- `gas_unabated` = CCGT + OCGT + reciprocating engines + gas CHP + CCGT CHP. Diesel and fuel oil are excluded.
- `biomass_beccs` = biomass + biomass CHP + CCS biomass; the BECCS part is given in each row's note. Waste/EfW excluded.
- `pumped_hydro_ldes` = pumped hydro + compressed air + liquid air; pumped hydro part given in the note. Hydrogen storage and vehicle-to-grid excluded.
- `electrolyser` = grid-connected electrolysis, installed electric capacity (GWe). Nuclear-connected capacity is in the note; non-networked electrolysis is not included.
- Demand = "GBFES System Demand: Total" = customer demand + networked electrolysis + transmission and distribution losses. This matches the Key Stats "Annual demand". ED1 labels it "Annual [Fiscal]" while ES3 says annual values are calendar years; the workbook is not consistent on this.
- Peak = "GBFES Peak Customer Demand: Total Consumption plus Losses", winter Average Cold Spell peak at 5-6pm, after smart charging and time-of-use shifting, excluding electrolysis, before V2G and storage.
- Carbon intensity is given both including and excluding BECCS. Including BECCS it is negative from the mid-2030s in the net zero pathways. Both exclude EfW and industrial CHP, and NESO states real-world values will be higher.
- Emissions = WS2 "Electricity without BECCS" (GB, major power producers, MtCO2e).
- Heat pumps = residential stock (ASHP, GSHP, hybrids), GB, from F.44 after the V005 correction. Non-residential excluded.
- EVs: three series (BEV cars; BEV cars + vans; all plug-in vehicles including PHEV).
- Gas price: NBP base case, real 2025 EUR/MWh, one series for all pathways. Carbon price: "GB total carbon price", real 2025 EUR/t, equal to the EU ETS series from 2030. The workbook's 2025 conversion is GBP to EUR 1.17, and 1 therm = 0.029307 MWh.
- Not in the workbook: wholesale electricity prices and system cost totals.
- Falling Behind has no hydrogen generation rows in ES1 (zero rows are omitted, per the ES1 note); zeros were added for that pathway and flagged in the note.

### 2. CCC Seventh Carbon Budget (208 rows, UK)
- Read: `The-Seventh-Carbon-Budget-Charts-and-data-in-the-report-v2.xlsx` (Sept 2025 corrected version), `The-Seventh-Carbon-Budget-full-dataset.xlsx`, and the report PDF (Table 7.5.1 on p.208, Table 7.7.1 on p.237).
- Charts sheets: 7.5.1 (emissions), 7.5.2 (intensity), 7.5.3 (capacity and generation mix: 2023, 2030, 2035, 2040, 2045, 2050), 7.5.4 (key indicators, annual), 7.5.7 and 7.5.8 (costs), 7.2.4 (heat pumps), 7.1.4 (EVs). Dataset sheet "Economy-wide data" for demand.
- Geography is the UK, not GB. Modelling by AFRY for the CCC; average weather year; figures before transmission, distribution and storage losses.
- Low-carbon dispatchable is gas CCS plus hydrogen combined. The split is not published.
- `biomass_beccs` is CCS biomass only. Unabated biomass, EfW, hydro and CHP sit in `other_generation`.
- `gas_unabated` excludes CHP.
- Battery and medium-duration storage GW come from 7.5.4; GWh from Table 7.5.1 (rounded integers, no 2045).
- Electrolyser GW from Table 7.7.1 (rounded; basis not stated).
- Demand: `TWh` = gross demand including electricity for hydrogen production; `TWh final` = final demand. Neither includes network losses.
- Heat pumps and EVs are published as shares (% of homes, % of car fleet) in these figures, so they are stored as shares. Not converted to counts.
- System cost: annualised system cost in p/kWh (2023 prices) for the Balanced Pathway and the baseline, plus net additional in-year cost in GBP bn. The p/kWh figure is a cost, not a wholesale or retail price.
- Not found: peak demand, wholesale price, gas and carbon price assumptions.

### 3. DESNZ Clean Power 2030 Action Plan (44 rows, GB)
- Read: gov.uk HTML of the main report (Table 1 and footnotes 20-25) and the Connections Reform Annex as updated April 2025 (Table 1, which adds the 2035 column).
- 2030 "Clean Power Capacity Range" and "2035 FES-derived capacity range" stored as low/high rows. The 2035 range is derived from FES 2024 net zero pathways for connection offers; it is not a target. Onshore wind 2035 (35-37 GW) is a DESNZ uplift over FES.
- Unabated gas is a single value, 35 GW. Low Carbon Dispatchable Power covers biomass, power BECCS, gas CCUS and hydrogen; its 2035 value is "up to 25" (high row only).
- "Current installed capacity" mixes vintages (renewables Q2 2024, nuclear/gas/LDES 2023, batteries Q4 2024); stored under year 2024. The annex prints batteries as 4.55 where the main report prints 4.5; the main report value is stored.
- Carbon intensity: 171 gCO2e/kWh in 2023, and the 2030 target "well below 50", stored as 50 and flagged as an upper bound.
- Consumer-led flexibility (10-12 GW in 2030, 29 GW in 2035, excluding storage heaters) is not in the CSV.
- Not found as numbers: 2030 demand and peak (figure 8 only).

### 4. NESO Clean Power 2030 advice (85 rows, GB)
- Read: `Clean Power 2030 Data Workbook_V003` (sheets CP.17, CP.06, CP.14, CP.22, CP.29, CP.32, ES1, ED1, EC2) and Annex 4 PDF (p.6-7, p.14).
- Pathways: Further Flex and Renewables, New Dispatch, and the Counterfactual for costs and intensity. Years 2023 and 2030.
- Gas capacity 35 GW includes gas CHP. Gas generation in the CSV is gas plus gas CHP; NESO's headline figure excludes CHP (both parts are in the note).
- Demand 315.2 TWh excludes electrolysis, which is stored separately. Peak 62.4 GW is ACS.
- Three carbon intensity definitions are stored. About 15-16 g/kWh excludes EfW/CHP and BECCS; about 51-52 g/kWh includes EfW and CHP and is the one closest to the government's metric.
- Assumptions: gas about 100 p/therm and carbon GBP 147/t in 2030, real 2024. Both are well above DESNZ central values, so the CP2030 cost numbers are not comparable with EEP prices.
- System cost: 2030 annuitised cost per useful unit of electricity, GBP/MWh real 2024 (Counterfactual 118.25, New Dispatch 125.55, Further Flex 132.66).
- Wholesale price: NESO tabulates only average import and export prices (CP.29). CP.32 gives a 101-point price duration curve; its simple mean is about 101 (Counterfactual), 70 (Further Flex) and 75 (New Dispatch) GBP/MWh real 2024. That mean is my calculation, so it is not in the CSV.

### 5. DESNZ Energy and Emissions Projections 2024-2050 (168 rows, UK)
- Read: Annex M (prices, sheets Reference, FFP_Low, FFP_High), Annex L (capacity, all power producers), Annex J (generation), all published February 2026.
- This is an existing-and-planned-policies baseline. Only plant with a CfD up to AR6 or firm funding is included, so unabated gas capacity rises to 73 GW by 2050. It is not a net zero pathway and should not be used as a capacity benchmark for one.
- Useful for prices: baseload and volume-weighted wholesale electricity (p/kWh, 2024 prices; multiply by 10 for GBP/MWh), gas (p/therm, 2024 prices; equals Fossil Fuel Price Assumptions 2025 central/low/high), carbon (UK ETS, and UK ETS + Carbon Price Support for power).
- Wholesale price is the short-run marginal cost from the Dynamic Dispatch Model. The annex does not say whether the modelled market is GB or UK.
- Renewables are published only as a total; storage as pumped hydro plus batteries combined.

### 6. Carbon values (42 rows)
- Green Book: "Valuation of greenhouse gas emissions for policy appraisal and evaluation" (Sept 2021), Annex 1. Low/central/high, GBP/tCO2e, 2020 prices. These are appraisal values, far above market prices (central 280 in 2030, 378 in 2050).
- Traded carbon values for modelling 2025 (published 3 Feb 2026), Table 1. Four trajectories, GBP/tCO2e real 2025, standalone UK ETS with no EU linking.

### 7. Independent studies
- Royal Society, Large-scale electricity storage (Sept 2023), GB, 2050. Read the report PDF: executive summary (p.5-7), p.26-27, figure 23 (p.62). Demand 570 TWh; peak 98.4 GW; an all wind-and-solar system with hydrogen storage needs 58-89 GW of electrolysers, 76-123 TWh of hydrogen storage and 100 GW of hydrogen generation; average cost GBP 52-92/MWh in 2021 prices. This is a stylised bound, not a least-cost mix with nuclear, CCS or interconnectors.
- Energy Systems Catapult, Innovating to Net Zero 2024 (version two), UK, 2050. Read the PDF (p.13, p.17, p.45). Ranges across ESME scenarios. The text and the roadmap figure differ slightly (offshore wind 37-72 vs 37-71 GW; solar 18-70 GW total vs 12-50 GW for solar farms; hydrogen peaking 9-30 GW vs "up to 37 GW" for hydrogen turbines).
- UCL highRES: Price, Keppo and Dodds, Energy 262 (2023). Read the open-access PDF. Most results are in charts, so only text numbers are stored: demand 628-661 TWh, system LCOE GBP 52-70/MWh for the BASE technology set, and the fixed 16.5 GW interconnection assumption. The text also says total wind and solar capacity is "~300 GW or more" and at most 2.2 GW of BECCS is needed; these are not in the CSV.
- Aurora Energy Research for Policy Exchange (March 2024), GB. Read the PDF text (p.6, p.30, p.36). Only capacities stated in text for the NZ30 and NZ35 scenarios are stored; chart values were not read.
- Cornwall Insight: two wholesale price points (GBP 83/MWh in 2027, GBP 77/MWh in 2030) seen only in a search snippet. The page returned 404, so the release date, edition and price base are unverified. Tagged `search`.

## Inconsistencies between sources

- GB vs UK: FES, CP2030 and NESO advice are GB. CCC, EEP, ESC and UCL highRES are UK, so they include Northern Ireland.
- Demand definitions differ. FES includes losses and networked electrolysis. NESO CP2030 excludes electrolysis. CCC gross demand includes electrolysis but excludes losses.
- 2030 demand: FES pathways 324-345 TWh; CCC 333 TWh; NESO CP2030 315 TWh plus 13-15 TWh electrolysis; EEP 339 TWh.
- 2050 offshore wind: CCC 125 GW (UK) against FES 80-104 GW (GB) and ESC 37-72 GW (UK).
- 2050 nuclear: FES 10-22 GW, CCC 11 GW, ESC 27-33 GW.
- 2030 unabated gas capacity: CP2030 35 GW, FES 31-46 GW, CCC 33.7 GW (excluding CHP).
- Carbon intensity definitions vary by a factor of three or more for the same system (NESO 2030: 15 vs 51 g/kWh).
- Carbon prices for 2030 span GBP 48-64 (DESNZ traded values, 2024 prices), about EUR 108 (FES, 2025 prices), GBP 147 (NESO CP2030, 2024 prices) and GBP 280 (Green Book appraisal value, 2020 prices).
- Gas prices for 2030: FES EUR 29.9/MWh (about 75 p/therm using the workbook's conversion factors, my calculation), DESNZ central 71 p/therm, NESO CP2030 about 100 p/therm.
- FES 2024 and 2025 columns are not a consistent pair. In Holistic Transition, gas generation falls from 93 TWh (2024) to 43 TWh (2025) and net imports rise from 5 to 29 TWh, and carbon intensity halves. The 2025 column is unconstrained model output for a 2013 weather year, not a forecast of outturn. Do not calibrate a 2025 start year against FES 2025 generation, emissions or intensity.

## Requested numbers not found

- Wholesale electricity price projections for FES and CCC (not published).
- Baseload wholesale price in NESO CP2030 (only import/export prices and a duration curve).
- Public consultancy wholesale price forecasts beyond the two unverified Cornwall Insight points. Aurora, LCP Delta and AFRY curves are subscriber-only or chart-only.
- CCC peak demand; CCC split of gas CCS vs hydrogen power; CCC heat pump and EV counts (shares only in the figures read).
- DESNZ CP2030 demand and peak values (figure only).
- Whole-system cost totals for FES 2025.
- EEP power-sector emissions and carbon intensity (Annex A was not read).
- National Infrastructure Commission Second Assessment and its Aurora modelling: nic.org.uk returned 404 for every document tried.
- Imperial College (Strbac et al.), Regen, PyPSA-GB and PyPSA-FES papers: not read.

## Local data found (read-only, nothing modified)

- `PyPSA-GB v0.0.1\data\FES\`: FES data workbooks 2020 (v1_4), 2021 (V08), 2022 (V006), 2023 (V003), 2024 (V006), 2025 (V005). The 2025 workbook is the one used.
- `PyPSA-GB v0.0.1\resources\FES\`: `FES_2024_data.csv` and `FES_2025_data.csv` are FES building-block (GSP-level) extracts, not used.
- `pypsa-fes\data\`: FES 2023 workbook V001.
- `PyPSA-GB-fix\PyPSA-GB\data\`: FES 2021 workbook V04 and FES 2022 workbook V4 with regional breakdowns.

# Notes for fes_drivers.csv

Annual FES 2025 series for every year 2025-2050, read from the same workbook (`Future Energy Scenarios 2025 Data Workbook V005_0.xlsx`). 16,510 rows, 152 series, columns `pathway,year,series,unit,value,sheet,definition_note,verified`. All rows are tagged `read`. Unique on `pathway, year, series, unit`.

- Pathways: Holistic Transition, Electric Engagement, Hydrogen Evolution, Falling Behind (2025-2050) and Ten Year Forecast (2025-2035 only, as published). Prices and conversion factors use `pathway = All pathways (base case)`.
- Rows whose `definition_note` starts with `SUM` are sums of several workbook rows (for example capacity across connection types). Every other row is a single workbook row, scaled only for units (GWh to TWh, MW to GW).
- Each row's `definition_note` quotes the workbook's own item name.

## Series families

| Prefix | Sheet | What it is |
|---|---|---|
| `demand_*` | ED1, ED5, ES1 | Annual electricity demand, TWh |
| `supp_*` | ED1 | Level 5 supplementary items (data centres, rail traction, residential micro-generation) |
| `peak_*` | ED1, ED5, FLX1 | Peak demand and its components, GW |
| `flex_*` | FLX1, ED5 | Demand-side flexibility at peak, GW (negative = reduction or export) |
| `ev_*`, `vehicles_*` | ED5 | Vehicle numbers |
| `heat_pumps_*`, `heat_pump_*` | ED7 | Heat pump stock (units), electricity (TWh), ACS peak (GW) |
| `capacity_*` | ES1, FLX1, WS1 | Installed capacity, GW; `_energy` suffix = GWh |
| `hydrogen_*`, `electricity_for_*` | WS1 | Hydrogen demand and supply (TWh of hydrogen), electricity into electrolysis |
| `price_*`, `fx_*`, `gdp_deflator_*`, `gas_therm_to_mwh` | CP1, CP2 | Fuel and carbon prices and the workbook's conversion factors |

## Definitions that matter

- Demand hierarchy (ED1, defined in ED2). `demand_total_system` is GB system demand, not customer demand. It equals `demand_residential` + `demand_industrial_incl_electrolysis` + `demand_commercial_underlying` + `demand_losses_transmission` + `demand_losses_distribution` + `demand_direct_transmission_customers`. Checked for Holistic Transition: the components match the total to within 0.002 TWh in every year.
- Residential = appliances + lighting + storage heat + resistive heat + heat pumps + EV charging at home + air conditioning + district heat, minus `demand_residential_smart_meter_reduction`. Checked: exact.
- Industrial = `demand_industrial_excl_electrolysis` + `demand_networked_electrolysis`.
- Commercial underlying = `demand_commercial_at_meter` + `demand_commercial_microgeneration`. At-meter = at-meter excluding EVs + `demand_commercial_ev_charging`.
- `supp_data_centres`, `supp_rail_traction` and `supp_residential_microgeneration` are level 5 supplementary items. ED2 says these are not added into the totals but relate to an aggregated component (data centres and rail traction are listed against Commercial). Do not add any of the three to the total.
- `demand_road_transport` (ED5) equals residential plus commercial EV charging (checked: exact), so it is already inside the totals.
- `demand_daccs` comes from ES1. ED2 does not list DACCS in the system demand hierarchy, so the workbook does not show whether it is inside `demand_total_system`.
- `electricity_for_non_networked_electrolysis` is outside system demand.
- ED1 labels annual values "Annual [Fiscal]"; ES3 says supply-side annual values are calendar years.
- `peak_total` is the winter Average Cold Spell peak at 5-6pm, including losses, after residential time-of-use shifting and smart EV charging, excluding electrolysis, and before V2G, storage and other demand-side response. It equals residential + industrial + commercial + direct connects (checked: exact).
- `peak_ev_unmanaged` + `flex_smart_charging_at_peak` = `peak_ev_managed`. `peak_heat_unconstrained` is heat demand at peak before heat flexibility.
- Heat pump stock is the number installed at the start of the year (ED8 definition). The residential total equals the published F.44 series. Commercial and industrial are given separately.
- `heat_pump_electricity_residential` (ED7, 3 decimals) matches ED1 `demand_residential_heat_pumps`.
- `capacity_*` from ES1 is as at 1 December of each year and sums transmission, distributed, micro and non-networked connections.
- `capacity_electrolyser_grid` and `capacity_electrolyser_nuclear` are installed electric capacity (FLX1). `capacity_electrolyser_non_networked` is from WS1, which does not state the basis.
- `hydrogen_demand_power_generation` is TWh of hydrogen burned, not electricity generated.

## Not given by the workbook, or partial

- Gas price in p/therm and carbon price in GBP/t: the workbook publishes EUR only (real 2025 EUR/MWh and EUR/tCO2). The file carries the published EUR series plus the workbook's own GBP-to-EUR rate by year, GDP deflator and therm factor. No converted series is included, because the workbook does not say in which order the exchange rate and deflator were applied.
- Smart-charging and V2G participation rates (share of vehicles): not in ED5 or FLX1; only the GW effects at peak are given. BB2 defines a building block "% Potential participating customers", whose values would be in the GSP-level BB1 table, which was not extracted.
- Wholesale electricity price and system cost: not in the workbook.
- Ten Year Forecast stops at 2035. Its nuclear-connected electrolysis row has values only for 2025-2029.
- Hybrid heat pumps with hydrogen boilers appear only in Hydrogen Evolution.
- Falling Behind has no hydrogen generation rows in ES1; zeros were entered for `capacity_hydrogen_power` on the strength of the ES1 note that zero rows are omitted.
- ED7 carries a workbook note that 2050 heat pump uptake is a copy of 2049 because of a modelling error. Stock values are as published.
