"""CfD bids from the firm's own expectations (decision_logic "expectations")."""
import copy
import logging
import warnings

import numpy as np
import pytest

from ukabm import GBMarketModel, get_scenario
from ukabm.decisions import ExpectationBids, make

warnings.filterwarnings("ignore")
logging.disable(logging.INFO)


@pytest.fixture(scope="module")
def setup():
    m = GBMarketModel(get_scenario("baseline"), seed=3, end=2025, network_every=0)
    return m, m.forecast(2028)


def bid(m, g, tech, fc, seed=0):
    m.rng = np.random.default_rng(seed)          # same noise draw for each comparison
    return ExpectationBids().cfd_bid(m.observation(g, "cfd_bid", tech=tech, forecast=fc))


def test_registered_and_selectable():
    assert isinstance(make("expectations"), ExpectationBids)


def test_higher_expected_prices_lower_the_bid(setup):
    m, fc = setup
    g = next(g for g in m.gencos if g.expectation == "adaptive")
    for tech in ("wind_offshore", "wind_onshore", "solar"):
        assert bid(m, g, tech, fc * 1.5) < bid(m, g, tech, fc)      # a more valuable merchant tail


def test_dearer_capital_and_risk_aversion_raise_the_bid(setup):
    m, fc = setup
    g = copy.copy(next(g for g in m.gencos if g.expectation == "adaptive"))
    base = bid(m, g, "wind_offshore", fc)
    g.wacc += 0.02
    assert bid(m, g, "wind_offshore", fc) > base
    g.wacc -= 0.02
    g.risk_aversion += 0.2
    assert bid(m, g, "wind_offshore", fc) > base


def test_myopic_firms_use_this_years_prices(setup):
    m, fc = setup
    g = copy.copy(m.gencos[0])
    g.expectation = "myopic"
    m.last_price = None
    with_forecast = bid(m, g, "solar", fc)                         # no history yet: falls back to forecast
    m.last_price = fc * 0.5
    assert bid(m, g, "solar", fc) > with_forecast                   # a poorer recent year, a higher bid
    m.last_price = None


def test_runs_with_the_target_tracking_government():
    sc = get_scenario("baseline")
    sc.update(decision_logic="expectations", government="targets")
    r = GBMarketModel(sc, seed=3, end=2026, network_every=0).run()
    assert r.cfd_awarded_mw.sum() > 0
