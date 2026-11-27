"""Decision interface (ukabm.decisions): default rules, custom decision makers, registry."""
import logging
import warnings

import pandas as pd
import pytest

from ukabm import GBMarketModel, get_scenario
from ukabm.decisions import REGISTRY, DecisionMaker, RuleBased, for_genco, make, register

warnings.filterwarnings("ignore")
logging.disable(logging.INFO)


class CountingRules(RuleBased):
    """The original rules, counting each decision."""
    name = "counting"

    def __init__(self):
        self.calls = {}

    def _count(self, k):
        self.calls[k] = self.calls.get(k, 0) + 1

    def merchant_investment(self, agent, forecast):
        self._count("merchant")
        return super().merchant_investment(agent, forecast)

    def cfd_bid(self, agent, tech, forecast):
        self._count("cfd")
        return super().cfd_bid(agent, tech, forecast)

    def cm_bid(self, agent, plant_or_tech, expected_margin_per_kw, new):
        self._count("cm")
        return super().cm_bid(agent, plant_or_tech, expected_margin_per_kw, new)


class NeverInvest(RuleBased):
    name = "never_invest"

    def merchant_investment(self, agent, forecast):
        return None


class Withholding(RuleBased):
    """Offers thermal plant at twice its cost: a strategic decision maker for the price test."""
    name = "withholding"

    def offer_price(self, agent, plant, srmc, year):
        p = super().offer_price(agent, plant, srmc, year)
        return 2 * srmc if plant.tech in ("ccgt", "ocgt", "biomass") else p


register("counting", CountingRules)
register("never_invest", NeverInvest)
register("withholding", Withholding)


def run(decision_logic=None, end=2026, seed=3):
    sc = get_scenario("baseline")
    if decision_logic is not None:
        sc["decision_logic"] = decision_logic
    m = GBMarketModel(sc, seed=seed, end=end, network_every=0)
    return m, m.run()


def test_default_is_the_original_rules_and_explicit_rules_are_identical():
    m0, r0 = run()
    assert all(type(g.decider) is RuleBased for g in m0.gencos)
    _, r1 = run("rules")
    pd.testing.assert_frame_equal(r0, r1)


def test_counting_subclass_reproduces_rules_and_sees_every_decision():
    _, r0 = run()
    m, r = run("counting")
    pd.testing.assert_frame_equal(r0, r)          # same rules, same random draws
    calls = {}
    for g in m.gencos:
        assert isinstance(g.decider, CountingRules)
        for k, v in g.decider.calls.items():
            calls[k] = calls.get(k, 0) + v
    assert calls.get("merchant", 0) > 0 and calls.get("cfd", 0) > 0 and calls.get("cm", 0) > 0


def test_per_genco_assignment_and_separate_instances():
    m, _ = run({"MerchantIPP": "never_invest", "OilMajor": "counting"}, end=2025)
    kinds = {g.name: type(g.decider) for g in m.gencos}
    assert kinds["MerchantIPP"] is NeverInvest and kinds["OilMajor"] is CountingRules
    assert kinds["InfraFund"] is RuleBased
    deciders = [g.decider for g in m.gencos]
    assert len({id(d) for d in deciders}) == len(deciders)   # stateful learners need one each


def test_offer_decisions_reach_the_market():
    _, r0 = run(end=2025)
    _, r = run("withholding", end=2025)
    assert r.loc[2025, "price_mean"] > r0.loc[2025, "price_mean"] + 20


def test_registry_and_make():
    assert REGISTRY["rules"] is RuleBased
    d = Withholding()
    assert make(d) is d and isinstance(make(NeverInvest), NeverInvest)
    assert isinstance(for_genco({}, "AnyCo"), RuleBased)
    with pytest.raises(KeyError):
        make("no_such_logic")
    with pytest.raises(TypeError):
        register("bad", dict)
    with pytest.raises(NotImplementedError):
        DecisionMaker().cfd_bid(None, "solar", None)
