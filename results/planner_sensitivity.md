# Planner sensitivity: the investment gap under other values of the planner's assumptions

Scenario `baseline`, seed 1, 2025-2050; code at `8dec60c`; `scripts/run_planner_sensitivity.py`. One agent run; the planner is re-solved under each variant and both fleets are costed by the evaluator under the same variant. Present values 2025-2054 at 3.5 %, GBP bn. See [the foundations review](../docs/review_2026-11_foundations.md), section 2.

Note: run for the foundations review with the first version of this script (same calculations), in two processes.

| variant | optimum | agents' fleet | investment gap | gap % | planner 2050, GW: offshore / onshore / solar / battery / OCGT / CCGT / gas CCS | planner unserved 2050 (GWh) | emissions 2050, planner / agents (Mt) |
|---|---|---|---|---|---|---|---|
| Default | 316.4 | 344.9 | 28.5 | 9.0 | 40.4 / 57.5 / 44.7 / 0.3 / 7.3 / 7.3 / 11.7 | 129 | 4.9 / 6.2 |
| Build limits x 0.5 | 326.5 | 344.9 | 18.5 | 5.7 | 60.0 / 28.8 / 44.3 / 0.0 / 7.9 / 6.7 / 11.6 | 132 | 4.9 / 6.2 |
| Build limits x 2 | 307.2 | 344.9 | 37.7 | 12.3 | 15.5 / 111.0 / 39.1 / 0.5 / 8.2 / 8.3 / 8.5 | 132 | 4.9 / 6.2 |
| Onshore limit lifted (20 GW a year) | 299.6 | 344.9 | 45.3 | 15.1 | 3.5 / 128.9 / 37.3 / 0.0 / 8.0 / 8.6 / 8.4 | 137 | 5.0 / 6.2 |
| Wind and solar limited to the CfD volumes (3.6 / 1.2 / 1.2 GW a year) | 327.6 | 344.9 | 17.3 | 5.3 | 62.6 / 27.6 / 33.4 / 0.0 / 7.5 / 6.5 / 12.2 | 128 | 4.7 / 6.2 |
| VoLL GBP 16,950/MWh | 313.8 | 344.9 | 31.2 | 9.9 | 40.4 / 57.5 / 46.3 / 3.1 / 11.9 / 6.7 / 11.5 | 0 | 4.9 / 6.2 |
| Carbon at appraisal values (GBP 310 -> 450/t) | 335.0 | 405.6 | 70.6 | 21.1 | 49.9 / 57.5 / 56.6 / 4.8 / 0.0 / 0.0 / 26.5 | 64 | 3.0 / 6.2 |
| Capital at 7 % (planner and annuities; present values at 3.5 %) | 372.9 | 417.1 | 44.2 | 11.9 | 21.0 / 57.5 / 32.0 / 0.0 / 6.9 / 8.0 / 14.1 | 123 | 6.9 / 6.2 |

Agents' fleet in 2050 (GW): battery 24.5, ccgt 17.6, hydro 1.5, nuclear 6.5, ocgt 33.9, pumped_hydro 2.9, solar 40.9, wind_offshore 87.5, wind_onshore 34.5.
