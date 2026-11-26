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
pytest -q                   # 10 tests, ~40 s
python scripts/run_scenarios.py baseline --end 2030      # ~40 s
python scripts/run_scenarios.py                          # all 6 scenarios 2025-2050 (~4 min each)
python scripts/make_plots.py                             # -> docs/figures/
python scripts/compare_outturn.py                        # 2025 vs GB outturn -> results/calibration_2025.md
python scripts/run_ensemble.py                           # baseline, no_cfd, heat_push x 5 seeds
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
ukabm/network.py       BM-style redispatch (bids/offers) on the PyPSA-GB zonal network, ETYS boundary limits
ukabm/data/pypsagb.py  PyPSA-GB adapter (raw clone or bundled snapshot)
ukabm/scenarios.py     baseline, high_carbon, no_cfd, heat_push, no_capacity_market, high_gas
ukabm/outturn.py       model-vs-outturn comparison (data/outturn: NESO generation mix + CI, Elexon)
ukabm/ensemble.py      multi-seed runs (run_ensemble, parallel) and per-year bands
```

## 2025 calibration (baseline, seed 42) vs GB outturn
| | model | outturn 2025 |
|---|---|---|
| price, time-weighted mean (£/MWh) | 83.9 | 79.9 (Elexon MID) |
| carbon intensity, NESO basis: wholesale / after BM redispatch (g/kWh) | 113 / 124 | 130 (NESO, generation-weighted) |
| gas / wind after BM redispatch (TWh) | 76 / 87 | 77 / 86 |
| nuclear / biomass (TWh) | 35 / 20 | 34 / 20 |
| imports / exports (TWh) | 45 / 15 | 44 / 15 (Elexon FUELHH) |
| constraint cost (£bn) | 1.04 | 1.83, of which ~0.54 BM premia not modelled (LCP Delta 2026, NESO data) |
| renewable turn-down in the BM (TWh) | 7.8 | 10.4 |

The network stage redispatches the copperplate schedule on the PyPSA-GB zones with dated ETYS boundary
capabilities. It turns down Scottish wind behind B4/B6 and turns up gas in England, which closes most of the CI gap.
Remaining residuals: the model has no CHP/waste "other" generation (4.7 TWh, ~+5 g/kWh) and its price
distribution is too narrow (no negative hours). Full table: [results/calibration_2025.md](results/calibration_2025.md).

## Headline results (single seed, illustrative)
| scenario | price 2030 / 2050 (£/MWh) | CI 2050 (g/kWh), direct (NESO basis) | LOLE total 2025-50 (h) | HP homes 2050 | batteries 2030 / 2050 (GW) |
|---|---|---|---|---|---|
| baseline | 81 / 39 | 12 (18) | 0 | 6.0 m | 12 / 28 |
| high_carbon (£300/t 2050) | 88 / 44 | 8 (12) | 0 | 5.2 m | 12 / 33 |
| no_cfd | 86 / 81 | 26 (37) | 0 | 4.0 m | 9 / 7 |
| no_capacity_market | 90 / 49 | 10 (16) | 468 | 5.1 m | 7 / 17 |
| heat_push (£11.5k grant, £25/MWh levy rebalancing) | 85 / 50 | 14 (20) | 0 | 27.3 m | 12 / 26 |
| high_gas (£45/MWh_th) | 104 / 58 | 16 (23) | 0 | 13.3 m | 13 / 42 |

Qualitative messages: CfDs drive offshore wind and lower long-run prices; removing the CM produces a
missing-money scarcity episode (2027-29, ~400 h, annual mean prices ~£320/MWh) before merchant entry responds (classic
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
| Storage arbitrage (battery, pumped hydro), smart EV valley-filling, electrolysers | ✅ works (heuristic, perfect intra-day foresight; storage fleet dispatched in price-aware tranches) |
| Merchant investment (5 heterogeneous GenCos, NPV on re-forecast prices) | ✅ works |
| CfD allocation rounds with pots; 2-way CfD settlement | ✅ works (simplified: no £ budget) |
| T-4 Capacity Market with sloping demand curve | ✅ works (no T-1, no penalties) |
| Retirement on persistent losses / end of life | ✅ works |
| PyPSA-GB link: zonal network, ESPENI profiles, DUKES siting, IC register, CM/CfD data | ✅ works (bundled snapshot or live clone) |
| Network stage: BM-style redispatch (bids/offers) on PyPSA-GB zones with dated ETYS boundary capabilities and monthly availability, 96 wind-stratified hours | ✅ 2025: £1.04bn vs £1.29bn outturn excl. BM premia; 7.8 vs 10.4 TWh turn-down; post-BM gas/wind within 1.5 TWh, CI 6 g/kWh low. Boundary cuts tested for bypass routes. ⚠️ Single GB wind shape for all zones; ~£0 in 2030–35 (see roadmap); redispatch is reported only, not settled |
| Heat-pump household agents + gas network tariff feedback | ✅ works (stylised, synthetic temperature) |
| Hydrogen: electrolysers + H2 turbine tech | ⚠️ stub-level: exogenous H2 price, no H2 storage/network |
| Batteries: revenue stack (day-ahead arbitrage + ancillary and intraday/BM pots shared across the fleet + CM) | ✅ 2025 stack £64k/MW/yr before CM (Modo index £73k incl. CM); batteries enter via CM and merchant NPV, 12 GW by 2030 and 26–42 GW by 2050. ⚠️ Stylised pots; low against Clean Power 2030 (23–27 GW by 2030) |
| Strategic BM bidding, nodal/ETYS network in loop, RL agents | ❌ not started |
| Price distribution | ⚠️ too narrow: no negative hours (244 in 2025), p05 £54 vs £9, p95 £100 vs £123 (no unit commitment / must-run, no scarcity tail) |
| Back-casts 2020–24, multi-seed Monte-Carlo, weather years, CI tolerance test | ❌ not started (2025 only) |

**Next (priority order)**

The daily agent takes the highest unfinished item it can complete in one run. Items marked
*needs human* are decisions for the maintainer and are skipped by the agent.

1. Multi-seed runs (5 seeds) for baseline + 2 policy scenarios; show uncertainty bands, not single lines,
   in the plots and the headline table.
2. Network follow-ups (2025 constraint cost and turn-down are now within 20–25 % of outturn, both low):
   (a) constraint cost drops to ~£0 in 2030–35 in every scenario. LCP Delta (Mar 2026) projects £6.1bn in
   2030 under FES25 Holistic Transition (47 GW offshore, 41 TWh turn-down) and a £4.2bn peak in its
   slower-build Central case (36 GW). The model has only 17 GW offshore in 2030, and the Holistic
   Transition boundary build-out (B6 10→17 GW, EGL1–4) arrives on time. It also has no East Anglia (EC5)
   constraint, which drives LCP's 2030 peak. Check the offshore build rate (CfD delivery and lead times;
   AR6/AR7 awards) against the 2030 pipeline, represent EC5, and consider a delayed-network sensitivity. (b) Zonal wind profiles: Scottish and English wind
   currently share one GB shape. (c) Interconnector and storage positions are held fixed in the
   redispatch. Where that leaves load unserved behind a constraint, the stage reports it as
   `network_shed_twh` (0.01 TWh in 2025, 0.76 TWh in no_capacity_market 2050). Consider allowing
   interconnector counter-trades. (d) By 2050 redispatch adds 5–15 g/kWh to NESO-basis CI
   (`intensity_neso_post_bm_g_kwh`), which the headline CI does not include yet.
3. Capacity Market target (the battery revenue stack is done). The model's T-4 target for 2029/30 is
   49.0 GW de-rated, against the published 39.4 GW. The published 2028/29 auction had a 43.7 GW target
   and procured 43.0 GW (Modo Energy, Feb 2026 and Mar 2025). Most model auctions are under-subscribed and
   clear at the £75/kW cap; GB's 2029/30 T-4 cleared at £27.10/kW. Reconcile the target (unmanaged HP/EV
   peak, T-1 holdback, de-rating factors) and check the `cm_new_chunks` entry cap; OCGT still reaches
   20–40 GW by 2050. Related: the 2025 price distribution is too narrow (no negative hours, p95 £100 vs
   £123), which understates arbitrage spreads; consider must-run/min-stable generation and RO bidding.
   Battery capex (£600/kW for 2 h) also looks high against 2025 project costs and needs a source.
4. Validation check: tolerance bands (in `docs/assumptions.md`) on the `ukabm.outturn.compare` table for
   2025 (price, CI, generation mix, flows) and a test, so regressions show up in CI.
5. Write up the heat_push vs baseline loop (HP uptake ↔ prices ↔ gas tariffs) as a docs page: the
   multi-energy headline result.
6. *needs human*: decide whether to extend validation to 2020–24 back-casts and multiple weather years.
   2025 currently uses NESO's historic generation mix and Elexon MID/FUELHH as the reference; confirm.
7. *needs human*: choose what to pursue next among hydrogen (H2 storage/network vs exogenous price),
   strategic BM bidding, nodal/ETYS network in the loop, and RL agents.
8. *needs human*: fuel and carbon price paths. The gas path (£32 → £25/MWh_th, 2025 → 2050) predates the
   2026 gas-price spike (NBP Dec-26 ~210p/therm ≈ £72/MWh_th in November 2026); decide which price
   scenarios the model should carry.

## Credits
Data extracts from PyPSA-GB (MIT), which in turn uses ESPENI, DUKES, NESO and LCCC data. Framework: Mesa, PyPSA, HiGHS.
