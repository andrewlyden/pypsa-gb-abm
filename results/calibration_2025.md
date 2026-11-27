# Model 2025 (baseline, seed 42) vs GB outturn

| metric | model | outturn | model - outturn |
|---|---|---|---|
| price, time-weighted mean (GBP/MWh) | 83.9 | 79.9 | 4.0 |
| price, model demand-weighted vs MID volume-weighted (GBP/MWh) | 85.0 | 80.9 | 4.1 |
| price p05 (GBP/MWh) | 47.3 | 8.7 | 38.6 |
| price p50 (GBP/MWh) | 86.2 | 82.2 | 4.0 |
| price p95 (GBP/MWh) | 100.1 | 123.4 | -23.3 |
| negative-price hours | 0.0 | 244.0 | -244.0 |
| carbon intensity, NESO basis (g/kWh) | 113.2 | 129.7 | -16.5 |
| carbon intensity, NESO basis, after BM redispatch (g/kWh) | 121.8 | 129.7 | -7.8 |
| carbon intensity, direct combustion (g/kWh) | 86.0 | – | – |
| constraint cost (GBP bn) | 0.7 | 1.8 | -1.1 |
| constraint cost excl. BM premia (GBP bn) | 0.7 | 1.3 | -0.6 |
| renewable curtailment in BM (TWh) | 6.9 | 10.4 | -3.5 |
| gas (CCGT+OCGT) (TWh) | 69.5 | 77.3 | -7.8 |
| nuclear (TWh) | 34.8 | 34.2 | 0.6 |
| wind incl. embedded (TWh) | 94.4 | 85.8 | 8.6 |
| gas after BM redispatch (TWh) | 74.7 | 77.3 | -2.6 |
| wind after BM redispatch (TWh) | 87.6 | 85.8 | 1.7 |
| solar (TWh) | 18.4 | 18.7 | -0.3 |
| biomass (TWh) | 19.9 | 19.9 | -0.1 |
| hydro (TWh) | 5.3 | 3.4 | 1.9 |
| storage discharge (TWh) | 2.2 | 1.3 | 0.9 |
| other (CHP, waste, oil) (TWh) | 0.0 | 4.7 | -4.7 |
| imports (TWh) | 45.1 | 44.0 | 1.1 |
| exports (TWh) | 15.6 | 14.8 | 0.8 |
| net imports (TWh) | 29.5 | 29.1 | 0.3 |
| total supply incl. imports (TWh) | 289.5 | 289.2 | 0.3 |

Outturn: NESO historic generation mix and carbon intensity (GB, incl. embedded wind/solar);
Elexon MID price (APXMIDP) and FUELHH interconnector flows (scripts/fetch_outturn.py);
constraint cost and curtailment: data/outturn/gb_constraints.csv (LCP Delta 2026, from NESO data).
Rows 'after BM redispatch' add the network stage's annualised redispatch to the wholesale result.
