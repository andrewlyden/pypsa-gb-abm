# Model 2025 (baseline, seed 42) vs GB outturn

| metric | model | outturn | model - outturn |
|---|---|---|---|
| price, mean vs day-ahead baseload (GBP/MWh) | 86.3 | 83.9 | 2.4 |
| price, time-weighted mean vs MID (GBP/MWh) | 86.3 | 79.9 | 6.4 |
| price, model demand-weighted vs MID volume-weighted (GBP/MWh) | 88.0 | 80.9 | 7.0 |
| price p05 (GBP/MWh) | 21.7 | 8.7 | 12.9 |
| price p50 (GBP/MWh) | 95.1 | 82.2 | 12.9 |
| price p95 (GBP/MWh) | 108.5 | 123.4 | -14.9 |
| negative-price hours | 0.0 | 244.0 | -244.0 |
| carbon intensity, NESO basis (g/kWh) | 114.2 | 129.7 | -15.4 |
| carbon intensity, NESO basis, after BM redispatch (g/kWh) | 125.7 | 129.7 | -3.9 |
| carbon intensity, direct combustion (g/kWh) | 84.6 | – | – |
| constraint cost (GBP bn) | 0.9 | 1.8 | -0.9 |
| constraint cost excl. BM premia (GBP bn) | 0.9 | 1.3 | -0.4 |
| renewable curtailment in BM (TWh) | 7.7 | 10.4 | -2.7 |
| gas (CCGT+OCGT) (TWh) | 67.3 | 77.3 | -10.0 |
| wind and solar, available (TWh) | 111.8 | 114.7 | -2.9 |
| nuclear (TWh) | 34.8 | 34.2 | 0.6 |
| wind incl. embedded (TWh) | 93.5 | 85.8 | 7.7 |
| gas after BM redispatch (TWh) | 75.8 | 77.3 | -1.5 |
| wind after BM redispatch (TWh) | 85.8 | 85.8 | -0.0 |
| solar (TWh) | 18.2 | 18.7 | -0.4 |
| biomass (TWh) | 20.4 | 19.9 | 0.4 |
| hydro (TWh) | 3.4 | 3.4 | 0.0 |
| pumped storage discharge (TWh) | 1.2 | 1.3 | -0.1 |
| coal (TWh) | 0.0 | 0.0 | 0.0 |
| other (CHP, waste, oil) (TWh) | 4.0 | 4.7 | -0.7 |
| imports (TWh) | 45.6 | 44.0 | 1.7 |
| exports (TWh) | 13.7 | 14.8 | -1.1 |
| net imports (TWh) | 31.9 | 29.1 | 2.7 |
| total supply incl. imports (TWh) | 290.3 | 289.2 | 1.0 |

The year on its own weather, fleet, fuel and carbon prices (money of the day) and neighbour prices.
Outturn: NESO historic generation mix and carbon intensity (GB, incl. embedded wind/solar);
Ofgem day-ahead baseload price; Elexon MID price (APXMIDP) and FUELHH interconnector flows
(scripts/fetch_outturn.py); constraint cost and curtailment: data/outturn/gb_constraints.csv
(LCP Delta 2026, from NESO data). 'Wind and solar, available' adds the wind turned down in the
Balancing Mechanism to outturn. Rows 'after BM redispatch' add the network stage's redispatch.
