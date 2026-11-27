# External (non-PyPSA-GB) data

| file | source | licence | use in ukabm |
|---|---|---|---|
| neighbour_prices_2024.csv | Energy-Charts API (Fraunhofer ISE) day-ahead prices for FR, NL, BE, NO2, DK1, DE-LU; data from Bundesnetzagentur \| SMARD.de. Built by `scripts/fetch_neighbour_prices.py` | CC BY 4.0 | hourly price shape of each interconnector neighbour (same weather year as the ESPENI profile) |

Outturn data used for calibration/validation is in `data/outturn/` (see `scripts/fetch_outturn.py`).
