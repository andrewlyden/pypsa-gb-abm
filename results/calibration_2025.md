# Model 2025 (baseline, seed 42) vs GB outturn

| metric | model | outturn | model - outturn |
|---|---|---|---|
| price, time-weighted mean (GBP/MWh) | 84.6 | 79.9 | 4.7 |
| price, model demand-weighted vs MID volume-weighted (GBP/MWh) | 85.6 | 80.9 | 4.7 |
| price p05 (GBP/MWh) | 53.9 | 8.7 | 45.2 |
| price p50 (GBP/MWh) | 86.2 | 82.2 | 4.0 |
| price p95 (GBP/MWh) | 100.1 | 123.4 | -23.3 |
| negative-price hours | 0.0 | 244.0 | -244.0 |
| carbon intensity, NESO basis (g/kWh) | 112.3 | 129.7 | -17.3 |
| carbon intensity, NESO basis, after BM redispatch (g/kWh) | 125.4 | 129.7 | -4.2 |
| carbon intensity, direct combustion (g/kWh) | 85.1 | – | – |
| constraint cost (GBP bn) | 1.2 | 1.8 | -0.6 |
| constraint cost excl. BM premia (GBP bn) | 1.2 | 1.3 | -0.1 |
| renewable curtailment in BM (TWh) | 9.5 | 10.4 | -0.9 |
| gas (CCGT+OCGT) (TWh) | 69.3 | 77.3 | -8.1 |
| nuclear (TWh) | 34.8 | 34.2 | 0.6 |
| wind incl. embedded (TWh) | 94.4 | 85.8 | 8.6 |
| gas after BM redispatch (TWh) | 77.7 | 77.3 | 0.4 |
| wind after BM redispatch (TWh) | 84.9 | 85.8 | -1.0 |
| solar (TWh) | 18.4 | 18.7 | -0.3 |
| biomass (TWh) | 20.3 | 19.9 | 0.4 |
| hydro (TWh) | 5.3 | 3.4 | 1.9 |
| storage discharge (TWh) | 3.6 | 1.3 | 2.3 |
| other (CHP, waste, oil) (TWh) | 0.0 | 4.7 | -4.7 |
| imports (TWh) | 45.2 | 44.0 | 1.2 |
| exports (TWh) | 15.5 | 14.8 | 0.7 |
| net imports (TWh) | 29.7 | 29.1 | 0.5 |
| total supply incl. imports (TWh) | 291.2 | 289.2 | 2.0 |

Outturn: NESO historic generation mix and carbon intensity (GB, incl. embedded wind/solar);
Elexon MID price (APXMIDP) and FUELHH interconnector flows (scripts/fetch_outturn.py);
constraint cost and curtailment: data/outturn/gb_constraints.csv (LCP Delta 2026, from NESO data).
Rows 'after BM redispatch' add the network stage's annualised redispatch to the wholesale result.
