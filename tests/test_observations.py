"""Information sets and action spaces (roadmap item 34): what a decision maker may see and return."""
import dataclasses
import json
import logging
import warnings

import numpy as np
import pytest

from ukabm import GBMarketModel, get_scenario
from ukabm.decisions import RuleBased, register
from ukabm.observations import ACTIONS, MarketInfo, Observation, Outcome, PlantView, Traits, validate

warnings.filterwarnings("ignore")
logging.disable(logging.INFO)


@pytest.fixture(scope="module")
def model():
    m = GBMarketModel(get_scenario("baseline"), seed=3, end=2026, network_every=0)
    m.run()
    return m


def test_observation_carries_no_model(model):
    g = model.gencos[0]
    obs = model.observation(g, "merchant_investment", forecast=model.forecast(model.year + 3))
    for x in (obs, obs.traits, obs.market) + obs.own:
        for f in dataclasses.fields(x):
            v = getattr(x, f.name)
            assert not isinstance(v, GBMarketModel), f.name
            assert type(v).__name__ not in ("GenCo", "Plant"), f.name
    assert not hasattr(obs, "model") and not hasattr(obs.market, "model")
    assert all(isinstance(p, PlantView) for p in obs.own)
    assert all(p.pid in {q.pid for q in model.plants if q.owner is g} for p in obs.own)   # own plants only
    assert obs.market.last_price is not None and not obs.market.last_price.flags.writeable


def test_merchant_options_are_allowed_and_affordable(model):
    g = model.gencos[1]
    g.budget_left = 1.0e9
    obs = model.observation(g, "merchant_investment", forecast=model.forecast(model.year + 3))
    from ukabm.config import TECHS
    for t in obs.options:
        assert TECHS[t].investable and t != "nuclear" and TECHS[t].capex * 1000 * TECHS[t].chunk_mw <= 1.0e9
    del g.budget_left


def test_actions_are_validated():
    obs = Observation(kind="merchant_investment", traits=None, market=None, options=("ocgt",))
    assert validate("merchant_investment", ("ocgt", 300, 1.0), obs) == ("ocgt", 300, 1.0)
    assert validate("merchant_investment", None, obs) is None
    with pytest.raises(ValueError):
        validate("merchant_investment", ("ccgt", 800, 1.0), obs)          # not an option
    assert validate("cfd_bid", None, obs) is None                          # abstain
    for kind, bad in (("offer_price", float("nan")), ("cm_bid", -1.0), ("cm_bid", None), ("cfd_bid", 1e6)):
        with pytest.raises(ValueError):
            validate(kind, bad, obs)
    assert set(ACTIONS) == {"offer_price", "expected_carbon", "merchant_investment", "cfd_bid", "cm_bid"}


class Recorder(RuleBased):
    """The rules, recording observations and rewards."""
    name = "recorder"

    def __init__(self):
        self.outcomes, self.kinds = [], set()

    def merchant_investment(self, obs):
        self.kinds.add(obs.kind)
        json.dumps(obs.to_dict())                     # JSON-safe summary, e.g. for an LLM prompt
        return super().merchant_investment(obs)

    def cfd_bid(self, obs):
        self.kinds.add(obs.kind)
        return super().cfd_bid(obs)

    def learn(self, outcome):
        self.outcomes.append(outcome)


class Abstainer(RuleBased):
    name = "abstainer"

    def cfd_bid(self, obs):
        return None


class InvalidOffer(RuleBased):
    name = "invalid_offer"

    def offer_price(self, obs):
        return float("nan")


register("recorder", Recorder)
register("abstainer", Abstainer)
register("invalid_offer", InvalidOffer)


def run(logic, end=2026):
    sc = get_scenario("baseline")
    sc["decision_logic"] = logic
    m = GBMarketModel(sc, seed=3, end=end, network_every=0)
    return m, m.run()


def test_learning_agents_get_a_yearly_reward_equal_to_their_profit():
    m, r = run({"OilMajor": "recorder"})
    g = next(g for g in m.gencos if g.name == "OilMajor")
    rec = g.decider
    assert [o.year for o in rec.outcomes] == list(r.index)
    for o in rec.outcomes:
        assert isinstance(o, Outcome)
        expect = sum(h for p in m.plants if p.owner is g for y, h in p.history if y == o.year)
        assert o.profit == pytest.approx(expect)
    assert {"merchant_investment", "cfd_bid"} <= rec.kinds


def test_abstaining_firms_win_nothing_in_cfd_rounds():
    m, _ = run("abstainer", end=2025)
    assert not [p for p in m.plants if p.support == "cfd" and p.online > 2025 and p.tech != "nuclear"]   # HPC: CfD from the start


def test_invalid_actions_are_rejected():
    with pytest.raises(ValueError):
        run("invalid_offer", end=2025)
