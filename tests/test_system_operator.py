"""System operator agent (ukabm.institutions.SystemOperator): Capacity Market target and T-1 auctions."""
import logging
import warnings

import pandas as pd
import pytest

from ukabm import GBMarketModel, get_scenario
from ukabm.config import TECHS

warnings.filterwarnings("ignore")
logging.disable(logging.INFO)


def model(end=2025, **keys):
    sc = get_scenario("baseline")
    sc.update(keys)
    return GBMarketModel(sc, seed=7, end=end, network_every=0)


@pytest.fixture(scope="module")
def standard_run():
    m = model(end=2027, system_operator="standard")
    m.run()
    return m


def test_formula_is_the_default_without_t1():
    m = model(end=2026)
    assert m.operator.mode == "formula" and not m.operator.t1
    m.run()
    assert all(a["ahead"] == 4 for a in m.cm_log)


def test_reliability_standard_matches_the_published_t4_target():
    # Published T-4 target for delivery 2029/30: 39.4 GW de-rated (NESO / Modo Energy). The old formula
    # gives ~49 GW; the reliability standard should be within 10 %.
    m = model(system_operator="standard")
    full, _ = m.operator.full_target(2029)
    t4 = full * (1 - m.operator.params["t1_holdback"])       # the published 39.4 GW is the T-4 target after holdback
    assert abs(t4 / 1e3 - 39.4) / 39.4 < 0.05
    assert m.operator.full_target(2029)[0] < model().operator.full_target(2029)[0]


def test_holdback_goes_to_t1_auctions(standard_run):
    m = standard_run
    log = pd.DataFrame(m.operator.log)
    h = m.operator.params["t1_holdback"]
    t4 = log[log.ahead == 4]
    # T-4 buys the full target less the T-1 holdback and less capacity already holding agreements
    assert (t4.target_mw - (t4.full_mw * (1 - h) - t4.held_mw)).abs().max() < 1e-6
    t1 = log[log.ahead == 1]
    assert (t1.target_mw <= t1.full_mw).all()
    cm = pd.DataFrame(m.cm_log)
    assert (cm.ahead == 1).sum() == len(t4)                         # one T-1 per year
    biggest = max(t.chunk_mw * t.derating for t in TECHS.values())
    assert (cm.procured_mw <= cm.target_mw + 1500 + biggest).all()


def test_unknown_system_operator_raises():
    with pytest.raises(KeyError):
        model(system_operator="no_such_operator")
