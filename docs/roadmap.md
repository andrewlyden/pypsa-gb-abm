# Roadmap: what the model is missing

The project asks how far the system that many actors build (emergent) is from the one a single planner
would build (optimal), where the gap comes from, and which market designs and plans close it. The first
measurement ([gap.md](gap.md)) put the baseline gap at about £32bn (10 %) over 2025–54. It also showed
that the model cannot yet say *where* the gap comes from: the decisions that set most of the outcome are
fixed parameters, not decisions anyone in the model makes.

This page sets out what is missing, grouped by the question each gap blocks, and why it matters. The
priority list the build agent works from is in the [README](../README.md#status--roadmap); item numbers
below refer to it.

## 1. Who decides? The rules are parameters, not decisions

What the code does today:

* **CfD.** Each year the round procures 6 GW (`Policy.cfd_budget_gw_per_year`), split 60 % offshore,
  20 % onshore, 20 % solar. Every GenCo bids two blocks of each technology every year, at its levelised
  cost at its cost of capital minus 2.5 points, ±5 % noise. Bids come out around £50–60/MWh against
  administrative caps of £85–113, so the caps never bind and every round fills. **Renewable volumes are
  therefore set by the policy parameters**: 3.6 GW offshore a year for 25 years is the 88 GW the agents
  reach by 2050. Competition decides who builds and at what strike price, and strike prices are transfers
  that cancel in system cost. This is why the agents' traits barely move the gap.
* **Capacity Market.** The target is peak demand four years ahead × 1.06, less supported plant. It is a
  fixed formula with no forecaster, no reliability standard and no T-1 auction. It sits ~25 % above
  published targets and explains most of the agents' extra OCGT and batteries.
* **Carbon price, nuclear, transmission, interconnectors.** All exogenous: a linear £60→£180/t path,
  Hinkley Point C and Sizewell C hard-coded, ETYS boundary capabilities by year, and the interconnector
  register.

What is missing:

* **A government agent** (DESNZ) that sets each allocation round's £ budget, pot split and
  administrative strike prices. It would respond to targets (Clean Power 2030, carbon budgets), the
  previous round's result (AR5 drew no offshore bids, and AR6 raised the offshore cap by about two-thirds)
  and the bill impact. With it, volumes come from the interaction of the government's budget and the
  firms' bids, and "plan design" becomes a behaviour that can be studied and varied. [items 2, 3]
* **A system operator agent** (NESO) that sets the CM target from the 3 h LOLE reliability standard on
  its own demand forecast, with a T-1 holdback. [item 5]
* **Rules that change over time.** Reforms triggered by outcomes (a failed round, a price spike) and
  options such as those in the review of electricity market arrangements (REMA). This is the deck's
  "emergent institutions" theme. [items 2, 18]
* **Later:** a carbon market whose price emerges from a cap (UK ETS), and nuclear and transmission
  treated as government decisions. [item 27]

What the government maximises is a research choice, not an engineering one. [*needs human*, item 28]

## 2. What do firms decide?

* **No project pipeline.** Every firm bids every technology every year. Real projects pass through
  seabed leasing, consent and the grid connection queue over several years, with development costs sunk
  before any auction, and many drop out. [item 14]
* **CfD bids ignore expectations.** The price forecast is passed to `cfd_bid` but not used. There is no
  capture-price or reference-price risk, no cost inflation, no view of competitors, no option to abstain
  and no non-delivery. [item 3]
* **Renewables only through CfDs.** While CfDs exist, merchant investment excludes wind and solar: there
  are no PPAs and no merchant projects. [item 4]
* **A short investment horizon.** Every technology is judged on one forecast year (t+3), whatever its
  lead time (5 years for offshore wind, 6 for gas CCS), and the margin is assumed flat over the plant's
  life, so cannibalisation over the life of a plant is missed. [item 4]
* **Finance.** Each firm has a fixed WACC, and CfD de-risking is a flat −2.5 points. The cost of capital
  does not depend on how much revenue is merchant, contracted or capacity payments. There are no balance
  sheets, and the same five firms exist for 25 years. [item 26]
* **Lumpy, strategic, ageing.** Blocks of 300–1,600 MW; a fixed bid mark-up with no withholding and no
  strategic investment such as pre-empting rivals; plants retire after two loss-making years or at end of
  life, with no life-extension or mothballing decisions.

## 3. What is "optimal", and is the comparison fair?

* **No convergence test.** Under textbook conditions (energy-only market priced at VoLL in scarcity,
  price-taking firms, perfect foresight, divisible investment) a competitive market reproduces the
  least-cost plan. The model has never been checked against this. Until ideal agents in an ideal market
  land close to the planner, part of every gap may be an artefact of the decision procedure. [item 6]
* **Different ambitions.** The planner values carbon at the carbon price. The agents' system emits *less*
  than the optimum after 2035, because policy buys low-carbon capacity, so part of the gap pays for
  ambition rather than waste. An optimum with the agents' emissions (and reliability) as constraints
  separates efficiency from ambition. [item 9]
* **Different information.** The planner has perfect foresight and the agents do not, so the gap mixes
  the value of information with the cost of decentralised decisions. A rolling-horizon planner (a
  planner with the agents' information) splits the two. [item 10]
* **No "planned" pathway.** The deck contrasts optimal and emergent. The actual plan (Clean Power 2030,
  FES) is a third pathway, so the comparison becomes optimal vs planned vs emergent. [item 11]
* **Reserve and response, option set, build limits, multi-sector optimum:** items 8, 16 and 29.

## 4. Physics and economics that bias the gap

* **Technology costs are constant 2025–2050.** There is no learning for solar, batteries or offshore
  wind, so waiting has no value and the timing of investment cannot matter as it should. This affects
  path dependence directly. [item 15]
* **One weather year.** There is no prolonged cold, still spell (dunkelflaute), so the planner gives no
  value to the insurance a capacity market buys. [item 30]
* **Neighbouring markets are frozen.** Interconnector prices are 2024 shapes, so Europe does not
  decarbonise or depress prices when its own wind blows. Net trade is worth £17bn PV to the optimum, so
  the gap is sensitive to this. [item 22]
* **No network in the planner; transmission exogenous.** [items 20, 21]
* **Price formation:** no negative prices and no unit commitment. [item 24]
* **Demand side and long-duration storage.** No price-responsive demand beyond EV valley-filling (no heat
  or industrial flexibility), no hydrogen storage or other long-duration storage, and an exogenous
  hydrogen price. These shape the 2050 system in both pathways. [item 23]
* **Supply chain.** The planner has build-rate limits; the agents are limited only by the CfD volume and
  six merchant decisions a year. Neither faces cost inflation when building fast.

## 5. Beyond system cost

* **Who pays.** Transfers cancel in system cost, but they decide bills, profits and the public purse, and
  so the politics that change the rules. Report consumer cost, producer surplus and policy cost for both
  pathways. [item 12]
* **Risk.** Spread of bills and loss of load across seeds and weather years, not only medians.
* **Emissions.** Cumulative emissions against the carbon budgets, not only the 2050 value.

## 6. Evidence

* **Auction history.** CfD rounds AR1–AR6 (2015–2024) and CM T-4 auctions (2014–2025) give clearing
  prices and volumes by technology. Back-casting the government and firm logic over that history is the
  only direct test of the emergent investment pathway; the 2025 calibration tests operation only.
  [item 13]
* **Operation back-casts 2020–24 and weather years.** [*needs human*, item 30]
* **Tolerance test** on the 2025 calibration. [item 25]

## 7. The experiments the deck asks for

Once sections 1–3 are in place:

* **Where the gap comes from:** a ladder with government rungs and firm rungs, run in several orders.
  [item 17]
* **Which designs close it:** sweeps of CfD budget and pot split, reliability standard, zonal pricing
  and REMA options. [item 18; zonal pricing needs item 20]
* **How it moves over time:** tipping points, lock-in, multiple equilibria. [item 19]
* **Other decision makers:** Q-learning and LLM agents behind the decision interface. [items 1, 31]

## 8. Practical

A 27-run gap batch takes about 2 hours on 12 cores, and the experiments above need tens of batches.
Each merchant decision re-clears a full 8,760-hour market as a forecast, up to seven times a year per
run. Profiling and speeding up the runs comes before the experiments. [item 7]
