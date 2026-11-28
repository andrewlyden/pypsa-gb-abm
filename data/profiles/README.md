# Hourly demand, wind and solar profiles for Great Britain

Built by `scripts/build_profiles.py` from openly licensed NESO and Elexon data:

    python scripts/build_profiles.py 2024

The script downloads what it needs to `data/profiles/raw/` (not committed; a second run reuses it), prints the
checks below and writes a year only if the checks pass.

| File | Content |
|---|---|
| `profiles_<year>.csv` | the hourly profile, 8,760 rows |
| `wind_units_<year>.csv` | every wind BM unit used: type, region, capacity and its source, metered and turned-down energy, capacity factors, vintage |
| `wind_cf_by_vintage_<year>.csv` | capacity factor by type and vintage band (units complete all year) |
| `validation.csv` | the check figures, one row per year built |
| `wind_units_manual.csv` | hand-made input: unit classifications and offshore commissioning years, a source per row |
| `benchmarks_desnz.csv` | input: DESNZ Energy Trends table 6.1 figures used in the checks |

Years built: 2021, 2022, 2023, 2024 and 2025. Not built: 2019 and earlier (the Elexon API has per-unit output, B1610, from
1 February 2019 only, and the capacity rule needs the last quarter of the previous year); 2020 was not asked for.

## Columns of `profiles_<year>.csv`

One row per hour, UTC, the first 8,760 hours of the year (in a leap year 31 December is dropped). Each value is
the mean of the two half hours.

| Column | Meaning |
|---|---|
| `demand_mw` | GB demand consistent with NESO's generation mix: `GENERATION` (all GB generation and imports, including embedded wind and solar) minus interconnector exports minus pumped-storage pumping. Includes station load and battery charging. See "Demand". |
| `wind_onshore_cf` | available output per MW of the GB onshore fleet: onshore wind BM units plus NESO's embedded wind |
| `wind_offshore_cf` | available output per MW of the offshore wind BM units |
| `solar_cf` | NESO embedded solar generation / embedded solar capacity |
| `hour`, `doy` | hour of day (0-23) and day of year (1-365), UTC |
| `wind_onshore_scot_cf` | onshore BM units in Scotland |
| `wind_onshore_ew_cf` | onshore BM units in England & Wales plus NESO's embedded wind (see the warning under "Regions") |
| `wind_offshore_scot_cf` | offshore BM units connected in Scotland |
| `wind_offshore_ew_cf` | offshore BM units connected in England & Wales |
| `demand_nd_embedded_mw` | NESO national demand ND + embedded wind + embedded solar (the earlier definition; excludes station load) |

"Available" means what the wind could have produced: metered output plus the volume turned down in the Balancing
Mechanism. The model curtails wind itself, so it must not be given output that is already curtailed.

## Method

**Wind units.** The 241 BM units with fuel type WIND in Elexon's BM unit list, plus Goole Fields
(`wind_units_manual.csv`). 202 of them generated in 2024; the others are newer, or supplier units without
output. Offshore units are identified by, in order: the manual file (9 units whose names say so); an id ending
`O-<n>`; IGCPU production type "Wind Offshore". IGCPU alone is not usable: it covers 131 wind units and mislabels some (West of Duddon Sands is
"Wind Onshore", Fort Dunlop gas turbine and Moriston hydro are "Wind Onshore").

**Regions.** Scotland = GSP groups North Scotland and South Scotland. Transmission-connected units have no GSP
group; they are placed by their transmission loss factor, which is set per GSP-group zone, so a unit belongs to
the zone whose embedded units carry the same factor. No unit needed a manual region. The region is that of the
grid connection: Robin Rigg stands in Scottish waters but connects in Cumbria and is England & Wales here.
*Warning for `wind_onshore_ew_cf`*: only two onshore wind farms in England & Wales are BM units (Pen y Cymoedd
and Goole Fields, 260 MW). NESO does not publish embedded wind by region, so the series is those two farms
plus the whole GB embedded fleet (6.5 GW), part of which is in Scotland. It is the best open proxy for wind
outside the Scottish transmission-connected fleet, not a clean England & Wales series. Its hourly correlation
with the two-farm series alone is 0.76 to 0.83, depending on the year. The two regional onshore series together make up exactly
the fleet of `wind_onshore_cf`.

**Output.** B1610 "Actual generation output per generation unit": metered volume per unit and half hour, latest
settlement run. Negative values (imports of idle wind farms) are set to zero.

**Curtailment added back.** BOAV "Bid-offer acceptance volumes" gives, per acceptance and half hour, the
accepted volume in each bid-offer pair of each unit. The volumes in the negative pairs are below the unit's
final physical notification (FPN): bids, which are negative, and the offers that undo them. Minus their sum is
the turn-down, and

    available = metered output + turn-down     (not more than the unit's capacity)

Accepted volumes are measured from the FPN, which is the operator's own forecast of the unit's output an hour
ahead, so in a curtailed half hour the available output is in effect that forecast. For 2024 the turn-down
added back is 8.3 TWh (4.9 offshore, 3.4 onshore, 8.2 of it at Scottish units); the Electric Insights report
for Q4 2024 says "Some 8.3 TWh of wind energy had to be rejected from the grid" in 2024.

**Capacity of a unit.** Two capacities are published per unit: IGCPU "installed capacity" and the "generation
capacity" of the BM unit list. Neither is reliable (Moray East: 1,200 and 900 MW for a 950 MW wind farm;
Seagreen: 1,130 and 1,773 MW; Thanet: 518 MW for a 300 MW wind farm). Each is therefore tested against the
unit's own peak output P, the 99.9th percentile of its half-hourly output since 1 October of the previous year:

* the capacity of a complete unit is the published number closest to P if P is between 90% and 103% of it;
  otherwise it is P / 0.98, where 0.98 is the median of P / capacity over the units whose published number
  was kept (computed each year, `peak_share` in `validation.csv`);
* a unit has no capacity before it first generates;
* while the highest output a unit has shown so far (in the Decembers of earlier years, since 1 October of the
  previous year, and looking 30 days ahead) is below 90% of P, the unit is taken to be part-built and its
  capacity is that highest output / 0.98. This follows wind farms through commissioning (Seagreen 2023, Moray
  West, Neart na Gaoithe and Dogger Bank A in 2024).

`wind_units_<year>.csv` shows the result for every unit (`capacity_source`: IGCPU, bmunits or own peak).

**Aggregation.** A fleet's capacity factor in a half hour is the sum of available output over the sum of
capacity of its units. The national onshore series adds NESO's embedded wind generation and capacity to both
sums. Hourly means, UTC.

## Validation

`validation.csv` holds all figures. "Metered" is before the curtailment add-back and is the figure comparable
with DESNZ; "DESNZ method" divides the metered energy by the mean of the capacity at the start and the end of
the year, as DESNZ does. DESNZ: Energy Trends table ET 6.1 "Renewable electricity capacity and generation",
edition of 29 September 2026 (`benchmarks_desnz.csv`). DESNZ figures are for the UK; all Northern Irish wind is
onshore, so "GB" onshore is the UK figure less the Northern Ireland sheet. NESO mix: wind (transmission) +
embedded wind in the "Historic generation mix" file.

| | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---:|---:|---:|---:|---:|
| **Capacity factor, offshore** | | | | | |
| available (the profile) | 38.2% | 41.1% | 40.5% | 41.5% | 41.3% |
| metered | 37.6% | 39.5% | 39.1% | 37.6% | 36.8% |
| metered, DESNZ method | 37.4% | 40.1% | 39.7% | 37.1% | 37.0% |
| DESNZ ET 6.1 load factor (UK) | 37.8% | 41.3% | 39.7% | 36.2% | 36.4% |
| **Capacity factor, onshore** | | | | | |
| available (the profile) | 26.1% | 30.4% | 27.5% | 29.9% | 29.3% |
| metered | 24.5% | 28.6% | 25.2% | 27.2% | 26.2% |
| metered, DESNZ method | 24.4% | 28.6% | 25.4% | 27.3% | 26.3% |
| DESNZ ET 6.1 load factor (GB = UK less NI) | 23.0% | 27.4% | 24.7% | 25.4% | 24.3% |
| DESNZ ET 6.1 load factor (UK) | 23.4% | 27.3% | 25.1% | 25.0% | 24.1% |
| **Capacity factor by region, available (metered)** | | | | | |
| offshore, Scotland | 38.0% (33.3%) | 45.5% (35.2%) | 30.2% (24.1%) | 43.0% (25.4%) | 40.7% (23.7%) |
| offshore, England & Wales | 38.3% (38.1%) | 40.4% (40.1%) | 42.9% (42.7%) | 41.1% (40.9%) | 41.5% (41.4%) |
| onshore, Scotland (BM units) | 26.1% (22.7%) | 32.0% (28.2%) | 27.5% (23.1%) | 30.5% (25.1%) | 29.1% (23.2%) |
| onshore, E&W BM units + embedded | 26.0% | 29.0% | 27.4% | 29.4% | 29.6% |
| embedded wind alone (NESO estimate) | 25.9% | 28.9% | 27.2% | 29.4% | 29.5% |
| **Solar capacity factor** | | | | | |
| profile | 9.8% | 10.5% | 9.7% | 9.0% | 10.3% |
| DESNZ ET 6.1 load factor (UK) | 9.9% | 11.0% | 10.5% | 9.2% | 11.1% |
| **Wind energy, TWh (capacity factor x capacity, whole year)** | | | | | |
| metered: BM units + embedded | 61.8 | 75.9 | 77.3 | 80.7 | 83.9 |
| NESO generation mix: wind + embedded wind | 62.2 (-0.6%) | 77.2 (-1.7%) | 78.9 (-2.1%) | 82.7 (-2.4%) | 85.8 (-2.3%) |
| DESNZ, GB (offshore + onshore less NI) | 61.6 (+0.3%) | 76.8 (-1.2%) | 79.2 (-2.4%) | 80.9 (-0.3%) | 83.6 (+0.4%) |
| offshore metered / DESNZ | 34.7 / 35.6 | 43.3 / 45.1 | 47.5 / 49.4 | 47.3 / 48.8 | 50.5 / 52.0 |
| onshore metered / DESNZ GB | 27.1 / 26.0 | 32.6 / 31.7 | 29.8 / 29.7 | 33.4 / 32.1 | 33.4 / 31.5 |
| turn-down added back: offshore / onshore | 0.55 / 1.77 | 1.80 / 2.06 | 1.66 / 2.64 | 4.90 / 3.38 | 6.24 / 3.91 |
| of which at Scottish units | 2.21 | 3.62 | 4.04 | 8.17 | 9.98 |
| **Capacity, MW, start -> end of year** | | | | | |
| offshore BM units | 9,751 -> 11,432 | 11,538 -> 13,146 | 13,157 -> 14,169 | 13,967 -> 15,019 | 15,167 -> 15,968 |
| DESNZ offshore (UK = GB) | 10,383 -> 11,255 | 11,255 -> 13,847 | 13,847 -> 14,735 | 14,735 -> 16,140 | 16,140 -> 16,650 |
| onshore: BM units + embedded | 12,439 -> 12,849 | 12,862 -> 13,176 | 13,199 -> 13,549 | 13,589 -> 14,232 | 14,264 -> 14,802 |
| of which embedded (NESO) | 6,527 -> 6,527 | 6,527 -> 6,545 | 6,545 -> 6,488 | 6,488 -> 6,606 | 6,606 -> 6,606 |
| DESNZ onshore, GB | 12,720 -> 13,063 | 13,063 -> 13,410 | 13,410 -> 14,082 | 14,082 -> 14,728 | 14,728 -> 14,912 |
| **Shape (hourly)** | | | | | |
| correlation onshore / offshore | 0.783 | 0.789 | 0.759 | 0.783 | 0.800 |
| correlation onshore Scotland / onshore E&W | 0.824 | 0.851 | 0.808 | 0.838 | 0.808 |
| correlation offshore Scotland / offshore E&W | 0.492 | 0.474 | 0.346 | 0.485 | 0.483 |
| hours with onshore CF < 0.1 | 25.8% | 17.0% | 19.3% | 17.8% | 17.3% |
| hours with offshore CF < 0.1 | 17.4% | 13.5% | 9.9% | 9.7% | 8.1% |
| **Nameplate factor: capacity used here / DESNZ installed capacity (means of start and end of year)** | | | | | |
| `nameplate_factor_offshore` | 0.979 | 0.983 | 0.956 | 0.939 | 0.950 |
| `nameplate_factor_onshore` (BM units + embedded / DESNZ GB) | 0.981 | 0.984 | 0.973 | 0.966 | 0.981 |
| **Demand, TWh (whole year)** | | | | | |
| demand_mw | 278.0 | 266.8 | 262.3 | 267.8 | 272.7 |
| demand_nd_embedded_mw | 274.9 | 263.0 | 257.2 | 261.8 | 264.9 |
| peak of demand_mw, GW | 48.6 | 48.7 | 46.4 | 48.2 | 48.9 |
| wind units with output | 169 | 182 | 189 | 202 | 217 |

Reading the table:

* **Energy.** Metered wind energy (units + embedded) is within 2.4% of DESNZ for GB in every year (-2.4% to
  +0.4%) and 0.6 to 2.4% below NESO's generation mix. In 2024 the half-hourly sum of the BM units correlates
  0.998 with NESO's transmission wind and is steadily 3% lower: B1610 is settlement metering at the boundary
  point, NESO's figure is operational metering.
* **Onshore / offshore split.** Offshore energy is below DESNZ and onshore above it. The likely reason is the
  older offshore wind farms that are not BM units (Kentish Flats, Lynn and Inner Dowsing, Rhyl Flats, Scroby
  Sands, Teesside, North Hoyle, Blyth, Methil; about 0.65 GW): they are not in the offshore fleet here and
  appear to be inside NESO's embedded wind, which is counted as onshore.
* **Level of the capacity factors and the nameplate factor.** The metered capacity factors are up to 2 points
  above DESNZ's load factors for onshore and within 1.2 points for offshore. The capacity behind them is lower
  than DESNZ's installed capacity (offshore 2 to 6% lower, onshore 2 to 3%), because DESNZ counts nameplate
  capacity as soon as it is installed, and small-scale wind, while a unit here counts once it generates, at a
  capacity it has demonstrated. **Multiplying these capacity factors by DESNZ's installed capacity therefore
  overstates wind energy.** `validation.csv` gives the correction per year, `nameplate_factor_offshore` and
  `nameplate_factor_onshore`: the mean of the capacity used here at the start and the end of the year over the
  same mean of DESNZ's GB installed capacity (onshore: BM units + NESO embedded capacity over DESNZ GB
  onshore). The model multiplies DESNZ nameplate capacity by a capacity factor, so it multiplies the profile by
  this factor; capacity x factor x capacity factor then returns the energy in the table above.
* **Turn-down.** The volume added back in 2024, 8.3 TWh, equals the Electric Insights figure quoted above; for
  2025 it is 10.2 TWh against 10.4 TWh of renewable turn-down in `data/outturn/gb_constraints.csv` (LCP Delta).
* **Checks that gate a year** (all must hold or nothing is written): metered wind energy within 5% of the NESO
  mix; metered load factor (DESNZ method) within 3 points of DESNZ for offshore and for onshore (GB); B1610
  present for every half hour; the demand data and the generation mix aligned in time (embedded solar of the
  two files correlated above 0.99); 8,760 hours without gaps.

## Demand

The model is calibrated against NESO's generation mix, whose `GENERATION` column is all GB generation plus
imports, embedded wind and solar included. The demand that this generation served is

    demand_mw = GENERATION - interconnector exports - pumped-storage pumping

with exports the negative interconnector flows of the NESO demand data, and pumping the net import of the
pumped-storage BM units in B1610. NESO states that in the mix "Pumped Storage units (NET) are represented in
the STORAGE category. All Net-Negative values are curtailed at zero", so the matching pumping is the negative
part of the fleet's net output; the positive part reproduces the mix's `STORAGE` to within 0.02 TWh in every year (last row of the table below).
NESO's own `PUMP_STORAGE_PUMPING` column is not used: for 2024 it sums to 1.72 TWh, less than the pumped-storage
generation in the mix (1.88 TWh), which a storage cycle with losses cannot produce; the BM units' meters show
2.71 TWh of pumping (2.51 TWh net of simultaneous generation).

Reconciliation (whole year, TWh):

| | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---:|---:|---:|---:|---:|
| generation mix `GENERATION` | 284.87 | 289.78 | 274.60 | 280.94 | 289.23 |
| - interconnector exports | 4.41 | 20.45 | 10.13 | 10.61 | 14.80 |
| - pumped-storage pumping (B1610, fleet net) | 2.42 | 2.57 | 2.20 | 2.51 | 1.72 |
| **= `demand_mw`** | **278.04** | **266.76** | **262.27** | **267.82** | **272.70** |
| `demand_nd_embedded_mw` (ND + embedded wind + solar) | 274.87 | 263.00 | 257.22 | 261.83 | 264.90 |
| **difference** | **3.16** | **3.76** | **5.04** | **5.99** | **7.80** |
| = station load allowance (TSD - ND - NESO pumping column - exports) | 4.74 | 4.74 | 4.73 | 4.77 | 4.75 |
| + mix transmission generation above TSD (`GENERATION` - embedded - TSD) | 0.46 | 0.65 | 1.03 | 1.94 | 3.26 |
| + embedded wind and solar, mix minus demand data | -1.57 | -1.01 | 0.06 | 0.08 | -0.00 |
| - pumping not in NESO's pumping column (B1610 net - column) | 0.46 | 0.62 | 0.79 | 0.79 | 0.21 |
| pumped-storage output: B1610 fleet net / mix `STORAGE` | 1.80 / 1.80 | 1.93 / 1.92 | 1.67 / 1.66 | 1.90 / 1.88 | 1.32 / 1.31 |

The earlier definition, ND + embedded wind + embedded solar, is kept as `demand_nd_embedded_mw`. ND excludes
station load by construction (NESO: "ND ... is the sum of metered generation, but excludes generation required
to meet station load, hydro storage pumping and interconnector exports"); NESO's station-load allowance is a
round 500 to 700 MW. The generation mix has no such deduction, so station load is in `demand_mw`.

Batteries: NESO states that "Batteries (NET discharge) are currently included in the OTHER category" of the
mix, floored at zero like pumped storage. Battery charging is therefore part of the load that `GENERATION`
served and is **inside `demand_mw`**. No data on battery charging is used here, so it is not removed and its
size is not estimated. A model that charges its own batteries on top of `demand_mw` counts that energy twice.

## Capacity factor by vintage

`wind_cf_by_vintage_<year>.csv`: for the units that were complete throughout the year, the capacity-weighted
capacity factor by type and vintage band. `cf_available` includes the curtailment add-back, `cf_metered` does
not. Units still commissioning in the year are excluded and counted in `units_excluded_commissioning`.

2021:

| Type | Vintage | Units | MW | CF available | CF metered | Excluded (commissioning) |
|---|---|---:|---:|---:|---:|---|
| offshore | pre-2015 | 24 | 3,503 | 35.3% | 35.2% | 0 units, 0 MW |
| offshore | 2015-2019 | 28 | 4,365 | 39.2% | 38.2% | 0 units, 0 MW |
| offshore | 2020 or later | 5 | 1,880 | 45.6% | 45.4% | 7 units, 1,683 MW |
| onshore | 2019 or earlier | 91 | 5,709 | 26.2% | 22.8% | 0 units, 0 MW |
| onshore | 2020 or later | 3 | 177 | 25.7% | 24.1% | 11 units, 436 MW |

2022:

| Type | Vintage | Units | MW | CF available | CF metered | Excluded (commissioning) |
|---|---|---:|---:|---:|---:|---|
| offshore | pre-2015 | 24 | 3,480 | 36.8% | 36.8% | 0 units, 0 MW |
| offshore | 2015-2019 | 28 | 4,364 | 42.7% | 41.1% | 0 units, 0 MW |
| offshore | 2020 or later | 10 | 3,242 | 46.1% | 42.0% | 7 units, 2,060 MW |
| onshore | 2019 or earlier | 88 | 5,543 | 31.8% | 28.4% | 3 units, 184 MW |
| onshore | 2020 or later | 14 | 640 | 35.7% | 29.4% | 8 units, 264 MW |

2023:

| Type | Vintage | Units | MW | CF available | CF metered | Excluded (commissioning) |
|---|---|---:|---:|---:|---:|---|
| offshore | pre-2015 | 24 | 3,489 | 39.1% | 38.9% | 0 units, 0 MW |
| offshore | 2015-2019 | 28 | 4,364 | 42.5% | 42.1% | 0 units, 0 MW |
| offshore | 2020 or later | 14 | 4,974 | 43.0% | 41.4% | 7 units, 1,342 MW |
| onshore | 2019 or earlier | 91 | 5,688 | 27.4% | 23.3% | 0 units, 0 MW |
| onshore | 2020 or later | 18 | 817 | 31.5% | 24.5% | 7 units, 556 MW |

2024:

| Type | Vintage | Units | MW | CF available | CF metered | Excluded (commissioning) |
|---|---|---:|---:|---:|---:|---|
| offshore | pre-2015 | 24 | 3,486 | 38.0% | 37.9% | 0 units, 0 MW |
| offshore | 2015-2019 | 28 | 4,364 | 41.7% | 41.6% | 0 units, 0 MW |
| offshore | 2020 or later | 19 | 6,034 | 44.0% | 35.3% | 9 units, 1,136 MW |
| onshore | 2019 or earlier | 91 | 5,707 | 30.0% | 25.6% | 0 units, 0 MW |
| onshore | 2020 or later | 23 | 1,317 | 31.6% | 25.5% | 8 units, 602 MW |

2025:

| Type | Vintage | Units | MW | CF available | CF metered | Excluded (commissioning) |
|---|---|---:|---:|---:|---:|---|
| offshore | pre-2015 | 24 | 3,493 | 36.9% | 36.7% | 0 units, 0 MW |
| offshore | 2015-2019 | 28 | 4,364 | 41.1% | 41.1% | 0 units, 0 MW |
| offshore | 2020 or later | 24 | 6,974 | 43.6% | 33.8% | 7 units, 1,136 MW |
| onshore | 2019 or earlier | 90 | 5,653 | 27.7% | 24.3% | 1 units, 82 MW |
| onshore | 2020 or later | 31 | 1,941 | 33.0% | 20.9% | 12 units, 520 MW |

How far to trust it:

* **Vintage year.** Offshore: the project commissioning year from Wikipedia's "List of offshore wind farms in
  the United Kingdom" (in `wind_units_manual.csv`, farm and date per unit), which is the year the whole farm
  was commissioned and can be later than its first power. Offshore farms not in that list,
  and all onshore units: the first December (from 2019) in which the unit generated in B1610, so "2019 or
  earlier" cannot be split for onshore. IGCPU's `effectiveFrom` is not a commissioning date (Clyde, built
  2012, has 2020-02; many units have 2019-01) and is not used.
* **Offshore, pre-2015 and 2015-2019.** Metered, hardly curtailed, 3 to 4 GW each: solid for the weather of
  the year. They contain real outages (a Gwynt y Mor unit ran at 8% in 2024).
* **Offshore, 2020 or later.** The evidence for new-build offshore. In 2024, 6.0 GW: Hornsea One and Two, East
  Anglia One and Triton Knoll (England, metered about 0.41 to 0.46) and Moray East and Seagreen (Scotland).
  For the Scottish two the available figure rests on the add-back (Seagreen: metered 0.14, available 0.47),
  i.e. on the operators' own notified output during curtailment, which nobody metered. Treat the band's
  `cf_available` as less certain than its English part alone.
* **Onshore.** Scottish transmission-connected and BM-registered farms only (5.7 GW "2019 or earlier", 1.3 GW
  "2020 or later" in 2024); no English or Welsh farm and no small embedded farm. Heavily curtailed: the
  difference between available and metered is 2 to 12 points depending on year and band, all from the add-back.
* One weather year per file. 2024 was a below-average wind year for offshore (DESNZ load factor 36.2%, against
  39.7% in 2023 and 41.3% in 2022).

## Sources and licences

| Data | Source | Licence |
|---|---|---|
| Demand, interconnector flows, embedded wind and solar | NESO Data Portal, "Historic Demand Data", https://www.neso.energy/data-portal/historic-demand-data | NESO Open Data Licence v1.0 |
| Generation by fuel | NESO Data Portal, "Historic generation mix and carbon intensity", https://www.neso.energy/data-portal/historic-generation-mix | NESO Open Data Licence v1.0 |
| BM units, IGCPU, B1610, BOAV | Elexon Insights Solution API, https://data.elexon.co.uk/bmrs/api/v1 (documentation https://bmrs.elexon.co.uk/api-documentation) | Elexon BMRS open data licence |
| Capacity, generation and load factors used in the checks | DESNZ, Energy Trends table ET 6.1, https://www.gov.uk/government/statistics/energy-trends-section-6-renewables | Open Government Licence v3.0 |
| Offshore commissioning years | Wikipedia, "List of offshore wind farms in the United Kingdom", https://en.wikipedia.org/wiki/List_of_offshore_wind_farms_in_the_United_Kingdom | CC BY-SA 4.0 (only the years are used) |
| Wind curtailed in 2024, for comparison | Electric Insights Q4 2024, "Wind becomes Britain's largest source of electricity in 2024", https://reports.electricinsights.co.uk/ | quoted figure only |

**NESO** (https://www.neso.energy/data-portal/neso-open-licence, "National Energy SO Open Data Licence v1.0";
both datasets carry "NESO Open Data Licence" in the portal metadata). Operative text: "The Licensor grants you
a worldwide, royalty-free, perpetual, non-exclusive licence to use the Information subject to the conditions
below." "You are free to: copy, publish, distribute and transmit the Information; adapt the Information;
exploit the Information commercially and non-commercially for example, by combining it with other Information,
or by including it in your own product or application." Condition: "Acknowledge NESO as the source of the
Information by including the following attribution statement 'Supported by National Energy SO Open Data'".

Attribution: **Supported by National Energy SO Open Data**

**Elexon** (https://www.elexon.co.uk/bsc/data/balancing-mechanism-reporting-agent/copyright-licence-bmrs-data/,
"Copyright: Licence to use BMRS open data"; it applies to users who are not BSC Parties, and defines BMRS Data
as "the BMRS Data made available on the Insights Solution website or (for historic BMRS Data) the Elexon Portal
website"). Operative text: "Elexon Limited hereby grants You a worldwide, royalty-free, perpetual,
non-exclusive licence to Use the BMRS Data subject to the conditions below." "You are free to: copy, publish,
distribute and transmit the BMRS Data; adapt the BMRS Data; exploit the BMRS Data, including commercially, or
by including it in your own product or application". Condition: "When You Use BMRS Data, You must always use
the following attribution statement to acknowledge the source of the information: Contains BMRS data © Elexon
Limited copyright and database right [year]. Where possible You must also contain a link to this licence."
The same statement must be passed on in any sub-licence.

Attribution: **Contains BMRS data © Elexon Limited copyright and database right 2026.**

**DESNZ**: Contains public sector information licensed under the Open Government Licence v3.0.

The profile files are derived from the NESO and Elexon data and carry both attributions.

## Known limitations

* **Available output during curtailment is the operator's forecast**, not a measurement. If operators notify
  more than the wind would have delivered, the add-back is too high. It is capped at the unit's capacity.
  Turn-down outside the Balancing Mechanism (trades and other balancing services) and curtailment of embedded
  wind by distribution networks are not added back. Wind that operators held back themselves, for instance at
  negative prices, is in neither the metered output nor the add-back.
* **Embedded wind is NESO's estimate**, not metered data, and is 46% of the onshore capacity. It appears to
  contain about 0.65 GW of older offshore wind farms. It is neither curtailed nor split by region.
* **`wind_onshore_ew_cf` is not a clean England & Wales series** (see "Regions").
* **Capacity is inferred** where the published numbers fail the test against output (34 of 202 units in 2024).
  A unit that ran at reduced capacity for the whole 15-month window gets a capacity that is too low and a
  capacity factor that is too high. Export limits below nameplate (Hornsea Two: 1,320 MW against 1,386 MW
  installed) are taken as the capacity.
* **Capacity basis differs from DESNZ** (see "Validation"): apply the nameplate factors of `validation.csv` when
  the profile is multiplied by DESNZ capacity.
* **A supplier unit in the list.** `2__BLOND003` ("EDFE Aggregate E Mids 03", fuel type WIND in Elexon's list)
  is an aggregate unit; it has output from 2025 only (13 MW on average) and is counted as onshore E&W.
* **Units outside the list.** `E_BODW-1` (up to about 40 MW, no entry in Elexon's BM unit list, identity not
  established) and `E_GNFSW-3` (Gunfleet Sands 3, 12 MW, which the API does not return when filtered by unit)
  are not included.
* **The unit list and the loss-factor zones are today's.** Units deregistered before the download are absent;
  none was found missing in spot checks of 2019, 2021 and 2025. Cached monthly files hold the units of the list
  at download time: delete `raw/elexon_b1610_wind_*` and `raw/elexon_boav_wind_*` after adding units.
* **Leap years** lose 31 December (8,760 hours). Annual figures in `validation.csv` are for the whole year.
* **Battery charging is inside `demand_mw`** (see "Demand").
