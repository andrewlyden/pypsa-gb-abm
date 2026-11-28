# Contributing

This repository holds the model `ukabm` (package) and the scripts and data that produce its results.
It is maintained by Andrew Lyden (University of Edinburgh, GitHub `andrewlyden`). Contributions are
welcome as pull requests; this page says how to set up, how changes are made and reviewed, and what
every change must record.

## Set up

Python 3.11 or later is required (the scenario files are read with `tomllib`).

```bash
git clone https://github.com/andrewlyden/pypsa-gb-abm.git
cd pypsa-gb-abm
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e .[dev]          # the model and pytest
pip install -e .[raw]          # only to rebuild the PyPSA-GB snapshot (pyproj, openpyxl)
pip install markdown           # only for scripts/build_docs.py
```

The model runs from the data in `data/`; no download is needed. The scripts that rebuild data
(`scripts/build_*.py`, `scripts/fetch_*.py`) call public APIs that need no key.

## Run the tests

```bash
pytest -q                      # the test suite; long runs are skipped
UKABM_SLOW=1 pytest -q         # also the tests marked slow (e.g. the convergence test)
pytest tests/test_market.py -q # one file
```

The same suite runs on GitHub Actions for every push and pull request (`.github/workflows/tests.yml`,
Python 3.11). A change that alters results should come with a test that pins the new behaviour, and
existing tests that change their expected numbers should say why in the commit message.

## Branches and pull requests

1. Create a branch from `main` for one piece of work (`git checkout -b roadmap/<item>-<short-name>`
   is the convention used so far). Do not commit to `main`.
2. Commit in steps that each leave the model working. Say in the commit message what changed for a
   user of the model and, if results move, by how much.
3. Open a pull request against `main`. Describe what changed, which results were re-run, and which
   documents were updated.
4. The maintainer reviews and merges. Contributors do not merge their own pull requests.

## What every change must record

* **A new or changed constant** (in `ukabm/config.py`, a module-level or class constant, a
  constructor default, or a number written inline that changes results) gets a row in
  [docs/parameters.md](docs/parameters.md): name, value, unit, status and where it is used. The status
  is exactly one of `sourced` (a published value: name the publisher and document in the code comment
  and in the register), `measured` (computed from data in the repository: say which file),
  `calibrated` (set so the model matches an observation: say which, and in which year) or `assumed`
  (your judgement; write ASSUMPTION in the code comment). A value without a source in the code comment
  is `assumed`.
* **A new dataset** (a file under `data/`, or a download by a script) gets a row in
  [docs/data.md](docs/data.md): path, content, source (publisher, document, edition or date, URL),
  licence, the attribution the licence requires, and the script that builds it. If you cannot find
  the licence, write "not stated" and add the dataset to the licence questions in that file; do not add
  data whose licence forbids redistribution under the repository's MIT licence. Values read by hand
  carry a `source`, `url` and `verified` column in the CSV (`read`, `search` or `secondary`).
* **A new scenario key** must be declared in `ukabm.scenarios.SCENARIO_KEYS` with a one-line
  description; the model raises an error on any key that is not declared. New fields of
  `config.Policy`, `config.Fuels` or `config.RESERVE` are accepted in the `policy`, `fuels` and
  `reserve` sub-tables automatically. Scenarios themselves are defined in `ukabm/data/scenarios.toml`.
* **A change to agent or planner behaviour** should be described in [docs/odd.md](docs/odd.md) (the
  model description) and, where it changes results, followed by a re-run of the affected results.
* **AI assistance**: if code, data or text was written with an AI assistant, say so in the commit
  (the repository uses `Co-Authored-By` trailers) and state how you checked it; see
  [docs/ai_use.md](docs/ai_use.md).

## How results are regenerated

Results in `results/` and figures in `docs/figures/` are written by scripts and committed by hand.
State in the pull request which ones you re-ran and at which commit.

**Model runs**

| Script | What it does |
|---|---|
| `scripts/run_scenarios.py` | Runs the scenarios of `ukabm/data/scenarios.toml` (all, or those named) and saves annual results and selected hourly data (`results/annual_<scenario>.csv`). |
| `scripts/run_ensemble.py` | Multi-seed ensembles: one annual results CSV per scenario in long format, column `seed` (default baseline, no_cfd, heat_push × 5 seeds). |
| `scripts/run_gap.py` | Optimal versus emergent: planner benchmark, agent runs and the gap between them (ladder, levers, and the "pathway limits" and reserve sensitivities); writes `results/gap_costs.csv`, `gap_capacity.csv`, `gap_annual.csv`, `gap_summary.csv`. Takes hours. |
| `scripts/run_convergence.py` | Convergence test: runs the `competitive_benchmark` scenario through `ukabm.gap` and writes `results/convergence_summary.md` and `results/convergence_*.csv` (about 1 h for 3 seeds). |
| `scripts/run_planner_sensitivity.py` | How far the optimum, and so the investment gap, moves with the planner's own assumptions (build limits, VoLL, carbon value, cost of capital); writes `results/planner_sensitivity.json` and `.md` (about 90 min). |
| `scripts/run_backcast.py` | Operating back-cast: runs each year 2021–2025 on its own weather, fleet, interconnectors, neighbour prices and money-of-the-day fuel and carbon prices, and compares with GB outturn (`results/backcast.md`, `results/backcast.csv`). |

**Comparisons and checks**

| Script | What it does |
|---|---|
| `scripts/compare_outturn.py` | Compares the model's 2025 with GB outturn and writes `results/calibration_2025.md`. |
| `scripts/compare_pathways.py` | Compares the model's future years with published pathways (FES 2025, CCC Seventh Carbon Budget, Clean Power 2030) and writes `results/pathways_comparison.md`, marking each quantity as driver, target or result. |
| `scripts/check_auctions.py` | Checks the model's first CfD round against Allocation Round 7 and its first T-4 Capacity Market auction against the 2029/30 auction, without fitting anything (`results/auction_check.md`). |
| `scripts/replay_cfd_rounds.py` | Sets the cleared strike of every CfD allocation round beside the levelised cost in the government's generation-cost report current at the time, to show whether bidders' deviation from published costs is stable (`results/cfd_rounds_replay.md`). |
| `scripts/make_plots.py` | Makes figures from `results/` into `docs/figures/`. |

**Data builds** (run only when the inputs change; each prints its checks)

| Script | What it does |
|---|---|
| `scripts/build_profiles.py <year> ...` | Builds hourly GB demand, onshore and offshore wind and solar profiles of one or more weather years from NESO and Elexon open data, with checks against DESNZ and NESO (`data/profiles/`). |
| `scripts/build_fleet.py` | Builds the starting fleet (`data/fleet/fleet_2025.csv`) and the contracted pipeline (`pipeline_2025.csv`) from the DUKES station list, GB capacity by year and the CfD register. |
| `scripts/build_costs.py` | Builds the technology cost table `data/parameters/cost_paths.csv` from DESNZ *Electricity Generation Costs 2025* (`data/history/desnz_generation_costs.csv`). |
| `scripts/build_history.py` | Builds the annual historical inputs `data/history/annual_inputs.csv` (gas, coal, carbon and power prices 2010–2025, deflator, exchange rate) from `data/history/sources/`. |
| `scripts/build_docs.py` | Builds the README and `docs/` as linked HTML pages in `site/` (not committed). |
| `scripts/fetch_outturn.py <years>` | Builds the GB annual outturn reference `data/outturn/gb_annual_outturn.csv` from NESO and Elexon. |
| `scripts/fetch_neighbour_prices.py <year>` | Fetches hourly day-ahead prices of the continental neighbours from Energy-Charts (`data/external/`). |
| `scripts/extract_pypsagb_snapshot.py <path>` | Rebuilds `data/pypsagb_snapshot/` from a local PyPSA-GB clone (needs the `raw` extra). |

## Style

Code: follow the existing style (no formatter is enforced); put the source or ASSUMPTION next to every
number. Documents: plain English, full sentences, numbers with units, tables for tabular content.
