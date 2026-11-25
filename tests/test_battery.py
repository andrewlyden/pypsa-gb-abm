import logging
import warnings
from types import SimpleNamespace

import numpy as np

import ukabm.model as model_mod
from ukabm import GBMarketModel
from ukabm.config import BATTERY_ANCILLARY_POT, BATTERY_FLEET_FLOOR_MW, BATTERY_TRADING_PER_MW_VRE
from ukabm.market import Block, clear, merit_order

warnings.filterwarnings("ignore")
logging.disable(logging.INFO)


def _fleet(batt_mw, vre_mw):
    return [SimpleNamespace(tech="battery", mw=batt_mw), SimpleNamespace(tech="wind_offshore", mw=vre_mw)]


def test_battery_services_saturate_with_fleet_and_grow_with_vre():
    f = GBMarketModel.battery_services_per_mw
    s10, s20 = f(_fleet(10e3, 50e3)), f(_fleet(20e3, 50e3))
    assert np.isclose(s10, 2 * s20)                         # pots shared: per-MW halves when fleet doubles
    assert f(_fleet(10e3, 100e3)) > s10                     # trading pot grows with wind + solar
    # no extrapolation above the 2025 level for fleets smaller than the 2025 fleet
    assert np.isclose(f(_fleet(1e3, 50e3)), f(_fleet(BATTERY_FLEET_FLOOR_MW, 50e3)))
    assert np.isclose(f(_fleet(1e3, 50e3), extra_mw=10e3), f(_fleet(11e3, 50e3)))
    assert np.isclose(s10, (BATTERY_ANCILLARY_POT + BATTERY_TRADING_PER_MW_VRE * 50e3) / 10e3)


def test_clear_with_reused_merit_order_is_identical():
    rng = np.random.default_rng(0)
    blocks = [Block(i, rng.uniform(0, 100, 48), rng.uniform(50, 500)) for i in range(1, 30)]
    d = rng.uniform(1000, 6000, 48)
    curve = merit_order(blocks, 48)
    for a, b in zip(clear(d, blocks), clear(d, blocks, curve=curve)):
        np.testing.assert_array_equal(a, b)
    p2, _, _ = clear(d * 0.9, blocks, curve=curve)
    np.testing.assert_array_equal(p2, clear(d * 0.9, blocks)[0])


def test_storage_tranches_keep_fleet_arbitrage_positive(monkeypatch):
    def battery_arbitrage(tranches):
        monkeypatch.setitem(model_mod.STORAGE_TRANCHES, "battery", tranches)
        m = GBMarketModel(end=2025, network_every=0)
        plants = m.active(2025)
        for p in plants:            # a large fleet makes the fleet's own price impact visible
            if p.tech == "battery":
                p.mw *= 3
        st = m.settle(2025, plants, m.run_market(2025, plants))
        return st["battery"]["arbitrage"]
    one, three = battery_arbitrage(1), battery_arbitrage(3)
    assert three > 0 and three > one


def test_2025_battery_revenue_stack_and_investment_signal():
    m = GBMarketModel(end=2025, network_every=0)
    r = m.run().loc[2025]
    total = r.battery_arbitrage_k_per_mw + r.battery_services_k_per_mw + r.battery_cm_k_per_mw
    # Modo ME BESS GB 2-hour index: ~GBP 73k/MW/yr over the 12 months to April 2026 (incl. CM)
    assert 50 < total < 80
    # expected margin of a new battery falls as more batteries are in the pipeline (saturation)
    price = m.hourly[2025].price.values
    g = m.gencos[0]
    before = m.expected_margin_per_mw("battery", price, g)
    m.new_plant(g, "battery", "Z9", 5000, 2026)
    assert m.expected_margin_per_mw("battery", price, g) < before
