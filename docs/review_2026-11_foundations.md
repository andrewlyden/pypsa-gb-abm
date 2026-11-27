# Foundations review, 27 November 2026

The [code review](review_2026-11.md) asked whether the code does what the model says. This review asks
whether the model is the right one: how its foundations compare with other approaches to the same
problem, which assumptions do not hold up, and what the repository needs before others can reuse it and
build GB agent-based research on it.

**What was done.** (1) The code and documents on `roadmap/34-information-sets` (8dec60c) were read in
full. (2) Five literature and evidence searches (investment ABMs; optimum-against-market methods; GB
auction and modelling evidence; learning and LLM agents; validation and software standards); the
sources, each marked as read in full, abstract only or search result only, are in the
[literature review](research/literature_review.md), sections 4–8, and keys such as [Tao2021] refer to
its reference list. (3) Checks against the committed results, and one new run: a baseline agent run
(seed 1) with eight planner variants ([section 2](#2-how-far-the-optimum-moves-with-its-own-assumptions)).

Each finding is tagged **new** (not in the roadmap or assumptions before this review), **sharpened**
(known, now with evidence or a number) or **known**. Evidence is tagged *code* (read in the code),
*results* (committed results), *run* (the new run) or *lit*.

## 1. Summary

**What stands up.**
* *Hourly clearing over 8,760 hours.* The field moved from load-duration curves to hourly resolution
  because the curves overstate renewables and cannot represent storage [Kell2020, Chappin2017].
* *One cost definition and one evaluator for both pathways.* This is the harmonisation that
  Torralba-Díaz et al. put first [Torralba2020], and the investment/operation split is clean.
* *The convergence test.* Checking that idealised agents recover the optimum is what Tao et al.
  recommend [Tao2021] and few investment ABMs do.
* *Government and system operator as agents.* In the models reviewed, auction volumes and capacity
  targets are inputs. A government that adapts budgets and caps to auction outcomes is unusual.
* *The decision interface with an explicit observation.* Holding the information set and the action
  space equal across rule, learning and LLM agents is the precondition for comparing them.
* *The research question is open.* The nearest prior work compares operation only [Torralba2020], is
  stylised [Jonson2020], or compares a learned mix with a plan without attributing the difference
  [GonzalezRuiz2025]. No paper was found that splits an investment gap by source for a real market's
  instruments. The link to PyPSA-GB for the network is also unusual among ABMs.

**What does not yet stand up, in order of threat to the headline result.**

1. **The optimum is not a fixed point to measure from.** Its wind and solar mix is set by assumed build
   limits, because the model gives onshore and offshore wind the same hourly shape (F1). The investment
   gap is £28.5bn in the default and between £17bn and £71bn (5–21 %) when the build limits, the
   carbon value or the cost of capital take other defensible values (section 2, F2). The default plan
   is also not the optimum of the year it is costed on: a plan with more peakers is £2.6bn cheaper
   (F3). One weather year and perfect foresight each carry an error as large as the gap in the
   literature (F4, F5).
2. **The unexplained residual is a third of the headline.** The convergence test leaves 3.3 % (£10bn)
   under textbook conditions; the baseline gap is 9.9 % (£32bn). Torralba-Díaz et al. harmonised their
   two models to 0.0001 % before reading any gap (F17).
3. **The investment procedure is the known weak point of this model class.** Firms forecast with the
   model's own run on the true future paths and the committed pipeline only, the method Tao et al. show
   to be the most sensitive to hidden assumptions (F8). The order of moves hands every project to one
   firm at a time (F9).
4. **The model fails the auction evidence the repository already holds.** Offshore wind bids come out
   at £53–66/MWh against £91 in AR7; the Capacity Market clears at its cap for a decade, and the agents
   add 14 GW of CCGT by 2029 where the real auction for 2029/30 brought no new gas; there are no
   negative-price hours against 150–190 a year (F10–F13).
5. **Nothing after 2025 is validated, and the stated uncertainty is not uncertainty.** Seeds vary agent
   draws in a deterministic world, so a ±£1bn range says little (F20, F21).
6. **Two planned experiments rest on premises the literature does not support.** Tabular Q-learning
   cannot learn from 25 annual rewards, and model size is not a scale of bounded rationality (F22–F24).
7. **The repository is not yet reusable by others.** Parameters and scenarios live in code, the bundled
   demand and wind profile is under a non-commercial licence, there are no releases or citation
   metadata, and there is no protocol description (F26–F33).

None of this argues against the project. The first measurement did its job: it showed what the gap is
made of. The argument is about order. Sections 3–8 give the findings; section 9 proposes the order of
work and the new roadmap items (40–55).

## 2. How far the optimum moves with its own assumptions

One baseline agent run (seed 1, 2025–2050). The planner is then re-solved under each variant, and both
fleets are costed by the evaluator under the same variant. The agents' fleet is the same in every row
(2050: 88 GW offshore, 35 GW onshore, 41 GW solar); only the benchmark and the yardstick change. The
table is the investment gap; the operation gap (about £4bn) is not affected. Reproduce with
`python scripts/run_planner_sensitivity.py` (about 90 minutes); numbers by year are in
[results/planner_sensitivity.md](../results/planner_sensitivity.md).

| Variant | Optimum, PV £bn | Agents' fleet, PV £bn | Investment gap, £bn (%) | Planner 2050: offshore / onshore / solar, GW |
|---|---|---|---|---|
| **Default** (limits as in `config.py`, 3.5 %, carbon £60 → £180/t, VoLL £6,000) | 316.4 | 344.9 | **28.5 (9.0)** | 40 / 58 / 45 |
| Build limits × 0.5 | 326.5 | 344.9 | 18.5 (5.7) | 60 / 29 / 44 |
| Build limits × 2 | 307.2 | 344.9 | 37.7 (12.3) | 16 / 111 / 39 |
| Onshore limit lifted (20 GW a year) | 299.6 | 344.9 | 45.3 (15.1) | 3.5 / 129 / 37 |
| Wind and solar limited to the CfD volumes (3.6 / 1.2 / 1.2 GW a year) | 327.6 | 344.9 | 17.3 (5.3) | 63 / 28 / 33 |
| VoLL £16,950/MWh | 313.8 | 344.9 | 31.2 (9.9) | 40 / 58 / 46 |
| Carbon at appraisal values (£310 → £450/t) | 335.0 | 405.6 | 70.6 (21.1) | 50 / 58 / 57 |
| Capital at 7 % | 372.9 | 417.1 | 44.2 (11.9) | 21 / 58 / 32 |

Notes: the carbon row is the Green Book central series (£260 → £378/t in 2020 prices) moved to 2024
prices with an approximate factor of 1.19. In the capital row the planner optimises at 7 % and capex is
annuitised at 7 % for both fleets; annual costs are still discounted to present value at 3.5 %.

What the table shows:

1. **Build limits alone move the investment gap between £17bn and £45bn (5–15 %).** With the onshore
   limit lifted the planner builds 129 GW of onshore wind and lets offshore wind run down to 3.5 GW. The
   planner's wind mix is its limit (F1).
2. **About £11bn of the £28.5bn is the difference between two volume assumptions.** When the planner
   may build no more wind and solar each year than the CfD rounds award, the gap is £17bn. It still
   stops at 63 GW offshore against the agents' 88 GW, so the rest is over-build of offshore wind,
   batteries and peakers.
3. **The default plan is not the optimum of the year it is costed on.** At a VoLL of £16,950 the planner
   adds 4.6 GW of OCGT and 3 GW of batteries and has almost no unserved energy (1 GWh in 2040). That
   plan costs £313.8bn at either VoLL, £2.6bn less than the default plan. The default planner optimises
   on 1,272 sampled hours and is costed on 8,760; the sample understates scarcity. "The optimum chooses
   some loss of load" is largely this artefact, and the gap is understated by at least £2.6bn (F3).
4. **At appraisal carbon values the gap is £71bn (21 %).** The agents' fleet keeps 51 GW of unabated gas
   where the planner builds 26.5 GW of gas CCS and none. The agents did not face that price, so this is
   a statement about the yardstick, not about their behaviour.
5. **A higher cost of capital widens the gap here; it does not narrow it.** The expectation from the
   literature was that a 3.5 % yardstick inflates the gap. In this model policy makes the agents' fleet
   more capital-intensive than the planner's, so dearer capital penalises the agents more (£44bn at
   7 %). The planner at 7 % builds half the offshore wind (21 GW) and emits more than the agents in
   2050 (6.9 against 6.2 Mt).
6. **The investment gap lies between £17bn and £71bn (5–21 %) across choices that are assumptions or
   conventions.** The seed range of ±£1bn is small beside this. One seed and one agent run; the
   variants are not combined.

## 3. The optimum

**F1. The planner's wind and solar mix is set by its build limits, not by system value. (new; code,
results, run)**
* *Model.* `GBMarketModel.cf_profile` gives onshore wind 0.75 × and offshore wind 1.10 × the same GB
  hourly shape. To a linear programme the two are the same product at different prices: £46/MWh onshore
  and £53/MWh offshore at 3.5 % with the model's costs (solar £42). The planner therefore builds the
  cheaper one up to its limit and fills the rest with the other.
* *Results.* The planner's onshore fleet follows `PLANNER_BUILD_MW_PER_YEAR` (2.5 GW a year, net of
  retirements: 20.6, 30.1, 39.1, 47.5, 57.5 GW in 2030–2050) and solar is at its limit in 2030
  (44.5 GW). In the
  convergence test the agents, who have no limit, build 98 GW onshore and 12 GW offshore.
* *Run.* With the onshore limit lifted the planner builds 129 GW onshore and no new offshore wind, and
  the investment gap rises from £28.5bn to £45bn. With all limits halved it falls to £18.5bn.
* *So what.* "88 GW offshore against the optimum's 40" compares a CfD pot share with a planning
  assumption. Neither is a decision, and the cost difference between them is the £7/MWh between two
  assumed costs. The "flat cost surface" seen in the convergence test is partly the same artefact: the
  model has made the two technologies interchangeable. With real profiles they are not: offshore and
  onshore wind differ in timing, in location relative to the network and in correlation with demand.
  The limits themselves are marked ASSUMPTION in `config.py`.
* *Do.* Separate onshore, offshore and at least north/south wind profiles (atlite, through PyPSA-GB) in
  both runs before reading any statement about the wind mix [item 41]. Report every gap for a range of
  limits [item 20], and as a position inside or outside the near-optimal band [item 10].

**F2. The yardstick is a set of normative choices, and official values exist for each. (sharpened;
lit, run)**
* *Discount rate.* Both pathways are costed at 3.5 %. HM Treasury cut the Green Book rate to 3.0 % in
  October 2026 [HMT2026]. DESNZ's hurdle rates are 7.6–8.9 % [CEPA2025]. A 3.5 % yardstick books every
  difference in the fleet that a higher cost of capital causes as waste. Whether a risk premium is a
  transfer or a real cost is contested: the Committee on Climate Change held that risk passed to the
  private sector "is a genuine resource cost" [CCC2011], and in the equilibrium literature a premium
  under incomplete risk markets is a real cost [deMaere2017, Dimanchev2024a]. Jonson et al. found the
  discount rate mattered more than foresight [Jonson2020]; in zonal-pricing studies a 0.3–0.9 point
  change in WACC reverses the sign of the result (literature review 6.1).
* *Run.* At 7 % the gap rises from £28.5bn to £44bn. The direction is the opposite of the one the
  literature suggests, because here the agents' fleet is the more capital-intensive of the two. So the
  social rate does not manufacture the gap in this model; it flatters the agents' fleet.
* *Carbon.* Emissions are costed at the carbon price firms face (£60 → £180/t). Appraisal values are
  £260 → £378/t in 2020 prices, and the guidance separates them from market prices [BEIS2021]. Using
  the Treasury's discount rate with a market carbon price mixes two yardsticks. At appraisal values the
  gap is £71bn (21 %), because the agents' fleet keeps unabated gas that the planner replaces with CCS.
* *So what.* The headline needs a small table, not one number: the gap at the social rate and at hurdle
  rates, at market and at appraisal carbon values (section 2).
* *Do.* [item 40].

**F3. The planner's loss of load is a sampling artefact, and its only reliability test is one
deterministic year. (new; code, lit, run)**
* *Model.* The planner optimises on 1,272 sampled hours per period (every seventh day plus the day of
  highest net load) and is costed on 8,760. It values unserved energy at £6,000/MWh, the balancing price
  cap, and leaves 129 GWh unserved in 2050. The agents' system operator buys capacity to the 3 h
  standard and the agents leave none.
* *Run.* At a VoLL of £16,950 the planner adds 4.6 GW of OCGT and 3 GW of batteries, has almost no
  unserved energy, and costs £2.6bn *less* than the default plan on the default yardstick. A cheaper
  feasible fleet than the "optimum" exists, so the sample understates scarcity and the default plan is
  short of firm capacity by mistake, not by choice. The gap moves little (£28.5bn → £31bn).
* *Evidence.* The 3 h standard was derived from a VoLL of £16,950/MWh and a cost of new entry of
  £47.18/kW/yr [DECC2013]; Newbery calls the difference from £6,000 "missing money" [Newbery2016]. NESO
  applies the standard over 34 weather years × 100 outage patterns and procures to "substantially less
  than 3 hours" [PTE2025]. The model has one weather year and no plant outages (availability is a flat
  derating), so "3 h LOLE" is the fourth-highest hour of one deterministic year.
* *So what.* The VoLL is not what separates the two runs: at £16,950 the planner still holds 12 GW of
  OCGT against the agents' 34 GW. What a reliability standard pays for is cold, still years and plant
  failures, and neither is in the model. Until they are, "without the Capacity Market the gap halves"
  compares the modelled CM (F11) with a planner that faces no adequacy risk.
* *Do.* A test that the planner's cost on the full year is no higher than that of any fleet the model
  can find (start with the £16,950 plan); a sample that reproduces full-year scarcity, or iteration
  between plan and evaluation; the £16,950 VoLL in the yardstick table [item 40]; weather years and
  outages [item 17].

**F4. One weather year and linear dispatch put an error on the optimum of the same order as the gap.
(sharpened; lit)** Single-year designs differ by about ±10 % in system cost [Gotske2024]; for GB they
risk inadequacy [Zeyringer2018]; a 0.5 % cost slack already allows a wide range of fleets [Neumann2021].
Items 17 and 10 are the right responses. The gap should be reported with a band from weather years and
from the near-optimal space, and a 3–10 % gap inside that band is not yet a finding.

**F5. Perfect foresight against the agents' information. (known; lit)** Myopia alone costs 23 % in a
European study and up to 61 % in a GB one [Mannhardt2024, Heuberger2018]. The planner here also sees the
2026–28 gas spike coming. Item 11 (a rolling-horizon planner) is essential before any share of the gap
is attributed to markets, and belongs before the ladder.

**F6. "Transfers cancel" leaves out what CfDs and the Capacity Market are for. (sharpened; lit)** In
equilibrium models with risk-averse investors these instruments complete a missing risk market, and
their value is the welfare difference between incomplete and complete risk trading [deMaere2017,
Mays2019]. In a deterministic model at one discount rate that value is zero by construction, so the
instruments can only appear as distortions or as volume rules. The relevant optimum for risk-averse
firms is the complete-market risk-averse plan, not a risk-neutral plan at 3.5 % [Dimanchev2024a,
Makrides2025]. Items 35 and 37 start this; a small equilibrium model for the risk rung would check the
ABM where an exact answer exists [item 54].

**F7. Smaller, known.** Only every fifth year is costed, so the 2026–27 gas spike is in neither present
value (code review D5). The planner cannot retire existing plant early (D4). Neighbouring prices do not
respond to GB exports, and they rise with the GB carbon price because they are anchored on a GB CCGT
(item 28). The planner inherits the agents' smart-charging profile, which was shaped to the agents'
fleet (*code*: `gap_run` passes `m.hourly[y]["load"]`).

## 4. The agents

**F8. Firms forecast with the model itself, on the true future. (sharpened; code, lit)**
* *Model.* `forecast(t+3)` re-clears the full market with the committed pipeline on the true fuel,
  carbon and demand paths. Firms differ only in a carbon belief. The `expectations` logic adds t+8 and
  t+13 with wind and solar extended at their recent rate and peakers added until the system is adequate.
* *Evidence.* This is Tao et al.'s "myopic agents" projection: it assumes no entry after the known
  pipeline, results "vary enormously" with the horizon, and longer look-ahead over-builds, mostly
  peakers [Tao2021]. The horizon fill in `forecast_horizons` is one of the fixes they describe as
  reducing transparency. Other models give firms their own forecast: regressions on history (EMLab,
  ElecSim 2019), an expansion model per firm (EMIS-AS), or iteration to an equilibrium (PowerACE).
  "Investors have their own model inside the simulation. This inherently limits what can be done"
  [Chappin2017].
* *So what.* Two opposite errors sit in one procedure. Firms know more than any investor (the exact
  2028 gas price) and less than a rational one (no entry by others after t+3). Results will depend on
  the choice of t+3, which no one has varied.
* *Do.* Vary the horizon and the projection rule in the convergence test and report the spread; add a
  projection that is consistent with entry (iterate until no firm wants to enter, or fill the horizon
  with the least-cost additions) [item 45]. Item 36 then replaces the true paths with firms' own
  forecasts.

**F9. The order of moves gives each project to the first firm in line. (new; code)**
* *Model.* In `invest`, the order is drawn once a year. In each round the first firm in that order with
  a positive NPV builds one block, the forecast is re-run and the loop restarts from the first firm. So
  one firm takes every project until its NPV turns negative or its budget runs out, and total entry is
  set by the least demanding firm that still has budget.
* *Evidence.* EMLab re-draws the order and loops until nobody invests; PowerACE iterates to a Nash
  equilibrium; the DDM peer review flagged that utilities "always pre-empt" merchants [DDMreview].
* *So what.* Firm heterogeneity (WACC, risk aversion, beliefs) mostly decides who owns the plant, not
  how much is built. This is a second reason, beside fixed volumes, why the ladder's rungs barely move.
* *Do.* Re-draw the order at every decision, and test block size [item 45].

**F10. Costs and hurdle rates do not reproduce the auctions the repository cites. (new; code, lit)**
* *Offshore wind.* `config.py` records AR7 at £91.20/MWh (2024 prices). With the model's costs
  (£2,500/kW, 42 % capacity factor) the levelised cost is £53/MWh at 3.5 % and £66 at 6 %, and rule-based
  bids are £50–60. "Bids never reach the caps", the observation that led to the government agent, is
  largely a cost assumption. DESNZ states that "levelised costs are not strike prices" [GenCosts2023].
* *Constant costs.* Offshore clearing prices went 37 → no bids → 59 → 65 (£2012) between 2022 and 2026
  while hurdle rates rose 1–2 points [GenCosts2025]. Item 19 covers cost trajectories; the level in 2025
  is wrong first.
* *Hurdle rates.* The model varies WACC by firm type (6–10 %) and takes 2.5 points off for a CfD.
  Official rates vary by technology (7.6 % solar and onshore, 8.9 % offshore and gas), a CfD is worth
  0.8–1.5 points, and the uncertainty is ±1.1–1.7 points [EE2018, CEPA2025].
* *Do.* Calibrate 2025 costs and technology hurdle rates so that the model's AR6 and AR7 clearing
  prices are in range, before any cost trajectory [item 44; item 37 for hurdle rates].

**F11. The Capacity Market does not behave like the real one. (new; results, lit)**
* *Results.* In the gap baseline (median of seeds 1–3) the T-4 auction clears at the £75 cap in every
  year from 2030 to 2042, and CCGT capacity rises from 30 GW to 44 GW by 2029. In the seed-42 scenario
  run the auction is within £2 of the cap from 2028 to 2037. The first modelled auction (held 2025,
  delivery 2029) clears at £16 (seed 42) or £36 (gap seeds).
* *Evidence.* The T-4 auction for 2029/30 cleared at £27.10 with 44 GW entering for a 39.4 GW target;
  no new-build gas cleared. No T-4 auction has cleared at the cap (range £6–65). New capacity has come
  from small engines, batteries, demand response and refurbishment (literature review 6.3).
* *Why.* New-build bids are net cost of new entry at the firm's WACC on a 15-year agreement; there are
  no engines, demand response or refurbishment options; batteries are de-rated at a flat 20 % where the
  scheme scales with duration; and the target comes from one weather year.
* *Do.* Add the entrant types that set the price, duration-based de-rating, and a back-cast of 2014–2026
  [items 16, 44]. Until then, "the Capacity Market over-builds peakers" is a property of the model's CM.

**F12. Awarded capacity is always built, every year, in whole blocks. (new; code, lit)**
* 3.8 GW of AR4 and AR6 offshore awards were abandoned, and NESO assumes 3.9 GW of CM non-delivery
  [PTE2025]. The model has no non-delivery.
* The 6 GW a year "fixed" rule awards 7 GW: pots accept whole blocks while below their limit, so offshore
  gets 4 GW a year, not 3.6 (*results*: `cfd_awarded_mw` = 7,000 every year).
* Rounds were irregular until 2022; onshore wind and solar share one pot; terms were 15 years before
  AR7; from AR7 the budget is set after seeing the bids. The `targets` government has none of these.
* Plants retire after two loss-making years. EMIS-AS requires three conditions and BRAIN-Energy up to
  ten years.

**F13. Prices are too smooth for the technologies whose value depends on spread. (sharpened; results,
lit)** The baseline has no negative-price hour in any year; GB had 149–190 in 2025. The wind capture
discount reached 16 % in summer 2025. Battery revenue fell about 60 % as the fleet grew. The model
recovers battery revenue with two service "pots", which are a calibration device, not a market. Any
result about batteries, electrolysers, flexible demand or the merchant tail of wind depends on this
(item 30 is rated too low for that reason).

**F14. Five invented firms, each with a slice of everything. (new; code)** The initial fleet is dealt
round-robin by zone, so every firm owns a share of every technology. Portfolio effects, market power and
entry by new types of owner cannot be studied, and the mark-up rung can only be a transfer. ElecSim
starts from the actual owners in DUKES; BRAIN-Energy from six investor types with different foresight
and finance. Real ownership is public (DUKES, REPD, the TEC register) [item 52].

**F15. A deterministic world. (known; code)** Fuel, carbon, demand and weather follow one known path.
Risk aversion is a haircut on a certain number. Item 35 is correctly placed first in phase A2: without
it there is no limited information and no risk, and F6 cannot be addressed.

**F16. Institutions and households run on invented parameters. (sharpened; code, lit)**
* The governments' rules (`GOVERNMENT_*`: levy thresholds, cap steps, election effects) are labelled
  illustrative. They can serve as levers. They cannot support a claim about emergent institutions until
  they reproduce at least the AR5 failure and the AR6 response (cap +66 %).
* The household logit (scale £1,500, hassle £4,000, discount rates 4–20 %) is uncalibrated. Cost-only
  choice overstates uptake [Frontier-heat]; installations are about 60,000 a year; the grant rise of
  October 2023 is a natural experiment for the grant response.
* The gas-network feedback has no quantified peer-reviewed counterpart. Label the multi-energy modules
  as stylised until item 14, and keep them out of headline claims.

## 5. The comparison

**F17. The residual under textbook conditions is a third of the headline. (sharpened; results,
lit)** The convergence test leaves 3.3 % (2.6–4.1 % over three seeds) with fleets that differ by tens
of GW. Torralba-Díaz et al. reached 0.0001 % before interpreting gaps of 0.03–4 % [Torralba2020]. Their
models share a fleet, which is the easier problem, but the principle holds: a gap can be read only
above the residual. Close it in steps, each with a target:
1. *Same fleet, market against evaluator* (the operation gap, 1–2 % of cost). This should be near
   zero for price-taking firms. What remains is the storage, interconnector and electrolyser heuristics,
   which are modelling shortcuts, not behaviour.
2. *Same options.* Equal build limits, battery services off or valued on both sides (items 20, 9).
3. *Investment.* Then the projection rule and the order of moves (F8, F9).
[item 42]

**F18. Attribution. (known; lit)** A ladder in one order is not an attribution unless the model is
additive [Saltelli2010]; negative rungs are expected in a second-best world [Lipsey1956,
Dimanchev2024b]. Item 21 (all orders) is right; report pairwise interactions with it, as Shapley values
hide them [Green2021]. Until F8, F9 and F15 are dealt with, the firm rungs measure levers that cannot
move.

**F19. What the gap can claim today.** A 10 % gap is at the low end of what the real UK transition
showed against a cost optimum (9–23 %, [Trutnevyte2016]). That makes the number plausible, not
validated. The defensible statements now are comparisons between runs of the same model, as
[gap.md](gap.md) says, and those depend on F11 for the Capacity Market and on F1 and F10 for CfDs.

## 6. Evidence

**F20. No test of the investment model exists, and several are available now. (sharpened)**
* The 2025 comparison tests operation, with parameters tuned to the same year (code review, section C).
  In TRACE terms it is output verification; corroboration needs data not used in development
  [Grimm2020].
* Ready-made tests the model currently fails or has never been run against: AR6 and AR7 prices and
  volumes; T-4 clearing prices and the absence of new gas; negative-price hours; capture-price discounts;
  battery revenue against fleet size; heat-pump installations (literature review 6.2–6.4).
* The strongest test is an investment hindcast: start from the 2015 fleet with historical fuel and
  carbon prices and auction parameters, and compare the 2025 fleet, prices and auction results with
  outturn. ElecSim did this for 2013–18, although fitted in-sample [Kell2020]; Kell et al. back-cast
  AR4 to within 5 % [Kell2023]. This is not the operation back-cast of 2020–24 that was set aside; it
  extends item 16 from auctions to the fleet they produced [item 43].
* Fix the list of patterns and tolerances before tuning to them [Fagiolo2019].

**F21. The reported ranges are not uncertainty. (sharpened)**
* Seeds vary vintages, bid noise, siting, the order of moves and households. The world is the same in
  every seed. A range of ±£1bn over three seeds describes the model's noise, not confidence in £32bn.
* No sensitivity analysis has been run. The standard sequence is one factor at a time over wide ranges,
  then Morris screening, then Sobol indices on the factors that matter [tenBroeke2016]. The number of
  replications should come from the stability of the outputs, and distributions should be inspected for
  two modes (the deck's "multiple equilibria") rather than summarised as median and range [Lee2015].
* The model has several dozen constants that are assumed or tuned to one year: interconnector price
  levels and spread, the 0.45 interconnector de-rating, battery pots, the 15 % haircut, the 10 % PPA
  discount, CfD de-risking, the scarcity σ, retirement after two years, block sizes, build limits, and
  the government and household parameters. A register with a status for each (sourced, calibrated to
  what, assumed) and a range is the input to both the sensitivity analysis and any history matching
  [item 46].

## 7. Learning and LLM agents

**F22. Tabular Q-learning on annual rewards cannot learn what the roadmap asks of it. (new; lit)** A
stationary two-firm pricing game needs about 850,000 periods to converge [Calvano2020]. A run gives
about 25 rewards per firm in a market that changes every year. The one comparable study of learned
investment used policy gradients, 69 parallel environments and 16–32 GPU-hours per run in a stylised
market, and still has no equilibrium guarantee [GonzalezRuiz2025]. Options: (a) learn offer mark-ups
only, in a fast stage game with the fleet frozen, where thousands of steps are cheap; (b) keep the
table but call it an adaptive heuristic in the Roth–Erev tradition and report parameter sweeps; (c) a
surrogate environment for investment.

**F23. "Check for tacit collusion" needs benchmarks first. (new; lit)** Prices above marginal cost from
Q-learners are attributed in the literature to imperfect exploration, asynchronous updating and matched
hyperparameters as much as to strategy [denBoer2022, Abada2023, Asker2024, Banchio2022]. In a
uniform-price market pivotal firms raise prices unilaterally. Before the word is used: a one-shot Nash
and a monopoly benchmark, forced-deviation tests, an exploration sweep and a synchronous-update control.

**F24. LLM agents: three premises to change. (new; lit)**
* *Model size is not bounded rationality.* Models under 40B parameters "were not reliably able to
  outperform random guessing" on economic rationality [Raman2024]; "model scale alone does not determine
  performance" [Jia2025]. Small models are noisier and differently wrong, not human-like. Treat model
  identity as a nuisance factor to average over, and use explicit behavioural parameters as the lever.
* *Temperature 0 and a seed do not make runs reproducible*; batch size and hardware change outputs
  [Atil2024, Yuan2025]. The response cache is the only guarantee, so pin the weight hash, quantisation
  and runtime, and report agreement over repeated uncached calls.
* *The LLM knows GB's history and the textbook answer.* Test with a fictional-country variant and with
  parameters that contradict GB history [Ludwig2024, Gui2023].
* Also: gate every model on single-firm tasks with a known optimum before any run [Fish2024]; permute
  option order and paraphrase prompts and report how often the choice flips [Zheng2024, Sclar2024];
  measure the correlation of decisions across firms that share weights [Ross2026]; report the LLM arm
  as exploratory, with fallback rates [Larooij2025].
* The division of labour in item 25 (the model computes, the LLM chooses among options) matches the
  evidence on numeracy and should stay.

**F25. Build the behavioural arm first, and note what all arms share. (new)** A hurdle-rate premium,
payback rules, limited foresight and imitation have empirical support for firms [Jagannathan2011,
Barazza2020, Masini2013]; LLMs as proxies for firms have none. This arm is cheap and gives the learning
agents something meaningful to be compared with [item 55]. All arms receive the same price projection
through `Observation.market`, which is the right design [Tao2021], but that projection is the perfect
one of F8, so the comparison inherits it.

## 8. The platform

**F26. Mesa is a dependency in name only. (new; code)** `GBMarketModel` and `GenCo` inherit from Mesa
classes with a fallback shim; the model drives every phase itself, households are arrays, there is no
AgentSet, DataCollector or batch runner, and a workaround is needed for a name clash with Mesa 3.5
(`scenario`). Either use it (agents as agents, `DataCollector`, `batch_run`, a dashboard) or drop it and
say so. For market clearing, ASSUME is the nearer framework and has PyPSA-based zonal clearing; building
on it was not assessed here.

**F27. Parameters and scenarios live in code. (new; code)** Every reusable model inspected keeps inputs
in YAML or TOML plus CSV with defaults and overrides, and the strongest validate them against a schema
(literature review 8.2). Here a mistyped scenario key is ignored silently (`scenario.get`), calibration
constants are module globals in `model.py` and `config.py`, and a new user must edit Python to change
a cost [item 47].

**F28. The bundled profile is under a non-commercial licence. (new; lit)** `profiles_2024.csv` is
extracted from ESPENI, whose current versions are CC BY-NC 4.0 [ESPENI]; the repository is MIT. Elexon
and NESO data are redistributable with attribution; Modo and LCP figures are commercial products. The
data READMEs say only that sources "carry their own licences". Rebuild the profile from Elexon and NESO
data, or fetch ESPENI at build time and label it, and add a table of every dataset with its version,
source and licence [item 48]. To be confirmed by the maintainer with the ESPENI authors.

**F29. No releases, citation or contribution path. (new)** No tagged release, changelog, DOI,
`CITATION.cff`, `CONTRIBUTING`, hosted documentation or API reference. The README is also the build
agent's task list and a results page. FAIR4RS asks for an identifier per version and provenance; JOSS
asks for six months of public history, evidence of research use and community guidelines [Barker2022,
JOSS]. Among investment ABMs none has tagged releases, so this is also where the repository can lead
[item 49].

**F30. No protocol description. (new)** `model_design.md` is not structured by ODD, gives no rationale
for the decision models and has no table from description to code. ODD+D asks for the theoretical and
empirical basis of each decision rule, which is the content of this review's sections 4 and 6. A TRACE
record would hold the calibration, verification and corroboration steps as they are done [item 50].

**F31. Results have no provenance. (known)** Code review, section C: no git hash or arguments in the
outputs, results committed by hand, stale figures. Stamp every output and build results with one
command [item 49].

**F32. Code written by AI agents needs verification a reader can see. (new; lit)** The code review
found eleven bugs that biased published results, after the results were in the README. JOSS requires
disclosure of AI use and an affirmation that people "reviewed, modified, and validated all AI-generated
content" [JOSS]; periodic AI reviews do not meet it. What would: tests written by a person before the
code [Bridgeford2025]; analytical benchmarks (a merit order checked by hand; the convergence test at a
tight tolerance); invariants asserted in every run (energy balance; payments equal receipts across
firms, levy and consumers; capacity stock and flow); mutation testing, since the code review found tests
that cannot fail; and one independent replication of a headline number [item 51].

**F33. Structure and scope. (new; code)** `GBMarketModel` is 940 lines holding the market, settlement,
both auctions, forecasts and the network stage. Firms' decisions are pluggable; market designs are not,
so a zonal market, a reliability option or a deemed CfD means editing the model class. A platform for
market-design research needs mechanisms to be modules as decision makers already are. A run takes
about 6 minutes and a plan with its evaluations about 7, which is too slow for the sensitivity analysis
of F21 (item 8). On scope: users
value a model they can understand over added features [literature review 8.2, Süsser et al.]. The
roadmap has 39 items and one validated year.

## 9. Proposed order of work

A recommendation; the priorities are the maintainer's. New items are numbered 40–55 in the
[README](../README.md#status--roadmap).

1. **Make the benchmark robust** before more agent features: separate wind profiles [41], the yardstick
   table [40], equal options and the near-optimal band [20, 10, 9], weather years [17], the
   rolling-horizon planner [11].
2. **Close the residual** in steps to under 1 % [42], with the projection rule and order of moves [45].
3. **Calibrate to the auctions and hindcast** [44, 16, 43], with the pattern list fixed first.
4. **Uncertain futures and risk** [35, 37], then the ladder in all orders [21], with the equilibrium
   cross-check [54].
5. **Uncertainty and sensitivity** [46], which needs the speed-up [8].
6. **Platform**, in parallel from now because it does not change results: licences [48] first, then
   inputs as data [47], verification [51], releases and documentation [49, 50], Mesa [53].
7. **Learning agents last**: the behavioural arm [55], then Q-learning and LLM agents as amended by
   F22–F25.

A statement of what the model can and cannot be used for (TRACE's domain of applicability) belongs at
the top of the README once step 1 is done.
