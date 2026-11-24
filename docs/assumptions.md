# Assumptions & limitations (read before using any number)

**Status: illustrative prototype. Not calibrated or validated. Do not quote numbers as forecasts.**

* Costs/technologies in `ukabm/config.py` are indicative (order of DESNZ Generation Costs 2023); real 2024 £.
* Initial fleet c.2025 (MW) is a stylised aggregate; vintages are randomised per zone; nuclear units and dates indicative (AGR closures, Hinkley C 2030/31, Sizewell C 2038/39).
* One weather/demand year (ESPENI 2024, hourly). Wind/solar capacity factors are derived by normalising ESPENI output by a high quantile (no installed-capacity series) — onshore = 0.75×, offshore = 1.10× the GB shape. No spatial weather variation.
* Temperature for heat demand is synthetic. Heat pump SPF fixed at 2.9. 0.6 m HPs and 1.2 m EVs assumed embedded in the 2024 base demand.
* Market: single GB price, perfect within-day foresight for storage/flex, no unit commitment, no ramping, no reserves; ORDC-type scarcity adder (σ = 2.5 GW) stands in for scarcity pricing.
* Continental prices are a function of GB CCGT cost and GB wind (correlated), declining 25 % by 2050; interconnector capacity fixed after the PyPSA-GB register.
* CfD: AR-style pots (60/20/20 offshore/onshore/solar), pay-as-clear by technology, 20-year contracts, no £ budget. CM: T-4 only, linear demand curve ±1.5 GW, price cap £75/kW, CfD/RO plant excluded but netted off the target. Battery ancillary revenue £20k/MW/yr declining.
* Network stage: zonal transport model (no KVL), 96 random hours scaled to a year; cost vs. copperplate offer cost; storage and interconnectors held at market positions.
* Gas network: allowed revenue £5.5bn/yr, –1 %/yr after 2030; non-domestic demand –1.5 %/yr.
* Retail: electricity = HP-weighted wholesale + £70 network + levies + £25 supplier; gas = wholesale + network tariff + £12.
* Ensembles (`ukabm.ensemble`): 5 seeds for baseline, no_cfd, heat_push; other scenarios single seed (42). Seeds vary agent/path draws (vintages, CfD/RO split, bid noise, siting, merchant order, households), not weather, demand, fuel or carbon paths. Bands are min–max of 5 seeds, not confidence intervals.
