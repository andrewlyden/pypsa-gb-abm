"""Reserve and response in the optimum and the evaluator (README roadmap item 9)."""
import logging
import warnings

import numpy as np
import pandas as pd
import pytest

from ukabm import GBMarketModel, get_scenario
from ukabm.config import RESERVE
from ukabm.costs import total
from ukabm.planner import _add_reserve, evaluate, reserve_settings

warnings.filterwarnings("ignore")
logging.disable(logging.INFO)

S = dict(RESERVE, response_mw=3.0, vre_share=0.1, load_share=0.0, hours=1.0, shortfall_cost=1000.0)


def _solve(n, s, **kw):
    import pypsa  # noqa: F401
    status, _ = n.optimize(solver_name="highs", solver_options={"output_flag": False},
                           extra_functionality=lambda n_, _s: _add_reserve(n_, s), **kw)
    assert status == "ok"
    return n


def _toy():
    import pypsa
    n = pypsa.Network()
    n.set_snapshots(pd.RangeIndex(6))
    wind = np.array([0.1, 0.5, 0.9, 0.9, 0.3, 0.0])
    n.add("Bus", "b")
    n.add("Load", "l", bus="b", p_set=100.0)
    n.add("Generator", "shed", bus="b", p_nom=1e4, marginal_cost=6000.0)
    n.add("Generator", "wind", bus="b", carrier="wind_onshore", p_nom=50.0, p_max_pu=wind, marginal_cost=0.0)
    n.add("Generator", "ccgt", bus="b", carrier="ccgt", p_nom=100.0, marginal_cost=50.0)
    n.add("Generator", "ocgt", bus="b", carrier="ocgt", p_nom=20.0, marginal_cost=100.0)
    n.add("Generator", "nuc", bus="b", carrier="nuclear", p_nom=10.0, marginal_cost=10.0)
    n.add("StorageUnit", "bat", bus="b", carrier="battery", p_nom=5.0, max_hours=2.0, marginal_cost=0.0,
          cyclic_state_of_charge=True)
    return n, wind


def test_settings_scale_and_override():
    m = GBMarketModel(get_scenario("baseline"), end=2025, network_every=0)
    assert reserve_settings(m)["response_mw"] == RESERVE["response_mw"]
    m.scenario["reserve"] = {"scale": 0}
    assert reserve_settings(m) is None                              # switched off
    m.scenario["reserve"] = {"scale": 2, "hours": 0.5}
    s = reserve_settings(m)
    assert s["vre_share"] == 2 * RESERVE["vre_share"] and s["hours"] == 0.5


def test_dispatch_holds_response_and_reserve():
    n, wind = _toy()
    _solve(n, S)
    p = n.generators_t.p
    head = {g: n.generators.at[g, "p_nom"] - p[g] for g in ("ccgt", "ocgt")}     # thermal headroom
    sp = n.storage_units_t.p
    bat_head = 5.0 - sp["bat"]
    need = 3.0 + 0.1 * 50.0 * wind                                   # response on storage + reserve
    assert (head["ccgt"] + head["ocgt"] + bat_head >= need - 1e-6).all()
    assert (bat_head >= 3.0 - 1e-6).all()                            # response is on storage only
    assert (n.storage_units_t.state_of_charge["bat"] >= 3.0 - 1e-6).all()   # with an hour of energy
    assert float(n.model["Reserve-response-shortfall"].solution.sum()) == pytest.approx(0, abs=1e-6)
    assert float(n.model["Reserve-reserve-shortfall"].solution.sum()) == pytest.approx(0, abs=1e-6)
    assert "Generator-reserve" in n.model.variables
    assert "nuc" not in n.model["Generator-reserve"].coords["name"].values   # nuclear holds none


def test_shortfall_is_costed_not_infeasible():
    n, _ = _toy()
    n.remove("StorageUnit", "bat")
    _solve(n, S)                                                     # no storage: response cannot be held
    short = n.model["Reserve-response-shortfall"].solution.values
    assert np.allclose(short, 3.0)


def test_planner_builds_storage_for_response_and_masks_inactive_assets():
    import pypsa
    n = pypsa.Network()
    snaps = pd.MultiIndex.from_product([[2025, 2030], range(4)], names=["period", "timestep"])
    n.set_snapshots(snaps)
    n.investment_periods = [2025, 2030]
    n.add("Bus", "b")
    n.add("Load", "l", bus="b", p_set=10.0)
    n.add("Generator", "shed", bus="b", p_nom=1e4, marginal_cost=6000.0, build_year=2025, lifetime=100)
    n.add("Generator", "base", bus="b", carrier="nuclear", p_nom=20.0, marginal_cost=1.0,
          build_year=2025, lifetime=100)
    # an old battery that closes before 2030: it may hold response in 2025 only
    n.add("StorageUnit", "old_bat", bus="b", carrier="battery", p_nom=5.0, max_hours=2.0,
          build_year=2020, lifetime=10, cyclic_state_of_charge=True, cyclic_state_of_charge_per_period=True)
    n.add("StorageUnit", "new_bat", bus="b", carrier="battery", p_nom_extendable=True, capital_cost=1.0,
          max_hours=2.0, build_year=2030, lifetime=20, cyclic_state_of_charge=True,
          cyclic_state_of_charge_per_period=True)
    s = dict(S, response_mw=3.0, vre_share=0.0)
    status, _ = n.optimize(multi_investment_periods=True, solver_name="highs",
                           solver_options={"output_flag": False},
                           extra_functionality=lambda n_, _s: _add_reserve(n_, s))
    assert status == "ok"
    assert n.storage_units.at["new_bat", "p_nom_opt"] == pytest.approx(3.0, rel=1e-6)
    rf = n.model["StorageUnit-response"].solution.sel(name="old_bat").values
    per = snaps.get_level_values(0)
    assert np.allclose(rf[per == 2030], 0.0)                          # closed plant holds nothing


@pytest.fixture(scope="module")
def run2030():
    m = GBMarketModel(get_scenario("baseline"), seed=1, end=2030, network_every=0)
    m.run()
    return m, m.hourly[2030]["load"].values


def test_evaluator_with_and_without_the_requirement(run2030):
    m, load = run2030
    on = evaluate(m, 2030, m.plants, load)
    m.scenario["reserve"] = {"scale": 0}
    try:
        off = evaluate(m, 2030, m.plants, load)
    finally:
        del m.scenario["reserve"]
    assert on["reserve_shortfall_mwh"] < 1.0 and off["reserve_shortfall_mwh"] == 0.0
    assert total(off["costs"]) <= total(on["costs"]) <= total(off["costs"]) * 1.01
