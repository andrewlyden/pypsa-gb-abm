# PyPSA-GB data snapshot

Small extracts of [PyPSA-GB](https://github.com/andrewlyden/PyPSA-GB) data (MIT licence) so the ABM runs
without the full 5 GB clone. Rebuild with `python scripts/extract_pypsagb_snapshot.py /path/to/PyPSA-GB`.

| file | PyPSA-GB source | use in ukabm |
|---|---|---|
| zonal_buses.csv, zonal_links.csv | data/network/zonal/buses.csv, links.csv (internal links only) | PyPSA zonal redispatch |
| interconnectors.csv | data/network/zonal/links_future.csv | interconnector capacity by year |
| zone_demand_share.csv | data/network/zonal/zone_definitions.csv (population weights) | zonal demand split |
| zone_tech_share.csv | data/generators/dukes_power_station_coordinates.csv (OSGB -> nearest zone) | plant siting |
| profiles_2024.csv | data/demand/espeni.csv (2024, hourly mean) | demand shape, wind/solar CF shapes |
| cm_auction_parameters.csv | data/market/capacity_market/ | CM reference parameters |
| cfd_strike_prices_by_round.csv | data/market/lccc/ | legacy CfD strikes |
| emissions_intensity.csv | data/generators/emissions_intensity_by_types.csv | reference |

ESPENI and DUKES carry their own licences/attribution (see PyPSA-GB docs).
