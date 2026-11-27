"""Convergence test (roadmap item 7): the competitive benchmark against the least-cost plan."""
import logging
import os
import warnings

import pytest

from ukabm import SCENARIOS, GBMarketModel, get_scenario
from ukabm.decisions import ExpectationBids
from ukabm.scenarios import BENCHMARKS, IDEAL_TRAITS

warnings.filterwarnings("ignore")
logging.disable(logging.INFO)


def test_benchmark_is_textbook_and_not_a_policy_scenario():
    assert "competitive_benchmark" in BENCHMARKS and "competitive_benchmark" not in SCENARIOS
    m = GBMarketModel(get_scenario("competitive_benchmark"), seed=1, end=2025, network_every=0)
    assert not m.policy.cfd_enabled and not m.policy.cm_enabled and m.scarcity_on is False
    for g in m.gencos:
        assert isinstance(g.decider, ExpectationBids)
        assert g.wacc == IDEAL_TRAITS["capital"]["wacc"] and g.markup == 0.0 and g.risk_aversion == 0.0
    assert GBMarketModel(get_scenario("baseline"), seed=1, end=2025, network_every=0).scarcity_on is True


def test_without_the_adder_prices_rise_only_with_unserved_energy():
    m = GBMarketModel(get_scenario("competitive_benchmark"), seed=1, end=2025, network_every=0)
    r = m.run()
    h = m.hourly[2025]
    assert r.loc[2025, "price_max"] < m.policy.voll or r.loc[2025, "unserved_gwh"] > 0
    assert (h.price <= 1000).mean() > 0.99


@pytest.mark.slow
@pytest.mark.skipif(not os.environ.get("UKABM_SLOW"), reason="long run: set UKABM_SLOW=1")
def test_competitive_benchmark_converges_on_the_plan():
    from ukabm.gap import gap_run, summarise
    out = gap_run("competitive_benchmark", seed=1, end=2035)
    s = summarise(out["costs"]).iloc[0]
    assert s.gap_total_pct < 5.0
