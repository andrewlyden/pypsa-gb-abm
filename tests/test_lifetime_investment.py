"""Merchant and PPA renewables and lifetime forecasts (decision_logic "expectations", roadmap item 4)."""
import copy
import logging
import warnings

import numpy as np
import pytest

from ukabm import GBMarketModel, get_scenario
from ukabm.config import TECHS
from ukabm.decisions import ExpectationBids, RuleBased

warnings.filterwarnings("ignore")
logging.disable(logging.INFO)


@pytest.fixture(scope="module")
def setup():
    m = GBMarketModel(get_scenario("baseline"), seed=3, end=2025, network_every=0)
    return m, m.forecast(2028)


def test_long_horizon_forecasts_are_adequate_and_cached(setup):
    m, _ = setup
    hz = m.forecast_horizons()
    assert sorted(hz) == [2033, 2038]
    for p in hz.values():
        assert np.isfinite(p).all() and p.mean() < 300          # no permanent scarcity pricing
    assert m.forecast_horizons() is hz                           # cached within the model year


def test_flat_path_npv_matches_the_rules():
    margin = 120_000.0
    for tech in ("ccgt", "battery", "solar"):
        flat = ExpectationBids.path_npv(tech, {2030: margin, 2040: margin}, 2030, 0.08, 0.1)
        t = TECHS[tech]
        annuity = (1 - 1.08 ** -t.life) / 0.08
        assert flat == pytest.approx((margin * 0.9 - t.fom * 1000) * annuity - t.capex * 1000)


def test_declining_margins_lower_the_npv_and_favour_a_ppa():
    flat = ExpectationBids.path_npv("solar", {2028: 60_000.0, 2040: 60_000.0}, 2026, 0.08)
    falling = ExpectationBids.path_npv("solar", {2028: 60_000.0, 2040: 20_000.0}, 2026, 0.08)
    assert falling < flat
    ppa = ExpectationBids.path_npv("solar", {2028: 60_000.0, 2040: 20_000.0}, 2026, 0.08,
                                   first=(15, 60_000.0 * 0.9, 0.065))
    assert ppa > falling                                          # locking in today's value pays when it falls


def test_wind_and_solar_are_merchant_candidates_alongside_cfds(setup):
    m, fc = setup
    assert m.policy.cfd_enabled
    g = copy.copy(m.gencos[0])
    g.tech_preference = ["wind_onshore"]
    e = ExpectationBids()
    obs = m.observation(g, "merchant_investment", forecast=fc)
    assert RuleBased().merchant_investment(obs) is None          # the rules leave wind to the CfD
    path = e.margin_path(obs, "wind_onshore")
    online = m.year + TECHS["wind_onshore"].lead_time
    merchant = e.path_npv("wind_onshore", path, online, g.wacc, g.risk_aversion)
    ppa = e.path_npv("wind_onshore", path, online, g.wacc, g.risk_aversion,
                     first=(e.PPA_YEARS, path[m.year + 3] * (1 - e.PPA_DISCOUNT), max(g.wacc - e.PPA_RATE_CUT, 0.03)))
    decision = e.merchant_investment(obs)
    if max(merchant, ppa) > 0 and TECHS["wind_onshore"].capex * 1000 * TECHS["wind_onshore"].chunk_mw <= g.budget:
        assert decision is not None and decision[0] == "wind_onshore"
    else:
        assert decision is None
