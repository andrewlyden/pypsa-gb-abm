# How the model's parameters are set, and how they are checked

This page is the record of calibration and checking (the part of a TRACE document that covers data,
parameters and corroboration). The full list of constants is in the [parameter register](parameters.md);
the datasets and their licences are in the [data register](data.md).

## The rule

1. **A published value is used where there is one.** Costs, hurdle rates, de-rating factors, support
   terms, fleets, prices and demand drivers come from official statistics and documents, read from the
   source table and kept in `data/` with the source next to the number.
2. **A measured value is used where the data allow it.** Hourly profiles and the capacity factor of
   new wind farms are computed from metered output.
3. **What is left is calibrated on one operating year, 2025, and checked on four others.** These are a
   handful of operating parameters that no source gives directly (listed below).
4. **Auction results and published pathways are checks, not targets.** No parameter is set so that the
   model reproduces a CfD strike, a Capacity Market price or a pathway's fleet. Where the model misses
   one, the miss is reported, with what it implies about bidders, and left in.

The reason for rule 4 is the number of observations. There are seven CfD rounds and a dozen T-4
auctions, held under costs and rules that changed between them. A model with as many adjustable
numbers as there are rounds can match all of them and learn nothing. PyPSA-GB's own work shows how
unstable a fitted number would be: the capital-cost factor at which published offshore wind costs
reproduce the cleared strike is 0.90 for Allocation Round 2, 0.52 for Round 3, 0.34 for Round 4, 0.85
for Round 6 and 0.90 for Round 7 (`data/public_ownership/financing/private_cost_calibration.csv` in
PyPSA-GB).

## What comes from where

| Input | Source | Built by |
|---|---|---|
| Hourly demand, onshore wind, offshore wind and solar, 2021–2025 | NESO historic demand data and generation mix; Elexon metered output and accepted bid volumes per wind farm | `scripts/build_profiles.py` → `data/profiles/` |
| Starting fleet: capacity by technology | DESNZ, DUKES 2026 Tables 5.12 and 5.16 (mean of end 2024 and end 2025) | `ukabm/config.py`, `data/history/gb_capacity.csv` |
| Starting fleet: vintages, locations, owners | DESNZ, DUKES 2026 Table 5.11 (station list) | `scripts/build_fleet.py` → `data/fleet/` |
| Support of existing plant; contracted pipeline | CfD allocation round results and the LCCC register (via PyPSA-GB); RO closure dates and bandings (Ofgem) | `scripts/build_fleet.py` |
| Capital cost, fixed cost, life, efficiency of new plant | DESNZ, Electricity Generation Costs 2025 | `scripts/build_costs.py` → `data/parameters/cost_paths.csv` |
| Hurdle rates by technology; merchant uplift | CEPA (2025) for DESNZ | `ukabm/config.py` |
| Capacity factor of new wind | measured: GB wind farms commissioned since 2020, mean of 2021–2025; then DESNZ's assumption for 2030–2040 | `data/profiles/wind_cf_by_vintage_*.csv`, `ukabm/config.py` |
| Fuel, carbon and power prices 2010–2025 | Ofgem, DESNZ, UK ETS Authority | `scripts/build_history.py` → `data/history/annual_inputs.csv` |
| Neighbouring markets' hourly prices 2021–2025 | Energy-Charts (Bundesnetzagentur, SMARD.de); ECB exchange rates | `scripts/fetch_neighbour_prices.py` |
| Offers of supported plant; scarcity mark-up; de-rating factors | contract terms as coded in PyPSA-GB; PyPSA-GB's 2024 scarcity curve; NESO de-rating factors | `ukabm/config.py` |
| Demand growth, EVs, electrolysers, interconnectors, nuclear, pumped hydro to 2050 | NESO Future Energy Scenarios 2025, the pathway named by `fes_pathway` | `ukabm/drivers.py`, `data/fes/` |

## What is calibrated, and on what

Set so that the 2025 operating year matches outturn, and not changed for other years:

| Parameter | Value | Set to match |
|---|---|---|
| Interconnector price level of neighbours against the GB gas plant, and the spread on flows | 0.68 (continent), 1.10 (Irish market); £12/MWh | 2025 gross imports and exports. Used for future years only: historical years use the neighbours' observed prices |
| Availability of the existing nuclear fleet | 0.62 (AGRs), 0.88 (Sizewell B) | nuclear output in 2024 and 2025 |
| Availability of biomass and hydro | 0.78, 0.26 | 2025 output on the capacity in the model |
| Efficiency of existing gas plant by age | 0.54 (new) to 0.46 (oldest) | the fleet's published mean efficiency of about 50 % (DUKES) |
| Battery revenue outside the hourly market | two pots, £128m and £4,780 per MW of wind and solar | the 2025 revenue index for GB batteries (Modo Energy) |
| Output of "other" plant (waste, CHP) | 0.7 GW at 0.65 | NESO's 2024 and 2025 mix |

Everything else in the register is `sourced`, `measured` or `assumed`. The `assumed` ones are the
authors' judgement and are where sensitivity tests should start: the five firm types and their traits,
the technologies each type invests in, the build-rate limits, the technical life of existing gas plant,
and the household heat-pump choice model.

## Check 1: operating back-cast, 2021–2025

`python scripts/run_backcast.py` runs each year on its own weather, fleet, fuel and carbon prices and
neighbour prices, and writes [results/backcast.md](../results/backcast.md). Only 2025 was used for
calibration.

What it shows:

* **Wind and solar output** (before curtailment) is within 3 % of outturn in all five years.
* **Net imports** are within 4 TWh in all five years, including 2022, when Great Britain exported on
  balance for the first time. Gross flows in both directions are too large in 2021–2023.
* **Gas generation** before redispatch is within 10 % in all five years.
* **The mean price** is within 3 % of the day-ahead baseload price in 2023, 2024 and 2025, and 12 % low
  in 2021 and 2022, the years of the gas crisis, when prices carried a premium the model does not have.
* **The price distribution is too narrow in every year.** The 5th percentile is about twice the
  outturn and there are no hours with a negative price, against 244 in 2025. In the cheapest hours the
  model imports at the neighbours' price plus the interconnector spread, and Great Britain is not in
  surplus. The 95th percentile is 10–12 % low in 2024 and 2025 with the scarcity mark-up, which was
  fitted (by PyPSA-GB) on 2024.
* **Nuclear output** is right in 2021 and 2025 and 10–20 % low in 2022–2024: availability was set on a
  poor year.

## Check 2: the first auctions

`python scripts/check_auctions.py` writes [results/auction_check.md](../results/auction_check.md).
The model starts in 2025, so its first CfD round is the counterpart of Allocation Round 7 and its
first T-4 auction that of the auction for 2029-30.

* **Solar** clears within 1 % of the Round 7 strike.
* **Offshore wind** clears about 20 % above it. With published costs and CEPA's hurdle rate the
  levelised cost of an offshore project commissioning in 2030 is £105/MWh (DESNZ's own figure is £103);
  Round 7 cleared at £91. The model's strike would equal the auction's with capital costs at 0.75 of the
  published ones, or a required return about two points lower, which is within the ±1.1–1.7 points of
  uncertainty that CEPA gives.
* **Onshore wind** clears about 13 % below the Round 7 strike: the published cost is lower than what
  bidders asked.
* **The Capacity Market** clears at about £38/kW for 2029 against £27 in the auction held; the auctions
  held since 2014 have ranged from £6 to £65.

Before the costs were taken from DESNZ's 2025 edition, including connection and use-of-system charges,
the model's offshore bids were £53–66/MWh.

## Check 3: published pathways

`python scripts/compare_pathways.py` writes
[results/pathways_comparison.md](../results/pathways_comparison.md): the baseline in 2030, 2035, 2040
and 2050 against the four FES 2025 pathways, the CCC's Balanced Pathway and the Clean Power 2030 range.
The table marks each quantity as a *driver* (taken from the pathway), a *target* (the government's
target path is the pathway's) or a *result*, because agreement means little for the first two.

Where the baseline is outside the range of the four FES pathways:

* **Heat pumps: 5 million homes in 2050 against 9–24 million.** Households choose on running cost at
  today's grant and price ratio, and the levy that pays for CfDs and capacity is on electricity bills.
  This is a result of the model, not an input, and it is the main difference from published thinking:
  the pathways assume the policy that closes this gap.
* **Offshore wind in 2030: 33 GW against 36–48 GW** (Clean Power 2030: 43–50 GW). The contracted
  pipeline gives 36 GW by 2031; a round held in 2025 delivers in 2030 and no more than 6 GW a year can
  come online.
* **Batteries in 2030 and 2035: 13 and 20 GW against 20–33 GW.** Capacity Market agreements already
  held by batteries not yet built are not in the starting pipeline.

## What has not been done

* No parameter has been estimated statistically; nothing here has a confidence interval.
* The firms' behavioural traits (cost-of-capital spread by type, expectation rule, mark-up) are
  assumptions. The auction check suggests which direction they are wrong in for offshore and onshore
  wind, but one round per technology cannot identify them.
* A hindcast of investment from 2015 (starting the model from the 2015 fleet and letting the firms bid
  in every round since) has not been run. The data for it are in `data/history/`.
* Seeds vary the firms' draws only. Weather is one year (2024) in the forward runs; profiles for
  2021–2025 are available for a weather-year sensitivity.
