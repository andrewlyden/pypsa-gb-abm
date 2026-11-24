# pypsa-gb-abm — agent-based GB electricity market model linked to PyPSA-GB

A modular Python (Mesa + PyPSA) agent-based model of the **GB electricity market** — hourly operation
(bidding, dispatch, pricing) and annual investment (technology choice, expectations, CfD / Capacity
Market / carbon policy) — linked to [PyPSA-GB](https://github.com/andrewlyden/PyPSA-GB) data and its
zonal network, with **multi-energy coupling** to heat (household heat-pump agents), gas networks, EVs
and hydrogen.

> ⚠️ Prototype for a workshop. Uncalibrated; numbers are illustrative. See [assumptions](docs/assumptions.md).

* Research: [literature review](docs/research/literature_review.md) ·
  [capability-vs-challenge matrix](docs/research/capability_matrix.md) ·
  [gap analysis](docs/research/gap_analysis.md)
* Design: [model design](docs/model_design.md) · [assumptions & limitations](docs/assumptions.md)

## Quick start
```bash
pip install -e .            # numpy pandas scipy matplotlib mesa pypsa highspy
pytest -q                   # 6 tests, ~30 s
python scripts/run_scenarios.py baseline --end 2030      # ~40 s
python scripts/run_scenarios.py                          # all 6 scenarios 2025-2050 (~4 min each)
python scripts/make_plots.py                             # -> docs/figures/
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
```

## Headline results (single seed, illustrative)
| scenario | price 2030 / 2050 (£/MWh) | CI 2050 (g/kWh) | LOLE total 2025-50 (h) | HP homes 2050 |
|---|---|---|---|---|
| baseline | 77 / 31 | 9 | 0 | 6.7 m |
| high_carbon (£300/t 2050) | 84 / 40 | 4 | 0 | 6.0 m |
| no_cfd | 82 / 89 | 26 | 7 | 4.4 m |
| no_capacity_market | 1328 / 37 | 8 | 13,228 | 3.8 m |
| heat_push (£11.5k grant, £25/MWh levy rebalancing) | 82 / 48 | 19 | 15 | 27.3 m |
| high_gas (£45/MWh_th) | 100 / 47 | 14 | 0 | 14.8 m |

Qualitative messages: CfDs drive offshore wind and lower long-run prices; removing the CM produces a
missing-money scarcity episode before merchant entry responds (classic ABM investment cycle); high gas
prices and levy rebalancing both accelerate heat-pump uptake, which raises winter peak and carbon intensity
until the fleet catches up.

![scenarios](docs/figures/scenario_comparison.svg)
![capacity](docs/figures/capacity_mix.svg)

## STATUS / roadmap (workshop: Tuesday)

| area | status |
|---|---|
| Hourly GB market clearing (agent offers, ORDC scarcity, interconnector tranches) | ✅ works, unit-tested |
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
| Calibration/validation vs 2020–24 outturn, multi-seed Monte-Carlo, weather years | ❌ not started |

**Before Tuesday (priority order)**
1. Multi-seed runs (5 seeds) for baseline + 2 policy scenarios; show bands not lines.
2. Sanity-check 2025 against outturn (price ~£75–80/MWh ✅, CI ~ 47 g/kWh vs ~125 actual ❌ — imports & biomass too high, CCGT too low).
3. Fix network stage: use PyPSA-GB Reduced 32-bus network & zonal wind profiles (Scottish vs English wind) — constraint costs should rise.
4. Add battery ancillary/BM revenue; check CM over-procurement of OCGT (CM clears at cap every year: target too high with unmanaged EV peak).
5. Present heat_push vs baseline loop (HP uptake ↔ prices ↔ gas tariffs) as the multi-energy headline.

## Credits
Data extracts from PyPSA-GB (MIT), which in turn uses ESPENI, DUKES, NESO and LCCC data. Framework: Mesa, PyPSA, HiGHS.
