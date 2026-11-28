# External (non-PyPSA-GB) data

| file | source | licence | use in ukabm |
|---|---|---|---|
| `neighbour_prices_<year>.csv`, 2021–2025 | Energy-Charts API (Fraunhofer ISE) day-ahead prices for FR, NL, BE, NO2, DK1, DE-LU, in EUR/MWh; data from Bundesnetzagentur \| SMARD.de. Built by `scripts/fetch_neighbour_prices.py <year>` | CC BY 4.0 | the price of each interconnector neighbour in the weather year: the level itself when a historical year is back-cast, the hourly shape in future years |

Outturn data used for calibration and checks is in `data/outturn/` (see `scripts/fetch_outturn.py`).
Every dataset and its licence: [docs/data.md](../../docs/data.md).
