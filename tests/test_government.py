"""Government agent (ukabm.institutions) and the GBP-budget CfD auction."""
import logging
import warnings

import pandas as pd
import pytest

from ukabm import GBMarketModel, get_scenario
from ukabm.config import TECHS
from ukabm.institutions import CFD_TECHS, FixedRules, TargetTracking, make_government

warnings.filterwarnings("ignore")
logging.disable(logging.INFO)


def model(end=2027, seed=3, **keys):
    sc = get_scenario("baseline")
    sc.update(keys)
    return GBMarketModel(sc, seed=seed, end=end, network_every=0)


@pytest.fixture(scope="module")
def targets_run():
    m = model(government="targets")
    r = m.run()
    return m, r, pd.DataFrame(m.government.log)


def test_fixed_is_the_default_and_identical_to_explicit_fixed():
    m0 = model(end=2026)
    assert isinstance(m0.government, FixedRules)
    r0 = m0.run()
    r1 = model(end=2026, government="fixed").run()
    pd.testing.assert_frame_equal(r0, r1)
    assert (r0.cfd_awarded_mw <= 6000 + max(TECHS[t].chunk_mw for t in CFD_TECHS)).all()


def test_targets_buy_what_is_missing_within_budget(targets_run):
    m, r, log = targets_run
    assert isinstance(m.government, TargetTracking) and len(log) == 3 * len(r)
    for _, row in log.iterrows():
        # volume: never more than the missing capacity plus one block
        assert row.accepted_mw <= row.need_mw + TECHS[row.tech].chunk_mw + 1e-6
        # GBP budget at the pay-as-clear strike
        if row.accepted_mw > 0:
            support = max(row.clearing - row.reference_price, 0) * 8760 * m.capacity_factor(row.tech)
            assert row.accepted_mw * support <= row.budget_gbp + 1e-3
    assert r.cfd_awarded_mw.sum() > 0 and r.cfd_budget_bn.notna().all()


def test_no_award_when_targets_are_met():
    met = {t: {2025: 0.0} for t in CFD_TECHS}
    r = model(end=2025, government="targets", cfd_targets_gw=met).run()
    assert r.loc[2025, "cfd_awarded_mw"] == 0


def test_round_without_bids_under_the_cap_raises_the_cap():
    low = {"wind_offshore": 20.0, "wind_onshore": 20.0, "solar": 20.0, "nuclear": 110.0}
    sc = get_scenario("baseline")
    sc.update(government="targets", policy={"cfd_admin_strike_cap": low})
    m = GBMarketModel(sc, seed=3, end=2026, network_every=0)
    r = m.run()
    assert r.loc[2025, "cfd_awarded_mw"] == 0
    for t in CFD_TECHS:
        assert m.government.cap[t] == pytest.approx(20.0 * 1.15 ** 2)    # raised after each failed round
        assert m.government.cap[t] <= 20.0 * m.government.params["cap_ceiling"]


def test_levy_above_threshold_cuts_budgets():
    m = model(end=2025, government="targets")
    fc = m.forecast(2028)
    m.levy = 0.0
    calm = m.government.round_settings(2025, fc)
    m.levy = 1e3
    squeezed = m.government.round_settings(2025, fc)
    scale = m.government.params["levy_budget_scale"]
    for t in CFD_TECHS:
        assert squeezed[t].budget_gbp == pytest.approx(calm[t].budget_gbp * scale)


def test_unknown_government_raises():
    with pytest.raises(KeyError):
        model(end=2025, government="no_such_government")
