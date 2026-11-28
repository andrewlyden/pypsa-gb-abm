# Operating back-cast: model against GB outturn

Baseline, seed 42; each year on its own weather, fleet and prices (money of the day); code at 399535c.
Parameters fitted to an operating year were set on 2025; the other years check them.

| metric | 2021 model / outturn | 2022 model / outturn | 2023 model / outturn | 2024 model / outturn | 2025 model / outturn |
|---|---|---|---|---|---|
| price, mean vs day-ahead baseload (GBP/MWh) | 115.3 / 127.5 | 190.9 / 211.8 | 97.3 / 97.3 | 80.4 / 75.7 | 86.3 / 83.9 |
| price, time-weighted mean vs MID (GBP/MWh) | 115.3 / 115.2 | 190.9 / 198.2 | 97.3 / 93.5 | 80.4 / 71.4 | 86.3 / 79.9 |
| price, model demand-weighted vs MID volume-weighted (GBP/MWh) | 117.1 / 120.0 | 194.2 / 202.1 | 99.6 / 96.7 | 82.1 / 73.5 | 88.0 / 80.9 |
| price p05 (GBP/MWh) | 80.3 / 42.1 | 119.0 / 60.8 | 35.5 / 21.1 | 20.6 / 8.9 | 21.7 / 8.7 |
| price p50 (GBP/MWh) | 116.4 / 90.7 | 196.0 / 179.7 | 103.9 / 91.5 | 85.8 / 73.9 | 95.1 / 82.2 |
| price p95 (GBP/MWh) | 131.2 / 248.9 | 214.9 / 399.5 | 120.5 / 161.4 | 101.0 / 110.7 | 108.5 / 123.4 |
| negative-price hours | 0.0 / 32.5 | 0.0 / 65.5 | 0.0 / 214.0 | 0.0 / 247.5 | 0.0 / 244.0 |
| carbon intensity, NESO basis (g/kWh) | 163.0 / 186.7 | 182.8 / 182.6 | 135.2 / 151.2 | 113.4 / 127.7 | 114.2 / 129.7 |
| carbon intensity, NESO basis, after BM redispatch (g/kWh) | 169.2 / 186.7 | 190.0 / 182.6 | 142.7 / 151.2 | 120.7 / 127.7 | 125.7 / 129.7 |
| carbon intensity, direct combustion (g/kWh) | 129.4 / – | 153.0 / – | 103.2 / – | 81.9 / – | 84.6 / – |
| constraint cost (GBP bn) | 0.7 / – | 1.0 / – | 0.7 / – | 0.5 / – | 0.9 / 1.8 |
| constraint cost excl. BM premia (GBP bn) | 0.7 / – | 1.0 / – | 0.7 / – | 0.5 / – | 0.9 / 1.3 |
| renewable curtailment in BM (TWh) | 4.0 / – | 5.0 / – | 4.8 / – | 4.8 / – | 7.7 / 10.4 |
| gas (CCGT+OCGT) (TWh) | 101.7 / 107.3 | 107.9 / 111.2 | 78.8 / 86.7 | 62.8 / 72.6 | 67.3 / 77.3 |
| wind and solar, available (TWh) | 75.9 / 76.3 | 92.2 / 94.4 | 94.2 / 96.8 | 103.1 / 105.0 | 111.8 / 114.7 |
| nuclear (TWh) | 45.4 / 43.4 | 34.8 / 44.7 | 34.8 / 38.3 | 34.8 / 38.4 | 34.8 / 34.2 |
| wind incl. embedded (TWh) | 64.3 / 62.2 | 79.2 / 77.2 | 80.7 / 79.0 | 88.8 / 82.7 | 93.5 / 85.8 |
| gas after BM redispatch (TWh) | 106.3 / 107.3 | 113.4 / 111.2 | 83.9 / 86.7 | 67.9 / 72.6 | 75.8 / 77.3 |
| wind after BM redispatch (TWh) | 60.3 / 62.2 | 74.3 / 77.2 | 76.0 / 79.0 | 84.0 / 82.7 | 85.8 / 85.8 |
| solar (TWh) | 11.6 / 11.8 | 13.0 / 13.3 | 13.4 / 13.6 | 14.3 / 14.1 | 18.2 / 18.7 |
| biomass (TWh) | 20.7 / 19.0 | 20.7 / 15.0 | 20.7 / 13.4 | 20.6 / 18.8 | 20.4 / 19.9 |
| hydro (TWh) | 3.4 / 3.2 | 3.4 / 3.3 | 3.4 / 3.2 | 3.4 / 3.6 | 3.4 / 3.4 |
| pumped storage discharge (TWh) | 0.5 / 1.8 | 0.9 / 1.9 | 1.3 / 1.7 | 1.3 / 1.9 | 1.2 / 1.3 |
| coal (TWh) | 1.3 / 5.0 | 6.8 / 4.3 | 0.3 / 2.8 | 0.2 / 1.6 | 0.0 / 0.0 |
| other (CHP, waste, oil) (TWh) | 4.7 / 1.8 | 4.5 / 2.6 | 4.3 / 2.6 | 4.1 / 3.3 | 4.0 / 4.7 |
| imports (TWh) | 39.4 / 29.2 | 26.6 / 16.2 | 40.7 / 33.5 | 48.3 / 43.9 | 45.6 / 44.0 |
| exports (TWh) | 14.2 / 4.4 | 29.8 / 20.4 | 14.3 / 10.1 | 9.5 / 10.6 | 13.7 / 14.8 |
| net imports (TWh) | 25.2 / 24.8 | -3.2 / -4.2 | 26.4 / 23.4 | 38.8 / 33.3 | 31.9 / 29.1 |
| total supply incl. imports (TWh) | 293.2 / 284.9 | 298.3 / 289.8 | 279.5 / 274.6 | 280.1 / 280.9 | 290.3 / 289.2 |

Outturn: NESO historic generation mix and carbon intensity (GB, incl. embedded wind and solar); Ofgem day-ahead baseload price;
Elexon MID price and FUELHH interconnector flows; constraint cost and curtailment: data/outturn/gb_constraints.csv.
'Wind and solar, available' adds the wind turned down in the Balancing Mechanism to outturn generation.
Rows 'after BM redispatch' add the network stage's redispatch to the wholesale result.
