# ukabm model design

## Architecture
```
                 ┌───────────── Government / policy (config.Policy) ─────────────┐
                 │ carbon path · CfD rounds (pots, admin strikes) · T-4 CM · RO  │
                 └───────┬──────────────────────┬───────────────────────┬────────┘
                         │ contracts            │ levies                │ grants
 ┌──────────────┐  offers ┌──────────────────┐ prices ┌──────────────────────────────┐
 │ GenCo agents │────────▶│ Hourly market     │──────▶│ Multi-energy modules          │
 │ (5, hetero-  │◀────────│ (uniform price,   │◀──────│ HeatModule (household agents) │
 │ geneous WACC,│ dispatch│  ORDC scarcity,   │ load  │ GasNetworkModule (tariffs)    │
 │ beliefs,     │         │  storage, flex,   │       │ EVModule (smart/unmanaged)    │
 │ mark-ups)    │         │  interconnectors) │       │ HydrogenModule (electrolysers)│
 └──────┬───────┘         └────────┬─────────┘       └──────────────────────────────┘
        │ invest/retire            │ sample hours
        ▼                          ▼
  plant pipeline         PyPSA-GB zonal network (PyPSA + HiGHS), ETYS boundary capabilities by year:
  (lead times)           BM-style redispatch (bids/offers) → constraint cost, curtailment, post-BM mix/CI;
                         zonal prices → siting signal only in the locational_signal (zonal-pricing) sensitivity
```

## Annual loop (`GBMarketModel.step`)
1. Commission pipeline / retire (end of life, 2 consecutive loss years without CM contract).
2. Demand = ESPENI-2024 shape × growth + heat-pump load (temperature-shaped) + EVs + electrolysers.
3. Market: pass 1 clears inflexible demand → smart EV valley-filling and electrolysers respond → storage
   is dispatched in tranches, each on the price left by the tranches before it, skipping days on which a
   tranche's own trades lose money → pass 2 → pass 3 withdraws electrolysers above their willingness-to-pay.
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
7. Investment: forecast prices for *t+3* from the known pipeline; CfD round; T-4 CM; sequential merchant
   decisions, re-forecasting after each (agents see each other's commitments).

## Agents
| agent | decisions | heterogeneity |
|---|---|---|
| GenCo ×5 (IntegratedUtility, MerchantIPP, OilMajor, InfraFund, GreenDeveloper) | offers, CfD bids (LCOE at de-risked WACC), CM bids (net missing money), merchant NPV investment, retirement | WACC 6–10 %, myopic/adaptive/carbon-optimist beliefs, mark-ups 0–8 %, risk aversion, budgets |
| Households ×2000 (each ≈14k homes) | heating system at boiler replacement (logit on lifecycle cost + hassle) | heat demand, discount rate, hassle cost, on/off gas grid, boiler age |
| Government (`ukabm.institutions`) | each CfD round's pots: volume limit, £ budget, administrative strike price; reacts to the last round and to the levy | `government`: `fixed` (default) or `targets` |
| Policy (parameters) | carbon path, CM target & curve, HP grant, levy rebalancing | scenario |

### Decision interface (`ukabm.decisions`)
Every GenCo decision goes through a `DecisionMaker`: `offer_price`, `expected_carbon`,
`merchant_investment`, `cfd_bid` and `cm_bid`. The model calls the GenCo, and the GenCo calls its
decision maker with itself (traits, and the year, fleet, policy and forecasting helpers through
`agent.model`) and the call's arguments (price forecast, plant, technology). `RuleBased` holds the
rules described above and is the default; results are identical to the code before the interface.

Other decision makers subclass `RuleBased` (or `DecisionMaker`), override the decisions they make and
are registered by name. A scenario selects them with `decision_logic`: one name for every GenCo, or
`{genco_name: name}` for some (the rest keep `"rules"`). Each GenCo gets its own instance, so learning
agents can keep state. Random draws must come from `agent.model.rng`. Government and system-operator
agents, Q-learning and LLM decision makers (README roadmap items 2, 5, 6, 24, 25) plug in here.

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
* `GBMarketModel.system_cost` records the realised cost every year (`syscost_*_bn` columns).
* Agent traits are idealised by trait group through the scenario key `agents_ideal`
  (`scenarios.IDEAL_TRAITS`, `scenarios.LADDER`), which `gap.ladder_tasks` uses to attribute the gap.
* `scripts/run_gap.py` runs the ladder and the policy levers; `scripts/make_plots.py` draws
  `gap_over_time`, `gap_ladder`, `gap_levers`, `gap_capacity` and writes `results/gap_summary.md`.
* Extension points: put the network in both runs (planner on the PyPSA-GB zones, agents' redispatch
  cost in the system cost); a decision-logic interface so rule-based, Q-learning and LLM agents plug into
  the same `GenCo` decisions (deck slide 16); multi-sector planner (heat pumps, hydrogen storage) so demand-
  side choices enter the gap.
