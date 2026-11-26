---
title: pypsa-gb-abm
---
# Agent-based modelling of the GB (multi-)energy market

**What:** a Mesa + PyPSA agent-based model of the GB electricity market (operation + investment + policy),
linked to [PyPSA-GB](https://github.com/andrewlyden/PyPSA-GB), with heat, gas, EV and hydrogen coupling.
**Status:** prototype — 2025 operation calibrated against GB outturn ([assumptions](assumptions.md#2025-calibration-vs-outturn)); 2026-2050 pathway illustrative.

## 1. Research
* [Literature & framework survey](research/literature_review.md) — AMIRIS, EMLab-Generation, ASSUME, PowerACE, ElecSim, AMES, Mesa, CNZ heat ABM, EV & H2 ABMs, PyPSA-GB.
* [Capability vs UK challenge matrix](research/capability_matrix.md) ([CSV](research/capability_matrix.csv))
* [Gap analysis & scope decision](research/gap_analysis.md)

## 2. Model design
* [Architecture, agents, annual loop, extension hooks](model_design.md)
* [Assumptions & limitations](assumptions.md)

## 3. Optimal versus emergent
How far the system the agents build is from the least-cost plan, where the gap comes from, and which
market designs close it: [the gap](gap.md). First measurement (illustrative, 3 seeds): the baseline costs
about £32bn (10 %) more than the optimum over 2025–54, mostly in what is built; without CfDs the gap
nearly doubles, without the Capacity Market it halves.

![Gap over time](figures/gap_over_time.svg)
![Gap ladder](figures/gap_ladder.svg)

## 4. Results (baseline + 5 scenarios, 2025-2050)
Multi-seed bands (median, min–max of 5 seeds) for baseline, no_cfd and heat_push:
![Ensemble bands](figures/ensemble_bands.svg)

Single seed, all scenarios:
![Scenario comparison](figures/scenario_comparison.svg)
![Capacity](figures/capacity_mix.svg)
![Generation](figures/generation_mix.svg)
![Multi-energy](figures/multienergy.svg)
![Policy & network costs](figures/policy_costs.svg)
![Winter week](figures/winter_week.svg)
![Price duration](figures/price_duration.svg)
![Zonal network](figures/zonal_network.svg)

## 5. Usage
```bash
pip install -e . && pytest -q
python scripts/run_scenarios.py && python scripts/run_gap.py && python scripts/make_plots.py
```
See the [README](https://github.com/andrewlyden/pypsa-gb-abm#readme) for the STATUS / roadmap.
