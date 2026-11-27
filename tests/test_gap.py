import logging
import warnings

import numpy as np
import pytest

from ukabm import GBMarketModel, get_scenario
from ukabm.config import Fuels, TECHS
from ukabm.costs import Unit, crf, fixed_costs, present_value, total
from ukabm.planner import evaluate, plan
from ukabm.scenarios import IDEAL_TRAITS, with_ideal

warnings.filterwarnings("ignore")
logging.disable(logging.INFO)


@pytest.fixture(scope="module")
def run2030():
    m = GBMarketModel(get_scenario("baseline"), seed=1, end=2030, network_every=0)
    r = m.run()
    loads = {y: m.hourly[y]["load"].values for y in (2025, 2030)}
    return m, r, loads


def test_gas_path_central_override_and_adder():
    f = Fuels()
    assert f.gas(2025) == 32.0 and f.gas(2027) == 63.0 and f.gas(2050) == 25.0
    assert 45.0 > f.gas(2029) > 35.0                                  # linear between points
    assert f.gas(2060) == 25.0                                        # flat after the last point
    lin = Fuels(gas_2025=40.0, gas_2050=20.0)
    assert lin.gas(2025) == 40.0 and np.isclose(lin.gas(2037.5), 30.0)
    assert np.isclose(Fuels(gas_adder=15.0).gas(2027), 78.0)
    assert Fuels(gas_adder=15.0).price("gas", 2040) == f.price("gas", 2040) + 15.0


def test_cost_helpers():
    assert np.isclose(crf(0.035, 25) * sum(1.035 ** -k for k in range(1, 26)), 1.0)
    old = Unit("ccgt", 1000, 2010, 2030)
    new = Unit("ccgt", 1000, 2028, 2052)
    c = fixed_costs([old, new], 2029, start=2025)
    t = TECHS["ccgt"]
    assert np.isclose(c["fom"], 2 * t.fom * 1e6)
    assert np.isclose(c["capex"], t.capex * 1e6 * crf(0.035, t.life))   # the pre-start unit is sunk
    assert fixed_costs([new], 2027, start=2025) == {"capex": 0.0, "fom": 0.0}
    assert np.isclose(present_value({2025: 1.0}, 0.0, 2025, step=5), 5.0)
    assert np.isclose(present_value({2026: 1.035}, 0.035, 2025), 1.0)


def test_idealised_agent_traits():
    m = GBMarketModel(with_ideal(get_scenario("baseline"), ["capital", "strategic"]), end=2025, network_every=0)
    for g in m.gencos:
        assert g.wacc == IDEAL_TRAITS["capital"]["wacc"] and g.risk_aversion == 0.0 and g.markup == 0.0
    assert {g.expectation for g in m.gencos} != {"adaptive"}          # expectations not idealised


def test_capacity_market_does_not_procure_beyond_the_demand_curve(run2030):
    m, _, _ = run2030
    biggest = max(t.chunk_mw * t.derating for t in TECHS.values())
    for a in m.cm_log:
        assert a["procured_mw"] <= a["target_mw"] + 1500 + biggest


def test_system_cost_components_and_evaluator_consistency(run2030):
    m, r, loads = run2030
    parts = r.filter(like="syscost_").drop(columns="syscost_bn")
    np.testing.assert_allclose(parts.sum(1), r.syscost_bn)
    assert (r.syscost_fom_bn > 0).all() and (r.syscost_fuel_bn > 0).all()
    assert r.loc[2025, "syscost_capex_bn"] == 0.0                     # nothing new online in the first year
    # least-cost dispatch of the same 2025 fleet is no dearer than the market outcome, and close to it
    ev = total(evaluate(m, 2025, m.plants, loads[2025])["costs"]) / 1e9
    assert ev <= r.loc[2025, "syscost_bn"] * 1.001
    assert ev >= r.loc[2025, "syscost_bn"] * 0.97


def test_planner_without_new_build_reproduces_the_starting_fleet(run2030):
    m, _, loads = run2030
    p = plan(m, loads, build_limits={})
    assert p.units == [] and p.built_mw.to_numpy().sum() == 0


def test_planner_pathway_is_no_dearer_than_the_agents(run2030):
    m, _, loads = run2030
    p = plan(m, loads)
    assert p.built_mw.loc[2025].sum() == 0                            # no new build in the first period
    assert p.built_mw.loc[2030, "wind_offshore"] > 0
    # lead times: offshore (5 y) can reach 2030 only from 2025 decisions, one year of build
    from ukabm.config import PLANNER_BUILD_MW_PER_YEAR
    assert p.built_mw.loc[2030, "wind_offshore"] <= PLANNER_BUILD_MW_PER_YEAR["wind_offshore"] + 1
    assert p.built_mw.loc[2030, "wind_onshore"] <= 3 * PLANNER_BUILD_MW_PER_YEAR["wind_onshore"] + 1
    planner = total(evaluate(m, 2030, list(m.initial_fleet) + p.units, loads[2030])["costs"])
    agents = total(evaluate(m, 2030, m.plants, loads[2030])["costs"])
    assert planner <= agents
