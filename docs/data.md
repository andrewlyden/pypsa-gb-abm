# Data register

Every dataset that the repository ships under `data/`, or that its scripts download, with its source,
licence, the attribution that the licence requires and the script that builds it. The register
describes the files as they are on the branch `foundations/implementation` (commit a47ec5f). It was compiled from the
README in each data folder, the docstrings of the build scripts and the `source`, `url` and `verified`
columns inside the CSV files. Where a licence is not written down anywhere in the repository, the
register says "not stated in the repository"; it does not infer one.

Terms used below:

* **OGL v3.0**: Open Government Licence v3.0 (UK public sector information).
* **NESO ODL v1.0**: the "National Energy SO Open Data Licence v1.0", https://www.neso.energy/data-portal/neso-open-licence.
* **Elexon BMRS licence**: "Copyright: Licence to use BMRS open data",
  https://www.elexon.co.uk/bsc/data/balancing-mechanism-reporting-agent/copyright-licence-bmrs-data/.
* **Hand-made**: written or extracted by the authors (or by an AI assistant working for them, see
  [ai_use.md](ai_use.md)) rather than produced by a script in the repository.
* **`verified` tag**: a column in several source tables. `read` means the value was read from the
  primary document or table named in the row; `search` means it was seen only in a search-result
  snippet; `secondary` means it was read from a document that quotes the primary source.

## Attribution sentences

The licences named below require these statements wherever the data, or files derived from them, are
redistributed. They are collected here so that one block can be copied into a publication or a release.

| Licence | Required statement (as given in the repository, or the licence's standard form) |
|---|---|
| NESO ODL v1.0 | "Supported by National Energy SO Open Data" (wording required by the licence; quoted in `data/profiles/README.md`) |
| Elexon BMRS licence | "Contains BMRS data © Elexon Limited copyright and database right 2026." and, where possible, a link to the licence (quoted in `data/profiles/README.md`) |
| OGL v3.0 | "Contains public sector information licensed under the Open Government Licence v3.0." |
| CC BY 4.0 (SMARD) | Proposed: "Day-ahead prices: Bundesnetzagentur \| SMARD.de, CC BY 4.0, retrieved through the Energy-Charts API (Fraunhofer ISE); quarter-hourly values averaged to hours." The repository does not record the exact form of credit that SMARD asks for. |
| CC BY-SA 4.0 (Wikipedia) | Proposed: "Offshore wind farm commissioning years from Wikipedia, 'List of offshore wind farms in the United Kingdom' (CC BY-SA 4.0), read 27 November 2026." Only years are taken (see the licence questions below). |
| MIT (PyPSA-GB) | The MIT licence requires PyPSA-GB's copyright notice and permission notice to accompany substantial portions of it. That notice is not reproduced in `data/pypsagb_snapshot/`. |

## `data/profiles/`: hourly demand, wind and solar, 2021–2025

Built by `python scripts/build_profiles.py <year> ...`. The script downloads its inputs to
`data/profiles/raw/` (not committed) from public APIs that need no key, prints checks against DESNZ
and NESO figures, and writes a year only if the checks pass. Method, checks and limitations are in
`data/profiles/README.md`.

| Path | What it is | Source | Licence | Attribution | Built by |
|---|---|---|---|---|---|
| `profiles_<year>.csv` (2021–2025) | Hourly GB demand (`demand_mw`), onshore and offshore wind capacity factors (available output: metered plus Balancing Mechanism turn-down), solar capacity factor; 8,760 rows, UTC | NESO Data Portal "Historic Demand Data", https://www.neso.energy/data-portal/historic-demand-data; NESO "Historic generation mix and carbon intensity", https://www.neso.energy/data-portal/historic-generation-mix; Elexon Insights Solution API (BM unit list, IGCPU/B1420, B1610, BOAV), https://data.elexon.co.uk/bmrs/api/v1; downloaded November 2026 | Derived from NESO ODL v1.0 and Elexon BMRS licence data | NESO and Elexon statements | `scripts/build_profiles.py` |
| `wind_units_<year>.csv` (2021–2025) | Every wind BM unit used: type, region, capacity and its basis, metered and turned-down energy, capacity factors, vintage | as above | as above | NESO and Elexon statements | `scripts/build_profiles.py` |
| `wind_cf_by_vintage_<year>.csv` (2021–2025) | Capacity factor by wind type and vintage band, units complete all year | as above | as above | NESO and Elexon statements | `scripts/build_profiles.py` |
| `validation.csv` | The check figures, one row per year (demand reconciliation, capacity factors against DESNZ, nameplate factors) | as above, plus DESNZ Energy Trends ET 6.1 (edition of 29 September 2026) | as above; DESNZ figures OGL v3.0 | NESO, Elexon and OGL statements | `scripts/build_profiles.py` |
| `wind_units_manual.csv` | Hand-made input (77 rows): onshore/offshore type for units the automatic rules do not identify, and the commissioning year of offshore units, a source per row | Elexon BM unit list (unit names); Wikipedia, "List of offshore wind farms in the United Kingdom", https://en.wikipedia.org/wiki/List_of_offshore_wind_farms_in_the_United_Kingdom, read 27 November 2026 | Elexon BMRS licence (names); Wikipedia text CC BY-SA 4.0, only years used | Elexon statement; Wikipedia credit (proposed above) | hand-made |
| `benchmarks_desnz.csv` | DESNZ Energy Trends table ET 6.1 figures used in the checks (UK, Northern Ireland and Scotland sheets) | DESNZ, Energy Trends ET 6.1 "Renewable electricity capacity and generation", edition published 29 September 2026, https://www.gov.uk/government/statistics/energy-trends-section-6-renewables | OGL v3.0 | OGL statement | hand-made |
| `raw/` (not committed) | Cached API downloads | NESO, Elexon | as above | – | downloaded by `scripts/build_profiles.py` |

The model reads `profiles_<year>.csv` and `validation.csv` (nameplate factors) through
`ukabm/data/pypsagb.py`. Forward runs use the 2024 weather year by default (`profile_year=2024`).

## `data/fleet/`: starting fleet, owners and contracted pipeline

Built by `python scripts/build_fleet.py`; rules in its docstring and in `data/fleet/README.md`.

| Path | What it is | Source | Licence | Attribution | Built by |
|---|---|---|---|---|---|
| `fleet_2025.csv` | Share of each technology's 2025 capacity by zone, vintage, owner and support scheme (with CfD strike and end year) | DESNZ, *Digest of UK Energy Statistics (DUKES) 2026*, Table 5.11 "Power stations in the United Kingdom", sheet "5.11 Full list" (end of 2025), https://assets.publishing.service.gov.uk/media/6a6a365b0ddb7e4831c629f3/DUKES_5.11.xlsx; `data/history/gb_capacity.csv`; the CfD register extract `data/pypsagb_snapshot/cfd_strike_prices_by_round.csv`; zone buses from `data/pypsagb_snapshot/zonal_buses.csv`; battery vintages from DUKES 2026 Table 5.16 (constant `BATTERY_MW` in the script) | OGL v3.0 (DUKES, CfD results); MIT (PyPSA-GB extracts), as stated in `data/fleet/README.md` | OGL statement; PyPSA-GB MIT notice | `scripts/build_fleet.py` |
| `pipeline_2025.csv` | CfD capacity contracted but not built at the start of 2025: 13 rows by technology, online year and round (19.1 GW offshore wind, 5.0 GW onshore wind, 8.2 GW solar) | CfD register extract as above; withdrawals in the script's `WITHDRAWN` constant | as above | as above | `scripts/build_fleet.py` |
| `firms.csv` | The model's twelve firms: name, type (utility, generator, major, fund, developer) and a description | authors' grouping of the companies in the DUKES station list | part of the repository (MIT); company names only | – | hand-made (read by `scripts/build_fleet.py` and the model) |
| `owners.csv` | Map from the 54 companies in the DUKES station list to the twelve firms, with notes on joint ventures | authors' judgement from company names in DUKES 2026 Table 5.11 | part of the repository (MIT) | – | hand-made (read by `scripts/build_fleet.py`) |
| `raw/` (not committed) | DUKES 2026 Table 5.11 workbook | DESNZ | OGL v3.0 | OGL statement | downloaded by `scripts/build_fleet.py` |

## `data/history/`: annual prices, capacity and generation costs

There is no README in this folder, although `scripts/build_history.py` refers to
`data/history/README.md`. The source of every value in `sources/` is recorded in the row itself
(`source`, `url`, `verified`, `note` columns).

| Path | What it is | Source | Licence | Attribution | Built by |
|---|---|---|---|---|---|
| `annual_inputs.csv` | One row per year 2010–2025: NBP day-ahead gas, coal delivered to major power producers, carbon price paid by GB generators (allowance plus Carbon Price Support), day-ahead baseload power price, in money of the day and 2024 prices; GDP deflator; GBP per EUR | `sources/prices.csv` and `sources/ecb_gbp_per_eur.csv` (below); the Carbon Price Support rate of £18/tCO2 is a constant (`CPS`) in the script | as the inputs | as the inputs | `scripts/build_history.py` |
| `gb_capacity.csv` | GB installed capacity by technology at the end of each year 2011–2025 (227 rows) | DESNZ, DUKES 2026 Tables 5.12 and 5.16 (stated in `ukabm/config.py` and `data/fleet/README.md`) | OGL v3.0 (stated in `data/fleet/README.md`) | OGL statement | no script in the repository: `ukabm/config.py` says `scripts/build_history.py`, but that script writes only `annual_inputs.csv`. Presumably derived from `sources/capacity_by_year.csv`; not recorded |
| `desnz_generation_costs.csv` | Tidy extract (6,379 rows) of the central, low and high assumptions of *Electricity Generation Costs* 2013, 2016, 2020, 2023 and 2025 (DECC/BEIS/DESNZ), with a URL per row | DESNZ and predecessors; 2025 edition annex: https://assets.publishing.service.gov.uk/media/69d8efec96c86b7513170229/annex-a-additional-estimates-and-key-assumptions-2025.xlsx (eight URLs in the file) | OGL v3.0 (stated in the docstring of `scripts/build_costs.py`) | OGL statement | hand-made extract; method not recorded |
| `sources/prices.csv` | Annual and monthly gas, coal, electricity and carbon prices with their series definitions (536 rows) | Ofgem data portal, wholesale market indicators; DESNZ Quarterly Energy Prices Table 3.2.1 (29 September 2026); DESNZ Energy and Emissions Projections 2023–2050 Annex M; UK ETS Authority civil-penalty carbon prices 2021–2027 and *Report on the functioning of the UK carbon market for 2025*; determinations of the EU ETS carbon price 2014–2020 (gov.uk); HMRC Environmental Taxes Bulletin and Climate Change Levy rates; one row from a European Environment Agency briefing seen only in a search summary (`verified` = `search`) | not stated in the repository | not stated | hand-made |
| `sources/ecb_gbp_per_eur.csv` | Annual average GBP per EUR, 2010–2025 | European Central Bank, euro foreign exchange reference rates, series EXR.A.GBP.EUR.SP00.A | not stated in the repository | not stated | hand-made |
| `sources/capacity_by_year.csv` | GB and UK capacity by technology, connection and year (2,163 rows) | DESNZ DUKES 2026 Tables 5.7, 5.12, 5.13, 5.16 and 6.2; Energy Trends ET 6.1 (September 2026); six URLs in the file | OGL v3.0 for DUKES and Energy Trends (stated for these publications in `data/fleet/README.md`, `data/profiles/README.md` and `docs/research/literature_review.md`) | OGL statement | hand-made |
| `sources/generation_demand.csv` | Generation, supply and demand by year (1,088 rows) | DUKES 2026 Tables 5.1.2, 5.6 and 5.10; NESO "Historic generation mix and carbon intensity" (downloaded 27 November 2026) | OGL v3.0 (DUKES); NESO ODL v1.0 (NESO dataset, as stated in `data/profiles/README.md`) | OGL and NESO statements | hand-made |
| `sources/cm_auctions.csv` | Capacity Market auctions 2014–2026: targets, clearing prices, volumes by class and technology, de-rating factors, parameters (2,118 rows) | NESO Data Portal Capacity Market Register (auction static data, de-rating factors, CMU list); EMR Delivery Body final results reports and auction guidelines (many via web.archive.org); BEIS/DESNZ parameter letters; Ofgem annual reports on the Capacity Market | not stated in the repository | not stated | hand-made |
| `sources/ro_fit.csv` | Renewables Obligation and feed-in tariff rules: bandings, closure dates, buy-out prices, accredited capacity (347 rows) | Ofgem RO annual reports, guidance and buy-out price notices; DECC banding table; Ofgem FiT annual report 2018–19; DECC, DCLG, DLUHC and MHCLG statements on onshore wind | not stated in the repository | not stated | hand-made |
| `sources/closures_openings.csv` | Dated openings, closures and conversions of plant and interconnectors, nuclear schedules (119 rows) | DUKES 2026 Tables 5.11 and 5.13A; EDF and Centrica press releases and fleet updates (2021–2026); NAO, *Hinkley Point C* (HC 40, 2017); BEIS and DESNZ press releases; a 2015 ministerial speech | OGL v3.0 for the DUKES rows; not stated in the repository for the other rows (only dates, capacities and short quotations are recorded) | OGL statement for DUKES rows; otherwise not stated | hand-made |

Of these files the model reads `annual_inputs.csv` and `gb_capacity.csv` (`ukabm/config.py`);
`scripts/build_costs.py` and `scripts/replay_cfd_rounds.py` read `desnz_generation_costs.csv`
(the replay also reads the deflator in `annual_inputs.csv`); `scripts/build_fleet.py` reads
`gb_capacity.csv`; `scripts/build_history.py` reads `sources/prices.csv` and
`sources/ecb_gbp_per_eur.csv`. The other source tables are evidence for documents and for future
hindcasts; no code reads them.

## `data/parameters/`

| Path | What it is | Source | Licence | Attribution | Built by |
|---|---|---|---|---|---|
| `cost_paths.csv` | Capital cost, fixed O&M, VOM, hurdle rate, life, load factor and efficiency of offshore wind, onshore wind, solar, CCGT, OCGT, gas CCS and hydrogen CCGT by commissioning year 2030–2050 (35 rows), real 2024 prices | DESNZ, *Electricity Generation Costs 2025*, central case, via `data/history/desnz_generation_costs.csv` | OGL v3.0 (stated in `scripts/build_costs.py`) | OGL statement | `scripts/build_costs.py` |

## `data/fes/`: Future Energy Scenarios and published pathways

Documented in `data/fes/NOTES.md`. Neither file has a build script in the repository; both were read
from the source workbooks and documents (NOTES.md describes sheets, pages and definitions).

| Path | What it is | Source | Licence | Attribution | Built by |
|---|---|---|---|---|---|
| `fes2025_drivers.csv` | Annual series 2025–2050 for the five FES 2025 pathways (Ten Year Forecast to 2035): demand components, EV stock, heat pumps, capacities (3,689 rows, 34 series, columns `pathway, year, series, unit, value, sheet`) | NESO, *Future Energy Scenarios 2025 Data Workbook* V005 (version sheet: uploaded 11 November 2025), https://www.neso.energy/publications/future-energy-scenarios-fes; read from a local copy | not stated in the repository (see licence question b) | not stated | hand-made extract |
| `published_pathways.csv` | 1,765 values from 12 sources for comparison with the model: capacity, generation, demand, emissions, prices and costs by pathway and year, each with `url` and `verified` | NESO FES 2025 workbook; CCC *Seventh Carbon Budget* (charts and full dataset, report); DESNZ *Clean Power 2030 Action Plan* (main report and connections reform annex); NESO *Clean Power 2030* advice (data workbook V003 and Annex 4); DESNZ *Energy and Emissions Projections 2024–2050* Annexes J, L, M; DESNZ Green Book carbon values (2021) and traded carbon values for modelling (2025); Royal Society *Large-scale electricity storage* (2023); Energy Systems Catapult *Innovating to Net Zero* (2024); Price, Keppo and Dodds, *Energy* 262 (2023), https://doi.org/10.1016/j.energy.2022.125450; Aurora Energy Research for Policy Exchange (2024); Cornwall Insight (two values from a search snippet, `verified` = `search`) | not stated in the repository for any of the 12 sources | not stated | hand-made extract |
| `NOTES.md` | Definitions, sheets and inconsistencies between sources | – | – | – | hand-made |

`NOTES.md` does not quite match the committed files: it calls the comparison file `pathways.csv`
(the file is `published_pathways.csv`), and describes `fes2025_drivers.csv` as 16,510 rows and 152
series with `definition_note` and `verified` columns, whereas the committed file has 3,689 rows, 34
series and neither column. The committed file appears to be a subset of the extract described.

## `data/external/`: neighbouring markets' prices

| Path | What it is | Source | Licence | Attribution | Built by |
|---|---|---|---|---|---|
| `neighbour_prices_<year>.csv` (2021–2025) | Hourly day-ahead prices (EUR/MWh, UTC) for FR, NL, BE, NO2, DK1 and DE-LU, aligned with the profile of the same year | Energy-Charts API (Fraunhofer ISE), https://api.energy-charts.info/price; for these zones the data are Bundesnetzagentur \| SMARD.de | CC BY 4.0 (stated in `data/external/README.md` and `scripts/fetch_neighbour_prices.py`) | SMARD credit (proposed wording above) | `scripts/fetch_neighbour_prices.py <year>` |

`data/external/README.md` lists only the 2024 file and refers to "the ESPENI profile"; both are out of
date. The Irish market (SEM) has no openly licensed hourly series there, so the model uses a proxy
shaped by GB wind (`ukabm/data/pypsagb.py`).

## `data/outturn/`: GB outturn for comparison

| Path | What it is | Source | Licence | Attribution | Built by |
|---|---|---|---|---|---|
| `gb_annual_outturn.csv` | One row per year 2021–2025: generation by fuel (incl. embedded wind and solar), NESO carbon intensity, MID price statistics, interconnector flows and peak import, CCGT/OCGT split | NESO "Historic generation mix and carbon intensity" (`df_fuel_ckan.csv`); Elexon Insights API, Market Index Data (APXMIDP) and FUELHH | NESO ODL v1.0; Elexon BMRS licence | NESO and Elexon statements | `scripts/fetch_outturn.py <years>` |
| `gb_constraints.csv` | 2025 constraint cost (£1.83bn), renewable turn-down (10.4 TWh) and BM premia (£0.54bn) | LCP Delta, *From Bottlenecks to Balance* (March 2026), pp. 16–19 and 45, from NESO constraint and BM data | not stated in the repository; the foundations review calls LCP figures commercial products. Only three figures are quoted | not stated | hand-entered (`ukabm/outturn.py`: "hand-entered from cited reports") |

## `data/pypsagb_snapshot/`: extracts of PyPSA-GB

Small extracts of [PyPSA-GB](https://github.com/andrewlyden/PyPSA-GB) (MIT licence, same maintainer),
so that the model runs without a PyPSA-GB clone. `python scripts/extract_pypsagb_snapshot.py
/path/to/PyPSA-GB` rebuilds them through `ukabm/data/pypsagb.py` (needs the `raw` extra: `pyproj`,
`openpyxl`). The README in the folder says that "ESPENI and DUKES carry their own licences/attribution
(see PyPSA-GB docs)"; those licences are not reproduced in this repository.

| Path | What it is | Underlying source | Licence | Attribution | Built by |
|---|---|---|---|---|---|
| `zonal_buses.csv`, `zonal_links.csv` | 20 zone buses and 31 internal transfer links | PyPSA-GB `data/network/zonal/` | MIT (PyPSA-GB); original source of the network data not stated in the repository | PyPSA-GB MIT notice | `scripts/extract_pypsagb_snapshot.py` |
| `interconnectors.csv` | Interconnector register: name, country, landing zone, MW, year (14 rows) | PyPSA-GB `data/network/zonal/links_future.csv` | MIT (PyPSA-GB) | PyPSA-GB MIT notice | `scripts/extract_pypsagb_snapshot.py` |
| `zone_demand_share.csv` | Share of GB demand by zone (population weights) | PyPSA-GB `zone_definitions.csv` | MIT (PyPSA-GB); population data source not stated | PyPSA-GB MIT notice | `scripts/extract_pypsagb_snapshot.py` |
| `zone_tech_share.csv` | Share of each technology's capacity by zone | PyPSA-GB `dukes_power_station_coordinates.csv` (DUKES station coordinates mapped to the nearest zone) | MIT (PyPSA-GB); DUKES OGL v3.0 | PyPSA-GB MIT notice; OGL statement | `scripts/extract_pypsagb_snapshot.py` |
| `cfd_strike_prices_by_round.csv` | CfD contracts by round, technology and delivery year: strike (2012 prices) and MW (69 rows) | PyPSA-GB `data/market/lccc/`; rows cite DECC/BEIS/DESNZ allocation round results AR1–AR7a (gov.uk), NAO reports (2014, 2017), a Drax press release and environmental-finance.com. **Seven rows labelled `AR8_modelled` are modelled values, not results** (PyPSA-GB's `build_ar8_modelled_strikes.py`) | MIT (PyPSA-GB); OGL v3.0 for the allocation round results (stated in `data/fleet/README.md`); not stated for the NAO, Drax and press rows | PyPSA-GB MIT notice; OGL statement | `scripts/extract_pypsagb_snapshot.py` |
| `cm_auction_parameters.csv` | Capacity Market targets, demand-curve points, net CONE, price cap and clearing for T-4 2028/29, 2029/30, 2030/31 and T-1 2029/30 (4 rows) | DESNZ parameter letters (July 2025, July 2026); NESO auction static data; Deloitte Auction Monitor Report (12 March 2026) | MIT (PyPSA-GB); underlying documents not stated | PyPSA-GB MIT notice | `scripts/extract_pypsagb_snapshot.py` |
| `emissions_intensity.csv` | Emission intensity by generation type (49 rows), kept for reference | PyPSA-GB `emissions_intensity_by_types.csv`; original source not stated | MIT (PyPSA-GB) | PyPSA-GB MIT notice | `scripts/extract_pypsagb_snapshot.py` |
| `profiles_2024.csv` | Hourly 2024 demand, one GB wind shape and solar shape | ESPENI (via PyPSA-GB `data/demand/espeni.csv`), hourly means; capacity factors normalised by a high quantile | **ESPENI: v1.0.0 (2020) CC BY 4.0; current versions CC BY-NC 4.0** (stated in `docs/research/literature_review.md`). The version behind this file is not recorded | not stated | `scripts/extract_pypsagb_snapshot.py` |

The model uses `profiles_2024.csv` only when it is asked for with `PyPSAGBData(profiles="espeni")`;
no script or test asks for it. Note also that re-running `scripts/extract_pypsagb_snapshot.py` now
writes the open NESO/Elexon profile of the year into `profiles_<year>.csv`, not the ESPENI profile,
because `PyPSAGBData` replaces the ESPENI profile with the open one when `data/profiles/profiles_<year>.csv`
exists.

## Other inputs that are not datasets

* `ukabm/data/scenarios.toml`: scenario definitions written by the authors (MIT, part of the code).
* `results/`: model outputs committed by hand; produced at different commits (each file states the
  commit or should be checked against `git log`).

## Licence questions for the maintainer

These points are not settled by anything in the repository and need a decision by a person.

a. **`data/pypsagb_snapshot/profiles_2024.csv` (ESPENI).** It is derived from ESPENI, whose current
   versions are licensed CC BY-NC 4.0; only the 2020 release (v1.0.0) was CC BY 4.0, and that release
   cannot contain 2024 data. A non-commercial file does not fit redistribution in an MIT repository.
   Since the open NESO/Elexon profiles replaced it as the default, it is read only when
   `profiles="espeni"` is requested, and no script or test requests it. **Recommendation: delete the
   file and the `"espeni"` option** (and change `scripts/extract_pypsagb_snapshot.py` so that it no
   longer writes profiles). Until then, the README in the folder should state its licence.
b. **FES 2025 values in `data/fes/`.** `fes2025_drivers.csv` and the FES rows of
   `published_pathways.csv` were read from the FES 2025 Data Workbook, a document published on
   NESO's website. It is not established whether the workbook is a dataset released under the NESO
   ODL v1.0 (which permits redistribution with the statement "Supported by National Energy SO Open
   Data") or a publication covered only by the website's terms of use. The NESO ODL is applied per
   dataset on the Data Portal; the FES workbook is distributed from the publications pages. The
   maintainer should check the workbook's own licence statement, or ask NESO, before the files are
   released.
c. **The other 11 sources in `published_pathways.csv`.** CCC, DESNZ, NESO advice, Royal Society,
   Energy Systems Catapult, Aurora/Policy Exchange, Cornwall Insight and the *Energy* article: the
   licence of each is not stated in the repository. The file holds individual figures with citations,
   which may be acceptable as quotation, but this has not been checked. The two Cornwall Insight values
   come from a search snippet whose page returned 404 and should be removed or verified.
d. **Hand-made source tables in `data/history/sources/`.** `prices.csv` (Ofgem, UK ETS Authority, HMRC,
   EEA, DESNZ projections), `ecb_gbp_per_eur.csv` (ECB), `cm_auctions.csv` (NESO register, EMR Delivery
   Body, BEIS/DESNZ, Ofgem), `ro_fit.csv` (Ofgem, DECC, DLUHC) and the non-DUKES rows of
   `closures_openings.csv` (EDF, Centrica, NAO): the licence of each source is not stated in the
   repository. Many are UK government or regulator publications that are likely OGL v3.0, but the
   repository does not say so and Ofgem, NESO and the ECB publish under their own terms.
e. **DESNZ Quarterly Energy Prices and Energy and Emissions Projections**, which feed `annual_inputs.csv`
   (used by the model for historical years): licence not stated in the repository.
f. **`data/outturn/gb_constraints.csv` (LCP Delta).** A commercial report; three figures are quoted.
   Whether quoting them is permitted is not recorded.
g. **Wikipedia years in `wind_units_manual.csv`.** Only commissioning years are taken, which are facts,
   but the file also quotes farm names and dates from a CC BY-SA 4.0 table. Whether ShareAlike applies
   to the file should be decided; if so, the file needs the CC BY-SA notice or the years should be taken
   from another source (DUKES Table 5.11 or the Crown Estate).
h. **PyPSA-GB extracts.** PyPSA-GB is MIT, but the snapshot does not carry PyPSA-GB's copyright notice,
   and several extracts contain third-party data whose licences are not reproduced here (DUKES
   coordinates, network data, population weights, CfD and CM documents, the Deloitte report). The
   `AR8_modelled` rows are model output from PyPSA-GB, not published data, although the file is
   described as a register extract.
i. **SMARD attribution.** The CC BY 4.0 credit line for the neighbour prices is proposed above; the form
   SMARD asks for should be checked, and whether Energy-Charts adds terms of its own.
j. **NESO and Elexon attribution in outputs.** The model's results (`results/`) and figures are derived
   from NESO and Elexon data (profiles, outturn). The required statements should appear in the README
   and in any release, not only in `data/profiles/README.md`.
