# Assumptions & limitations (read before using any number)

**Status: illustrative prototype. The 2025 operating year is calibrated against outturn (below); the
2026-2050 pathway is not validated. Do not quote numbers as forecasts.**

* Costs/technologies in `ukabm/config.py` are indicative (order of DESNZ Generation Costs 2023); real 2024 £.
* Initial fleet c.2025 (MW) is a stylised aggregate; vintages are randomised per zone; nuclear units and dates indicative (AGR closures, Hinkley C 2030/31, Sizewell C 2038/39).
* Legacy fleet performance (calibrated to 2025): AGR availability 0.62 and Sizewell B 0.88 (GB nuclear 34.2 TWh in 2025, NESO; EDF fleet update Jan 2026); existing CCGTs 0.54 → 0.46 efficiency (GCV) falling with age, fleet mean ~0.50 (DUKES Table 5.10), new CCGTs 0.55; biomass availability 0.70 (19.9 TWh in 2025 = 60 % load factor on 3.8 GW).
* One weather/demand year (ESPENI 2024, hourly). Wind/solar capacity factors are derived by normalising ESPENI output by a high quantile (no installed-capacity series) — onshore = 0.75×, offshore = 1.10× the GB shape. No spatial weather variation.
* Temperature for heat demand is synthetic. Heat pump SPF fixed at 2.9. 0.6 m HPs and 1.2 m EVs assumed embedded in the 2024 base demand.
* Market: single GB price, perfect within-day foresight for storage/flex (storage fleet dispatched in tranches, see below), no unit commitment, no ramping, no reserves; ORDC-type scarcity adder (σ = 2.5 GW) stands in for scarcity pricing.
* Interconnectors: capacity from the PyPSA-GB register with corrected commissioning years (NeuConnect 2028, GridLink 2030, FAB Link 2031, NorthConnect not built, Greenlink 2025 → 10.5 GW in 2025). One import offer and one export bid per neighbour market. Foreign price = SRMC of an existing GB CCGT × level (continent 0.68, SEM 1.10; calibrated to 2025 day-ahead price ratios) × the observed 2024 hourly price shape of each neighbour (Energy-Charts/SMARD, same weather year as the GB profile; SEM has a GB-wind-shaped proxy). Spread ±£12/MWh around the foreign price, calibrated to 2025 gross flows (imports 44 TWh, exports 15 TWh). Foreign prices fall 25 % relative to the GB CCGT reference by 2050.
* Carbon intensity is reported two ways: `intensity_g_kwh` (direct combustion emissions in GB / total supply) and `intensity_neso_g_kwh` (NESO accounting: CCGT 394, OCGT 651, biomass 120, imports 65 g/kWh), which is the one to compare with NESO's published CI.
* CfD: AR-style pots (60/20/20 offshore/onshore/solar), pay-as-clear by technology, 20-year contracts, no £ budget. CM: T-4 only, linear demand curve ±1.5 GW, price cap £75/kW, CfD/RO plant excluded but netted off the target.
* Battery revenue stack (`config.BATTERY_*`, `GBMarketModel.battery_services_per_mw`). On top of the modelled hourly day-ahead arbitrage and the CM, batteries share two pots across the battery fleet, so revenue per MW falls as the fleet grows:
  * ancillary services (frequency response and reserve), a fixed-size £100m/yr pot, i.e. £20k/MW on the 5 GW 2025 fleet. Modo Energy monthly ME BESS GB reports put frequency response at roughly £20–25k/MW/yr through 2025;
  * intraday and BM trading that the hourly day-ahead clearing does not capture, £3,960/yr per MW of wind and solar capacity (balancing and forecast-error volume scale with VRE).

  Calibration: the 2025 trading revenue (modelled arbitrage ~£5.6k/MW plus the pot) is ~£44k/MW. That is 60 % of Modo's 2-hour GB BESS index of £73k/MW/yr for the 12 months to April 2026. Per-MW revenue is not extrapolated above its 2025 level when the fleet is smaller than 5 GW. The same function is used in settlement (realised) and in investment and CM bids (expected at the fleet in the first operating year, or the delivery year for CM new build, including the pipeline and the candidate project).

  Limitations: other flexible providers (CCGT, DSR, interconnectors) do not compete for the pots, and the pots are not charged to consumers (no BSUoS in the retail tariff). Battery capex is still £600/kW for 2 h (`config.TECHS`), which looks high against 2025 project costs. Storage is dispatched in tranches (3 for batteries), each a price-taker on the price left by earlier tranches, and a tranche skips days on which its own trades would lose money. This stops the fleet trading away its own spread, which had given negative realised arbitrage for fleets above ~8 GW.
* Network stage (every 5 years in scenario runs, every year in `compare_outturn.py`): BM-style redispatch of the wholesale schedule on the PyPSA-GB 20-zone network, solved as a transport model (no KVL) with HiGHS. Each plant can be turned down at its *bid* and turned up at its *offer*. Bids: thermal = SRMC (fuel saved); RO renewables = −ROC value; CfD renewables = −(strike − market price), the top-up lost; merchant renewables/hydro = 0; nuclear = −£300/MWh (never turned down in practice). Offers = the plant's wholesale offer. No BM premia (offer multipliers/adders above SRMC), so the model is compared with outturn excluding the ~£0.54bn of premia. Storage and interconnectors stay at their market positions. Load the redispatch cannot serve behind a constraint is reported as `network_shed_twh` and is not costed (in practice it would be resolved by interconnector counter-trades or storage, which this stage holds fixed).
  * Scottish boundary capabilities B0, B2, B4, B5, B6 (MW including HVDC) for 2025/2030/2035 from NESO's Holistic Transition build-out as tabulated by LCP Delta, *From Bottlenecks to Balance* (Mar 2026, p.58), interpolated and held after 2035. The PyPSA-GB zonal links carry future HND-era values (e.g. 22 GW across Scotland–England), so these are replaced. HVDC links are steps at target energisation (Caithness–Moray, Shetland, Western Isles 2030, Western HVDC, EGL1 2027, EGL2 2029, EGL3/4 2031; SSEN Transmission, Ofgem ASTI). English and Welsh links keep their PyPSA-GB capacities.
  * Monthly available share of boundary capability (planned outages) from LCP Delta (2026, p.59; NESO day-ahead constraint limits 2019–24), with an extra 0.76 derate on Scottish boundaries in 2025 for upgrade outages (LCP Delta p.18; NESO 2025 Annual Balancing Costs Report).
  * Hours: 96 per network year, stratified by GB wind CF into 8 equal-probability strata (12 hours each, weight = stratum size / 12), seeded by year; costs and volumes are annualised with these weights.
  * Redispatch is fed back into reporting only: `bm_net_<tech>` (TWh, + = turned up), `curtailment_twh` and `intensity_neso_post_bm_g_kwh`. Settlement, investment and the headline wholesale CI are not changed by it; zonal prices (weighted median over the sample hours) feed the siting choice.
  * Limitations: one GB wind shape for every zone (no Scottish vs English weather), so the model curtails by boundary capability rather than by local weather; no voltage, stability or inertia constraints (only thermal boundary limits); constraint cost in 2030+ depends strongly on the assumed network build-out dates.
* Gas network: allowed revenue £5.5bn/yr, –1 %/yr after 2030; non-domestic demand –1.5 %/yr.
* Retail: electricity = HP-weighted wholesale + £70 network + levies + £25 supplier; gas = wholesale + network tariff + £12.
* Single seed in the published results; ABM outcomes are path-dependent — run several seeds.

## 2025 calibration vs outturn
`python scripts/compare_outturn.py` writes [results/calibration_2025.md](../results/calibration_2025.md) (outturn
built by `scripts/fetch_outturn.py` from NESO's historic generation mix and Elexon MID / FUELHH). Known,
explained residuals in the 2025 comparison:
* **Wind +8–9 TWh / gas −8 TWh**: the wholesale stage is a copperplate, so it does not curtail Scottish wind.
  In 2025 ~8.8 TWh was curtailed in northern Scotland alone (Montel 2025 curtailment report) and replaced by
  gas in England through the Balancing Mechanism; NESO's mix is after those actions. The network stage
  now reports the redispatch: after BM redispatch, 2025 wind is 84.9 TWh (outturn 85.8) and gas 77.7 TWh
  (77.3), and NESO-basis CI is 125 g/kWh (130). Constraint cost is £1.23bn against £1.83bn outturn, which
  includes ~£0.54bn of BM premia the model does not represent (£1.29bn without them); renewable turn-down
  9.5 TWh vs 10.4 TWh (LCP Delta 2026, from NESO data; `data/outturn/gb_constraints.csv`).
* **CI (NESO basis) ~17 g/kWh low before redispatch, ~4 g/kWh low after**: the curtailment effect above (+13 g/kWh) plus 4.7 TWh of "other"
  generation (CHP, waste, oil; NESO factor 300 g/kWh, ~+5 g/kWh) that the model does not represent.
* **Price ~£5/MWh high, distribution too narrow**: no low-price/negative hours (no unit commitment,
  must-run or inflexibility; GB had 244 negative hours in 2025) and no scarcity tail (p95 £100 vs £123).
  Gas in 2025 is £32/MWh_th in the model vs ~£31 NBP (~90p/therm).
* **Hydro +2 TWh, storage +2 TWh**: NESO's mix counts transmission-connected hydro and storage only.
