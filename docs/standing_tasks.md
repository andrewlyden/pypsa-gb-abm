# Standing tasks

Pre-approved work the build agent may do **without a proposal or roadmap entry**, but only when no item in
the README's roadmap priority list is actionable (all done, *needs human*, or already covered by an open
pull request). Take them roughly in the order listed. One task per pull request, same rules as roadmap
items (branch, tests, PR body, `agent` label). The maintainer can edit this list at any time.

1. **Reviewer follow-ups.** Nice-to-have items from review comments on merged agent pull requests that
   were not done at the time.
2. **Test coverage.** Add meaningful tests for untested behaviour, starting with `ukabm/multienergy.py`,
   `ukabm/network.py`, `ukabm/agents.py` and `ukabm/data/pypsagb.py` (currently only `market.py` and
   `model.py` have tests). Test behaviour and invariants (energy balance, price bounds, monotonic
   responses), not just that code runs.
3. **Ensembles.** Run 5-seed ensembles for any scenario that still has single-seed results, and keep the
   README headline table on ensemble results.
4. **Sensitivity analyses.** One key assumption from `docs/assumptions.md` per pull request (e.g. gas
   price, carbon price, hurdle rates, heat-pump grant, interconnector prices): run a low/central/high sweep,
   add the results and a short interpretation to `docs/sensitivity/<parameter>.md`.
5. **Validation depth.** Extend the outturn comparison with more metrics (e.g. annual generation by
   technology, peak demand, interconnector flows) using openly available data, documenting sources.
6. **Docs in sync.** Make `docs/model_design.md` and `docs/assumptions.md` match the code; flag anything
   undocumented.
7. **Performance.** Speed-ups that leave results identical for a fixed seed (prove it in the PR).

Never use standing tasks to start new features or change model behaviour beyond what a task describes.
