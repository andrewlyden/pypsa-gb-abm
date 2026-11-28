# Disclosure of AI use

## What was written with AI assistance

The code, tests, data-build scripts, data extracts and documentation of this repository were written
largely with AI coding assistants (Anthropic's Claude models) under the direction of the maintainer,
Andrew Lyden. The maintainer set the research questions, the scope and the order of work, took the
decisions recorded as his in the README ("Decided by the maintainer"), and merges the pull requests.

The extent is recorded only partly in the repository:

* 42 of the 89 commits that are not merges (at commit a47ec5f) carry a `Co-Authored-By` trailer
  naming a Claude model. Commits without a trailer may also have been written with AI assistance; the
  repository does not record which.
* Hand-made data extracts (for example `data/fes/`, `data/history/sources/`,
  `data/history/desnz_generation_costs.csv`) were read from the source workbooks and documents in the
  same way. Their rows carry the source and a `verified` tag, but not who read them.
* The reviews in `docs/review_2026-11.md` (code review in four parts) and
  `docs/review_2026-11_foundations.md` were produced in the same working sessions; the repository does
  not state whether each reviewer was a person or an AI assistant.

## What verification exists

| Check | What it shows | Where |
|---|---|---|
| Test suite | Unit and integration tests of market clearing, settlement, auctions, government and system-operator rules, decisions and action spaces, reserve constraints, costs, drivers, fleet, network boundaries, gap accounting and scenarios (about 120 test functions in 22 files at the time of writing); runs on GitHub Actions for every push and pull request. Long tests are skipped unless `UKABM_SLOW=1` | `tests/`, `.github/workflows/tests.yml` |
| Operating back-cast | Each year 2021–2025 run on its own weather, fleet and prices and compared with GB outturn (prices, generation by fuel, trade, carbon intensity). Operating parameters were set on 2025 only, so 2021–2024 are an out-of-sample check of operation (not of investment) | `scripts/run_backcast.py`, `results/backcast.md` |
| Auction check | The model's first CfD round and first T-4 auction against those held (AR7; T-4 2029/30), with nothing fitted to them | `scripts/check_auctions.py`, `results/auction_check.md` |
| CfD rounds replay | Every cleared CfD strike since 2015 against the official levelised cost of the day, showing that the ratio between them is not stable across rounds (the reason no bidding parameter is fitted) | `scripts/replay_cfd_rounds.py`, `results/cfd_rounds_replay.md` |
| Comparison with published pathways | The model's future years against NESO FES 2025, the CCC's Seventh Carbon Budget and Clean Power 2030, with each quantity marked as an input, a target or a result | `scripts/compare_pathways.py`, `results/pathways_comparison.md` (the output file was not yet in the repository when this page was written) |
| Convergence test | Under textbook conditions (energy-only market, idealised firms investing merchant on lifetime forecasts) the agents' system should come close to the least-cost plan; the last recorded result was within 2.6–4.1 % of the optimum's present-value cost over three seeds, produced at commit 99c6b18, before the changes of the current branch | `scripts/run_convergence.py`, `tests/test_convergence.py` (slow), `results/convergence_summary.md` |
| Source and verification tags | Every hand-read value in `data/history/sources/` and `data/fes/published_pathways.csv` names its source document and URL and is tagged `read`, `search` or `secondary`; the literature review marks each reference as read in full, abstract only or search result only | the CSV files; `docs/research/literature_review.md` |
| Data build checks | `scripts/build_profiles.py` writes a year only if wind energy and load factors agree with NESO and DESNZ within stated tolerances | `data/profiles/README.md`, `data/profiles/validation.csv` |
| Registers | Every constant with its status (sourced, measured, calibrated, assumed); every dataset with its source and licence | `docs/parameters.md`, `docs/data.md` |

## What has not been done

* **No independent human line-by-line review of the whole code base.** No person has reviewed every
  module line by line, independently of the AI assistants that wrote it.
* **No independent replication of a headline number in another model.** The gap, the 2050 fleet and the
  back-cast results have not been reproduced in a separate code base (for example dispatch of one year
  in PyPSA-GB or ASSUME), as proposed in README roadmap item 51.
* No mutation testing of the test suite, and no run-time checks of invariants such as energy balance or
  payments equalling receipts in every run (also item 51).
* No sensitivity analysis of the assumed and calibrated parameters (item 46).
* The licences of several datasets are not settled (see the licence questions in `docs/data.md`).

Readers should treat results accordingly: the tests and checks above show that the code does what its
documentation says in the cases tested and that operation in 2021–2025 is close to outturn; they do not
establish that the model's investment behaviour or its 2026–2050 results are right.
