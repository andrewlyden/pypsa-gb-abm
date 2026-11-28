# Model description (ODD+D)

This document describes the model in the package `ukabm` following the ODD protocol (Overview,
Design concepts, Details) as updated by Grimm et al. (2020), with the extension for human
decision-making, ODD+D, of Müller et al. (2013). It describes the code on the branch
`foundations/implementation` (commit a47ec5f) with the default settings (`ukabm.config.DEFAULTS` and the defaults of
`GBMarketModel`), and says where scenario keys change the behaviour. Every number given here is
listed with its source and status in the [parameter register](parameters.md); every dataset is in the
[data register](data.md). A table at the end maps each section to the file and function that
implements it.

For each decision rule the description states its basis: which published rule, data or theory it
follows, and which parts are the authors' assumptions.

References: Grimm, V., Railsback, S.F., Vincenot, C.E., Berger, U., Gallagher, C., DeAngelis, D.L. et
al. (2020). The ODD protocol for describing agent-based and other simulation models: a second update
to improve clarity, replication, and structural realism. *Journal of Artificial Societies and Social
Simulation* 23(2), 7. Müller, B., Bohn, F., Dreßler, G., Groeneveld, J., Klassert, C., Martin, R. et
al. (2013). Describing human decisions in agent-based models – ODD+D, an extension of the ODD
protocol. *Environmental Modelling & Software* 48, 37–48.

---

## I. Overview

### I.i Purpose and patterns

**Purpose.** The model asks how far the electricity system that many actors build under Great
Britain's market design, 2025–2050, is from the system a single planner with perfect foresight would
build at least cost, where that difference (the *gap*) comes from, and which market designs or
government objectives close it. It is a research model for comparing designs and decision rules, not
a forecasting model; `docs/assumptions.md` states that numbers after 2025 are illustrative.

To answer the question the model runs the same system two ways on the same inputs:

1. **The emergent system ("Run 2").** Generation companies (firms), a government, a system operator
   and households make their own decisions each year; an hourly wholesale market, Contract for
   Difference (CfD) allocation rounds and Capacity Market (CM) auctions connect them.
2. **The optimal system ("Run 1").** A least-cost capacity expansion plan (a linear programme in
   PyPSA) built from the same starting fleet, against the demand the agents' run produced.

Both fleets are then dispatched by the same least-cost evaluator and costed with one definition of
system cost (a resource cost: capital, fixed and fuel costs, carbon, trade, unserved energy;
payments between actors cancel). The gap is the difference in present value at the social discount
rate, split into an *investment gap* (what was built) and an *operation gap* (how it was run).

**Patterns** against which the model is evaluated (none is used as a calibration target, except the
2025 operating year as stated):

| Pattern | Data | Where |
|---|---|---|
| Hourly operation of the GB system in each year 2021–2025, on that year's weather, fleet and prices: mean and percentile prices, generation by fuel, imports and exports, carbon intensity | NESO generation mix, Elexon MID and FUELHH, Ofgem day-ahead price (`data/outturn/`) | `scripts/run_backcast.py` → `results/backcast.md`. Operating parameters were set on 2025 (nuclear on 2024–25); 2021–2024 are a check |
| The model's first CfD round against Allocation Round 7, and its first T-4 Capacity Market auction against the auction for 2029/30 | AR6, AR7 results; T-4 2029/30 clearing price | `scripts/check_auctions.py` → `results/auction_check.md` |
| Whether bidders' deviation from published costs is stable across CfD rounds 2015–2026 (it is not, so no bidding parameter is fitted) | CfD round results; DESNZ generation-cost reports of the time | `scripts/replay_cfd_rounds.py` → `results/cfd_rounds_replay.md` |
| The baseline's capacity, demand and heat-pump stock in 2030–2050 against published pathways | NESO FES 2025, CCC Seventh Carbon Budget, Clean Power 2030 (`data/fes/published_pathways.csv`) | `scripts/compare_pathways.py` → `results/pathways_comparison.md` |
| Under textbook conditions (energy-only market, idealised firms investing merchant on lifetime forecasts) the emergent system should approach the least-cost plan | the planner itself | benchmark scenario `competitive_benchmark`, `scripts/run_convergence.py` |

### I.ii Entities, state variables and scales

| Entity | Implemented as | Number (default) | State variables |
|---|---|---|---|
| **Firm** (generation company) | `ukabm.agents.GenCo`, a Mesa agent | 12 (`data/fleet/firms.csv`: RWE, SSE, EDF, Orsted, ScottishPower, Uniper, Drax, and the groups IndependentThermal, OtherUtilities, InfrastructureFunds, OilMajors, Independents); 5 stylised firms with scenario `firms = "stylised"` | name; type (utility, generator, major, fund, developer); cost of capital `wacc`; technology hurdle rates (CEPA rates shifted by `wacc` − 7.7 %); merchant uplift; expectation type (myopic, adaptive, carbon optimist); offer mark-up; risk aversion; annual capital budget; technologies it invests in; decision maker (`decisions.ExpectationBids` by default); this year's panel row |
| **Plant** | `ukabm.agents.Plant` (data class; not an agent) one per row and zone of `data/fleet/fleet_2025.csv` (850 rows), plus nuclear units and pipeline blocks; grows with every award and project | owner; technology; zone; MW; first and last year of operation; support scheme (merchant, CfD, RO) with strike, contract end, whether paid at negative prices; CM agreement (price, first and last delivery year) and pre-2025 agreements; availability and efficiency where they differ from the technology; route (initial, pipeline, cfd, cm, dpa, merchant); profit history; consecutive loss years |
| **Government** | `ukabm.institutions.TargetTracking` (default); `FixedRules`, `LeastCost`, `BillsFirst`, `Political` | 1 | target capacity path per technology; current administrative strike price (cap) per pot; last clearing strike per pot; rule parameters; log of rounds |
| **System operator** | `ukabm.institutions.SystemOperator` (mode `standard`) | 1 | mode; reliability-standard parameters; log of targets |
| **Households** | `ukabm.multienergy.HeatModule`, arrays (not Mesa agents) | 2,000 cohorts of 14,000 homes each (28 million homes) | annual heat demand; implicit discount rate; non-financial "hassle" cost; boiler age; on or off the gas grid; heat pump or not |
| Gas network | `GasNetworkModule` (submodel, no decisions) | 1 | allowed revenue; tariff |
| EV fleet | `EVModule` (submodel) | 1 | stock and charging energy (from FES 2025 by default); share charging smartly |
| Electrolysers | `HydrogenModule` (submodel) | 1 | capacity (from FES 2025 by default); willingness to pay |
| Neighbouring markets | interconnector offer and bid blocks in `GBMarketModel.interconnector_blocks` | 7 price zones (FR, NL, BE, NO2, DK1, DE-LU, SEM) | capacity by year (register, then FES); hourly price |
| Environment | `GBMarketModel` | 1 | year; fuel, carbon and demand paths; FES drivers; last year's hourly prices; last CM clearing price; policy levy; auction log; results |

**Scales.** Time advances in annual steps from `start` (2025) to `end` (2050), 26 steps. Within each
step the wholesale market clears every hour of one weather year (8,760 hours; the 2024 profile by
default), which is reused for every model year, scaled for demand growth. Space is one GB price zone
(copperplate) for the market, the auctions and the planner. Plants are located in the 20 zones of the
PyPSA-GB zonal network; the zones matter only in the network stage, run every `network_every` years
(default 5; 0 in gap runs) on 96 sampled hours, and in the optional `locational_signal` sensitivity.
Money is in real 2024 pounds, except in historical years run in money of the day (back-cast).

### I.iii Process overview and scheduling

`GBMarketModel.step` runs once per year *y*, in this order. All firms act within a phase before the
next phase starts; the model, not a Mesa scheduler, sets the order.

1. **Fleet of the year.** Plants with first year ≤ *y* ≤ last year are active (this is how the
   pipeline commissions and how closures take effect).
2. **Wholesale market** (`run_market`). Firms' offers are formed; the market clears inflexible demand
   (pass 1); smart EV charging and electrolysers respond to pass 1; storage is dispatched in tranches;
   the market clears again (pass 2); electrolysers withdraw from hours priced above their willingness
   to pay (pass 3).
3. **Settlement** (`settle`). Each plant is paid the hourly price for its output, plus CfD difference
   payments or Renewables Obligation (RO) certificates, plus CM payments, less fuel, carbon and fixed
   costs. Batteries also receive a share of two service revenue pots.
4. **Learning hook** (`_learn`). Each firm's decision maker receives the firm's realised profit
   (no default decision maker uses it).
5. **System cost** of the year (`system_cost`) and the **policy levy**: (CfD + RO + CM payments) /
   GB final consumption.
6. **Network stage** (`network_stage`), in years where (*y* − start) is a multiple of `network_every`:
   Balancing-Mechanism-style redispatch on the zonal network. Its results are reported; they do not
   enter settlement or decisions (except zonal prices under `locational_signal`).
7. **Multi-energy feedbacks.** Retail electricity and gas prices are formed; the gas network tariff
   is updated from gas throughput (homes, industry, power stations); households replacing a boiler
   choose a heat pump or a boiler.
8. **Retirement.** Gas, biomass, battery, gas CCS and hydrogen plant that lost money in each of the
   last two years and holds no CM agreement for the next four years closes at the end of *y*.
9. **Investment** (`invest`), in this order: a price forecast for *y* + 3; the **CfD allocation
   round**; the **government tender for gas CCS and hydrogen power** (`dpa_round`); the **T-4 Capacity
   Market auction** (delivery *y* + 4); the **T-1 auction** (delivery *y* + 1); up to six **merchant
   investment decisions**, each preceded by a new forecast and a new random order of firms.
10. **Records**: the annual results row, hourly series, the firm panel (Mesa `DataCollector`), then
    *y* ← *y* + 1.

Decisions in year *y* take effect after each technology's lead time (1–10 years), so the fleet of a
year is fixed before its market runs. Households' choices in *y* change demand from *y* + 1.

The optimal system is computed after the agents' run: `ukabm.gap.gap_run` runs the model, takes its
inflexible demand in 2025, 2030, …, 2050, solves the planner (`planner.plan`), and evaluates both
fleets in each of those years (`planner.evaluate`).

---

## II. Design concepts

### II.i Theoretical and empirical background

* **Market and policy design** follows GB institutions as published: a uniform-price hourly
  wholesale market (one price for GB, as decided under REMA in July 2025); CfD allocation rounds with
  technology pots, administrative strike prices, a budget and pay-as-clear pricing; a Capacity Market
  with a sloping demand curve, a price cap, T-4 and T-1 auctions, multi-year agreements for new build;
  the Renewables Obligation for older plant; a reliability standard of 3 hours loss of load
  expectation. The support terms that set offers (RO certificates per MWh; CfDs of rounds 1–3 paid at
  negative prices, from round 4 not) follow the contracts as coded in PyPSA-GB.
* **Firms' investment** follows the net present value rule of corporate finance: a project is worth
  building if its discounted margins cover its capital cost at the firm's required return. Required
  returns are the technology hurdle rates CEPA estimated for DESNZ (2025), shifted by the firm's own
  cost of capital, with a 1.5-point uplift for merchant revenue. Capital and fixed costs are DESNZ's
  *Electricity Generation Costs 2025*. The firms are boundedly rational in specific, assumed ways:
  heuristic carbon-price expectations, price forecasts from re-clearing the market with committed plant
  only, lumpy projects, a limited number of decisions a year, annual budgets.
* **Bids in auctions** follow the logic the auctions are designed around: a CfD bid is the lowest
  strike at which the project earns its required return; a CM bid is the plant's "missing money"
  (capital annuity plus fixed cost less expected market margin, per de-rated kW), the concept behind
  the CM's net cost of new entry.
* **Households** choose a heating system with a logit (random utility) model on lifecycle cost plus a
  non-financial barrier that falls as adoption spreads, a stylised diffusion mechanism. Parameter
  values are assumed, not estimated.
* **The benchmark** is a least-cost capacity expansion with perfect foresight (welfare economics: under
  complete markets and perfect competition a market outcome equals the planner's). The convergence
  test checks that the agents approach it when those conditions are imposed.
* **Empirical basis.** Fleet, costs, hurdle rates, de-rating factors, support terms, profiles, prices
  and FES drivers are published or measured (see the registers). Firms' traits, the government's and
  households' rules, and several operating heuristics are assumptions; the parameter register marks
  each. No behavioural parameter has been estimated from data.

### II.ii Individual decision making

**Who decides what.** Firms decide offers, carbon-price expectations, CfD bids, CM bids and merchant
investments; the closure rule is applied to their plants by the model. The government decides each
CfD round's volume limit, cap and budget per technology. The system operator decides each CM
auction's target. Households decide heat pump or boiler when a boiler is replaced. Electrolysers,
storage and smart EV charging respond to prices by fixed rules and are not decision makers in the
ODD+D sense.

All firm decisions pass through one interface (`ukabm.decisions.DecisionMaker`). The firm builds an
`Observation` of what it may know (`ukabm.observations`), the decision maker returns a decision, and
the answer is checked against a declared action space. Decision makers never see the model object.

The rules, with their basis:

| Decision | Rule (default `ExpectationBids`, which inherits from `RuleBased`) | Follows | Authors' assumption |
|---|---|---|---|
| Day-ahead offer of each plant | RO wind, solar, hydro: minus the certificate value (banding × £65/ROC). CfD of rounds 1–3: minus the strike. CfD from round 4: £0. Merchant renewables: £0.5/MWh. Nuclear and "other": −£50/MWh (must run). Fuelled RO plant (biomass): SRMC less the certificate value. Thermal plant: short-run marginal cost (fuel and carbon / efficiency + VOM) × (1 + mark-up) | Support contract terms (as coded in PyPSA-GB); Ofgem bandings and buy-out price; marginal-cost bidding in a competitive market | the mark-ups (0–8 % by firm type), the must-run offer, the merchant renewable offer; no start-up costs or unit commitment |
| Expected carbon price for year *t* | adaptive: the published path; myopic: today's price; carbon optimist: 1.3 × the path | – | the three types and the factor 1.3 |
| CfD strike bid (one 500–1,000 MW block, two per firm and technology per round) | Lowest strike *s* at which capital cost = PV of (s × output × (1 − 2 %) − fixed cost) over a 20-year contract at the contracted hurdle rate + PV of (tail capture price − VOM) × output − fixed cost over the rest of the asset's life at the merchant rate; divided by (1 − 0.5 × risk aversion); ± 2 % normal noise. Tail capture price: myopic firms use last year's prices; adaptive firms the *t*+3 forecast less 15 %; carbon optimists the forecast without the haircut. Capacity factors are measured (new build per `NEW_BUILD_CF`) | Levelised-cost logic of DESNZ EGC; CEPA hurdle rates; measured capacity factors; 20-year CfD terms of recent rounds | the 2 % basis, the 15 % haircut, the tail-view rules, the noise, two blocks per firm |
| Merchant investment (one block, per call) | Among the technologies the firm invests in that are investable, not banned, not nuclear and affordable within the year's remaining budget: NPV at the merchant rate of margins forecast for *t*+3, *t*+8 and *t*+13 (linear between, flat after), less fixed cost, over the asset life; wind and solar may instead take a 15-year PPA at 90 % of the *t*+3 capture value at the rate without the merchant uplift. The highest positive NPV is built; none if all are negative. The model then checks the build-rate limit for the online year | NPV rule; CEPA hurdle rates and merchant uplift | the forecast horizons and method (see II.v), PPA terms, one block per decision, annual budgets by firm type |
| CM bid, new build (CCGT, OCGT, battery, H2 turbine within the lead time; up to 4 projects per firm and technology, each 3 % dearer) | (capital cost × 15-year annuity at the contracted rate + fixed cost − expected energy margin) / de-rating, floored at 0. Batteries form a stepwise curve in which each project expects the service revenue of the battery fleet ranked ahead of it | CM "missing money" logic; 15-year agreements for new build; NESO de-rating factors | the margin definition, the number of projects, the 3 % step |
| CM bid, existing plant without an agreement | (fixed cost − expected gross margin) / de-rating, floored at 0; the margin is the mean of the plant's last two years (without CM payments), or its margin on the forecast | as above | as above |
| Closure | close if a loss in each of the last two years and no CM agreement for the next four | – | the whole rule; existing CCGT and OCGT also close at 40 and 45 years |
| Government (default `targets`): CfD round | For each pot, the volume limit is the capacity missing at the delivery year from the target path (FES 2025 pathway capacity by default), cut to the build-rate room; the cap is the current administrative strike price; the budget is missing MW × expected support per MW (expected strike − forecast capture price, × expected output) × 1.1, × 0.6 when the levy is above £30/MWh. The expected strike is the last clearing strike, else the cap. After a round, a pot that accepted less than half its limit while bids were above the cap gets its cap raised 15 % (up to 2 × the initial cap) | CfD allocation framework (pots, administrative strike prices, budget, pay-as-clear); targets from FES 2025 or the Clean Power 2030 Action Plan | the budget formula, the levy threshold and squeeze, the cap rule; other objectives (`least_cost`, `bills`, `political`) are illustrative |
| Government tender for gas CCS and hydrogen power (`dpa_round`) | With a FES pathway and a government other than `fixed`: contract the capacity the pathway has in the delivery year, within the build-rate limit, in blocks; each project is paid its missing money per de-rated kW for its life (an availability payment recovered through the levy). Projects go to eligible firms in turn | DESNZ Dispatchable Power Agreement and hydrogen-to-power business models (that such contracts exist); FES 2025 capacities | the payment rule, the allocation, that the government follows the pathway exactly |
| System operator (default `standard`): CM target | De-rated MW such that net demand (load less supported wind and solar on their hourly profiles, less other supported plant at de-rating) is above it in at most 3 hours of the delivery year: the 4th-highest hour, × (1 + weather margin, 0). T-4 buys 97.5 % of it less capacity already holding agreements; T-1 buys what is still missing less 0.45 × interconnector capacity | GB reliability standard (3 h LOLE); T-1 holdback of 2029/30 (DESNZ) | deterministic standard on one weather year; no outages; the 0.45 interconnector factor |
| Household heating choice | At boiler replacement (age 15 years or 2 %/yr at random): utility of heat pump = −(£11,000 − grant + hassle + 15-year PV of running cost at retail electricity price, COP 2.9); of boiler = −(£3,000 + PV of gas cost at 88 % efficiency; off-grid homes pay 1.6 × gas). Hassle = initial hassle × (1 − 0.8 × min(national heat-pump share / 0.3, 1)). Choose the heat pump with logistic probability on the utility difference (scale £1,500) | random-utility discrete choice; diffusion with a falling barrier | every parameter value; national (not local) adoption share |

**Objectives.** Firms maximise NPV per decision at their required return, subject to budget and the
options their type allows; they do not optimise a portfolio. The `targets` government tracks a
capacity path at an acceptable levy; `least_cost` tracks the planner's path; `bills` gives more weight
to the levy; `political` funds less before elections. The system operator meets the reliability
standard. Households minimise perceived lifecycle cost with random taste variation.

**Adaptation to changing conditions.** Firms' decisions respond each year to new forecasts, last
year's prices (myopic firms) and the last auction results that enter observations. The government
adapts caps and budgets to the previous round and to the levy. The system operator recomputes the
target each year from the delivery-year demand and the supported fleet. Households respond to retail
prices and the adoption share.

**Uncertainty in decisions.** Firms treat their forecast as certain; risk enters only through the
hurdle rates and the merchant uplift (risk aversion is 0 by default). There is no scenario-based or
risk-measure valuation.

**Social norms and cultural values.** Not represented, except the household hassle cost falling with
adoption, which stands for social influence and installer maturity together.

**Spatial aspects.** None in decisions by default: GB keeps a national price, and new plant is sited at
random in proportion to each technology's existing capacity by zone. With `locational_signal` the
siting probabilities are weighted by zonal prices from the last network stage.

**Temporal aspects.** Firms look three years ahead for most decisions and to *t*+13 in the
`expectations` merchant rule; lead times delay every decision's effect; the government looks to each
pot's delivery year; the system operator to the delivery year of each auction.

### II.iii Learning

No firm learns in the default model. `DecisionMaker.learn` receives each firm's realised profit once a
year as a reward, so that learning decision makers (Q-learning, LLM agents; roadmap items 24 and 25)
can be plugged in, but `RuleBased` and `ExpectationBids` do nothing with it. The `targets` government
adapts in a rule-based way (last clearing strike as its expectation; cap raised after a failed round),
which is adaptation rather than learning. Households do not learn individually; the falling hassle cost
is a population-level effect.

### II.iv Individual sensing

A firm's `Observation` holds: its own traits and the budget it has left this year; views of its own
plants (including profit history); the current year; the published policy (carbon path, caps, scheme
switches); last year's hourly prices; the last T-4 clearing price and the last CfD clearing strike per
technology; and analysis tools that compute expected margins, capacity factors and the long-horizon
forecasts. It does not see other firms' plants or decisions directly, only through the forecasts and
prices. The tools are closures over the model, so the boundary is a convention that decision makers
must respect, not a sandbox (`ukabm/observations.py`).

The government senses the levy, the capacity active in each future year (the committed pipeline), the
forecast capture price and the auction results. The system operator senses demand and the supported
fleet in the delivery year without error. Households sense retail prices and the national heat-pump
share. Sensing has no cost and no error.

### II.v Individual prediction

* **Price forecast for *t*+3** (`GBMarketModel.forecast`): the market is re-cleared for year *t*+3
  with the plants committed to be active then, and that year's fuel, carbon and demand paths. Firms
  therefore know future fundamentals exactly and assume that nobody builds after the committed pipeline
  (foundations review F8). The forecast is recomputed before each merchant decision, so later firms see
  earlier firms' new projects.
* **Long-horizon forecasts** (`forecast_horizons`, *t*+8 and *t*+13): committed plant active at the
  horizon, plus wind and solar growing at their build rate of the last five years, plus OCGT to keep the
  de-rated margin at 6 % above peak, re-cleared on the horizon year's paths.
* **Carbon prices**: by expectation type (II.ii).
* **Existing plant margins** for CM bids: the mean of the last two years.
* **Households** assume today's retail prices persist for 15 years.
* Heat-pump stock in forecasts is today's (the model does not project household choices).

### II.vi Interaction

Interaction is indirect, through markets and institutions:

* **Wholesale market**: all offers set one hourly price; each plant's revenue depends on everyone's
  offers and on the fleet.
* **Auctions**: firms compete in each CfD pot and in each CM auction; the clearing price is set by the
  marginal accepted bid (CfD) or by the demand curve and marginal offer (CM).
* **Sequential merchant decisions**: each new project enters the next forecast, lowering the expected
  margins of later projects (cannibalisation).
* **Battery service pots**: batteries share two fixed revenue pots, so each battery's revenue falls as
  the fleet grows.
* **Government–firm feedback**: the government sets caps and budgets from the previous round's results
  and the levy; the levy depends on the support paid to firms' plants.
* **System operator–firm feedback**: the target depends on supported plant, which depends on CfD
  rounds; existing plant with an agreement cannot close.
* **Households–market feedback**: retail prices include the wholesale price and the levy; heat pumps
  add electricity demand; fewer gas homes raise the gas network tariff for those who remain.

There is no communication or negotiation between agents and no network of agents.

### II.vii Collectives

Several firms are collectives represented as one agent: IndependentThermal (independent gas plant
owners), OtherUtilities, InfrastructureFunds, OilMajors and Independents (all wind, solar and battery
capacity outside the station list, including small owners). Each household agent is a cohort of
14,000 homes. Collectives are fixed at initialisation; none forms or dissolves during a run.

### II.viii Heterogeneity

Firms differ by type in cost of capital (6–10 %), expectation type, offer mark-up (0–8 %), annual
budget (£1–4bn) and the technologies they invest in; and by their portfolio, which comes from the
companies' actual stations (`data/fleet/owners.csv`). Within a type, firms differ only in portfolio.
Decision rules are the same for all firms unless `decision_logic` assigns different decision makers to
named firms. Households differ in heat demand, discount rate (4–20 %), hassle cost, boiler age and gas
grid connection. Plants differ in technology, vintage, efficiency (existing CCGTs by age), availability
(nuclear units), support terms and zone.

### II.ix Stochasticity

Random numbers come from generators seeded by the model's `seed`, so a run is reproducible:

* the model's generator (`seed`): the zone of every new plant and pipeline project; noise on CfD bids;
  the order in which firms are asked for merchant investments (drawn again before each decision); and,
  with `fleet = "random"` only, vintages and support of the starting fleet;
* the household generator (`seed + 1`): household attributes, which homes have heat pumps at the start,
  random boiler failures and each logit draw;
* the network stage's hour sample uses a generator seeded by the year (the same for every seed);
* the synthetic temperature series uses a fixed seed.

Weather, demand, fuel and carbon paths do not vary with the seed: ensembles show variation from the
agents' draws in one deterministic world (`ukabm/ensemble.py`). In copperplate gap runs
(`network_every = 0`) the random zone of a plant has no effect on costs.

### II.x Observation

Each year the model records one row of annual results (`GBMarketModel.results`): prices (means,
percentiles, negative hours), demand by component, generation and capacity by technology, imports and
exports, emissions and two carbon intensities (direct, and on NESO's accounting basis), CfD, RO and CM
costs, the levy, system cost by component, battery revenue stack, retail prices, heat-pump homes, EV
stock, gas network tariff, and network-stage results in network years. It also keeps hourly series per
year (`hourly`), a panel of every firm and year from a Mesa `DataCollector` (`firm_panel`: profit,
capacity by technology, MW closed, MW committed by route), one row per auction pot and year
(`auctions`), and the logs of the government and the system operator. `ukabm.gap` adds the planner's
and the evaluator's costs, capacity by pathway and the present-value gap. `ukabm.outturn.compare` sets
a year's results against GB outturn.

---

## III. Details

### III.i Implementation details

Python ≥ 3.11; Mesa ≥ 3 (agents and data collection); PyPSA ≥ 0.30 with the HiGHS solver (network
stage, planner, evaluator); NumPy, pandas, SciPy. Hourly market clearing is vectorised NumPy
(`ukabm/market.py`). The package is MIT-licensed; see `README.md` for how to run it and
[CONTRIBUTING.md](../CONTRIBUTING.md) for scripts.

### III.ii Initialisation

For a run starting in 2025 (`GBMarketModel(scenario, start=2025, end=2050, seed=42)`):

1. **Scenario**: the scenario table (`ukabm/data/scenarios.toml` or a user file) is checked; an
   unknown key raises an error.
2. **Exogenous drivers**: the FES 2025 pathway named by `fes_pathway` (default Holistic Transition).
3. **Firms**: the twelve firms of `data/fleet/firms.csv` with the traits of their type
   (`FIRM_TYPES`).
4. **Fleet**: capacity by technology from `config.INITIAL_FLEET_MW` (DUKES 2026, mean of end-2024 and
   end-2025), spread over zones, vintages, owners and support schemes by `data/fleet/fleet_2025.csv`;
   existing CCGTs get an efficiency that falls with age; existing gas plant closes at 40 (CCGT) or 45
   (OCGT) years, or after at least 5 more years. Nuclear units from `NUCLEAR_UNITS` (AGRs to 2029,
   Sizewell B to 2035, Hinkley Point C from 2030–31, Sizewell C from 2038–39, the last two on CfDs);
   further nuclear and pumped hydro where the FES pathway exceeds the listed stations; the contracted
   CfD pipeline of `data/fleet/pipeline_2025.csv`, shared among firms that invest in the technology in
   proportion to what they own. Dispatchable plant without support gets one-year CM agreements for
   delivery years already auctioned (2025–2028). The fleet at this point is stored as the starting fleet
   of the planner.
5. **Households**: 2,000 cohorts with random attributes; 0.6 million homes with heat pumps.
6. **Other state**: levy £20/MWh, last T-4 clearing £30/kW/yr, no last-year prices.

For a start before 2025 (back-cast), the fleet comes from that year's GB capacity table
(`config.fleet_mw`) and fuel and carbon prices from `data/history/annual_inputs.csv`.

### III.iii Input data

| Input | File | Varies in time |
|---|---|---|
| Hourly demand, onshore and offshore wind, solar for the weather year | `data/profiles/profiles_<year>.csv` (2024 by default) | the same year reused every model year |
| Neighbours' hourly day-ahead prices (shape; observed levels in back-cast years) | `data/external/neighbour_prices_<year>.csv` | as above |
| Demand growth other than EVs, heat pumps and electrolysis; EV stock and energy; electrolyser, interconnector, nuclear, pumped hydro, gas CCS and hydrogen power capacity; government targets for wind and solar | `data/fes/fes2025_drivers.csv` | yearly 2025–2050 |
| Capital and fixed cost by commissioning year | `data/parameters/cost_paths.csv` | by online year |
| Historical fuel, carbon and power prices | `data/history/annual_inputs.csv` | yearly 2010–2025 |
| Fleet, owners, pipeline | `data/fleet/` | start only |
| Zonal network, interconnector register, siting shares, CfD register | `data/pypsagb_snapshot/` | register by year |
| Gas and carbon price paths after 2025 | `config.GAS_PATH_CENTRAL`, `Policy.carbon_price_*` | yearly |

### III.iv Submodels

**Market clearing** (`market.clear`, `market.merit_order`). For every hour, offers are sorted by price
and accepted until demand is met; the price is the offer of the marginal block. If supply is short,
the price is VoLL (£6,000/MWh) and the shortfall is unserved energy. A scarcity mark-up is added to the
merit price, stepped on the hourly de-rated margin (available GB plant, storage and interconnectors at
de-rating, less demand) by `config.SCARCITY_STEPS`; with `scarcity_adder = "ordc"` an operating-reserve
demand curve formula is used instead, and with `false` none. Offers with the same price and
availability shape are merged before clearing and their dispatch split back pro rata.

**Interconnectors** (`interconnector_blocks`). Per neighbouring market, one import offer at foreign
price + £12/MWh and one export bid at foreign price − £12/MWh, each at 90 % of capacity. The export is
modelled as demand that is offered back at the bid price, so it is cut exactly when the GB price
exceeds the bid. Foreign price = SRMC of an existing GB CCGT × market level (continent 0.68, SEM 1.10)
× the observed hourly shape, declining 25 % relative to the CCGT by 2050. In a historical year run in
money of the day, observed continental prices are used, converted at that year's exchange rate.
Capacity follows the PyPSA-GB register (with corrected commissioning years); after 2030 it is raised
to the FES pathway's capacity where that is larger.

**Flexible demand and storage** (`run_market`). EV smart charging fills the valleys of residual load
(demand minus wind and solar) within 21:00–08:00 up to a charger limit; electrolysers run where the
pass-1 price is below their willingness to pay (£56/MWh). Storage is dispatched in tranches (three
for batteries, one for pumped hydro): each charges in the cheapest and discharges in the dearest hours
of each day on the price left by earlier tranches, when the spread covers losses and £5/MWh, and skips
days on which its own trades would lose money at the resulting price.

**Settlement** (`settle`). Per plant: energy revenue at the hourly price; CfD difference (strike −
price) on output (not in negative-price hours for contracts from round 4); RO certificates; CM
payment per de-rated kW; less SRMC × output and fixed O&M. Batteries add their share of the two service
pots, `BATTERY_ANCILLARY_POT` and `BATTERY_TRADING_PER_MW_VRE` × wind and solar MW, divided by the
battery fleet (not below its 2025 size). Profit and loss years are stored on the plant.

**System cost** (`ukabm.costs`, `system_cost`). Annuity of capital of plant built after the start
year at the social discount rate (3.5 %), with financing over the build lag; fixed O&M; fuel and VOM;
emissions × carbon price; imports at their offer price minus exports at their bid price; unserved
energy × VoLL; minus electrolyser consumption × willingness to pay. Transfers (CfD, RO, CM, scarcity
rents, mark-ups) cancel. Redispatch cost is not included.

**Network stage** (`network_stage`, `ukabm/network.py`). On 96 hours sampled in 8 strata of GB wind
output, each plant's market schedule can be turned down at its bid (thermal: SRMC; RO: minus the
certificate value; CfD: minus (strike − price); nuclear: −£300/MWh) and its headroom turned up at its
offer, on the 20-zone network with boundary capabilities by year (LCP Delta 2026 / NESO Holistic
Transition) and monthly availability; interconnector flows are fixed at their landing zones. A PyPSA
linear programme minimises redispatch cost; plants of one zone with identical bids and offers enter it
as one generator, and the result is shared among them pro rata. Outputs: annualised constraint cost, curtailment,
redispatch by technology, post-redispatch carbon intensity, zonal prices.

**CfD allocation round** (`cfd_round`). The government sets each pot (II.ii); firms that invest in
the technology submit two bids each; bids above the cap are excluded and counted; remaining bids are
accepted cheapest first in whole blocks while the pot's accepted MW is below its limit and, with the
bid as clearing strike, the support of all accepted MW stays within budget. All winners in a pot are
paid the highest accepted bid (pay-as-clear) for 20 years from the online year. The government then
observes the result.

**Government tender** (`dpa_round`): see II.ii.

**Capacity Market auction** (`cm_auction`). Offers: interconnectors at £0 (0.45 × capacity, T-4
only); existing plant without an agreement and without CfD or RO support; new build (II.ii). New-build
offers beyond the year's build-rate room are dropped. The demand curve falls linearly from the price
cap (£75/kW/yr) at target − 1.5 GW to zero at target + 1.5 GW. Offers are accepted in price order
until the next offer is above the curve or the end of the curve is reached; the clearing price is set
by the curve or the marginal offer. Existing plant receives a one-year agreement, new build a 15-year
agreement, at the clearing price. The T-1 auction is held only when the system operator's T-1 target
is positive.

**Merchant investment** (`invest`). Up to `max_merchant_decisions` (6) rounds per year. In each,
the *t*+3 forecast is recomputed, the order of firms is drawn at random, and firms are asked in turn
until one returns a positive-NPV project for which build room remains; that project is added and the
firm's budget reduced by its capital cost. The year's investment ends when no firm wants to build.

**Retirement** (`step`): see II.ii.

**Households, gas network, EVs, electrolysers** (`ukabm/multienergy.py`). Heat-pump load = heat
demand of heat-pump homes / COP, shaped by heating degree hours of a synthetic temperature series
with morning and evening peaks and a hot-water base (heat pumps already in the 2024 demand profile
are not added twice). Retail electricity price = heat-pump-weighted wholesale price + £70/MWh network
+ levy + £25/MWh supplier − levy rebalancing; retail gas price = wholesale gas + network tariff +
£12/MWh + 35 % of the rebalancing. Gas network tariff = allowed revenue (−1 %/yr after 2030) /
throughput (homes on gas, non-domestic demand falling 1.5 %/yr, power-station gas burn). EV energy and
electrolyser capacity follow FES 2025; the share of smart charging rises from 10 % (2025) to 60 %
(2040).

**Planner** (`planner.plan`). PyPSA multi-period capacity expansion on one GB bus, periods 2025,
2030, …, 2050, each standing for five years, discounted at 3.5 %, perfect foresight. Same technologies,
costs by commissioning year, fuel and carbon paths, profiles (new build on the new-build capacity
factors), interconnector offers and electrolysers as the agents, starting from the agents' starting
fleet and meeting the agents' realised inflexible demand. New build per technology and period is
limited to the build-rate limit × the years in which a decision could come online (the same limits
bind the firms; scenario key `build_limits` changes them for both). Hours: one ordinary
day in seven plus, for each period, the 8 days with the highest peak and the 8 with the highest mean
of a reference net load, weighted to the year. Reserve and response are required every hour (1,800 MW
of response on storage with an hour of energy behind it; reserve of 10 % of available wind and solar
on flexible plant and storage headroom), with shortfalls at £1,000/MWh.

**Evaluator** (`planner.evaluate`). Least-cost dispatch of a given fleet over all 8,760 hours of one
year, with the same reserve requirement, costed by `ukabm.costs`. Both the planner's and the agents'
fleets go through it.

**Gap** (`ukabm.gap`). For each period year: planner cost (evaluator on the planner's fleet), agents'
evaluated cost (evaluator on the agents' fleet) and agents' realised cost (from the run). Investment
gap = agents evaluated − planner; operation gap = agents realised − agents evaluated. Present value
2025–2054 at 3.5 %. `ladder_tasks` with `run_many` repeat the agents' run with trait groups idealised
(`scenarios.IDEAL_TRAITS`: expectations, capital, strategic), each against its own planner run, to
attribute the gap; the ladder is cumulative in one order, so its steps are indicative.

---

## From this description to the code

| Section | File | Function or object |
|---|---|---|
| I.i Purpose; gap method | `ukabm/gap.py` | `gap_run`, `summarise`, `ladder_tasks` |
| I.i Patterns | `scripts/run_backcast.py`, `scripts/check_auctions.py`, `scripts/compare_pathways.py`, `scripts/run_convergence.py`; `ukabm/outturn.py` | `compare`, `METRICS` |
| I.ii Firms | `ukabm/agents.py`; `ukabm/model.py` | `GenCo`; `FIRM_TYPES`, `GENCO_SPECS`; `GBMarketModel.__init__` |
| I.ii Plants | `ukabm/agents.py` | `Plant` |
| I.ii Government, system operator | `ukabm/institutions.py` | `TargetTracking`, `FixedRules`, `LeastCost`, `BillsFirst`, `Political`, `SystemOperator` |
| I.ii Households, gas, EVs, electrolysers | `ukabm/multienergy.py` | `HeatModule`, `GasNetworkModule`, `EVModule`, `HydrogenModule` |
| I.ii Scales; FES drivers | `ukabm/model.py`; `ukabm/drivers.py` | `GBMarketModel.__init__`, `demand`; `Drivers` |
| I.iii Scheduling | `ukabm/model.py` | `step`, `invest`, `run` |
| II.ii Offers, carbon, CfD, CM, merchant rules | `ukabm/decisions.py` | `RuleBased`, `ExpectationBids`, `npv_per_mw` |
| II.ii Decision interface, action spaces | `ukabm/decisions.py`, `ukabm/observations.py`, `ukabm/agents.py` | `DecisionMaker`, `ACTIONS`, `validate`, `GenCo._decide` |
| II.ii Government round settings | `ukabm/institutions.py` | `TargetTracking.round_settings`, `observe` |
| II.ii CM target | `ukabm/institutions.py` | `SystemOperator.full_target`, `cm_target` |
| II.ii Household choice | `ukabm/multienergy.py` | `HeatModule.update` |
| II.ii Closure | `ukabm/model.py` | `step` (retirement block) |
| II.iii Learning hook | `ukabm/model.py`, `ukabm/decisions.py`, `ukabm/observations.py` | `_learn`, `DecisionMaker.learn`, `Outcome` |
| II.iv Sensing | `ukabm/model.py`, `ukabm/observations.py` | `observation`, `_market_info`, `Observation`, `MarketInfo` |
| II.v Prediction | `ukabm/model.py` | `forecast`, `forecast_horizons`, `expected_margin_per_mw`, `existing_gross_margin_kw` |
| II.ix Stochasticity | `ukabm/model.py`, `ukabm/multienergy.py`, `ukabm/ensemble.py` | `rng`, `choose_zone`, `invest`, `network_sample`; `HeatModule`; `run_ensemble` |
| II.x Observation | `ukabm/model.py` | `results`, `hourly`, `firm_panel`, `auctions`, `_firm_rows` |
| III.ii Initialisation | `ukabm/model.py`, `ukabm/config.py`, `ukabm/scenarios.py` | `_init_fleet`, `_pathway_fleet`, `legacy_cfd_strikes`; `fleet_mw`, `INITIAL_FLEET_MW`; `validate`, `get_scenario` |
| III.iii Input data | `ukabm/data/pypsagb.py`, `ukabm/drivers.py`, `ukabm/config.py` | `PyPSAGBData`; `Drivers`; `_load_cost_paths`, `_load_table` |
| III.iv Market clearing | `ukabm/market.py`, `ukabm/model.py` | `clear`, `merit_order`, `scarcity_markup`; `run_market`, `blocks`, `_merge_blocks` |
| III.iv Interconnectors | `ukabm/model.py`, `ukabm/data/pypsagb.py` | `interconnector_blocks`; `interconnector_mw_by_market`, `IC_COMMISSIONING_OVERRIDES` |
| III.iv Storage and flexible demand | `ukabm/market.py`, `ukabm/model.py`, `ukabm/multienergy.py` | `storage_arbitrage`, `valley_fill`; `run_market`; `EVModule.hourly_load`, `HydrogenModule.hourly_load` |
| III.iv Settlement | `ukabm/model.py` | `settle`, `battery_services_per_mw` |
| III.iv System cost | `ukabm/costs.py`, `ukabm/model.py` | `fixed_costs`, `variable_cost`, `present_value`; `system_cost` |
| III.iv Network stage | `ukabm/model.py`, `ukabm/network.py`, `ukabm/data/pypsagb.py` | `network_stage`, `network_sample`, `bm_bids`, `interconnector_injection`; `redispatch`; `links_for_year`, `link_availability` |
| III.iv CfD round | `ukabm/model.py`, `ukabm/institutions.py` | `cfd_round`; `PotSettings` |
| III.iv Government tender | `ukabm/model.py` | `dpa_round`, `build_room` |
| III.iv Capacity Market | `ukabm/model.py` | `cm_auction`, `_cm_battery_supply` |
| III.iv Merchant investment | `ukabm/model.py`, `ukabm/decisions.py` | `invest`; `ExpectationBids.merchant_investment`, `margin_path`, `path_npv` |
| III.iv Households, gas, EVs, electrolysers | `ukabm/multienergy.py`, `ukabm/model.py` | module classes; `step` (retail prices), `demand` |
| III.iv Planner, evaluator, reserve | `ukabm/planner.py` | `plan`, `evaluate`, `sample_days`, `_add_reserve`, `reserve_settings` |
| III.iv Gap | `ukabm/gap.py`; `ukabm/scenarios.py` | `gap_run`, `summarise`, `run_many`; `IDEAL_TRAITS`, `LADDER` |
| Scenarios | `ukabm/scenarios.py`, `ukabm/data/scenarios.toml` | `SCENARIO_KEYS`, `validate`, `load_scenarios` |
