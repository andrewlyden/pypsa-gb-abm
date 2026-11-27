"""Regression tests for the fixes of the 27 Nov 2026 code review (docs/review_2026-11.md)."""
import logging
import warnings

import numpy as np
import pandas as pd
import pytest

from ukabm import GBMarketModel, get_scenario
from ukabm.agents import Plant
from ukabm.config import CPI_2012_TO_2024, LEGACY_CM_PRICE, RO_SCHEME_END, TECHS
from ukabm.costs import Unit, crf, fixed_costs
from ukabm.market import valley_fill
from ukabm.planner import evaluate, sample_days, sample_hours, sample_weights

warnings.filterwarnings("ignore")
logging.disable(logging.INFO)


@pytest.fixture(scope="module")
def run():
    m = GBMarketModel(get_scenario("baseline"), seed=7, end=2030, network_every=0)
    r = m.run()
    return m, r


# ---- A1, A2: Capacity Market bids and agreements
def test_existing_plant_bids_its_missing_money():
    m = GBMarketModel(get_scenario("baseline"), seed=7, end=2025, network_every=0)
    ccgt = next(p for p in m.plants if p.tech == "ccgt")
    t = TECHS["ccgt"]
    for profit_per_kw in (-31.0, -5.0, 0.0, 12.0):
        ccgt.energy_history = [(2024, profit_per_kw * ccgt.mw * 1000)] * 2
        bid = ccgt.owner.cm_bid(ccgt, m.existing_gross_margin_kw(ccgt, None), new=False)
        assert bid == pytest.approx(max(-profit_per_kw, 0) / t.derating)


def test_cm_agreements_pay_from_delivery_and_are_not_overwritten(run):
    m, _ = run
    new = [p for p in m.plants if p.cm_end >= p.cm_start + 14 and p.cm_start > 0]
    assert new, "expected new build with 15-year agreements"
    for p in new:
        assert p.online == p.cm_start                        # delivery year = online year
        assert not p.cm_held(p.cm_start - 1)                 # nothing paid before delivery
    for a in m.cm_log:                                       # held plant never re-offered: no double counting
        assert a["procured_mw"] <= a["target_mw"] + 1500 + max(t.chunk_mw * t.derating for t in TECHS.values())


def test_legacy_cm_agreements_cover_the_years_before_the_first_t4(run):
    m, r = run
    assert r.loc[2025, "cm_cost_bn"] > 0.5                    # 2025/26 agreements pre-date the model
    ccgt = next(p for p in m.plants if p.tech == "ccgt" and p.online < 2025 and p.active(2028))
    assert ccgt.cm_payment_price(2026) == LEGACY_CM_PRICE[2026]


def test_t1_without_need_buys_nothing():
    sc = get_scenario("baseline")
    sc.update(system_operator="standard", system_operator_params={"t1_holdback": 0.05})
    m = GBMarketModel(sc, seed=7, end=2025, network_every=0)
    m.operator.cm_target = lambda year, dy, ahead: (0.0, 50000.0)
    assert m.cm_auction(2025, None, ahead=1) == []


# ---- A3: smart EV charging delivers its daily energy
def test_valley_fill_conserves_energy_when_the_window_holds_the_daily_peak():
    signal = np.full(48, 30000.0)                            # flat 30 GW residual load: window at the peak
    window = list(range(0, 8)) + [21, 22, 23]
    load = valley_fill(np.array([28500.0, 28500.0]), signal, 14000.0, hours_window=window)
    assert load.reshape(2, 24).sum(axis=1) == pytest.approx([28500.0, 28500.0], rel=1e-6)


# ---- A4: sunk capital stays in system cost after an early closure
def test_capex_annuity_runs_over_the_economic_life():
    u = Unit("ccgt", 800, 2030, 2036)                         # closed after 7 of 25 years
    t = TECHS["ccgt"]
    c = fixed_costs([u], 2040, start=2025)
    assert c["fom"] == 0.0
    assert c["capex"] == pytest.approx(t.capex * 1000 * 800 * crf(0.035, t.life))
    assert fixed_costs([u], 2055, start=2025)["capex"] == 0.0   # after the economic life


# ---- A5, A6: RO end and legacy CfD strikes
def test_ro_support_ends_and_cfd_strikes_are_capacity_weighted(run):
    m, _ = run
    ro = [p for p in m.plants if p.support == "ro"]
    assert ro and all(p.online <= 2017 and p.ro_end <= min(p.online + 19, RO_SCHEME_END) for p in ro)
    s = m.data.cfd_strikes
    s = s[(s.technology == "offshore") & (s.capacity_mw > 0) & (s.delivery_year.str[:4].astype(int) <= 2025)]
    expect = (s.strike_price_gbp_per_mwh_2012 * s.capacity_mw).sum() / s.capacity_mw.sum() * CPI_2012_TO_2024
    assert m.legacy_cfd_strikes()["wind_offshore"] == pytest.approx(expect)
    assert 95 < expect < 125                                   # ~GBP 109/MWh (2024 prices)


# ---- D1, D2: the planner's sample and storage
def test_planner_sample_is_balanced_and_weights_sum_to_the_year():
    m = GBMarketModel(get_scenario("baseline"), seed=1, end=2025, network_every=0)
    loads = {y: m.prof.demand_mw.values for y in (2025, 2030)}
    ordinary, _ = sample_days(m, loads)
    counts = np.bincount(np.array(ordinary) % 7, minlength=7)
    assert counts.max() - counts.min() <= 1                    # every weekday sampled
    assert sample_weights(m, loads).sum() == pytest.approx(m.H)
    h = sample_hours(m, loads)
    load = m.prof.demand_mw.values
    assert abs((load[h] * sample_weights(m, loads)).sum() / m.H / load.mean() - 1) < 0.01


def test_sampled_evaluation_lets_storage_shift_its_full_energy():
    """With sampled hours (weight ~ 8760/len), a battery still moves at most its own energy per hour."""
    m = GBMarketModel(get_scenario("baseline"), seed=1, end=2025, network_every=0)
    hours = np.arange(0, 24 * 7)                                # one week, weight 52
    load = np.full(m.H, 30000.0)
    load[18::24] = 34000.0                                      # a 4 GW evening peak every day
    batt = Plant(1, m.gencos[0], "battery", "Z1", 4000.0, 2020, 2040)
    peaker = Plant(2, m.gencos[0], "ocgt", "Z1", 10000.0, 2020, 2040)
    base = Plant(3, m.gencos[0], "nuclear", "Z1", 31000.0, 2020, 2040, availability=1.0)
    out = evaluate(m, 2025, [batt, peaker, base], load, hours=hours)
    assert out["gen"].get("ocgt", 0.0) < 0.05 * out["gen"].get("battery", 1.0) + 1e3


def test_review_fix_summary_exists():
    from pathlib import Path
    doc = Path(__file__).resolve().parents[1] / "docs" / "review_2026-11.md"
    assert doc.exists() and "D1" in doc.read_text(encoding="utf-8")
