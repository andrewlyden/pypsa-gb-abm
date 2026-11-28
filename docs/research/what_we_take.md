# What this model takes from other models

The [literature review](literature_review.md) describes the other models; this page says what
`ukabm` takes from each, where it sits in the code, what could be taken next and what is left alone on
purpose. "Takes" has three strengths:

* **reused**: their data or their rule, as it stands (with the source file named);
* **followed**: their design, re-implemented here;
* **checked against**: used as a benchmark or a warning, not as a component.

Status in November 2026. Citation keys refer to the literature review's reference list.

## By model

| Model | Reused or followed now | Where in this repository | Could take next | Not taken, and why |
|---|---|---|---|---|
| **PyPSA-GB** (Lyden et al.) | **Reused:** zonal network and interconnector register; CfD strikes by round; Capacity Market auction parameters; NESO de-rating factors; RO bandings; the 2024 scarcity curve. **Reused rules:** offers by support contract (RO at minus the certificate value, CfDs of rounds 1–3 at minus the strike, round 4 on at zero and unpaid at negative prices); wholesale stage then Balancing Mechanism redispatch | `ukabm/data/pypsagb.py`, `data/pypsagb_snapshot/`; `config.RO_BANDS`, `SCARCITY_STEPS`, Tech de-rating; `decisions.RuleBased.offer_price`; `model.settle`; `ukabm/network.py` | Station-level registers (LCCC contract status, RO accreditation, Capacity Market register with parent companies) in place of the rule-based match in `scripts/build_fleet.py`; `technology_costs_vintage.csv` and `technology_costs_historical.csv` in place of this repository's own extract of the same DESNZ tables; heat demand and heat-pump performance from weather data; minimum-stable-generation proxy and must-take small solar for negative prices | Its Capacity Market supply curve (bid distributions fitted to two auctions): here bids come from each plant's costs, so that firms' decisions can differ. Its per-site weather-model wind profiles: here the profiles are metered output per wind farm, which needs no bias correction |
| **PyPSA** | **Reused:** the optimiser. The least-cost plan (multi-period capacity expansion) and the evaluator dispatch for both fleets, with reserve constraints | `ukabm/planner.py` | Near-optimal space (modelling to generate alternatives) to say whether a fleet is inside the band of near-least-cost fleets (README item 10); several weather years in one plan (item 17) | — |
| **Mesa** | **Reused:** agent and model base classes; the firm panel through a `DataCollector` | `ukabm/agents.py`, `model.firm_panel` | Mesa-LLM as the engine behind an LLM decision maker (item 25) | A Mesa scheduler: the model orders the phases of the year itself. Households stay as arrays for speed |
| **AMIRIS** (DLR) [AMIRIS-JOSS, Nitsch2021] | **Followed:** bids set by the support instrument (marginal cost minus the expected premium is the same idea as the GB rules above); must-run plant at a floor price; plants with the same bid share an award in proportion to capacity. **Checked against:** its back-tests set the level to expect from a merit-order model (Austria 2019: correlation 0.64, mean error €8/MWh; Germany 2019: correlation up to 0.87), and report the same failure as here: "no negative prices are modelled", lows too high and highs too low | `decisions.RuleBased.offer_price`; `model._merge_blocks`; `docs/calibration.md` | **Storage dispatch that knows its own price impact.** AMIRIS found storage "220 % overused" as a price taker and closest to history with a system-cost-minimising plan and a competition multiplier; this model uses three price-taking tranches. **A forecaster agent** whose forecast excludes flexible plant and can carry errors (item 36). **Mark-downs on inflexible plant** (its nuclear bids at −€100 to −€150/MWh) for negative prices. Hourly error and correlation as back-test metrics. A GB run in AMIRIS as the independent replication of one number (item 51) | The framework (Java on FAME) and its German instruments. It has no investment, Capacity Market or allocation rounds |
| **EMLab-Generation** (TU Delft) [Chappin2017, deVries2015] | **Followed:** investment by net present value on a future year re-cleared with the known pipeline; firms asked in random order, re-drawn; plant closed after years without profit | `model.invest`, `model.forecast`, `decisions.*.merchant_investment`; retirement in `model.step` | Loop until no firm wants to invest (here: a fixed number of decisions a year); debt and equity with a down-payment (item 32); horizons that differ by firm | Its load-duration curve: hourly clearing is kept (they report that the curve overstates renewables and cannot hold storage) |
| **EMLabpy + AMIRIS** [SanchezJimenez2024] | **Followed:** a check that a perfect-foresight investor recovers its costs, as this model's convergence test checks that idealised firms recover the plan | `scenarios.toml` `competitive_benchmark`, `scripts/run_convergence.py` | Invest on a median weather year, operate over many (items 17, 35): they find revenue variability triples | Two models soft-linked through files: here investment and operation are one model |
| **Tao et al. 2021** (method) [Tao2021] | **Followed:** benchmark the agents against the long-run optimum; a price projection that fills the horizon with expected entry (wind and solar at their recent rate, peakers to keep the system adequate); no first-mover advantage (order re-drawn before every decision) | `model.forecast_horizons`, `model.invest`; `ukabm/gap.py` | The sweep they recommend: convergence across look-ahead horizons, projection rules and block sizes (item 45) | — |
| **Torralba-Díaz et al. 2020** (method) [Torralba2020] | **Followed:** one cost definition and one evaluator for both the plan and the market outcome, so the gap is what was built and how it was run, not two accounting systems | `ukabm/costs.py`, `planner.evaluate` | Harmonise in steps until the two agree to a stated tolerance before reading a gap (item 42) | — |
| **DESNZ Dynamic Dispatch Model** (LCP) [DDM2012, DDMreview] | **Followed:** required returns by technology with an adjustment by investor (CEPA 2025 rates, shifted by firm type); a scarcity mark-up over short-run cost that rises as the margin falls, fitted to history (through PyPSA-GB's curve); build limits by technology | `config.HURDLE_RATE`, `hurdle_rate`, `SCARCITY_STEPS`, `PLANNER_BUILD_MW_PER_YEAR`; `model.build_room` | — | The model itself is not open. Its peer review's caveat (interconnectors not price-responsive) does not apply here |
| **MUSE** (Imperial) [MUSE] | **Followed:** investors described by type, each with its own objective settings and the set of technologies it searches | `model.FIRM_TYPES` (`tech_preference`), `data/fleet/firms.csv` | Objectives other than net present value by type (payback, levelised cost) for the behavioural arm (item 55) | Its prices from levelised costs iterated to equilibrium: here prices come from hourly clearing |
| **BRAIN-Energy** (UCL) [Barazza2020] | — | — | Foresight by actor type (5–25 years), imitation of the fastest-growing rival, patient retirement (7–10 loss years) for the behavioural arm (items 36, 55) | Its yearly resolution |
| **EMIS-AS** (NREL) [Anwar2022] | — | — | Risk-averse valuation over scenarios with beliefs that update (items 35, 37); retirement on three conditions, not one | Each firm solving its own expansion model: too slow here |
| **PowerACE** (KIT) [Fraunholz2021] | **Checked against:** their finding that the price forecast method "clearly" changes results is why the forecast is a named, replaceable part | `model.forecast`, `observations.MarketInfo` | Iterating investments to a Nash equilibrium as a cross-check on the sequential rule | — |
| **ElecSim** [Kell2019, Kell2020] | **Checked against:** the only GB investment back-cast found (2013–18) was fitted in-sample by tuning the price curve investors expect. That is the reason nothing here is fitted to auctions | `docs/calibration.md` | Its GB 2013–18 mix as one more comparison for the hindcast (item 43) | Fitting investor expectations to reproduce the mix |
| **ASSUME** [ASSUME-repo] | — | — | Learning bidders (item 24): it has reinforcement-learning strategies for short-term markets; a second dispatch model to replicate one number | It has no long-term investment |
| **NESO FES 2025** (PLEXOS), **CCC Seventh Carbon Budget**, **Clean Power 2030** | **Reused:** the pathway's demand growth, EVs, electrolysers, interconnectors, nuclear and pumped hydro as exogenous drivers; its wind and solar capacity as the government's target; its gas CCS and hydrogen capacity as the tender's target. **Checked against:** the baseline in 2030–2050 | `ukabm/drivers.py`, `data/fes/`; `scripts/compare_pathways.py` | Cost the pathways' own fleets with the evaluator: optimal against planned against emergent (item 12c) | Their fleets as calibration targets for the firms |
| **Gonzalez-Ruiz et al. 2025** (multi-agent RL against PyPSA) [GonzalezRuiz2025] | **Checked against:** the nearest study to this one; it compares a learned mix with a plan without attributing the difference | `ukabm/gap.py` (the ladder is the attribution they lack) | A comparison point for items 24 and 25 | — |

## By part of this model

| Part of `ukabm` | Comes from | Strength |
|---|---|---|
| Hourly uniform-price clearing | common to AMIRIS, PowerACE, PyPSA-GB's wholesale stage | followed |
| Offers of supported renewables, CfD settlement at negative prices | PyPSA-GB (GB contract terms); same logic as AMIRIS | reused rules |
| Scarcity mark-up | PyPSA-GB's 2024 curve; the DDM's approach | reused values |
| Storage dispatch (price-taking tranches) | own heuristic | weak point: AMIRIS's price-impact method is the candidate replacement |
| Interconnector trade | own (neighbours' observed prices; spread calibrated on 2025); PyPSA-GB uses a hurdle of similar size | own |
| Network redispatch | PyPSA-GB's zonal network and two-stage design | reused data, followed design |
| Profiles | own build from NESO and Elexon metered data | own |
| Starting fleet, owners, pipeline | DESNZ station list and the CfD register (via PyPSA-GB); own matching rules | reused data, own rules |
| Costs and hurdle rates | DESNZ 2025 and CEPA 2025, the sources PyPSA-GB and the DDM also use | reused values |
| Firm types | MUSE's investor types; values are assumptions | followed |
| Merchant investment | EMLab's rule, with Tao et al.'s corrections | followed |
| CfD bids (lowest strike meeting the required return, with a merchant tail) | own; PyPSA-GB's levelised strike is the special case with no tail and no construction financing | own |
| Capacity Market (cost-based bids, sloping demand curve, T-4 and T-1) | scheme rules; PyPSA-GB for parameters and de-rating | own rule, reused data |
| Government and system operator as agents | own (unusual among the models reviewed) | own |
| Least-cost plan and evaluator | PyPSA | reused |
| Gap, split into investment and operation, and the ladder | Torralba-Díaz et al. for the harmonisation; the attribution is own | followed / own |
| Convergence test | Tao et al.; EMLabpy's cost-recovery check | followed |
| Exogenous drivers and targets | NESO FES 2025 | reused values |
| Households and heat | own stylised model | own; the weakest-evidenced part |
| Description, registers, disclosure | ODD+D, TRACE, FAIR4RS, JOSS policy (literature review section 8) | followed |
