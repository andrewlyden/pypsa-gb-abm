# Starting fleet and contracted pipeline

Built by `python scripts/build_fleet.py` (rules in its docstring; nothing here is tuned to model output).

| File | Content |
|---|---|
| `fleet_2025.csv` | for each technology, the share of its 2025 capacity by zone, vintage (`online`) and support scheme (`support`: merchant, ro, cfd; `strike_2012` in £/MWh, 2012 prices; `support_end`: last year of support). `mw` is the capacity in the source; the model uses `share` × `ukabm.config.INITIAL_FLEET_MW`. A blank zone means the source has no location (batteries); the model places it. |
| `pipeline_2025.csv` | capacity with a CfD that was not yet built at the start of 2025: technology, first operating year, allocation round, MW, strike and last contract year. Both the agents' run and the planner start with it. |

## Sources

| Data | Source | Licence |
|---|---|---|
| Stations: technology, capacity, coordinates, year commissioned | DESNZ, *Digest of UK Energy Statistics 2026*, Table 5.11, sheet "5.11 Full list" (major power producers, end of 2025). Downloaded by the script to `raw/` (not committed). | Open Government Licence v3.0 |
| GB capacity at the end of each year, 2011–2025 | `data/history/gb_capacity.csv` (DUKES 2026 Tables 5.12 and 5.16) | Open Government Licence v3.0 |
| CfD contracts: round, technology, delivery year, MW, strike | `data/pypsagb_snapshot/cfd_strike_prices_by_round.csv` (DESNZ allocation round results and the LCCC register, via PyPSA-GB) | Open Government Licence v3.0 (results); PyPSA-GB extract MIT |
| Zone of a station | nearest PyPSA-GB zone bus (`data/pypsagb_snapshot/zonal_buses.csv`) | MIT |

Contains public sector information licensed under the Open Government Licence v3.0.

## What the fleet looks like

GB station list, MW by commissioning period (thermal plant and hydro) and yearly additions to GB capacity
(wind and solar):

| | before 2000 | 2000–09 | 2010–14 | 2015–19 | 2020–25 |
|---|---|---|---|---|---|
| CCGT | 11,369 | 8,010 | 8,644 | 884 | 840 |
| OCGT, engines, other gas | 1,926 | 290 | 50 | 388 | 0 |
| biomass (conversions) | 0 | 0 | 2,580 | 420 | 0 |
| offshore wind | 0 | 1,838 | 2,663 | 5,387 | 6,762 |
| onshore wind | 0 | 4,349 | 3,527 | 4,773 | 2,262 |
| solar | 0 | 0 | 5,466 | 7,545 | 8,507 |

Support in the 2025 fleet (share of capacity): offshore wind 67 % CfD, 32 % RO; onshore wind 81 % RO, 10 % CfD;
solar 55 % RO or feed-in tariff, CfD and merchant the rest; biomass RO.

Contracted pipeline: 19.1 GW of offshore wind (2026–2031), 5.0 GW of onshore wind (2026–2028) and 8.2 GW of solar
(2027–2028).

## Known limits

* The match of CfD contracts to capacity is by round order and year, not by project name, so which vintage
  holds which contract is approximate (in aggregate: 11.1 GW of offshore wind on CfDs in 2025).
* Small solar on feed-in tariffs is counted with RO solar. Ofgem's RO report for 2024–25 has 5.8 GW of
  accredited solar; the rule gives 11.8 GW of RO or FiT solar.
* The pipeline assumes every remaining contract is built on time. Known withdrawals are removed (Norfolk
  Boreas; AR4 capacity re-contracted in AR6). Capacity Market agreements for plant not yet built (mostly
  batteries) are not in the pipeline: the model's own auctions and merchant decisions add them.
* Existing gas plant closes on age at 40 (CCGT) or 45 years (`config.EXISTING_LIFE`), an assumption.
