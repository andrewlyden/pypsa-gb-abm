# Changelog

All notable changes to this project are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). The package version in `pyproject.toml` is
0.1.0; no version has been released or tagged yet.

## [Unreleased]

Changes on the branch `foundations/implementation` relative to `main` (merge commit 8cd61b6).

**Breaking changes, in short.** A model built with default settings is a different model from the one
on `main`: firms bid and invest on their own expectations, the government tracks capacity targets
within a budget, the system operator sets the Capacity Market target from the reliability standard,
the firms are twelve real companies and groups with their actual plants, the starting fleet has real
vintages and a contracted pipeline, demand and other exogenous inputs follow a NESO FES 2025 pathway,
and costs, hurdle rates and hourly profiles come from new published and measured sources. Every
annual result differs from `main`. An unknown scenario key now raises an error, Mesa is a required
dependency, and Python 3.11 or later is required. The benchmark scenario `legacy_rules` restores the
earlier decision rules, firms and fleet, but on today's data, so it does not reproduce earlier numbers.

### Added

* **Exogenous drivers from NESO FES 2025** (`ukabm/drivers.py`, `data/fes/fes2025_drivers.csv`;
  scenario key `fes_pathway`, default "Holistic Transition", "none" for the earlier assumptions):
  growth of demand other than EVs, heat pumps and electrolysis; EV stock and energy; electrolyser,
  interconnector, nuclear and pumped-hydro capacity; and the government's wind and solar targets.
  Heat pumps remain the households' choice.
* **Government tender for gas CCS and hydrogen power** (`GBMarketModel.dpa_round`, `Policy.dpa_enabled`):
  the government contracts the capacity of its FES pathway and pays each project its missing money,
  standing for Dispatchable Power Agreements and the hydrogen-to-power business model.
* **Build-rate limits for firms** (scenario key `agent_build_limits`, default on): CfD awards, Capacity
  Market new build and merchant projects coming online in one year are limited by
  `config.PLANNER_BUILD_MW_PER_YEAR`, as in the planner. Scenario key `build_limits` overrides the limits
  for the planner and the firms together; `scripts/run_gap.py` adds a "pathway limits" sensitivity
  (onshore wind and solar held to the highest FES 2025 pathway).
* **Twelve firms with real portfolios** (`data/fleet/firms.csv`, `owners.csv`; scenario key `firms`:
  "real" or "stylised"): seven named companies and five groups own the plants their companies own in
  the DUKES station list. Traits come from five firm types, each with the technologies it invests in;
  firms bid only for those.
* **Real starting fleet and contracted pipeline** (`scripts/build_fleet.py`, `data/fleet/fleet_2025.csv`,
  `pipeline_2025.csv`; scenario key `fleet`: "table" or "random"): vintages, zones, owners and support
  schemes from DUKES 2026 and the CfD register; 32 GW of wind and solar contracted but not built.
* **Open hourly profiles for 2021–2025** (`scripts/build_profiles.py`, `data/profiles/`): GB demand,
  separate onshore and offshore wind (available output, metered plus Balancing Mechanism turn-down)
  and solar, from NESO and Elexon open data, checked against DESNZ and NESO figures.
* **Capacity factors of new wind and solar by online year** (`config.NEW_BUILD_CF`, scenario key
  `new_build_cf`): measured on farms built since 2020, then DESNZ's assumptions to 2040.
* **Technology cost paths by commissioning year** (`config.COST_PATHS`, `data/parameters/cost_paths.csv`,
  `scripts/build_costs.py`) from DESNZ *Electricity Generation Costs 2025*, with financing during
  construction over a build lag (`config.BUILD_LAG`). `data/history/desnz_generation_costs.csv` holds
  the 2013–2025 editions.
* **Technology hurdle rates** (CEPA 2025 for DESNZ) and a 1.5-point merchant uplift
  (`config.HURDLE_RATE`, `MERCHANT_UPLIFT`, `hurdle_rate`); a firm's cost of capital shifts them.
* **Operating back-cast 2021–2025** (`scripts/run_backcast.py`, `results/backcast.md`): each year on its
  own weather, fleet (`config.fleet_mw`), neighbour prices and money-of-the-day fuel and carbon prices
  (`Policy.history_basis`, `Fuels.history_basis`). Historical inputs in `data/history/` with
  `scripts/build_history.py`; neighbour prices for 2021–2025; outturn for 2021–2023.
* **Coal and "other" (waste, CHP) plant** for historical years and the 2025 mix; nuclear and "other"
  offer as must-run.
* **Offers by support terms and a stepped scarcity mark-up** (`config.RO_BANDS`, `CFD_FROM_AR4_OFFER`,
  `SCARCITY_STEPS`; scenario key `scarcity_adder`: true, "ordc" or false).
* **Reserve and response in the planner and the evaluator** (`config.RESERVE`, scenario key `reserve`;
  "reserve off" and "reserve × 2" sensitivities in `scripts/run_gap.py`).
* **Planner day sample with extreme days** (`config.PLANNER_EXTREME_DAYS`, `planner.sample_days`).
* **Firm panel and auction table**: `GBMarketModel.firm_panel()` (a Mesa `DataCollector`, one row per
  firm and year) and `GBMarketModel.auctions()` (one row per auction pot and year); plants carry the
  route by which they were built.
* **Scenarios as TOML** (`ukabm/data/scenarios.toml`): users can keep their own file and load it with
  `get_scenario(name, file=...)`. Benchmarks `legacy_rules` and `competitive_benchmark`.
* **Checks against observations**: `scripts/check_auctions.py` (first CfD round against AR7, first T-4
  against 2029/30; `results/auction_check.md`), `scripts/replay_cfd_rounds.py` (every cleared CfD strike
  since 2015 against the official levelised cost of the day; `results/cfd_rounds_replay.md`) and
  `scripts/compare_pathways.py` (future years against FES 2025, the CCC and Clean Power 2030;
  `results/pathways_comparison.md`). `docs/calibration.md` records what is sourced, what is calibrated
  on 2025 and what the checks show.
* **Planner sensitivity** (`scripts/run_planner_sensitivity.py`, `results/planner_sensitivity.*`) and the
  foundations review (`docs/review_2026-11_foundations.md`, literature review sections 4–8).
* **Reference documentation**: data register (`docs/data.md`), parameter register
  (`docs/parameters.md`), ODD+D model description (`docs/odd.md`), disclosure of AI use
  (`docs/ai_use.md`), `CITATION.cff`, `CONTRIBUTING.md` and this changelog.
* New columns in the annual results, among them generation and capacity of coal and "other",
  `cap_electrolyser`, `peak_demand_gw` and `hours_zero_or_less`.

### Changed

* **Default decision makers** (`config.DEFAULTS`): `decision_logic` "expectations" (was "rules"),
  `government` "targets" (was "fixed"), `system_operator` "standard" (was "formula"), which adds a T-1
  Capacity Market auction each year.
* **Default firms, fleet and drivers**: `firms` "real", `fleet` "table", `fes_pathway` "Holistic
  Transition", `agent_build_limits` true. Firms have new names (RWE, SSE, …); a `decision_logic`
  table keyed by the old names (IntegratedUtility, MerchantIPP, …) applies only with
  `firms = "stylised"`.
* **Merchant investment order**: the order in which firms are asked is drawn again before every
  decision (`merchant_order` "redraw"; "fixed" keeps the earlier one order per year).
* **Scarcity pricing**: `scarcity_adder: true` now means the stepped curve on the de-rated margin; the
  earlier operating-reserve formula is `scarcity_adder: "ordc"`.
* **Default profile**: the open NESO/Elexon profile of the weather year replaces the ESPENI-derived
  profile, which is used only with `PyPSAGBData(profiles="espeni")`.
* **Unknown scenario keys raise `ValueError`**, also inside the `policy`, `fuels`, `reserve` and
  `multienergy` sub-tables. Valid keys are listed in `ukabm.scenarios.SCENARIO_KEYS`.
* **Python ≥ 3.11** (`requires-python`, for `tomllib`); **Mesa is a required dependency** (the fallback
  shims are removed).
* **Inputs**: capital and fixed costs of wind, solar and gas plant from DESNZ EGC 2025 (fixed O&M now
  includes insurance and connection and use-of-system charges); CfD bids use technology hurdle rates
  instead of the firm's WACC less 2.5 points; risk aversion is zero for every firm type (risk is in the
  rates); `INITIAL_FLEET_MW` re-based on DUKES 2026 (for example batteries 6.4 GW, solar 20.3 GW);
  battery service pots re-based so that revenue per MW on the 2025 fleet is unchanged; existing gas
  plant closes on age at 40 (CCGT) or 45 (OCGT) years; 2025 gas and carbon prices set to outturn
  (£29.4/MWh_th and £65/t, 2024 prices); AGR closures moved to March 2030; biomass 3.0 GW at 0.78
  availability, hydro at 0.26; Capacity Market de-rating factors from NESO's 2030-31 T-4 auction.
* **Demand after 2025** follows the FES pathway instead of 0.3 % a year; interconnector capacity is
  raised to the pathway's after 2030.
* **Benchmark `competitive_benchmark`**: five identical stylised firms that may build any technology,
  and no government tender for gas CCS or hydrogen power.
* **`scripts/compare_outturn.py`** runs 2025 on its own weather year, as the back-cast does.
* **Network stage**: plants of one zone with identical bids and offers are merged before the
  redispatch LP and the result shared pro rata (same result, far fewer generators).
* **Results**: every annual result differs from `main`. `results/backcast.md`,
  `results/auction_check.md`, `results/calibration_2025.md` and `results/cfd_rounds_replay.md` were
  produced on this branch. The scenario, ensemble, gap and convergence results in `results/` and the
  numbers quoted from them in `README.md` and `docs/gap.md` date from commit 99c6b18, before these
  changes, and have not been re-run.

### Fixed

* `market.clear` no longer floors every hourly price at zero; prices can be negative where negative
  offers are marginal.
* The first firm drawn in a year no longer takes every merchant project until its NPV or budget runs
  out (foundations review F9).
* The planner's day sample now includes the days with the highest net-load peak and mean, so plans are
  no longer short of firm capacity on the full year (foundations review F3).
* Onshore and offshore wind no longer share one hourly shape scaled by a factor (foundations review F1).
* Offshore wind CfD bids are no longer £25–40/MWh below the AR7 result for want of connection and
  use-of-system charges in fixed costs. (The first modelled round now clears about 20 % above AR7 for
  offshore wind; see `results/auction_check.md`.)
* The planner and evaluator now hold the reserve and response the agents' batteries are paid for, so
  those batteries are no longer counted as pure cost in the gap (README roadmap item 9).
* The bundled default profile is no longer derived from a non-commercially licensed source (ESPENI,
  CC BY-NC 4.0); the file itself is still in the repository (see `docs/data.md`).
