# Assumptions & limitations (read before using any number)

**Status: illustrative prototype. The 2025 operating year is calibrated against outturn (below); the
2026-2050 pathway is not validated. Do not quote numbers as forecasts.**

* Costs/technologies in `ukabm/config.py` are indicative (order of DESNZ Generation Costs 2023); real 2024 £.
* Initial fleet c.2025 (MW) is a stylised aggregate; vintages are randomised per zone; nuclear units and dates indicative (AGR closures, Hinkley C 2030/31, Sizewell C 2038/39).
* Legacy fleet performance (calibrated to 2025): AGR availability 0.62 and Sizewell B 0.88 (GB nuclear 34.2 TWh in 2025, NESO; EDF fleet update Jan 2026); existing CCGTs 0.54 → 0.46 efficiency (GCV) falling with age, fleet mean ~0.50 (DUKES Table 5.10), new CCGTs 0.55; biomass availability 0.70 (19.9 TWh in 2025 = 60 % load factor on 3.8 GW).
* One weather/demand year (ESPENI 2024, hourly). Wind/solar capacity factors are derived by normalising ESPENI output by a high quantile (no installed-capacity series) — onshore = 0.75×, offshore = 1.10× the GB shape. No spatial weather variation.
* Temperature for heat demand is synthetic. Heat pump SPF fixed at 2.9. 0.6 m HPs and 1.2 m EVs assumed embedded in the 2024 base demand.
* Market: single GB price, perfect within-day foresight for storage/flex, no unit commitment, no ramping, no reserves; ORDC-type scarcity adder (σ = 2.5 GW) stands in for scarcity pricing. The adder's margin is physical supply minus domestic demand (exports are treated as interruptible), and an export bid below the adder is curtailed, so exports are never served above their bid.
* Interconnectors: capacity from the PyPSA-GB register with corrected commissioning years (NeuConnect 2028, GridLink 2030, FAB Link 2031, NorthConnect not built, Greenlink 2025 → 10.5 GW in 2025). One import offer and one export bid per neighbour market. Foreign price = SRMC of an existing GB CCGT × level (continent 0.68, SEM 1.10; calibrated to 2025 day-ahead price ratios) × the observed 2024 hourly price shape of each neighbour (Energy-Charts/SMARD, same weather year as the GB profile; SEM has a GB-wind-shaped proxy). Spread ±£12/MWh around the foreign price, calibrated to 2025 gross flows (imports 44 TWh, exports 15 TWh). Price calibration uses time-weighted means; the model's demand-weighted price is not like-for-like with MID's volume-weighted price. Foreign prices fall 25 % relative to the GB CCGT reference by 2050.
* Carbon intensity is reported two ways: `intensity_g_kwh` (direct combustion emissions in GB / total supply) and `intensity_neso_g_kwh` (NESO accounting: CCGT 394, OCGT 651, biomass 120, imports 65 g/kWh), which is the one to compare with NESO's published CI.
* CfD: AR-style pots (60/20/20 offshore/onshore/solar), pay-as-clear by technology, 20-year contracts, no £ budget. CM: T-4 only, linear demand curve ±1.5 GW, price cap £75/kW, CfD/RO plant excluded but netted off the target. Battery ancillary revenue £20k/MW/yr declining.
* Network stage: zonal transport model (no KVL), 96 random hours scaled to a year; cost vs. copperplate offer cost; storage and interconnectors held at market positions.
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
  does not yet feed redispatch back into the reported mix (roadmap: network item).
* **CI (NESO basis) ~17 g/kWh low**: the curtailment effect above (~+12 g/kWh) plus 4.7 TWh of "other"
  generation (CHP, waste, oil; NESO factor 300 g/kWh, ~+5 g/kWh) that the model does not represent.
* **Price ~£5/MWh high, distribution too narrow**: no low-price/negative hours (no unit commitment,
  must-run or inflexibility; GB had 244 negative hours in 2025) and no scarcity tail (p95 £100 vs £123).
  Gas in 2025 is £32/MWh_th in the model vs ~£31 NBP (~90p/therm).
* **Hydro +2 TWh, storage +2 TWh**: NESO's mix counts transmission-connected hydro and storage only.
