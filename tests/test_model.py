import logging
import warnings

from ukabm import GBMarketModel, get_scenario

warnings.filterwarnings("ignore")
logging.disable(logging.INFO)


def test_short_run_produces_sane_outputs():
    m = GBMarketModel(get_scenario("baseline"), end=2027, network_every=0)
    r = m.run()
    assert len(r) == 3
    assert (r.price_twa > 0).all() and (r.price_twa < 1000).all()
    assert (r.demand_twh > 200).all()
    assert r.cap_ccgt.iloc[0] > 20


def test_network_stage_runs():
    m = GBMarketModel(end=2025, network_every=1, network_hours=12)
    r = m.run()
    assert "zonal_price" in m.network_results
