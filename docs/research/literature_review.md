# Literature & framework survey: agent-based models of electricity markets

*Sections 1–3: time-boxed review (workshop prep). Claims are taken from the cited project pages/papers;
ratings in the [capability matrix](capability_matrix.md) are the author's reading of the documentation
and should be checked against each code base before being quoted.*

*Sections 4–8: second review, 27 November 2026. It looks at methods rather than features: how other
models make the decisions this model makes, what is known about comparing an optimum with a simulated
market, what GB evidence exists to test the model against, and what a reusable research model needs.
What it means for this model is in the [foundations review](../review_2026-11_foundations.md). Each
source in the second reference list is marked ● (opened and read for this review), ◐ (abstract only) or
○ (search result only; check before quoting).*

## 1. Why ABM for the GB system?
Optimisation models (PyPSA-GB, ESO/NESO FES tools) answer *"what is least-cost?"*. ABMs answer
*"what will heterogeneous actors actually do under this market design and policy?"* — investment cycles,
imperfect expectations, missing money, strategic bidding, adoption dynamics and feedbacks between sectors.
EMLab-Generation's authors frame this explicitly as exploring "heterogeneity of actors, consequences of
imperfect expectations and investment behaviour outside of ideal conditions" [EMLab].

## 2. Frameworks reviewed

| Model | Owner / language | Focus | Key features | Source |
|---|---|---|---|---|
| **AMIRIS** | DLR, Java on FAME | Operation & policy | Endogenous prices from strategic bidding of prototyped actors; agent classes: plant operators, traders, marketplaces, policy providers, demand, storage; support-scheme instruments; open source | [AMIRIS-home], [AMIRIS-JOSS], [Helmholtz-RSD] |
| **EMLab-Generation** | TU Delft, Java/AgentSpring | Long-term investment | Two interconnected markets (e.g. UK vs Continent); power companies bid and invest on NPV; load-duration-curve segments; CO2 policy; capacity mechanisms & strategic reserve extensions | [EMLab], [EMLab-GH], [Bhagwat-CM] |
| **ASSUME** | Open-source Python | Operation, learning | Multi-agent deep RL bidding agents; modular market design toolbox | [ASSUME-SoftwareX], [ASSUME-docs] |
| **PowerACE** | KIT, Java | Day-ahead + investment | Hourly European day-ahead market, multi-year, endogenous conventional & storage investment, advanced price forecasting | [PowerACE], [PowerACE-forecast] |
| **ElecSim** | A. Kell, Python | Long-term UK investment | Open source, Monte-Carlo, set up with UK data, policy (carbon tax) optimisation | [ElecSim-GH], [ElecSim-arXiv], [Kell-carbon] |
| **Kell et al. 2021** | Applied Energy | Storage investment | ABM of investment in generation *and storage* in a liberalised market to 2050 | [Kell-storage] |
| **AMES** | Iowa State, Java/Python | Nodal (US RTO) | Day-ahead & real-time markets on a transmission grid, LMP congestion pricing, learning traders | [AMES], [AMES-GH] |
| **Mesa** | Python library | Generic ABM | Agents, schedulers/AgentSets, data collection, visualisation; Apache-2 | [Mesa], [Mesa-docs] |
| **CNZ domestic-heating-abm** | Centre for Net Zero, Python | Heat decarbonisation | Household agents (property type, age, tenure, off-gas-grid) choosing heating systems; policy interventions for HP targets | [CNZ-ABM], [CNZ-GH], [CNZ-BEIS] |
| **Heat-pump policy ABM (2025)** | Cardiff/Sustainable Futures | HP uptake UK | BAU projects 8.7 m HP households (30.8%) by 2050; grant sensitivity | [HP-ABM-2025] |
| **Frontier Economics heat-market ABM** | Consultancy | Heat market design | Agent architecture for a heat market (e.g. energy-plan business models) | [Frontier-heat] |
| **GB EV ABM (2026)** | Academic | EV driving & charging | Validated GB ABM of EV driving/charging with psychological & financial preferences | [EV-GB-ABM], [EV-Imperial], [EV-local] |
| **Hydrogen transition ABMs** | Argonne | H2 vehicles/infrastructure | Co-evolution of H2 supply chain and vehicle adoption | [ANL-H2], [ANL-H2-2] |
| **UK CM & balancing ABM** | Academic | GB capacity mechanism | ABM of interlinks between Capacity Mechanism and Balancing Market (CCGTs etc.) | [UK-CM-BM] |
| **MARL long-term market design (2025)** | arXiv | Investment under market design | RL GENCO agents in long-term market environment | [MARL-LT] |
| **PyPSA-GB** (comparator, not ABM) | A. Lyden et al., Python | GB network optimisation | ETYS network (~2,400 buses), reduced 32-bus and zonal versions; two-stage wholesale + balancing mechanism with CfD/RO/merchant-aware bids; FES & CP30 scenarios; hydrogen, storage, interconnectors | [PyPSA-GB] |

## 3. Observations
1. **Electricity-only is the norm.** AMIRIS, EMLab, ASSUME, PowerACE, ElecSim and AMES are electricity
   market models. Heat, EV and hydrogen behaviour live in *separate* ABMs (CNZ, EV-GB, Argonne) with
   exogenous electricity prices — the coupling is generally missing.
2. **Investment vs operation split.** AMIRIS/ASSUME are strong on short-term bidding; EMLab/ElecSim
   on long-term investment; PowerACE covers both at European scale.
3. **Networks are weak in ABMs.** Except AMES (US nodal) most ABMs are copperplate/zonal. GB's defining
   operational problem — Scotland–England boundary constraints and £bn balancing costs — needs a
   network stage, which PyPSA-GB already provides.
4. **GB-specific policy instruments** (CfD allocation rounds with pots, T-4/T-1 Capacity Market with sloping
   demand curve, RO, UK ETS + Carbon Price Support) are only partially represented (ElecSim/EMLab for
   carbon & capacity mechanisms; AMIRIS for support schemes but German-centric).
5. **Mesa is the natural Python substrate** to link to PyPSA (both Python), unlike Java-based AMIRIS/EMLab.

## 4. How other models decide to invest

### 4.1 The investment rule, side by side

| Model | Price forecast behind the decision | What is valued | Uncertainty and risk | Order of moves |
|---|---|---|---|---|
| **ukabm** `rules` | The model re-clears year t+3 at 8,760 h with the committed pipeline, on the true fuel, carbon and demand paths | One year's margin, held flat over the plant's life | None: the world is deterministic. A flat haircut on the margin; firms differ only in their carbon belief | Random order each year. The first firm in the order with a positive NPV builds one block, the forecast is re-run and the order restarts (up to 6 builds a year) |
| **ukabm** `expectations` | As above plus t+8 and t+13, with wind and solar extended at their recent build rate and peakers added to keep the system adequate | Margin path interpolated over the life | As above | As above (40 a year in the convergence test) |
| EMLab-Generation [Chappin2017, deVries2015] | Merit order on a forecast load-duration curve; demand, fuel and CO2 from regressions on history; fleet = existing + under construction − end of life | One reference year 6–8 years ahead (differs by agent), taken as typical of the whole life | Stochastic fuel prices; horizons and interest rates differ by agent; a risk extension gave less investment, mostly in gas | Re-drawn at random every year; rounds repeat until nobody invests |
| EMLabpy + AMIRIS [SanchezJimenez2024] | AMIRIS clears an hourly market 4 years ahead with all known plants; a 1 MW test unit per technology; build the best, re-clear, repeat | Not stated in what was read | Invests on one median weather year; operates over 40 random weather years | One investor. "No equilibrium is guaranteed"; decisions "do not account for subsequent investments" |
| PowerACE [Fraunholz2021] | Hourly prices for several future years from the duals of a time-coupled dispatch LP | NPV as an annuity | Perfect foresight of demand, renewables, fuel and carbon; no risk aversion (a stated limitation) | Investments are added and removed iteratively until a Nash equilibrium; investors randomised, then iterated |
| ElecSim [Kell2019, Kell2020] | 2019: each firm fits regressions to history and re-runs the market N years ahead. 2020: an exogenous linear expected price-duration curve ten years ahead, tuned by genetic algorithm | NPV over the plant life | WACC sampled; firms use different historical windows; fuel-price noise | Not found |
| EMIS-AS, NREL [Anwar2022, Frew2023] | Each firm solves its own expansion model (20 representative days, 10-year rolling horizon), then values each project in each scenario | Remaining life | Expected utility with firm-specific risk aversion; beliefs on load growth updated by Kalman filter | Firms decide independently |
| BRAIN-Energy, UCL [Barazza2020] | The actor's own expectations of demand, fuel and technology cost; foresight 5–25 years by actor type | NPV over n years, then highest return at or above the cost of capital | Heterogeneous expectations; imitation of the fastest-growing rival | Not found |
| MUSE, Imperial [MUSE] | No information beyond the investment year; prices are levelised costs iterated to a partial equilibrium (not marginal-price clearing) | Agent objective: NPV, LCOE or custom | Limited foresight by design | Not applicable |
| DDM, LCP for DESNZ [DDM2012, DDMreview] | Simulated revenues, looking ahead up to 15 years; perfect foresight or stated beliefs (e.g. a flat carbon price) | Simulated IRR of an example plant per technology against a technology hurdle rate | Through the hurdle rate: debt × gearing + equity × (1 − gearing) + technology premium + policy adjustment | The plant that clears its hurdle by most is built; repeat until none clears or a build limit binds |
| MARL, Gonzalez-Ruiz et al. [GonzalezRuiz2025] | Learned (independent PPO); bidding fixed at marginal cost, only investment learned | Step-wise NPV reward | Emerges from learning; no equilibrium guarantee | Simultaneous |

| Model | Finance | Time resolution and weather | Retirement | Validation its authors report |
|---|---|---|---|---|
| **ukabm** | Fixed WACC per firm, an annual capex budget; no debt, cash balance or bankruptcy | Hourly, one weather year (2024) | Two loss-making years without a CM agreement, or end of life | 2025 operation against outturn (several parameters tuned to the same year); no investment back-cast |
| EMLab-Generation | ~30 % down-payment from cash, the rest as debt annuities; separate equity and loan rates | 20-segment load-duration curve, yearly | End of technical life, or no operating profit for several years | Sensitivity analyses; historical price comparison |
| EMLabpy + AMIRIS | Debt ratio, equity down-payments in construction, WACC 7 % | Hourly; 40 weather years (1980–2019) in random sequence | Technical life only | A perfect-foresight agent with fixed profiles recovers its costs at about the WACC |
| PowerACE | Not found | 8,760 h, several countries | Exogenous | Correlation 0.71 with 2001 EEX prices [Sensfuss2001] |
| ElecSim | Upfront-capital share; loans and dividends settled yearly | 20 segments, then 8 representative days | End of operating period | 2018 price-duration curve: MAE £4/MWh. Generation mix 2013–18: MAE 0.6–9 points by technology, obtained by tuning the price curve investors expect (in-sample) |
| EMIS-AS | Capital-cost multipliers, risk premia, queue fees; capex sunk at construction | Day-ahead unit commitment + 5-minute dispatch | Negative expected utility *and* negative expected profit next year *and* losses in the two previous years | Against a planning model only |
| BRAIN-Energy | At least 20 % own cash, the rest debt at the actor's WACC | Yearly; average day and night demand plus a peak factor | An actor-specific run of loss years (7–10 for municipal utilities) | Calibrated from 2012 against "a few years of historical data" |
| AMIRIS (operation only) [AMIRIS-JOSS, Nitsch2021] | — | Hourly; a year of Germany runs in ~20 s | — | Austria 2019: mean 40.20 vs 40.06 EUR/MWh, MAE 8.06, correlation 0.64; no negative prices, lows too high and highs too low |
| DDM | Hurdle rates by technology and investor class | Half-hourly sample days × three wind levels | Economic | Peer review [DDMreview] |

ASSUME simulates short-term markets with deep-RL bidders and has no long-term investment [ASSUME-repo].

### 4.2 What these models' authors and reviewers report

1. **The price projection is the main risk.** Tao et al. [Tao2021] benchmark a core investment ABM
   against the long-run equilibrium of a generation expansion model. Results "vary enormously" with the
   projection method and the look-ahead horizon. Re-clearing a future year with only the known pipeline
   (their "myopic agents") assumes no later entry, so longer look-ahead over-builds, mostly peakers. Only
   a projection that fills in cost-minimising future investment "systematically approximates" the
   equilibrium. Fixes such as forced myopia, investment caps or price adjustments "reduce transparency".
2. **Investors carry a model inside the model.** "This inherently limits what can be done"
   [Chappin2017]. PowerACE found that the forecast method "clearly" changes simulated prices and that a
   naive forecast gives "no stable outcome" [Fraunholz2021].
3. **Order of moves.** EMLab re-draws the order every year and loops until nobody invests; PowerACE
   iterates to a Nash equilibrium; Tao sizes units so that the first mover has no advantage; the DDM
   peer review notes that utilities "always pre-empt" merchants on their lower WACC [DDMreview].
4. **The weather year investors plan on is first order.** With stochastic weather, cost-recovery
   variability more than triples and price variability rises more than tenfold [SanchezJimenez2024].
5. **Load-duration curves were abandoned.** They overstate renewables and cannot represent storage
   [Kell2020, Chappin2017]. Hourly resolution is where the field has moved.
6. **Investment cycles may be artefacts.** BRAIN-Energy and ElecSim report them as findings; Tao shows
   that the projection method alone generates them.
7. **Retirement rules elsewhere are more patient** than two loss-making years: EMIS-AS needs three
   conditions, BRAIN-Energy up to ten years of losses.
8. **A model should recover the equilibrium in a stationary world** [Tao2021]; EMLabpy's
   perfect-foresight check is the same idea [SanchezJimenez2024].
9. **Validation is the field's weak point.** Price back-tests reach correlations of 0.64–0.81. The only
   investment back-cast found (ElecSim, GB 2013–18) is fitted in-sample. Reviews say the same in
   different words: "the learning algorithm has considerable impact on the results" and behaviour such
   as investment needs better empirical data [Sensfuss2007]; modelling choices "appear arbitrary" and
   ABMs are one-offs "lacking clearly validated conventions" [Chappin2017]; Tesfatsion separates input,
   process, descriptive-output and predictive-output validation [Tesfatsion].
10. **Reusable models are the operational ones.** AMIRIS and ASSUME have a software paper, a package,
    versioned DOIs, examples and CI. No investment model reviewed (EMLab, ElecSim, EMIS-AS, EMLabpy,
    PowerACE) has tagged releases.

## 5. Comparing an optimum with a simulated market

**Direct comparisons.**
* Torralba-Díaz et al. [Torralba2020] define the *efficiency gap* as the difference between a
  theoretically optimal system and the real one. An optimisation model (E2M2) builds the fleet and
  AMIRIS dispatches it; only variable costs are compared. They first harmonise the two models to a
  residual of 0.0001 % of system cost. Gaps: 0.03 % (storage market power), 0.11 % (forecast errors),
  0.13 % (market premium), and 0.12 / 0.8 / 4.1 % at 40 / 60 / 80 % variable renewables. Investment is
  left to future work. A follow-up couples the models iteratively to find "realizable cost-optimal
  systems" [Torralba2024].
* Jonson et al. [Jonson2020] compare a stylised investment ABM with a surplus-maximising optimisation
  at the same 8 % rate. Limited foresight makes the agents under-invest in wind for 25 years, then
  over-invest; of foresight and discount rate, "it is the second feature that has the largest effect".
* Gonzalez-Ruiz et al. [GonzalezRuiz2025] train reinforcement-learning investors (merchant, CfD and
  capacity market; 8–32 firms; 2020–2040) and compare the 2040 mix with a PyPSA plan. Learned returns
  were 10.6–15 % against an 8 % discount rate.
* Trutnevyte [Trutnevyte2016]: the real UK electricity transition 1990–2014 deviated 9–23 % in
  cumulative system cost from the cost-optimal scenario.
* Kraan et al. [Kraan2018] and Barazza & Strachan [Barazza2020] show investment cycles and wide pathway
  spread from heterogeneous, boundedly rational investors; neither measures a cost gap. No paper was
  found that splits an investment gap against an optimum by source for a real market's instruments.

**Equilibrium models are the rigorous alternative for risk.** Stochastic equilibrium models with
CVaR investors compare complete with incomplete risk trading [Ehrenmann2011, deMaere2017, Hoschle2018].
CfDs, reliability options and capacity markets appear as risk-trading instruments. With incomplete risk
trading, capacity mechanisms tilt the mix towards plant with low fixed and high operating cost
[Mays2019]; missing risk markets shift investment from wind, solar and storage to gas and reduce
welfare [Dimanchev2024a, Makrides2025]; subsidies can then beat carbon pricing [Dimanchev2024b]. In this
literature the benchmark for risk-averse investors is the complete-market risk-averse plan, and a risk
premium under incomplete markets is a real cost, not a transfer.

**Foresight.** A 4-year myopic horizon with deployment limits costs Europe about 23 % more than perfect
foresight [Mannhardt2024]. For GB, myopically waiting for a technology that never arrives raises
cumulative cost by 61 % [Heuberger2018]. Foresight alone can produce a gap larger than this model's
headline.

**Discount rates and the cost of capital.**
* At USD 50/t CO2 a 3 % WACC gives about 40 % renewables in the optimal mix and 15 % gives almost none
  [Hirth2016]; about 40 % of the fall in German onshore wind cost came from cheaper finance [Egli2018].
* DESNZ's hurdle rates (pre-tax real): see section 6.1. They are 7.6–8.9 % for the main technologies,
  against a social discount rate of 3.5 %.
* The Committee on Climate Change held that risk transferred to the private sector "is a genuine
  resource cost" and used a private rate for power generation with a social-rate sensitivity [CCC2011].
* HM Treasury cut the Green Book rate from 3.5 % to 3.0 % for years 1–30 in October 2026; the 3.0 % is
  a 2 % risk-free rate plus a 1 % systematic risk premium [HMT2026].

**The optimum is uncertain by about as much as the gap.**
* A cost slack of 0.5 % already allows a wide range of investments [Neumann2021]; the near-optimal
  region is "fairly flat" [Pedersen2021].
* Designs optimised on each of 62 single weather years differ by about ±10 % in total system cost
  [Gotske2024]. For GB, single-year designs risk inadequacy [Zeyringer2018]. Designs robust across 41
  weather years emit up to 50 % less CO2 than the cost optimum [Grochowicz2023].
* At high renewable shares temporal detail matters more than operational constraints [Poncelet2016].

**Attribution.** One-at-a-time analysis is unjustified unless the model is linear [Saltelli2010]. Green
& Staffell use Shapley values to attribute GB decarbonisation to its drivers [Green2021]. Removing one
distortion while others remain can reduce welfare [Lipsey1956], so a rung of a ladder can legitimately
be negative.

**Adequacy.** The 3 h LOLE standard was derived from a VoLL of £16,950/MWh and a cost of new entry of
£47.18/kW/yr (LOLE 2.78 h) [DECC2013]. Against about £6,000/MWh paid in balancing, the difference is
"missing money" of about £33/kW/yr [Newbery2016]. Optimal procurement balances expected energy unserved
against capacity cost, which is equivalent to a reliability standard [Zachary2022].

**Carbon.** Appraisal values are £260 (2025), £280 (2030), £326 (2040) and £378/tCO2e (2050) in 2020
prices, with a ±50 % range; they "differ from carbon prices, which represent the observed price of
carbon in a relevant market" [BEIS2021].

## 6. GB evidence to test the model against

### 6.1 How government and NESO model investment and adequacy

* **DESNZ uses a simulation model, not an optimisation.** The Dynamic Dispatch Model (section 4.1) is a
  "profit-maximisation model" with typical 25-year runs [CP2030]. DESNZ states that the DDM "does not
  use levelised cost estimates directly" and that "levelised costs are not strike prices" [GenCosts2023].
  Peer-review caveats: interconnectors are not price-responsive; unsuited to transmission or
  ancillary-service questions [DDMreview].
* **Hurdle rates, pre-tax real, %:**

  | Source | Solar | Onshore | Offshore | CCGT | Other |
  |---|---|---|---|---|---|
  | Europe Economics 2018, with CfD [EE2018] | 5.0 | 5.2 | 6.3 | 7.5 | OCGT 7.1, Li-ion 7.3, DSR 7.5 |
  | Europe Economics 2018, merchant | 5.8 | 6.0 | 7.6 | — | |
  | CEPA 2025 for DESNZ [CEPA2025] | 7.6 | 7.6 | 8.9 | 8.9 | batteries 8.9, floating wind 11.4, nuclear (RAB) 7.6, CCUS and hydrogen power 8.9–10.1 |

  A CfD lowered the rate by 0.8 points (solar, onshore) and 1.3 points (offshore) in 2018; CEPA 2025
  puts the merchant uplift at 1.5 points (survey range 1.5–3) and the uncertainty at ±1.1–1.7 points.
  Rates rose by 1–2 points between Generation Costs 2023 and 2025 [GenCosts2025]. Official rates vary
  by technology, not by investor type.
* **NESO.** FES uses PLEXOS (a mixed-integer capacity expansion plus a production model), checked
  against 3–6 historic weather years [FES2025]. Adequacy uses 34 weather years × 100 outage patterns =
  3,400 simulations per portfolio; February 1986 dominates the risk [NESO-adequacy]. The CM target
  applies the 3 h standard "under a cautious Least Worst Regret", so procured LOLE is "substantially
  less than 3 hours"; a 0.4 GW risk premium was added in 2025 and 3.9 GW of non-delivery is assumed.
  The operator "bears none of the costs of over-procurement"; VoLL and the cost of new entry were "set
  over 10 years ago" [PTE2025]. Wind, solar and storage are de-rated by equivalent firm capacity.
* **Zonal pricing studies.** FTI for Ofgem: nodal consumer benefit £28–51bn over 2025–40, with no WACC
  change in the base case; a 0–50 bp WACC sensitivity costs £7.45bn [FTI2023]. Other studies report
  that a WACC rise of 0.3–0.9 points turns the benefit into a cost (○, not opened). Franken, Lyden &
  Friedrich find a GB zonal welfare gain of £380–770m/yr with an open 6-zone model calibrated on
  2022–24 [Franken2025]. The cost of capital decides these results as much as dispatch does.

### 6.2 CfD allocation rounds

Strike prices in £/MWh, 2012 prices:

| Round | Offshore wind | Onshore wind / solar | Notes |
|---|---|---|---|
| AR3 (2019) ○ | 39.65 | | |
| AR4 (2022) ○ | 37.35 (6.99 GW) | 42.47 / 45.99 | Norfolk Boreas (1.4 GW) later halted |
| AR5 (2023) [AR5] | no bids (cap £44) | 52.29 (1.48 GW) / 47.00 (1.93 GW) | |
| AR6 (2024) [AR6] | 58.87 (3.36 GW); re-bids 54.23 (1.58 GW) | 50.90 (0.99 GW) / 50.07 (3.29 GW) | offshore cap raised 66 % to £73; Hornsea 4 (2.4 GW) cancelled May 2025 |
| AR7 (Jan 2026) [AR7] | 65.45 = £91.20 in 2024 prices (6.87 GW); Scotland 64.23 (1.38 GW) | AR7a: 51.85 / 46.82 [AR7a] | cap £81; 24.8 GW bid for 8.2 GW; budget set after seeing bids (£900m → £1,790m); term 15 → 20 years [CarbonBrief2026] |

AR1 and AR2 prices were not retrieved. Rounds were irregular (2015, 2017, 2019, 2022, then yearly).
Onshore wind and solar compete in one pot.

What determines bids:
* Kell et al. back-cast AR4 with a stochastic bidder simulation: median £39.23 against £37.35 actual,
  winners predicted correctly; the best strategy is bid shading, and observed bids sat at a risk-averse
  floor [Kell2023]. This is the closest existing GB auction back-cast.
* The one-shot design with weak non-delivery penalties invites speculative bidding [Welisch2020 ◐].
* Bids embed expected merchant revenue after the contract [Jansen2020 ○]; the CfD's role is risk
  management and financing [Beiter2023 ○].
* 3.8 GW of AR4 and AR6 offshore awards were abandoned: awarded capacity is not built capacity.

### 6.3 Capacity Market

T-4 clearing prices, £/kW/yr, by auction year [EMRS, EnergyUK2026]:

| 2014 | 2015 | 2016 | 2017 | 2019 (T-3) | 2019 | 2020 | 2021 | 2022 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 19.40 | 18.00 | 22.50 | 8.40 | 6.44 | 15.97 | 18.00 | 30.59 | 63.00 | 65 ○ | 60 ○ | 27.10 |

* The auction is a descending clock from the £75/kW cap. No T-4 auction in the table cleared at the cap
  (range £6–65).
* T-4 for 2029/30 (March 2026): 44 GW entered against a 39.4 GW target; gas took 59 %; no new-build gas
  cleared; of 12.4 GW of refurbishing plant only 1.6 GW won three-year agreements [EnergyUK2026].
* Early auctions cleared near £20 against the £40–50 thought necessary for a new CCGT; new capacity
  came from small engines, storage and demand response [Grubb2018 ○]. The first auction gave
  interconnectors no contribution and over-procured [Newbery2016].
* Batteries are de-rated by duration: 17.89 % (0.5 h) to 96.11 % (4 h and over); 9.5 GW of battery
  connection capacity became 3.0 GW de-rated in 2029/30 (○).
* Models: EMLab [Bhagwat-CM], a dynamic investment model [Hach2016 ○], system dynamics [Franco2015 ○].

### 6.4 Stylised facts a GB model should reproduce

| Pattern | Evidence | Tag |
|---|---|---|
| Negative-price hours | 19–29 (2022), 86–107 (2023), 139–176 (2024), 149–190 (2025) | ○ |
| Capture-price discount | wind 3.2 % (summer 2019) → 16.2 % (summer 2025); solar captured 85 % of baseload in summer 2025 | ○ |
| Battery revenue falls as the fleet grows | £123k/MW/yr (2021), £51k (2023), ~£70k (2025); fleet ~4 GW (mid-2024) → 6.8–7.5 GW (end-2025) | ○ |
| Thermal constraint cost | ~£2bn (2025/26); projected £3.9bn (2027) and £6.8–7.7bn (2030), ~£2bn in 2031 | ● [NESO-constraints], check the document's status before quoting |
| Heat-pump installations | ~37k (2023), 58k (2024), over 60k (2025), against a target of 600k a year; applications more than tripled in the first week after the grant rose from £5,000 to £7,500 (Oct 2023) | ○ |
| CfD and CM auction outcomes | sections 6.2 and 6.3 | |
| Fleet history 2010–2025 | coal exit, gas build, offshore wind growth (DUKES, REPD) | not retrieved |

### 6.5 Open GB models

PyPSA-GB (MIT; validated against 2020 outturn) [PyPSA-GB]; the 6-zone market model of [Franken2025];
ElecSim (section 4); BRAIN-Energy (code availability not confirmed); highRES-GB (GAMS; public
repository, licence not confirmed, ○). UK TIMES and ESME are not openly licensed; the FTI, AFRY, LCP and
Aurora models are closed.

### 6.6 Heat pumps and the gas network

* Cost-only choice gives "much higher" uptake than observed, so non-monetary factors and discounting
  dominate [Frontier-heat]. The Cardiff model (logit plus utility, calibrated to survey and historic
  uptake) projects 8.7m homes by 2050 under business as usual [HP-ABM-2025].
* The Centre for Net Zero model's choice rule is documented in its report, not its README [CNZ-GH]; not
  retrieved.
* Gas network: 23m homes pay about £170 a year in network charges; Ofgem's no-action illustration
  reaches at least £2,000 a year in the 2040s (○). No peer-reviewed, quantified GB "death spiral" model
  was found.

## 7. Learning and LLM agents

**Reinforcement learning in electricity markets.**
* The state of the art is deep multi-agent RL on *short-term bidding*: ASSUME uses MATD3 with centralised
  critics; an episode is about a month of hourly steps, tens of thousands of rewards per agent. Its
  documentation states that convergence guarantees do not hold, that there is "no ground-truth error
  metric", and that high rewards can come from exploiting opponents or chance coordination
  [ASSUME-docs, Harder2023 ○].
* Learning *investment* is rare [Kell2022]. The closest analogue, [GonzalezRuiz2025], needed 69
  parallel environments on a GPU for 16–32 hours per run, in a stylised environment, with proxy
  validation only (a zero-profit "virtual plant", HHI, a cross-run league, a PyPSA plan).
* Validation against equilibrium is fragile: DDPG reaches an analytical Bertrand equilibrium only for
  some hyperparameters [Graf2024 ◐]; independent learners overfit to their co-players [Lanctot2017].
* Tabular Q-learning: Calvano et al.'s stationary two-firm pricing game needs about 850,000 periods to
  converge [Calvano2020]. An annual investment model gives about 25 rewards per firm per run.

**Algorithmic "collusion" is contested.** Q-learners reach supra-competitive prices [Calvano2020], but
only on timescales irrelevant to firms and with identical algorithms and matched hyperparameters
[denBoer2022]; in electricity storage, "seemingly collusive" outcomes stem from imperfect exploration
[Abada2023]; asynchronous updating gives near-monopoly prices and synchronous updating converges to
Nash [Asker2024 ○]; the mechanism is a statistical coupling of estimates [Banchio2022]. In electricity
markets, exploration level has a large effect [Aliabadi2017 ○], and profit above Nash is not sufficient
evidence [Seredynski2026 ◐]. In a uniform-price market with pivotal firms, unilateral market power
already puts prices above marginal cost [Kell2020b].

**LLM agents as economic decision makers.**
* Classic experiments are reproduced qualitatively [Horton2023 ◐, Aher2023 ◐], but LLMs are "neither
  entirely human-like nor entirely economicus-like" and inconsistent across settings [Ross2024 ◐].
* Validity threats, each documented: prompt-format sensitivity of up to 76 accuracy points that persists
  with model size [Sclar2024 ◐]; option-position and label bias across 20 models [Zheng2024 ◐]; changing
  one prompt variable shifts unstated ones [Gui2023 ◐]; training-data leakage [Ludwig2024 ◐];
  sycophancy [Sharma2023 ◐]; flattened heterogeneity [Wang2025 ◐]; correlated decisions across agents
  that share weights [Ross2026 ◐]; non-determinism at temperature 0, with batch size and GPU type
  changing greedy outputs [Atil2024 ◐, Yuan2025 ◐].
* Two near-equivalent prompt prefixes gave significantly different price levels in LLM pricing agents;
  the authors first screened each model on a monopoly task with a known answer [Fish2024].
* **Model size is not a bounded-rationality scale.** Models under 40B parameters "were not reliably
  able to outperform random guessing" on an economic-rationality benchmark, and 7–13B models scored
  below random [Raman2024]; "model scale alone does not determine performance" [Jia2025 ◐]; LLMs capture
  "only a partial form of human-like bounded rationality" [ZhengK2025 ◐].
* A review of 35 generative ABMs found 15 relying on subjective validation alone; LLMs "may
  exacerbate" ABM validation problems [Larooij2025].
* Electricity-specific work is thin: an LLM bidding benchmark with exact hourly references that
  "does not establish collusion" [WangS2026]; battery-dispatch agents that are near-optimal in simple
  settings and erratic in complex ones [Chen2025 ◐].

**Behavioural investment rules with empirical support.** Firms' hurdle rates sit about 5 points above
their WACC [Meier2007 ○]; CAPM explains about 10 % of the variation in hurdle rates and
option-to-wait proxies about 35 % [Jagannathan2011]; beliefs, short horizons and peer influence shape
renewable investment [Masini2013 ○]. BRAIN-Energy's limited foresight, heterogeneous expectations and
imitation are the working example [Barazza2020]. No evidence specific to energy investors was found
for heuristic switching or level-k reasoning.

**Evaluation standards.** Report interval estimates over many seeds [Agarwal2021 ◐]; test
exploitability and cross-play [Lanctot2017]; for LLMs report a performance interval over prompt formats
[Sclar2024] and agreement over repeated calls [Atil2024].

## 8. Standards for a reusable research model

### 8.1 Describing and validating an agent-based model

| Standard | What it asks |
|---|---|
| ODD, 2020 update [Grimm2020] | Seven elements (purpose and patterns; entities, state variables, scales; process overview and scheduling; design concepts; initialisation; input data; submodels), with the patterns used as evaluation criteria stated up front and a table mapping the description to code |
| ODD+D [Muller2013] | Adds the theoretical and empirical background of each decision model, and how individuals decide (rationality, uncertainty, adaptation, learning, sensing, prediction) |
| TRACE [Grimm2014, via Grimm2020 supplement] | A record of problem formulation and domain of applicability, data evaluation, conceptual model evaluation, implementation verification, output verification, model analysis and output corroboration. Corroboration uses data "not used, and preferably not even known" during development |
| Pattern-oriented modelling [Grimm2005 ○] | Several patterns at different scales constrain structure and parameters; one pattern cannot |
| Economic ABM validation [Fagiolo2019] | Separate input validation (behavioural rules, initial conditions, parameters) from output validation; fix the stylised facts in advance; run enough replications to estimate distributions |
| History matching [McCulloch2022] | Quantify ensemble variance, model discrepancy and observation error; discard parameter sets with implausibility above 3; iterate |
| Replications [Lee2015] | Choose the number of runs by the stability of the coefficient of variation across outputs; look at distributions for multimodality |
| Sensitivity analysis [tenBroeke2016, Thiele2014, Saltelli2019 ◐] | One factor at a time over wide ranges to find tipping points, then Morris screening, then Sobol indices; 42 % of highly cited analyses fail to explore the input space |

### 8.2 How reusable energy models are engineered

Inspected: PyPSA-Eur, PyPSA-GB, AMIRIS, ASSUME, Mesa, MUSE, otoole and Calliope. Common to nearly all:

1. Inputs outside the code (YAML or TOML plus CSV), with defaults and overrides, and a schema in the
   strongest cases (PyPSA-Eur ships `config.default.yaml` and `schema.default.json`).
2. Scenarios as data files, with a small bundled example that runs in one command.
3. A hosted documentation site: install, tutorials, input reference, API reference, release notes.
4. Tagged releases with a changelog and a DOI per version.
5. `CITATION.cff` and a software paper (JOSS, SoftwareX or a domain journal).
6. `CONTRIBUTING`, usually a code of conduct.
7. A licence statement per file or dataset (REUSE); PyPSA-Eur lists every dataset's version, source and
   licence in one table.
8. pre-commit, a linter and coverage reporting.
9. Back-tests shipped as runnable scenarios (AMIRIS: Germany 2015–19 and Austria 2019; PyPSA-GB:
   "Historical validation: 2020").
10. Results rebuilt by a workflow or command-line tool, not committed by hand.

EMLabpy has no maintained standalone repository and lives inside coupling workflows: the cautionary
case of an unpackaged model. With harmonised inputs, differences between modelling approaches were
small and differences of scope large [Gils2022 ○].

### 8.3 Research software and data licences

* **FAIR4RS** [Barker2022]: a persistent identifier per version, indexed metadata, a clear licence,
  detailed provenance, qualified references to dependencies.
* **JOSS** [JOSS]: an OSI licence file; at least six months of public history without development
  concentrated in a burst; evidence of research use; statement of need, install, examples, API
  documentation, CI tests, community guidelines; a tagged release and archive DOI; a mandatory AI-usage
  disclosure.
* **Data licences:**

  | Source | Licence | Consequence |
  |---|---|---|
  | ESPENI | v1.0.0 (2020) CC BY 4.0; current versions **CC BY-NC 4.0** [ESPENI] | A profile extracted from a recent version is non-commercial and cannot be redistributed under MIT |
  | Elexon BMRS | Own licence; commercial use and adaptation allowed with attribution [Elexon] | Redistributable with attribution |
  | NESO Open Data Licence | Based on OGL v3; attribution required; applies per dataset [NESO-licence] | Redistributable with attribution |
  | DUKES | OGL v3 | Redistributable with attribution |
  | LCCC | OGL (○) | Confirm per dataset |
  | Modo, LCP | Commercial products; not checked | Do not bundle derived values without permission |

### 8.4 Research code written with AI assistance

* JOSS requires authors to name the tools and where they were used, and to affirm that "human team
  members thoroughly reviewed, modified, and validated all AI-generated content" [JOSS]. Elsevier and
  Springer Nature require disclosure (○).
* "Ten simple rules for AI-assisted coding in science" [Bridgeford2025]: human-written behavioural tests
  before implementation; watch for tests edited to pass and tests that check nothing; "don't trust claims
  of success"; a regression test for every bug found; the researcher stays accountable.
* What a sceptical reviewer would ask for: disclosure; human-authored tests; analytical benchmarks
  (a merit order checked by hand, the limiting case in which the agents must reproduce the LP);
  conservation checks on every run (energy balance; money paid equals money received across agents,
  levy and consumers; capacity stock and flow); mutation testing to show the tests can fail; and an
  independent re-implementation or cross-model replication of the headline result. ASSUME ships
  loaders for AMIRIS and PyPSA scenarios, which makes it the cheapest cross-check [ASSUME-docs].

## References (sections 1–3)
- [AMIRIS-home] DLR, *AMIRIS*. https://dlr-ve.gitlab.io/esy/amiris/home/
- [AMIRIS-JOSS] Schimeczek et al. (2023) AMIRIS, *JOSS* 8(84) 5041. https://elib.dlr.de/194776/1/10.21105.joss.05041_AMIRIS.pdf
- [Helmholtz-RSD] https://helmholtz.software/software/amiris
- [EMLab] Chappin (2013) EMLab-Generation overview. https://emlab.tudelft.nl/generation/
- [EMLab-GH] https://github.com/EMLab/emlab-generation
- [Bhagwat-CM] Bhagwat et al., Cross-border effects of capacity mechanisms in interconnected power systems. https://www.researchgate.net/publication/315752173
- [ASSUME-SoftwareX] ASSUME (2025), *SoftwareX*. https://www.sciencedirect.com/science/article/pii/S2352711025001438
- [ASSUME-docs] https://assume.readthedocs.io/en/latest/learning.html
- [PowerACE] PowerACE – Agent-based electricity market model. https://www.researchgate.net/publication/379271153
- [PowerACE-forecast] Advanced price forecasting in agent-based electricity market simulation, *Applied Energy* (2021). https://www.sciencedirect.com/science/article/abs/pii/S0306261921002142
- [ElecSim-GH] https://github.com/alexanderkell/elecsim ; [ElecSim-arXiv] https://arxiv.org/abs/1911.01203 ; [Kell-carbon] https://arxiv.org/pdf/2006.01601
- [Kell-storage] Investing in generation and storage capacity in a liberalised electricity market: an agent based approach, *Applied Energy* (2021). https://www.sciencedirect.com/science/article/abs/pii/S0306261921003871
- [AMES] https://www2.econ.iastate.edu/tesfatsi/AMESMarketHome.htm ; [AMES-GH] https://github.com/ames-market/AMES-V5.0
- [Mesa] https://github.com/mesa/mesa ; [Mesa-docs] https://mesa.readthedocs.io/stable/
- [CNZ-ABM] https://www.centrefornetzero.org/technologies/agent-based-model ; [CNZ-GH] https://github.com/centrefornetzero/domestic-heating-abm ; [CNZ-BEIS] https://heatpumpingtechnologies.org/content/uploads/2022/11/05-beis--iea-heat-pump-research-conf-nov-2022.pdf ; https://www.centrefornetzero.org/papers/hitting-the-target-meeting-the-uk-s-heat-pump-targets
- [HP-ABM-2025] Agent-based modelling approach to explore efficacy of policies for heat pump uptake (2025). https://www.sciencedirect.com/science/article/pii/S266618882501161X
- [Frontier-heat] https://www.frontier-economics.com/media/t1qpocir/frontier-economics-agent-based-modelling-of-a-heat-market.pdf
- [EV-GB-ABM] https://www.sciencedirect.com/science/article/pii/S026427512600096X ; [EV-Imperial] https://spiral.imperial.ac.uk/server/api/core/bitstreams/dd9dd096-6813-479c-88b9-0edebd7df5ab/content ; [EV-local] https://www.sciencedirect.com/science/article/pii/S1877050921007833
- [ANL-H2] https://ceeesa.es.anl.gov/news/multiagent_hydrogen.html ; [ANL-H2-2] https://ieeexplore.ieee.org/iel5/9256/29392/01331110.pdf
- [UK-CM-BM] Balancing the UK electricity grid: interlinks between Capacity Mechanism and the Balancing Market. https://www.researchgate.net/publication/265627994
- [MARL-LT] https://arxiv.org/html/2512.17444
- [PyPSA-GB] https://github.com/andrewlyden/PyPSA-GB ; https://pypsa-gb.readthedocs.io

## References (sections 4–8, second review)

● opened and read for this review (full text, or the page or repository itself) · ◐ abstract only ·
○ search result only, check before quoting. Keys from the first list are reused where they apply.

**Investment and market ABMs**
- [Tao2021] ● Tao, Moncada, Poncelet & Delarue (2021). Review and analysis of investment decision making algorithms in long-term agent-based electric power system simulation models. *RSER* 136, 110405. Working paper: https://lirias.kuleuven.be/retrieve/593049
- [Chappin2017] ● Chappin, de Vries, Richstein, Bhagwat, Iychettira & Khan (2017). Simulating climate and energy policy with agent-based modelling: the Energy Modelling Laboratory (EMLab). *Environmental Modelling & Software* 96, 421–431. doi:10.1016/j.envsoft.2017.07.009
- [deVries2015] ● De Vries, Chappin & Richstein (2015). EMLab-Generation: an experimentation environment for electricity policy analysis, v1.2. https://emlab.tudelft.nl/generation/emlab-generation-report-1.2.pdf
- [SanchezJimenez2024] ● Sanchez Jimenez, Ribó-Pérez, Cvetkovic, Kochems, Schimeczek & de Vries (2024). Can an energy only market enable resource adequacy in a decarbonized power system? A co-simulation with two agent-based models. *Applied Energy* 360, 122695. doi:10.1016/j.apenergy.2024.122695
- [Fraunholz2021] ● Fraunholz (2021). Market design for the transition to renewable electricity systems. PhD dissertation, KIT (includes Fraunholz, Kraft, Keles & Fichtner 2021, *Applied Energy* 290, 116688). https://publikationen.bibliothek.kit.edu/1000133282/115247277
- [Sensfuss2001] ● Sensfuß & Genoese. Agent-based simulation of the German electricity markets: an analysis of the German spot market prices in the year 2001. Fraunhofer ISI.
- [Kell2019] ● Kell, Forshaw & McGough (2019). ElecSim: Monte-Carlo open-source agent-based model to inform policy for long-term electricity planning. ACM e-Energy 2019. https://arxiv.org/abs/1911.01203
- [Kell2020] ● Kell, Forshaw & McGough (2020). Long-term electricity market agent based model validation using genetic algorithm based optimization. ACM e-Energy 2020. https://arxiv.org/abs/2005.10346
- [Kell2020b] ◐ Kell, Forshaw & McGough (2020). Exploring market power using deep reinforcement learning for intelligent bidding strategies. IEEE BigData workshop. https://arxiv.org/abs/2011.04079
- [Kell2022] ● Kell, McGough & Forshaw (2022). Machine learning applications for electricity market agent-based models: a systematic literature review. https://arxiv.org/abs/2206.02196
- [Kell2023] ● Kell et al. (2023). Methodology to prepare for UK offshore wind Contract for Difference auctions. *Applied Energy* 336, 120844. https://strathprints.strath.ac.uk/84124/
- [Anwar2022] ◐ Anwar, Stephen, Dalvi, Frew, Ericson, Brown & O'Malley (2022). Modeling investment decisions from heterogeneous firms under imperfect information and risk in wholesale electricity markets. *Applied Energy* 306, 117908. doi:10.1016/j.apenergy.2021.117908
- [Frew2023] ● Frew, Anwar, Dalvi & Brooks (2023). The interaction of wholesale electricity market structures under futures with decarbonization policy goals: a complexity conundrum. https://www.osti.gov/servlets/purl/1969273 ; code https://github.com/NREL/EMISAgentSimulation.jl
- [Barazza2020] ● Barazza & Strachan (2020). The impact of heterogeneous market players with bounded-rationality on the electricity sector low-carbon transition. *Energy Policy* 138, 111274. https://discovery.ucl.ac.uk/10093351/
- [MUSE] ● MUSE documentation, https://muse-os.readthedocs.io ; code https://github.com/EnergySystemsModellingLab/MUSE_OS (Giarola et al. 2022, *Energy Strategy Reviews*, ○)
- [Nitsch2021] ● Nitsch, Schimeczek & Wehrle (2021). Back-testing the agent-based model AMIRIS for the Austrian day-ahead electricity market. doi:10.5281/zenodo.5726738
- [ASSUME-repo] ● https://github.com/assume-framework/assume
- [Harder2023] ○ Harder, Qussous & Weidlich (2023). Fit for purpose: modeling wholesale electricity markets realistically with multi-agent deep reinforcement learning. *Energy and AI*. doi:10.1016/j.egyai.2023.100295
- [GonzalezRuiz2025] ● Gonzalez-Ruiz, Rodriguez-Pardo, Savelli, Di Bella & Tavoni (2025). Assessing long-term electricity market design for ambitious decarbonization targets using multi-agent reinforcement learning. https://arxiv.org/abs/2512.17444 (= [MARL-LT])
- [Kraan2018] ◐ Kraan, Kramer & Nikolic (2018). Investment in the future electricity system: an agent-based modelling approach. *Energy* 151, 569–580.
- [Sensfuss2007] ● Sensfuß, Ragwitz, Genoese & Möst (2007). Agent-based simulation of electricity markets: a literature review. Fraunhofer ISI Working Paper S5/2007.
- [Tesfatsion] ● Tesfatsion. Empirical validation and verification of agent-based models. https://faculty.sites.iastate.edu/tesfatsi/archive/tesfatsi/empvalid.htm
- Not opened (paywall): Weidlich & Veit 2008 (*Energy Economics* 30, 1728–1759); Ringler, Keles & Fichtner 2016 (*RSER* 57, 205–215); Guerci, Rastegar & Cincotti 2010; Hansen, Liu & Morrison 2019 (*ERSS* 49, 41–52). [Kell-storage] in the first list is Mason, Qadrdan & Jenkins 2021 (*Applied Energy* 294, 116905), a GB investment ABM with hourly operation and storage (◐).

**Optimum against simulated market**
- [Torralba2020] ● Torralba-Díaz, Schimeczek, Reeg, Savvidis, Deissenroth-Uhrig, Guthoff, Fleischer & Hufendiek (2020). Identification of the efficiency gap by coupling a fundamental electricity market model and an agent-based simulation model. *Energies* 13(15), 3920. doi:10.3390/en13153920
- [Torralba2024] ◐ Torralba-Díaz, Schimeczek, Kochems & Hufendiek (2024). Iterative coupling of a fundamental electricity market model and an agent-based simulation model to reduce the efficiency gap. *Energy* 310, 133192.
- [Jonson2020] ● Jonson, Azar, Lindgren & Lundberg (2020). Exploring the competition between variable renewable electricity and a carbon-neutral baseload technology. *Energy Systems* 11, 21–44. doi:10.1007/s12667-018-0308-6
- [Trutnevyte2016] ● Trutnevyte (2016). Does cost optimization approximate the real-world energy transition? *Energy* 106, 182–193. doi:10.1016/j.energy.2016.03.038
- [Ehrenmann2011] ○ Ehrenmann & Smeers (2011). Generation capacity expansion in a risky environment: a stochastic equilibrium analysis. *Operations Research* 59(6), 1332–1346.
- [deMaere2017] ◐ de Maere d'Aertrycke, Ehrenmann & Smeers (2017). Investment with incomplete markets for risk: the need for long-term contracts. *Energy Policy* 105, 571–583.
- [Hoschle2018] ○ Höschle, Le Cadre, Smeers, Papavasiliou & Belmans (2018). An ADMM-based method for computing risk-averse equilibrium in capacity markets. *IEEE Trans. Power Systems* 33(5), 4819–4830.
- [Mays2019] ◐ Mays, Morton & O'Neill (2019). Asymmetric risk and fuel neutrality in electricity capacity markets. *Nature Energy* 4, 948–956.
- [Dimanchev2024a] ◐ Dimanchev, Gabriel, Reichenberg & Korpås (2024). Consequences of the missing risk market problem for power system emissions. *Energy Economics* 136, 107639.
- [Dimanchev2024b] ● Dimanchev, Gabriel, Fleten, Pecci & Korpås (2024). Choosing climate policies in a second-best world with incomplete markets. MIT CEEPR WP 2024-14.
- [Makrides2025] ◐ Makrides, Suski & Spyrou (2025). Quantifying the impact of missing risk markets for decarbonized power systems with long duration energy storage. https://arxiv.org/abs/2510.13514
- [Mannhardt2024] ● Mannhardt, Gabrielli & Sansavini (2024). Understanding the vicious cycle of myopic foresight and constrained technology deployment in transforming the European energy system. *iScience* 27(12), 111369.
- [Heuberger2018] ◐ Heuberger, Staffell, Shah & Mac Dowell (2018). Impact of myopic decision-making and disruptive events in power systems planning. *Nature Energy* 3, 634–640.
- [Hirth2016] ○ Hirth & Steckel (2016). The role of capital costs in decarbonizing the electricity sector. *Environmental Research Letters* 11, 114010.
- [Egli2018] ○ Egli, Steffen & Schmidt (2018). A dynamic analysis of financing conditions for renewable energy technologies. *Nature Energy* 3, 1084–1092.
- [CCC2011] ● Committee on Climate Change (2011). Time preference, costs of capital and hidden costs.
- [HMT2026] ● HM Treasury (October 2026). Green Book Discount Rate Review 2026: HM Treasury response. https://www.gov.uk/government/publications/green-book-discount-rate-review-2026
- [BEIS2021] ● BEIS (2021). Valuation of greenhouse gas emissions: for policy appraisal and evaluation. https://www.gov.uk/government/publications/valuing-greenhouse-gas-emissions-in-policy-appraisal
- [DECC2013] ● DECC (2013). Electricity Market Reform, Annex C: reliability standard methodology. https://assets.publishing.service.gov.uk/media/5a7c4a16ed915d338141dd0a/Annex_C_-_reliability_standard_methodology.pdf
- [Neumann2021] ◐ Neumann & Brown (2021). The near-optimal feasible space of a renewable power system model. *EPSR* 190, 106690. https://arxiv.org/abs/1910.01891
- [Pedersen2021] ◐ Pedersen, Victoria, Rasmussen & Andresen (2021). Modeling all alternative solutions for highly renewable energy systems. *Energy* 234, 121294.
- [Grochowicz2023] ◐ Grochowicz, van Greevenbroek, Benth & Zeyringer (2023). Intersecting near-optimal spaces: European power systems with more resilience to weather variability. *Energy Economics* 118, 106496.
- [Gotske2024] ◐ Gøtske, Andresen, Neumann & Victoria (2024). Designing a sector-coupled European energy system robust to 60 years of historical weather data. *Nature Communications*. doi:10.1038/s41467-024-54853-3
- [Zeyringer2018] ◐ Zeyringer, Price, Fais, Li & Sharp (2018). Designing low-carbon power systems for Great Britain in 2050 that are robust to the spatiotemporal and inter-annual variability of weather. *Nature Energy* 3, 395–403.
- [Poncelet2016] ◐ Poncelet, Delarue, Six, Duerinck & D'haeseleer (2016). Impact of the level of temporal and operational detail in energy-system planning models. *Applied Energy* 162, 631–643.
- [Saltelli2010] ○ Saltelli & Annoni (2010). How to avoid a perfunctory sensitivity analysis. *Environmental Modelling & Software* 25(12), 1508–1517.
- [Green2021] ○ Green & Staffell (2021). The contribution of taxes, subsidies, and regulations to British electricity decarbonization. *Joule* 5(10).
- [Lipsey1956] Lipsey & Lancaster (1956). The general theory of second best. *Review of Economic Studies* 24(1), 11–32. (not re-read)
- [Newbery2016] ● Newbery (2016). Missing money and missing markets: reliability, capacity auctions and interconnectors. *Energy Policy* 94, 401–410; EPRG WP 1508.
- [Zachary2022] ◐ Zachary, Wilson & Dent (2022). The integration of variable generation and storage into electricity capacity markets. *The Energy Journal* 43(4), 231–250.

**GB evidence**
- [DDM2012] ● DECC (2012). Dynamic Dispatch Model (DDM). https://assets.publishing.service.gov.uk/media/5a750fe840f0b6397f35d5ec/5425-decc-dynamic-dispatch-model-ddm.pdf
- [DDMreview] ● DECC (2012). DDM peer review (Newbery and Ralph). https://assets.publishing.service.gov.uk/media/5a78c45e40f0b6324769a031/5427-ddm-peer-review.pdf
- [GenCosts2023] ● DESNZ (2023). Electricity generation costs 2023. [GenCosts2025] ● DESNZ (2026). Electricity generation costs 2025.
- [CP2030] ● DESNZ (2024). Clean Power 2030 Action Plan, technical annex.
- [EE2018] ● Europe Economics (2018). Cost of capital update for electricity generation, storage and demand side response technologies. For BEIS.
- [CEPA2025] ● CEPA (2025). Hurdle rate estimates for electricity sector technologies. For DESNZ. https://assets.publishing.service.gov.uk/media/68cd1d818c44a661b4995d9f/cepa-desnz-hurdle-rates-electricity.pdf
- [FES2025] ● NESO (2025). FES 2025 modelling methods. [NESO-adequacy] ● NESO. Resource adequacy in the 2030s. [NESO-constraints] ● NESO (2026). Thermal constraints update.
- [PTE2025] ● Panel of Technical Experts (2025). Report on the NESO Electricity Capacity Report. https://assets.publishing.service.gov.uk/media/68762902a8d0255f9fe28e94/2025-panel-of-technical-experts-report-on-neso-ecr.pdf
- [FTI2023] ● FTI Consulting for Ofgem (2023). Assessment of locational wholesale pricing for GB: key findings.
- [Franken2025] ● Franken, Lyden & Friedrich (2025). Open 6-zone GB market model. https://arxiv.org/abs/2506.04107
- [AR5] [AR6] [AR7] [AR7a] ● DESNZ. Contracts for Difference allocation round 5, 6, 7 and 7a results (gov.uk).
- [CarbonBrief2026] ● Carbon Brief (2026). Q&A: what the UK record auction for offshore wind means for bills and clean power by 2030.
- [Welisch2020] ◐ Welisch & Poudineh (2020). Auctions for allocation of offshore wind contracts for difference in the UK. *Renewable Energy* 147, 1266–1274.
- [Jansen2020] ○ Jansen et al. (2020). Offshore wind competitiveness in mature markets without subsidy. *Nature Energy*. [Beiter2023] ○ Beiter et al. (2023). The enduring role of contracts for difference in risk management and market creation for renewables. *Nature Energy*.
- [EMRS] ● EMR Settlement. Capacity cleared price, historical data. [EnergyUK2026] ● Energy UK (2026). Energy UK explains: Capacity Market auctions.
- [Grubb2018] ○ Grubb & Newbery (2018). UK Electricity Market Reform and the energy transition. EPRG WP 1817. [Hach2016] ○ Hach, Chyong & Spinler (2016), *EJOR* 249, 691–705. [Franco2015] ○ Franco, Castaneda & Dyner (2015), *EJOR* 245, 273–285.

**Learning and LLM agents**
- [Calvano2020] ◐ Calvano, Calzolari, Denicolò & Pastorello (2020). Artificial intelligence, algorithmic pricing, and collusion. *AER* 110(10), 3267–97.
- [denBoer2022] ◐ den Boer, Meylahn & Schinkel (2022). Artificial collusion: examining supracompetitive pricing by Q-learning algorithms. Tinbergen DP 22-067.
- [Abada2023] ◐ Abada & Lambin (2023). Artificial intelligence: can seemingly collusive outcomes be avoided? *Management Science* 69(9), 5042–5065.
- [Asker2024] ○ Asker, Fershtman & Pakes (2024). The impact of artificial intelligence design on pricing. *JEMS* 33(2), 276–304.
- [Banchio2022] ◐ Banchio & Mantegazza (2022). Artificial intelligence and spontaneous collusion. https://arxiv.org/abs/2202.05946
- [Aliabadi2017] ○ Esmaeili Aliabadi, Kaya & Şahin (2017). Competition, risk and learning in electricity markets: an agent-based simulation study. *Applied Energy* 195, 1000–1011.
- [Seredynski2026] ◐ Seredyński & Tsaousoglou (2026). AI agents in algorithmic electricity markets: on the emergence of tacit collusion. arXiv:2608.26896
- [Graf2024] ◐ Graf, Zobernig, Schmidt & Klöckl (2024). Computational performance of deep reinforcement learning to find Nash equilibria. *Computational Economics*. https://arxiv.org/abs/2104.12895
- [Lanctot2017] ● Lanctot et al. (2017). A unified game-theoretic approach to multiagent reinforcement learning. NIPS 2017. https://arxiv.org/abs/1711.00832
- [Agarwal2021] ◐ Agarwal, Schwarzer, Castro, Courville & Bellemare (2021). Deep reinforcement learning at the edge of the statistical precipice. NeurIPS 2021.
- [Horton2023] ◐ Horton, Filippas & Manning (2023). Large language models as simulated economic agents: what can we learn from homo silicus? https://arxiv.org/abs/2301.07543
- [Aher2023] ◐ Aher, Arriaga & Kalai (2023). Using large language models to simulate multiple humans and replicate human subject studies. ICML 2023.
- [Ross2024] ◐ Ross, Kim & Lo (2024). LLM economicus? Mapping the behavioral biases of LLMs via utility theory. https://arxiv.org/abs/2408.02784
- [Raman2024] ● Raman, Lundy, Amouyal, Levine, Leyton-Brown & Tennenholtz (2024). STEER: assessing the economic rationality of large language models. https://arxiv.org/abs/2402.09552
- [Fish2024] ● Fish, Gonczarowski & Shorrer (2024). Algorithmic collusion by large language models. https://arxiv.org/abs/2404.00806
- [Sclar2024] ◐ Sclar, Choi, Tsvetkov & Suhr (2024). Quantifying language models' sensitivity to spurious features in prompt design. ICLR 2024.
- [Zheng2024] ◐ Zheng, Zhou, Meng, Zhou & Huang (2024). Large language models are not robust multiple choice selectors. ICLR 2024.
- [Gui2023] ◐ Gui & Toubia (2023). The challenge of using LLMs to simulate human behavior: a causal inference perspective. https://arxiv.org/abs/2312.15524
- [Ludwig2024] ◐ Ludwig, Mullainathan & Rambachan (2024). Large language models: an applied econometric framework. https://arxiv.org/abs/2412.07031
- [Sharma2023] ◐ Sharma et al. (2023). Towards understanding sycophancy in language models. https://arxiv.org/abs/2310.13548
- [Wang2025] ◐ Wang, Morgenstern & Dickerson (2025). Large language models that replace human participants can harmfully misportray and flatten identity groups. *Nature Machine Intelligence*.
- [Ross2026] ◐ Ross, So, De Simone, Pozniak & Lo (2026). Why better models can create riskier systems: evidence from LLM agents in financial markets. arXiv:2609.04373
- [Atil2024] ◐ Atil et al. (2024). Non-determinism of "deterministic" LLM settings. https://arxiv.org/abs/2408.04667 [Yuan2025] ◐ Yuan et al. (2025). Understanding and mitigating numerical sources of nondeterminism in LLM inference. https://arxiv.org/abs/2506.09501
- [Jia2025] ◐ Jia, Yuan, Pan, McNamara & Chen (2025). LLM strategic reasoning: agentic study through behavioral game theory. NeurIPS 2025. [ZhengK2025] ◐ Zheng, Zhou & Wang (2025). Beyond Nash equilibrium: bounded rationality of LLMs and humans in strategic decision-making. https://arxiv.org/abs/2506.09390
- [Larooij2025] ● Larooij & Törnberg (2025). Validation is the central challenge for generative social simulation: a critical review of LLMs in agent-based modeling. *Artificial Intelligence Review* 59, 15.
- [WangS2026] ● Wang (2026). Benchmarking LLM bidding agents in electricity markets. NeurIPS 2026 workshop. [Chen2025] ◐ Chen, Karaduman & Kuang (2025). Behavioral generative agents for energy operations. https://arxiv.org/abs/2506.12664
- [Meier2007] ○ Meier & Tarhan (2007). Corporate investment decision practices and the hurdle rate premium puzzle. [Jagannathan2011] ● Jagannathan, Meier & Tarhan (2011). The cross-section of hurdle rates for capital budgeting. NBER w16770. [Masini2013] ○ Masini & Menichetti (2013). Investment decisions in the renewable energy sector: an analysis of non-financial drivers. *Technological Forecasting and Social Change* 80(3), 510–524.

**Standards**
- [Grimm2020] ● Grimm et al. (2020). The ODD protocol for describing agent-based and other simulation models: a second update. *JASSS* 23(2), 7 (with supplement S6: TRACE examples; [Grimm2014] ○ *Ecological Modelling* 280). [Grimm2005] ○ *Science* 310, 987.
- [Muller2013] ● Müller et al. (2013). Describing human decisions in agent-based models: ODD+D. *Environmental Modelling & Software* 48, 37–48.
- [Fagiolo2019] ● Fagiolo, Guerini, Lamperti, Moneta & Roventini (2019). Validation of agent-based models in economics and finance. LEM WP 2017/23.
- [McCulloch2022] ● McCulloch et al. (2022). Calibrating agent-based models using uncertainty quantification methods. *JASSS* 25(2), 1.
- [Lee2015] ● Lee et al. (2015). The complexities of agent-based modeling output analysis. *JASSS* 18(4), 4.
- [tenBroeke2016] ● ten Broeke, van Voorn & Ligtenberg (2016). Which sensitivity analysis method should I use for my agent-based model? *JASSS* 19(1), 5. [Thiele2014] ● Thiele, Kurth & Grimm (2014). *JASSS* 17(3), 11. [Saltelli2019] ◐ Saltelli et al. (2019). Why so many published sensitivity analyses are false. https://arxiv.org/abs/1711.11359
- [Gils2022] ○ Gils et al. (2022). Model-related outcome differences in power system models with sector coupling. *RSER* 159, 112177.
- [Barker2022] ● Barker et al. (2022). Introducing the FAIR principles for research software. *Scientific Data* 9, 622.
- [JOSS] ● Journal of Open Source Software: review criteria, policies, submitting. https://joss.readthedocs.io
- [Bridgeford2025] ● Bridgeford et al. (2025). Ten simple rules for AI-assisted coding in science. https://arxiv.org/abs/2510.22254
- [ESPENI] ● ESPENI on Zenodo: v1.0.0 https://zenodo.org/records/3884859 (CC BY 4.0); v8.0.11 https://zenodo.org/records/16328483 (CC BY-NC 4.0).
- [Elexon] ● Elexon BMRS data licence. https://www.elexon.co.uk/bsc/data/balancing-mechanism-reporting-agent/copyright-licence-bmrs-data/ [NESO-licence] ● https://www.neso.energy/data-portal/neso-open-licence
- Repositories and documentation inspected ●: PyPSA-Eur, PyPSA-GB, AMIRIS and AMIRIS-Examples, ASSUME, Mesa, MUSE, otoole, Calliope.
