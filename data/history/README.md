# Historical data, 2010–2026

Used for back-casts of single operating years (`scripts/run_backcast.py`), for the replay of the CfD
rounds (`scripts/replay_cfd_rounds.py`) and for the starting fleet's vintages (`scripts/build_fleet.py`).
Licences and attribution: [docs/data.md](../../docs/data.md).

| File | Content | Built by |
|---|---|---|
| `annual_inputs.csv` | one row per year 2010–2025: gas, coal, carbon and day-ahead power prices in money of the day and in 2024 prices, the GDP deflator, the pound per euro | `scripts/build_history.py` from `sources/prices.csv` and `sources/ecb_gbp_per_eur.csv` |
| `gb_capacity.csv` | GB installed capacity (MW) at the end of each year by technology, 2011–2025 | `scripts/build_history.py` from `sources/capacity_by_year.csv` |
| `desnz_generation_costs.csv` | cost assumptions of DECC/BEIS/DESNZ *Electricity Generation Costs* 2013, 2016, 2020, 2023 and 2025: every item, technology, commissioning year and case (central, low, high), in the edition's price base | copied from the table read for `sources/` (see below), with the source-text columns dropped |
| `sources/` | the tables as read from the primary documents, one row per number, each with its source, URL and a `verified` tag (`read` = read in the primary table or document; `secondary`; `search`) | read by hand and by script from the documents named in each row, 27–28 November 2026 |

## `sources/`

| File | What | Main sources |
|---|---|---|
| `capacity_by_year.csv` | installed capacity by technology and year, GB, NI and UK, by network | DESNZ, DUKES 2026 Tables 5.7, 5.12, 5.13, 5.16, 6.2; Energy Trends 6.1 |
| `generation_demand.csv` | generation by fuel, demand and peak by year | DESNZ, DUKES 2026 chapter 5 |
| `prices.csv` | gas, coal, oil, carbon and electricity prices by year | Ofgem wholesale market indicators; DESNZ Quarterly Energy Prices 3.2.1; DESNZ Energy and Emissions Projections Annex M; UK ETS Authority; HMRC (Carbon Price Support) |
| `cm_auctions.csv` | every Capacity Market auction 2014–2026: target, clearing price, capacity by class and technology, new build, de-rating factors, auction parameters | NESO Capacity Market register and auction data; EMR Delivery Body final results; BEIS/DESNZ parameter letters; Ofgem annual reports |
| `ro_fit.csv` | Renewables Obligation and Feed-in Tariff: dates, bandings, buy-out prices, certificate values, accredited capacity; onshore wind planning rules | Ofgem; DECC |
| `closures_openings.csv` | thermal and nuclear plant opened, closed or converted since 2010; nuclear life extensions; Hinkley Point C schedule; interconnector openings | DESNZ, DUKES 2026 Table 5.11; EDF; Centrica; NAO |
| `ecb_gbp_per_eur.csv` | pound per euro, annual average | European Central Bank reference rates |

Not collected: a table of CfD rounds (the model reads `data/pypsagb_snapshot/cfd_strike_prices_by_round.csv`)
and yearly stylised facts such as capture prices and battery revenues.
