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
  firms' bids, and "plan design" becomes a behaviour that can be studied and varied. [items 2, 3, 6]
* **A system operator agent** (NESO) that sets the CM target from the 3 h LOLE reliability standard on
  its own demand forecast, with a T-1 holdback. [item 5]
* **Rules that change over time.** Reforms triggered by outcomes (a failed round, a price spike) and
  options such as those in the review of electricity market arrangements (REMA). This is the deck's
  "emergent institutions" theme. [items 2, 22]
* **Later:** a carbon market whose price emerges from a cap (UK ETS), and nuclear and transmission
  treated as government decisions. [item 33]

What the government maximises is a research choice. Decided: several objectives (targets, least cost,
bills, political), compared as levers. [items 2, 6]

## 2. What do firms decide?

* **No project pipeline.** Every firm bids every technology every year. Real projects pass through
  seabed leasing, consent and the grid connection queue over several years, with development costs sunk
  before any auction, and many drop out. [item 18]
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
  sheets, and the same five firms exist for 25 years. [item 32]
* **Lumpy, strategic, ageing.** Blocks of 300–1,600 MW; a fixed bid mark-up with no withholding and no
  strategic investment such as pre-empting rivals; plants retire after two loss-making years or at end of
  life, with no life-extension or mothballing decisions.

### What the agents cannot yet express

Mapped onto the sources the deck names:

| source | the agents now | missing | item |
|---|---|---|---|
| market and plan design | government and system-operator agents, CfD and CM rules, objectives as levers | regulator, transmission planning | 2–6, 27 |
| limited information | firms differ only in their carbon belief; every forecast is a perfect model run on the true paths | forecast errors, learning, heterogeneous information | 34, 36 |
| cost of capital and risk | a fixed WACC and a flat risk haircut in a deterministic world | uncertain futures, risk-based decisions, risk-dependent cost of capital | 35, 37 |
| strategic behaviour | static mark-ups (transfers) | withholding, pre-emption, bid shading, portfolio effects, BM gaming | 38, 24, 25 |
| path dependence | sequential, lumpy decisions with lead times | pipeline, learning-curve costs | 18, 19 |
| not yet identified | — | suppliers and PPAs, household flexibility, EV adoption | 39 |

Uncertainty (item 35) comes first among these: without it, limited information and risk cannot arise,
and the insurance value of CfDs and the Capacity Market is invisible to the gap.

**Built for learning and LLM agents.** Every firm decision goes through `ukabm.decisions.DecisionMaker`,
one instance per firm (so a learner keeps its own state), selectable per firm by scenario; governments
and system operators are registered classes in `ukabm.institutions`. What is still missing for Q-learning
and LLM agents is item 34: an explicit observation (what the agent may know), a declared action space
and a reward, so that a learning or LLM agent cannot read the model's true future.

## 3. What is "optimal", and is the comparison fair?

* **No convergence test.** Under textbook conditions (energy-only market priced at VoLL in scarcity,
  price-taking firms, perfect foresight, divisible investment) a competitive market reproduces the
  least-cost plan. The model has never been checked against this. Until ideal agents in an ideal market
  land close to the planner, part of every gap may be an artefact of the decision procedure. [item 7]
* **Different ambitions.** The planner values carbon at the carbon price. The agents' system emits *less*
  than the optimum after 2035, because policy buys low-carbon capacity, so part of the gap pays for
  ambition rather than waste. An optimum with the agents' emissions (and reliability) as constraints
  separates efficiency from ambition. [item 10]
* **Different information.** The planner has perfect foresight and the agents do not, so the gap mixes
  the value of information with the cost of decentralised decisions. A rolling-horizon planner (a
  planner with the agents' information) splits the two. [item 11]
* **Near-optimal space.** The cost surface is flat near the optimum: many different fleets cost within
  a few per cent of it. The convergence trial cost 1.7 % more than the planner with a quarter of its
  offshore wind. So the planner's exact mix is one point in a wide valley, and capacity differences
  overstate the error. Report each emergent run against the near-optimal bands (minimum and maximum of
  each technology within 2 % and 5 % of the optimal cost), alongside the £ gap. Inside the valley, choices
  are legitimately made on criteria the model does not price (planning acceptance, land, network,
  supply chains, distribution). [item 10]
* **No "planned" pathway.** The deck contrasts optimal and emergent. The actual plan (Clean Power 2030,
  FES) is a third pathway, so the comparison becomes optimal vs planned vs emergent. [item 12]
* **Reserve and response, option set, build limits:** items 9 and 20.
* **Electricity only.** The planner holds heat-pump uptake, EV charging and electrolysers at the agents'
  values, so household and hydrogen decisions sit outside the gap. Decided: a multi-energy optimum with
  heat and hydrogen. [items 14, 15]

* **FES is not used yet.** Future demand, EV, hydrogen and the government's later targets are "FES-like"
  guesses. FES should supply exogenous drivers and a planned benchmark, but never calibration targets
  for the agents' capacity mix (that would assume the answer). [item 12]
* **The yardstick values carbon at the market price.** The system cost uses the carbon price the agents
  face (£60 → £180/t). Judged at the government's appraisal values instead, low-carbon build that looks
  like over-build may not be. Report the gap at both.
* **Only every fifth year is costed.** The gap evaluates 2025, 2030, …, so the 2026–27 gas spike, which
  drives real decisions in the agent run, never enters the cost comparison.

## 4. Physics and economics that bias the gap

* **Technology costs are constant 2025–2050.** There is no learning for solar, batteries or offshore
  wind, so waiting has no value and the timing of investment cannot matter as it should. This affects
  path dependence directly. [item 19]
* **One weather year.** There is no prolonged cold, still spell (dunkelflaute), so the planner gives no
  value to the insurance a capacity market buys. [item 17]
* **Neighbouring markets are frozen.** Interconnector prices are 2024 shapes, so Europe does not
  decarbonise or depress prices when its own wind blows. Net trade is worth £17bn PV to the optimum, so
  the gap is sensitive to this. [item 28]
* **No network in the planner; transmission exogenous.** [items 26, 27]
* **Price formation:** no negative prices and no unit commitment. [item 30]
* **Demand side and long-duration storage.** No price-responsive demand beyond EV valley-filling (no heat
  or industrial flexibility), no hydrogen storage or other long-duration storage, and an exogenous
  hydrogen price. These shape the 2050 system in both pathways. [items 15, 29]
* **Supply chain.** The planner has build-rate limits; the agents are limited only by the CfD volume and
  six merchant decisions a year. Neither faces cost inflation when building fast.

## 5. Beyond system cost

* **Who pays.** Transfers cancel in system cost, but they decide bills, profits and the public purse, and
  so the politics that change the rules. Report consumer cost, producer surplus and policy cost for both
  pathways. [item 13]
* **Risk.** Spread of bills and loss of load across seeds and weather years, not only medians.
* **Emissions.** Cumulative emissions against the carbon budgets, not only the 2050 value.

## 6. Evidence

* **Auction history.** CfD rounds AR1–AR6 (2015–2024) and CM T-4 auctions (2014–2025) give clearing
  prices and volumes by technology. Back-casting the government and firm logic over that history is the
  only direct test of the emergent investment pathway; the 2025 calibration tests operation only.
  [item 16]
* **Weather years.** Decided: 4–6 historical years in both runs; operation back-casts 2020–24 not yet.
  [item 17]
* **Tolerance test** on the 2025 calibration. [item 31]

## 7. The experiments the deck asks for

Once sections 1–3 are in place:

* **Where the gap comes from:** a ladder with government rungs and firm rungs, run in several orders.
  [item 21]
* **Which designs close it:** sweeps of CfD budget and pot split, reliability standard, zonal pricing
  and REMA options. [item 22; zonal pricing needs item 26]
* **How it moves over time:** tipping points, lock-in, multiple equilibria. [item 23]
* **Other decision makers:** Q-learning and LLM agents behind the decision interface, compared with the
  rule-based agents and each other. [items 24, 25] The LLM agents run on open-weight models first:
  pinned weights and a published response cache make runs reproducible, there is no cost per call, and
  model size becomes a lever for how much reasoning an agent has (bounded rationality). The model does
  the arithmetic and the LLM chooses among options, because small models are unreliable with numbers.
  A CPU laptop runs a 4-bit 7–8B model for development; larger models and sweeps need a GPU cluster.

## 8. Practical

A 27-run gap batch takes about 2 hours on 12 cores, and the experiments above need tens of batches.
Each merchant decision re-clears a full 8,760-hour market as a forecast, up to seven times a year per
run. Profiling and speeding up the runs comes before the experiments. [item 8]

## 9. What the foundations review adds (27 Nov 2026)

The [foundations review](review_2026-11_foundations.md) compared the model with other approaches
([literature review](research/literature_review.md), sections 4–8) and tested the optimum against its
own assumptions. It confirms most of sections 1–8 and changes the picture in seven places. Items 40–55
are in the README; the review's section 9 proposes their order.

* **The optimum's wind mix is an artefact (F1).** Onshore and offshore wind share one hourly shape, so
  the planner builds the cheaper one to its build limit and the other for the rest. "88 against 40 GW
  offshore" compares a CfD pot share with an assumed limit. Separate profiles come before any statement
  about the mix. [item 41, with 17, 20 and 10]
* **The yardstick needs a table, not one number (F2, F3).** Three choices have official alternatives:
  the discount rate (Green Book 3.0 % since October 2026; DESNZ hurdle rates 7.6–8.9 %), the carbon
  value (£60–180 market path; £260–378 appraisal values) and the value of lost load (£6,000 in the
  planner; £16,950 behind the 3 h standard the agents are held to). On one seed the investment gap is
  £28.5bn by default, £17–45bn across build limits, £44bn with capital at 7 % and £71bn at appraisal
  carbon values (review section 2). [item 40] This sharpens section 3 above ("The yardstick values
  carbon at the market price").
* **The default plan is not optimal on the full year (F3).** A plan made at a VoLL of £16,950 has no
  loss of load and is £2.6bn cheaper than the default plan on the default yardstick: the planner's
  1,272 sampled hours understate scarcity. "The optimum chooses some loss of load" in
  [gap.md](gap.md) is largely this. A test should hold the planner's full-year cost at or below that
  of any fleet the model can find. [items 40, 42]
* **The residual comes first (F17).** The convergence test leaves 3.3 %; the headline is 9.9 %. Close
  the residual in steps (same fleet, then same options, then investment) to under 1 % before reading
  gaps. [item 42] Other investment models show that the price projection and the order of moves drive
  results as much as anything firms are assumed to want (F8, F9). [item 45]
* **The model fails auction evidence it could be tested on today (F10–F13, F20).** Offshore bids at
  £53–66/MWh against £91 in AR7; a Capacity Market at its cap for a decade, with 14 GW of new CCGT by
  2029 where the real 2029/30 auction brought none; no negative-price hours. Calibrate 2025 costs and
  technology hurdle rates to the auctions [item 44], and hindcast investment from 2015 [item 43]. This
  extends section 6.
* **Learning and LLM agents (F22–F25).** Tabular Q-learning cannot learn from 25 annual rewards, and
  model size is not a scale of bounded rationality. Notes are on items 24 and 25; a behavioural arm
  (hurdle-rate premium, payback, limited foresight, imitation) comes first. [item 55]
* **Reuse (F26–F33).** Inputs as data with a schema [47]; the licence of the bundled ESPENI profile
  [48]; releases, citation and provenance [49]; an ODD+D description [50]; verification a reader can
  see for code written with AI tools [51]; a decision on Mesa [53]. None of these changes results, so
  they can run in parallel.

Also new: a parameter register with sensitivity analysis and a replication count [46]; real firm
portfolios [52]; an equilibrium model as the exact answer for the risk rung [54].
