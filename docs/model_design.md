# ukabm model design

A description by the ODD protocol, with a table from each part to the code, is in [odd.md](odd.md);
how parameters are set and checked is in [calibration.md](calibration.md). This page explains the
design and its history.

## Architecture
```
                 ┌───────────── Government / policy (config.Policy) ─────────────┐
                 │ carbon path · CfD rounds (pots, admin strikes) · T-4 CM · RO  │
                 └───────┬──────────────────────┬───────────────────────┬────────┘
                         │ contracts            │ levies                │ grants
 ┌──────────────┐  offers ┌──────────────────┐ prices ┌──────────────────────────────┐
 │ Firms (12,   │────────▶│ Hourly market     │──────▶│ Multi-energy modules          │
 │ real port-   │◀────────│ (uniform price,   │◀──────│ HeatModule (household agents) │
 │ folios, five │ dispatch│  scarcity mark-up,│ load  │ GasNetworkModule (tariffs)    │
 │ types: rates,│         │  storage, flex,   │       │ EVModule (smart/unmanaged)    │
 │ beliefs)     │         │  interconnectors) │       │ HydrogenModule (electrolysers)│
 └──────┬───────┘         └────────┬─────────┘       └──────────────────────────────┘
        │ invest/retire            │ sample hours
        ▼                          ▼
  plant pipeline         PyPSA-GB zonal network (PyPSA + HiGHS), ETYS boundary capabilities by year:
  (lead times)           BM-style redispatch (bids/offers) → constraint cost, curtailment, post-BM mix/CI;
                         zonal prices → siting signal only in the locational_signal (zonal-pricing) sensitivity
```

## Inputs (November 2026)
* **Starting fleet** (`data/fleet/`, `scripts/build_fleet.py`): capacity by technology from DUKES 2026;
  vintages, zones and owners from the DUKES station list; support from the CfD register and RO rules;
  the contracted pipeline (CfD awards not yet built); nuclear units by name. With a FES pathway, the
  pathway's nuclear and pumped hydro beyond the listed stations are committed plant in both runs.
* **Profiles** (`data/profiles/`, `scripts/build_profiles.py`): hourly demand, onshore and offshore wind
  and solar for 2021–2025 from NESO and Elexon data. `cf_profile(tech, online)` gives the fleet's shape to
  plant online by the start year and a shape raised to `config.NEW_BUILD_CF` to later plant.
* **Costs and rates** (`data/parameters/cost_paths.csv`, `config.HURDLE_RATE`): DESNZ 2025 costs by the
  year a plant comes online; CEPA hurdle rates by technology, plus 1.5 points for merchant revenue,
  shifted by the firm's cost of capital; capital carried over the build lag at the valuer's rate.
* **Drivers** (`ukabm/drivers.py`, `data/fes/`): a FES 2025 pathway sets demand other than EVs, heat
  pumps and electrolysis, the EV fleet, electrolysers, interconnectors, nuclear and pumped hydro, and
  the government's wind and solar targets.
* **History** (`data/history/`): fuel, carbon and power prices 2010–2025, capacity by year, auction
  results, for back-casts.

## Annual loop (`GBMarketModel.step`)
1. Commission pipeline / retire (end of life, 2 consecutive loss years without CM contract).
2. Demand = the weather year's measured shape × growth (the pathway's, for demand other than EVs, heat
   pumps and electrolysis) + heat-pump load (temperature-shaped) + EVs + electrolysers.
3. Market: pass 1 clears inflexible demand → smart EV valley-filling and electrolysers respond → storage
   is dispatched in tranches, each on the price left by the tranches before it, skipping days on which a
   tranche's own trades lose money → pass 2 → pass 3 withdraws electrolysers above their willingness-to-pay.
   Offers that the clearing cannot tell apart (same price, same availability shape) are merged before
   clearing and the dispatch split back pro rata. Supported plant offers by the terms of its support
   (RO at minus the certificate value, early CfDs at minus the strike, later CfDs at zero); the price is
   the marginal offer plus a scarcity mark-up that rises as the de-rated margin falls.
   The hourly merit order is built once per market run and reused across passes (`market.merit_order`). Interconnectors
   trade inside every pass: per neighbour market (FR, NL, BE, NO2, DK1, DE, SEM) an import offer at
   foreign price + spread and an export bid at foreign price − spread (a "buy-back" block, so exports
   are curtailed exactly when the GB price is above the bid). Foreign prices = existing-CCGT SRMC ×
   market level × the observed 2024 hourly price shape of that neighbour.
4. Settlement per plant: energy, CfD difference (strike – price), RO, CM; emissions; gas burn. Batteries
   also earn `battery_services_per_mw`: ancillary and intraday/BM trading pots shared across the fleet.
   The same function enters battery investment NPVs and CM bids, at the expected fleet size.
5. Every *k* years: network stage (`network_stage`). 96 hours stratified by wind CF. Each plant's market
   schedule can be turned down at its BM bid (`bm_bids`: thermal SRMC, −ROC, −CfD top-up, nuclear −£300)
   and its headroom turned up at its offer, on the 20-zone network with year-dependent boundary
   capabilities and monthly availability (`PyPSAGBData.links_for_year`, `link_availability`). Outputs:
   annualised constraint cost, curtailment, net redispatch by technology and post-BM NESO-basis CI
   (reporting only). Interconnector flows are fixed injections at their landing zones. Zonal prices feed
   siting only in the `locational_signal` sensitivity; by default siting follows resource shares
   (GB national pricing).
6. Retail tariffs (wholesale + network + levies) → household heating decisions; gas throughput (homes +
   industry + **power-sector gas burn**) → gas network tariff.
7. Investment: forecast prices for *t+3* from the known pipeline; CfD round; the government's tender
   for gas CCS and hydrogen power (`dpa_round`); T-4 and T-1 Capacity Market; sequential merchant
   decisions, re-forecasting after each (agents see each other's commitments), the order of firms drawn
   again before each. Awards and projects are limited by each technology's build rate
   (`build_room`), the same limits as the planner's.
8. Records: the annual row, the firm panel (`firm_panel()`, a Mesa DataCollector) and the auction table
   (`auctions()`).

## Agents
| agent | decisions | heterogeneity |
|---|---|---|
| Firms ×12 (RWE, SSE, EDF, Orsted, ScottishPower, Uniper, Drax and five groups; `data/fleet/firms.csv`). `firms: "stylised"` gives the earlier five | offers, CfD bids (the lowest strike that meets the required return over the contract and a merchant tail), CM bids (net missing money), merchant and PPA investment on lifetime forecasts, retirement | real portfolios; by type (utility, generator, fund, major, developer): cost-of-capital spread −1.7 to +2.3 points, myopic/adaptive/carbon-optimist beliefs, mark-ups 0–8 %, budgets, technologies invested in |
| Households ×2000 (each ≈14k homes) | heating system at boiler replacement (logit on lifecycle cost + hassle) | heat demand, discount rate, hassle cost, on/off gas grid, boiler age |
| Government (`ukabm.institutions`) | each CfD round's pots: volume limit, £ budget, administrative strike price; reacts to the last round and to the levy; tenders gas CCS and hydrogen power to its pathway | `government`: `targets` (default), `fixed`, `least_cost`, `bills`, `political` |
| System operator (`ukabm.institutions`) | CM target per auction (T-4, and T-1 under `standard`) | `system_operator`: `standard` (default) or `formula` |
| Policy (parameters) | carbon path, CM demand curve, HP grant, levy rebalancing | scenario |

### Decision interface (`ukabm.decisions`)
Every GenCo decision goes through a `DecisionMaker`: `offer_price`, `expected_carbon`,
`merchant_investment`, `cfd_bid` and `cm_bid`. The model calls the GenCo, and the GenCo calls its
decision maker with itself (traits, and the year, fleet, policy and forecasting helpers through
`agent.model`) and the call's arguments (price forecast, plant, technology). `RuleBased` holds the
rules described above and is the default; results are identical to the code before the interface.

Decisions receive an `Observation` (see below), not the agent. Other decision makers subclass
`RuleBased` (or `DecisionMaker`), override the decisions they make and
are registered by name. A scenario selects them with `decision_logic`: one name for every GenCo, or
`{genco_name: name}` for some (the rest keep `"rules"`). Each GenCo gets its own instance, so learning
agents can keep state. Random draws must come from `agent.model.rng`. Government and system-operator
agents, Q-learning and LLM decision makers (README roadmap items 2, 5, 6, 24, 25) plug in here.

### Information sets, action spaces and rewards (`ukabm.observations`)
A decision maker never sees the model. For each decision the GenCo builds an `Observation`:
* `traits`: the firm's own characteristics and the budget it has left this year;
* `own`: views of its own plants (`PlantView`: capacity, dates, support, CM agreement, profit history),
  with no link to the model or to other firms;
* `market`: public information (year, published policy, last year's hourly prices as a read-only array,
  last T-4 and CfD clearing prices, banned technologies), the seeded random generator, and analysis
  tools that use only public information (capacity factors, a technology's expected margin on a price
  series, the long-horizon price forecasts);
* the decision's fields: `forecast`, `tech`, `plant`, `srmc`, `margin_per_kw`, `new`, `year`, and
  `options` (the technologies the firm may build: investable, allowed and affordable).

Each decision has a declared action space (`ACTIONS`: offer price, expected carbon price, a merchant
investment among `options` or none, a CfD strike or abstain, a CM bid) and the GenCo checks every
answer (`validate`), so an invalid action raises an error. Once a year after settlement each decision
maker's `learn(outcome)` receives the firm's realised profit, in total and by plant: the reward for
learning agents. `Observation.to_dict()` gives a JSON-safe summary for logs and LLM prompts.

The rule-based and `expectations` logics were ported to observations with identical results. The
tools are a boundary, not a sandbox (they are closures over the model). Today's forecasts are still the
model's own (perfect knowledge of the committed pipeline and published paths); firms' own imperfect
forecasts are item 36. Governments and system operators keep model access for now.

### Government and the CfD auction (`ukabm.institutions`)
Each year the government sets every technology pot of the CfD round (`PotSettings`): a volume limit, an
administrative strike price (bids above it are excluded) and an annual £ budget. Bids clear pay-as-clear
per pot: blocks are accepted cheapest first while the pot is under its volume limit and while all accepted
MW, paid the current bid as clearing strike, cost no more than the budget. Support per MW is valued as
(strike − forecast capture price) × expected generation, floored at zero (a simplification of the
allocation framework's budget impact). The government then sees the result (`observe`).

* `fixed` (default): the original rule, 6 GW a year at 60/20/20 with the policy caps and no £ budget.
  Results are identical to the code before the government agent.
* `targets`: asks for the capacity missing at each technology's delivery year against
  `config.CFD_TARGET_GW` (Clean Power 2030 lower bounds for 2030; indicative after), budgets it at the
  strike it expects (the pot's last clearing, else the cap) with 10 % headroom, raises a pot's cap by
  15 % (up to 2× the policy cap) after a round that failed for lack of bids under the cap, and cuts
  budgets to 60 % while the policy levy is above £30/MWh (`config.GOVERNMENT_TARGETS`, overridable with
  `government_params`; targets with `cfd_targets_gw`).

Firms still bid levelised cost ± noise (item 3 changes this), and each GenCo offers at most two blocks
per technology a year, so the supply of bids, not the government, limits early rounds in `targets`
(up to 10 GW offshore a year; the developer pipeline is item 18). New annual columns:
`cfd_awarded_mw`, `cfd_budget_bn`; per-round detail in `model.government.log`.

### CfD bids from expectations (`decision_logic: "expectations"`)
`ExpectationBids` replaces the levelised-cost bid with the lowest strike at which the project meets the
firm's hurdle rate: a 20-year two-way CfD at the de-risked rate (WACC − 2.5 points, floor 3.5 %), 2 % of
output unpaid (basis), then a merchant tail to the end of the asset's life at the firm's WACC, valued at
the firm's own capture-price view (myopic: this year's prices; adaptive: the t+3 forecast less 15 %;
carbon optimist: the forecast). Risk aversion adds a premium; ±2 % noise stands for project costs. A
firm whose required strike is above the cap is excluded (abstains). Other decisions are `RuleBased`.
Not yet the default (with the `targets` government, after items 4–6).

### Merchant and PPA investment over the asset's life (`decision_logic: "expectations"`)
`ExpectationBids` also replaces the merchant rule. Each candidate is valued on a margin path, not one
year: the t+3 forecast plus `GBMarketModel.forecast_horizons()` at t+8 and t+13, interpolated over the
asset's life (flat after the last point). The long-horizon fleet is the t+3 pipeline held, plus wind and
solar growing at their build rate of the last five years (cannibalisation), plus peaking capacity that
keeps the de-rated margin at the CM target, so investors expect an adequate system rather than
scarcity prices. Wind and solar are candidates alongside CfDs, merchant or on a 15-year PPA at 10 %
below the t+3 capture value with the cost of capital 1.5 points lower; the better of the two counts.
Two extra market clearings per model year.

### Government objectives (levers)
Three more governments, each a `TargetTracking` variant selected by `scenario["government"]`:
* `least_cost`: at its first round it solves the planner (`ukabm.planner.plan`) on the model's expected
  inflexible demand per five-year period and tracks the planner's wind and solar pathway (existing
  fleet plus cumulative build), ignoring the levy. This is the ideal-government rung. One planner solve
  per run (~10–30 minutes with the reserve requirement). On the baseline the planner's pathway reaches ~40–45 GW offshore and ~58 GW
  onshore by 2050, against the CfD rules' ~90 GW offshore.
* `bills`: the same targets at the lowest levy: squeeze from £20/MWh, to 40 % of the budget, caps rising
  5 % after a failed round (`config.GOVERNMENT_BILLS`).
* `political`: targets announced 15 % above the path; in the two years before each general election
  (2029, then every five years) it funds 30 % of the missing capacity, and 130 % of the budget otherwise
  (`config.GOVERNMENT_POLITICAL`).
All parameters are illustrative assumptions for comparing objectives, not estimates of actual policy.

### System operator and the Capacity Market target (`ukabm.institutions.SystemOperator`)
`scenario["system_operator"]`:
* `formula` (default): the original target, peak demand in the delivery year × 1.06 less the de-rated
  capacity of CfD/RO plant; T-4 only. Results identical to the code before.
* `standard`: a NESO-style reliability standard. Supported wind and solar enter through their hourly
  output in the delivery year; the target is the 4th-highest hour of the remaining net demand (3 h LOLE
  on the model's one weather year, `weather_margin` for more), 5 % of it held back for a T-1 auction a
  year ahead that buys what is still missing (plants with agreements covering the year and
  interconnectors count as held). Delivery 2029: 41.6 GW full target, 39.5 GW at T-4, against
  39.4 GW published for 2029/30; the formula gives 49.4 GW. The first T-1 auctions are larger because
  the model starts without the agreements earlier auctions would have signed.

### Convergence test (`competitive_benchmark`, `scripts/run_convergence.py`)
Textbook conditions under which a competitive market should reproduce the least-cost plan: no CfD, no
CM, scarcity priced only by unserved energy at VoLL (`scarcity_adder: False`), idealised firms on the
`expectations` logic with up to 40 merchant decisions a year. A benchmark, not a policy scenario
(`scenarios.BENCHMARKS`, not run by `run_scenarios.py`). First trial (seed 1, 2025–2035): gap 1.7 % of
the optimum's PV cost (investment 0.7 %, operation 1.0 %), within the 3 % aim, but with a very different
fleet (2035: 10 vs 46 GW offshore, 55 vs 30 GW onshore, 17 vs 2 GW batteries). The cost surface is flat
near the optimum, so fleets can differ a lot at almost the same cost (README item 10, near-optimal space).
Full run (3 seeds, to 2050) pending; slow test `tests/test_convergence.py` (`UKABM_SLOW=1`).

## Multi-energy hooks (extension points)
* `HeatModule.hourly_load` — swap synthetic temperature for PyPSA-GB atlite cutouts; add HP flexibility.
* `GasNetworkModule.update(h2_blend=…)` — hydrogen blending / network repurposing.
* `HydrogenModule` — add H2 storage and endogenous H2 price feeding `Fuels.hydrogen` for h2_turbine.
* `EVModule` — replace stock path with adoption agents; V2G as storage.
* `network.redispatch` — add zonal (Scottish vs English) wind profiles, KVL on the PyPSA-GB Reduced
  (32-bus) network, or call PyPSA-GB's `solve_balancing.py` stage directly with ABM bids; feed
  constraint costs into BSUoS in the retail tariff.

## Optimal versus emergent (`ukabm.gap`)
```
 scenario + seed ──▶ Run 2: GBMarketModel (agents)  ──▶ agents' fleet by year, realised system cost
        │                     │ realised inflexible demand, starting fleet
        │                     ▼
        └──────────▶ Run 1: planner.plan (PyPSA multi-period LP) ──▶ planner's fleet by period
                                         │
     planner.evaluate: least-cost 8760 h dispatch of each fleet in 2025, 2030, …, 2050, one cost definition
                                         ▼
     gap = agents realised − planner  =  investment (agents eval − planner)  +  operation (agents realised − agents eval)
```
* `ukabm/costs.py` defines system cost (resource cost; transfers cancel) and is used by all three.
* Reserve and response (item 9): `planner._add_reserve` is passed to PyPSA as `extra_functionality` in
  both `plan` and `evaluate`. It adds `Generator-reserve`, `StorageUnit-response` and
  `StorageUnit-reserve` variables (assets picked by `carrier`), headroom constraints (reserve plus
  output within available capacity, inactive assets masked per investment period with
  `n.get_active_assets`), an hour of stored energy behind storage response, and two hourly balance
  constraints, `Reserve-response` and `Reserve-reserve`, each with a shortfall variable costed in the
  objective at the snapshot × period weights. Settings: `planner.reserve_settings(model)`, from
  `config.RESERVE` and the scenario key `reserve`.
* `GBMarketModel.system_cost` records the realised cost every year (`syscost_*_bn` columns).
* Agent traits are idealised by trait group through the scenario key `agents_ideal`
  (`scenarios.IDEAL_TRAITS`, `scenarios.LADDER`), which `gap.ladder_tasks` uses to attribute the gap.
* `scripts/run_gap.py` runs the ladder and the policy levers; `scripts/make_plots.py` draws
  `gap_over_time`, `gap_ladder`, `gap_levers`, `gap_capacity` and writes `results/gap_summary.md`.
* Extension points: put the network in both runs (planner on the PyPSA-GB zones, agents' redispatch
  cost in the system cost); a decision-logic interface so rule-based, Q-learning and LLM agents plug into
  the same `GenCo` decisions (deck slide 16); multi-sector planner (heat pumps, hydrogen storage) so demand-
  side choices enter the gap.
