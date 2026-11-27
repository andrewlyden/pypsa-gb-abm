# pypsa-gb-abm — agent-based GB electricity market model linked to PyPSA-GB

A modular Python (Mesa + PyPSA) agent-based model of the **GB electricity market** — hourly operation
(bidding, dispatch, pricing) and annual investment (technology choice, expectations, CfD / Capacity
Market / carbon policy) — linked to [PyPSA-GB](https://github.com/andrewlyden/PyPSA-GB) data and its
zonal network, with **multi-energy coupling** to heat (household heat-pump agents), gas networks, EVs
and hydrogen.

> ⚠️ Prototype. The 2025 operating year is calibrated against GB outturn ([table](results/calibration_2025.md));
> the 2026-2050 pathway is not validated and numbers are illustrative. See [assumptions](docs/assumptions.md).

* Research: [literature review](docs/research/literature_review.md) ·
  [capability-vs-challenge matrix](docs/research/capability_matrix.md) ·
  [gap analysis](docs/research/gap_analysis.md)
* Design: [model design](docs/model_design.md) · [assumptions & limitations](docs/assumptions.md)

## Quick start
```bash
pip install -e .            # numpy pandas scipy matplotlib mesa pypsa highspy
pytest -q                   # 13 tests, ~45 s
python scripts/run_scenarios.py baseline --end 2030      # ~40 s
python scripts/run_scenarios.py                          # all 6 scenarios 2025-2050 (~4 min each)
python scripts/make_plots.py                             # -> docs/figures/
python scripts/compare_outturn.py                        # 2025 vs GB outturn -> results/calibration_2025.md
# optional: rebuild the outturn reference / neighbour prices (public APIs, no key)
python scripts/fetch_outturn.py 2024 2025 && python scripts/fetch_neighbour_prices.py 2024
# optional: rebuild the PyPSA-GB snapshot / run on a live clone
python scripts/extract_pypsagb_snapshot.py /path/to/PyPSA-GB
python scripts/run_scenarios.py baseline --pypsa-gb /path/to/PyPSA-GB
```
```python
from ukabm import GBMarketModel, get_scenario
m = GBMarketModel(get_scenario("heat_push"), end=2040, seed=1)
df = m.run()            # annual metrics: prices, mix, emissions, policy costs, HP/EV stock, gas tariffs
```

## Layout
```
ukabm/config.py        technologies, fuels, policy parameters (indicative)
ukabm/agents.py        GenCo agents (offers, CfD/CM bids, NPV investment), Plant
ukabm/market.py        vectorised hourly clearing, storage arbitrage, valley-filling
ukabm/model.py         GBMarketModel (Mesa): annual loop, auctions, settlement, investment
ukabm/multienergy.py   HeatModule (household agents), GasNetworkModule, EVModule, HydrogenModule
ukabm/network.py       PyPSA zonal redispatch on the PyPSA-GB zonal network
ukabm/data/pypsagb.py  PyPSA-GB adapter (raw clone or bundled snapshot)
ukabm/scenarios.py     baseline, high_carbon, no_cfd, heat_push, no_capacity_market, high_gas
ukabm/outturn.py       model-vs-outturn comparison (data/outturn: NESO generation mix + CI, Elexon)
```

## 2025 calibration (baseline, seed 42) vs GB outturn
| | model | outturn 2025 |
|---|---|---|
| price, time-weighted mean (£/MWh) | 84.6 | 79.9 (Elexon MID) |
| carbon intensity, NESO basis (g/kWh) | 112 | 130 (NESO, generation-weighted) |
| gas / wind / nuclear / biomass (TWh) | 69 / 94 / 35 / 20 | 77 / 86 / 34 / 20 |
| imports / exports (TWh) | 45 / 15 | 44 / 15 (Elexon FUELHH) |

Residuals are explained: the copperplate market does not curtail Scottish wind (~9 TWh in 2025, replaced by
gas in the Balancing Mechanism), the model has no CHP/waste "other" generation (4.7 TWh), and its price
distribution is too narrow (no negative hours). Full table: [results/calibration_2025.md](results/calibration_2025.md).

## Headline results (single seed, illustrative)
| scenario | price 2030 / 2050 (£/MWh) | CI 2050 (g/kWh), direct (NESO basis) | LOLE total 2025-50 (h) | HP homes 2050 |
|---|---|---|---|---|
| baseline | 82 / 43 | 13 (19) | 0 | 5.7 m |
| high_carbon (£300/t 2050) | 89 / 46 | 7 (10) | 0 | 5.0 m |
| no_cfd | 86 / 79 | 25 (35) | 0 | 4.1 m |
| no_capacity_market | 90 / 54 | 11 (18) | 553 | 4.7 m |
| heat_push (£11.5k grant, £25/MWh levy rebalancing) | 86 / 57 | 20 (28) | 0 | 27.2 m |
| high_gas (£45/MWh_th) | 105 / 64 | 17 (25) | 0 | 13.1 m |

Qualitative messages: CfDs drive offshore wind and lower long-run prices; removing the CM produces a
missing-money scarcity episode (2027-29, ~500 h, prices ~£340/MWh) before merchant entry responds (classic
ABM investment cycle; much smaller than before the 2025 calibration, when cheap imports had driven all CCGTs
to retire); high gas prices and levy rebalancing both accelerate heat-pump uptake, which raises winter peak
and carbon intensity until the fleet catches up.

![scenarios](docs/figures/scenario_comparison.svg)
![capacity](docs/figures/capacity_mix.svg)

## STATUS / roadmap

| area | status |
|---|---|
| Hourly GB market clearing (agent offers, ORDC scarcity) | ✅ works, unit-tested |
| Interconnectors: per-market import offers + export bids on observed 2024 neighbour price shapes | ✅ works; calibrated to 2025 flows (45/15 TWh vs 44/15) |
| 2025 calibration vs outturn (`scripts/compare_outturn.py`) | ✅ price +6 %, gas/imports/exports/nuclear/biomass within 10 %; CI (NESO basis) −13 % with explained residuals (curtailment, "other") |
| Storage arbitrage (battery, pumped hydro), smart EV valley-filling, electrolysers | ✅ works (heuristic, perfect intra-day foresight) |
| Merchant investment (5 heterogeneous GenCos, NPV on re-forecast prices) | ✅ works |
| CfD allocation rounds with pots; 2-way CfD settlement | ✅ works (simplified: no £ budget) |
| T-4 Capacity Market with sloping demand curve | ✅ works (no T-1, no penalties) |
| Retirement on persistent losses / end of life | ✅ works |
| PyPSA-GB link: zonal network, ESPENI profiles, DUKES siting, IC register, CM/CfD data | ✅ works (bundled snapshot or live clone) |
| PyPSA zonal redispatch → constraint cost, zonal price siting signal | ⚠️ runs; constraint costs look **too low** (~£0.1bn vs £1–2bn outturn) — zonal transport model, random 96 hours, single GB wind shape |
| Heat-pump household agents + gas network tariff feedback | ✅ works (stylised, synthetic temperature) |
| Hydrogen: electrolysers + H2 turbine tech | ⚠️ stub-level: exogenous H2 price, no H2 storage/network |
| Batteries | ⚠️ no new merchant batteries: flat price duration under OCGT-led CM; needs BM/ancillary revenue stack |
| Strategic BM bidding, nodal/ETYS network in loop, RL agents | ❌ not started |
| Price distribution | ⚠️ too narrow: no negative hours (244 in 2025), p05 £54 vs £9, p95 £100 vs £123 (no unit commitment / must-run, no scarcity tail) |
| Back-casts 2020–24, multi-seed Monte-Carlo, weather years, CI tolerance test | ❌ not started (2025 only) |

**Next (priority order)**

The daily agent takes the highest unfinished item it can complete in one run. Items marked
*needs human* are decisions for the maintainer and are skipped by the agent.

1. Multi-seed runs (5 seeds) for baseline + 2 policy scenarios; show uncertainty bands, not single lines,
   in the plots and the headline table.
2. Network stage: switch to the PyPSA-GB Reduced 32-bus network with zonal wind profiles (Scottish vs
   English wind) and representative rather than random hours. Constraint costs (~£0.1bn now) should move
   towards the £1–2bn/yr outturn. Also feed redispatch volumes back into the reported generation mix: the
   2025 calibration shows wholesale wind 8.6 TWh above NESO outturn (≈ Scottish curtailment, ~8.8 TWh in
   2025) and gas 8 TWh below, which is most of the remaining CI gap (112 vs 130 g/kWh, NESO basis).
3. Battery revenues: add a stylised BM/ancillary revenue stack so merchant batteries can enter. Then check
   the Capacity Market: it clears at the cap because it is under-subscribed (offered de-rated capacity below
   target; check the target vs NESO/EMR de-rated targets incl. managed EV/HP peak, and the `cm_new_chunks`
   entry cap), plus a demand-curve edge case where an auction clears at £0 with procurement above target + 1.5 GW. Related: the 2025 price distribution is too narrow (no negative hours, p95
   £100 vs £123), which understates arbitrage spreads; consider must-run/min-stable generation and RO bidding.
4. Validation check: tolerance bands (in `docs/assumptions.md`) on the `ukabm.outturn.compare` table for
   2025 (price, CI, generation mix, flows) and a test, so regressions show up in CI.
5. Write up the heat_push vs baseline loop (HP uptake ↔ prices ↔ gas tariffs) as a docs page: the
   multi-energy headline result.
6. *needs human*: decide whether to extend validation to 2020–24 back-casts and multiple weather years.
   2025 currently uses NESO's historic generation mix and Elexon MID/FUELHH as the reference; confirm.
7. *needs human*: choose what to pursue next among hydrogen (H2 storage/network vs exogenous price),
   strategic BM bidding, nodal/ETYS network in the loop, and RL agents.
8. Interconnector capacity after 2031: the register is flat at 14.7 GW from FAB Link (2031) to 2050, below
   FES net-zero pathways; add dated pipeline projects (LionLink, Nautilus, MaresConnect, Tarchon, …) from the
   NESO/Ofgem pipeline, or a sourced `ic_growth` path, so 2040s imports/exports are not capped low.
9. *needs human*: fuel and carbon price paths. The gas path (£32 → £25/MWh_th, 2025 → 2050) predates the
   2026 gas-price spike (NBP Dec-26 ~210p/therm ≈ £72/MWh_th in November 2026); decide which price
   scenarios the model should carry.

## Credits
Data extracts from PyPSA-GB (MIT), which in turn uses ESPENI, DUKES, NESO and LCCC data. Framework: Mesa, PyPSA, HiGHS.
