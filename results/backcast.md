# Operating back-cast: model against GB outturn

Baseline, seed 42; each year on its own weather, fleet and prices (money of the day); code at 560cc21.
Parameters fitted to an operating year were set on 2025; the other years check them.

| metric | 2021 model / outturn | 2022 model / outturn | 2023 model / outturn | 2024 model / outturn | 2025 model / outturn |
|---|---|---|---|---|---|
| price, mean vs day-ahead baseload (GBP/MWh) | 111.5 / 127.5 | 186.2 / 211.8 | 95.0 / 97.3 | 78.0 / 75.7 | 84.0 / 83.9 |
| price, time-weighted mean vs MID (GBP/MWh) | 111.5 / 115.2 | 186.2 / 198.2 | 95.0 / 93.5 | 78.0 / 71.4 | 84.0 / 79.9 |
| price, model demand-weighted vs MID volume-weighted (GBP/MWh) | 113.0 / 120.0 | 189.3 / 202.1 | 97.1 / 96.7 | 79.5 / 73.5 | 85.4 / 80.9 |
| price p05 (GBP/MWh) | 79.0 / 42.1 | 116.8 / 60.8 | 36.1 / 21.1 | 19.9 / 8.9 | 20.4 / 8.7 |
| price p50 (GBP/MWh) | 113.8 / 90.7 | 192.6 / 179.7 | 100.7 / 91.5 | 85.3 / 73.9 | 91.3 / 82.2 |
| price p95 (GBP/MWh) | 124.2 / 248.9 | 208.1 / 399.5 | 115.9 / 161.4 | 94.6 / 110.7 | 101.3 / 123.4 |
| negative-price hours | 0.0 / 32.5 | 0.0 / 65.5 | 0.0 / 214.0 | 0.0 / 247.5 | 0.0 / 244.0 |
| carbon intensity, NESO basis (g/kWh) | 164.6 / 186.7 | 185.5 / 182.6 | 139.6 / 151.2 | 116.4 / 127.7 | 118.0 / 129.7 |
| carbon intensity, NESO basis, after BM redispatch (g/kWh) | 170.8 / 186.7 | 192.8 / 182.6 | 146.5 / 151.2 | 123.6 / 127.7 | 128.9 / 129.7 |
| carbon intensity, direct combustion (g/kWh) | 131.8 / – | 156.5 / – | 108.4 / – | 85.5 / – | 89.0 / – |
| constraint cost (GBP bn) | 0.7 / – | 1.1 / – | 0.6 / – | 0.5 / – | 0.9 / 1.8 |
| constraint cost excl. BM premia (GBP bn) | 0.7 / – | 1.1 / – | 0.6 / – | 0.5 / – | 0.9 / 1.3 |
| renewable curtailment in BM (TWh) | 4.0 / – | 4.7 / – | 4.7 / – | 4.8 / – | 7.6 / 10.4 |
| gas (CCGT+OCGT) (TWh) | 102.8 / 107.3 | 111.1 / 111.2 | 82.8 / 86.7 | 65.5 / 72.6 | 70.8 / 77.3 |
| wind and solar, available (TWh) | 75.9 / 76.3 | 92.2 / 94.4 | 94.2 / 96.8 | 103.1 / 105.0 | 111.8 / 114.7 |
| nuclear (TWh) | 45.4 / 43.4 | 34.8 / 44.7 | 34.8 / 38.3 | 34.8 / 38.4 | 34.8 / 34.2 |
| wind incl. embedded (TWh) | 64.3 / 62.2 | 79.2 / 77.2 | 80.7 / 79.0 | 88.8 / 82.7 | 93.5 / 85.8 |
| gas after BM redispatch (TWh) | 107.4 / 107.3 | 116.4 / 111.2 | 87.5 / 86.7 | 70.5 / 72.6 | 78.7 / 77.3 |
| wind after BM redispatch (TWh) | 60.3 / 62.2 | 74.5 / 77.2 | 76.0 / 79.0 | 84.1 / 82.7 | 85.9 / 85.8 |
| solar (TWh) | 11.6 / 11.8 | 13.0 / 13.3 | 13.4 / 13.6 | 14.3 / 14.1 | 18.3 / 18.7 |
| biomass (TWh) | 20.7 / 19.0 | 20.7 / 15.0 | 20.3 / 13.4 | 20.1 / 18.8 | 19.8 / 19.9 |
| hydro (TWh) | 3.4 / 3.2 | 3.4 / 3.3 | 3.4 / 3.2 | 3.4 / 3.6 | 3.4 / 3.4 |
| pumped storage discharge (TWh) | 0.5 / 1.8 | 0.7 / 1.9 | 1.2 / 1.7 | 1.2 / 1.9 | 1.0 / 1.3 |
| coal (TWh) | 1.5 / 5.0 | 6.7 / 4.3 | 0.3 / 2.8 | 0.2 / 1.6 | 0.0 / 0.0 |
| other (CHP, waste, oil) (TWh) | 4.7 / 1.8 | 4.5 / 2.6 | 4.3 / 2.6 | 4.1 / 3.3 | 4.0 / 4.7 |
| imports (TWh) | 38.8 / 29.2 | 24.9 / 16.2 | 38.5 / 33.5 | 47.1 / 43.9 | 44.4 / 44.0 |
| exports (TWh) | 14.9 / 4.4 | 31.2 / 20.4 | 15.7 / 10.1 | 10.5 / 10.6 | 14.8 / 14.8 |
| net imports (TWh) | 23.9 / 24.8 | -6.3 / -4.2 | 22.8 / 23.4 | 36.6 / 33.3 | 29.6 / 29.1 |
| total supply incl. imports (TWh) | 293.9 / 284.9 | 299.5 / 289.8 | 280.7 / 274.6 | 280.9 / 280.9 | 291.7 / 289.2 |

Outturn: NESO historic generation mix and carbon intensity (GB, incl. embedded wind and solar); Ofgem day-ahead baseload price;
Elexon MID price and FUELHH interconnector flows; constraint cost and curtailment: data/outturn/gb_constraints.csv.
'Wind and solar, available' adds the wind turned down in the Balancing Mechanism to outturn generation.
Rows 'after BM redispatch' add the network stage's redispatch to the wholesale result.
