"""Government objectives as levers: least cost, bills, political (roadmap item 6)."""
import logging
import types
import warnings

import pandas as pd
import pytest

import ukabm.planner
from ukabm import GBMarketModel, get_scenario
from ukabm.config import GOVERNMENT_BILLS, GOVERNMENT_POLITICAL
from ukabm.institutions import CFD_TECHS, GOVERNMENTS, BillsFirst, LeastCost, Political

warnings.filterwarnings("ignore")
logging.disable(logging.INFO)


def model(gov, end=2025, **keys):
    sc = get_scenario("baseline")
    sc.update(government=gov, **keys)
    return GBMarketModel(sc, seed=3, end=end, network_every=0)


def test_registered():
    for name in ("fixed", "targets", "least_cost", "bills", "political"):
        assert name in GOVERNMENTS


def test_political_cuts_rounds_before_elections():
    m = model("political")
    gov = m.government
    assert isinstance(gov, Political)
    assert [y for y in range(2025, 2036) if gov.pre_election(y)] == [2027, 2028, 2032, 2033]
    fc = m.forecast(2028)
    gov.pre_election = lambda year: False
    after = gov.round_settings(2025, fc)
    gov.pre_election = lambda year: True
    before = gov.round_settings(2025, fc)
    P = GOVERNMENT_POLITICAL
    for t in CFD_TECHS:
        assert before[t].budget_gbp == pytest.approx(after[t].budget_gbp * P["pre_election_scale"] / P["post_election_scale"])
        assert before[t].max_mw <= after[t].max_mw
    # announced targets are more ambitious than the target path
    base = model("targets").government
    assert gov.target_mw("solar", 2030) == pytest.approx(base.target_mw("solar", 2030) * P["target_ambition"])


def test_bills_first_squeezes_earlier_and_harder():
    gov = model("bills").government
    assert isinstance(gov, BillsFirst)
    for k, v in GOVERNMENT_BILLS.items():
        assert gov.params[k] == v
    assert model("bills", government_params={"levy_threshold": 25.0}).government.params["levy_threshold"] == 25.0


def test_least_cost_tracks_the_planners_pathway(monkeypatch):
    calls = {}

    def fake_plan(m, loads, every_nth_day=7, **kw):
        calls["periods"] = sorted(loads)
        built = pd.DataFrame(0.0, index=sorted(loads), columns=list(CFD_TECHS))
        built.loc[2030, "wind_onshore"] = 9000.0
        return types.SimpleNamespace(built_mw=built)
    monkeypatch.setattr(ukabm.planner, "plan", fake_plan)
    m = model("least_cost")
    gov = m.government
    assert isinstance(gov, LeastCost) and gov.params["levy_threshold"] == float("inf")
    gov.round_settings(2025, m.forecast(2028))
    assert calls["periods"] == [2025, 2030, 2035, 2040, 2045, 2050]
    existing = sum(u.mw for u in m.initial_fleet if u.tech == "wind_onshore" and u.active(2035))
    assert gov.target_mw("wind_onshore", 2035) == pytest.approx(existing + 9000.0)
