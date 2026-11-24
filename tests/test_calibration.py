import logging
import warnings

import numpy as np

from ukabm import GBMarketModel
from ukabm.data import PyPSAGBData
from ukabm.market import Block, clear
from ukabm.outturn import compare, load_outturn

warnings.filterwarnings("ignore")
logging.disable(logging.INFO)


def test_export_bid_as_buyback_block():
    # export bid of 50 MW at 30: taken when the GB price is below 30, curtailed when above
    d = np.array([100.0, 100.0]) + 50.0
    blocks = [Block(1, np.array([10.0, 40.0]), 150.0), Block(-11, 30.0, 50.0)]
    p, disp, _ = clear(d, blocks, scarcity_on=False)
    export = 50.0 - disp[:, 1]
    assert list(p) == [10.0, 40.0]
    assert np.allclose(export, [50.0, 0.0])


def test_interconnector_register_corrections():
    d = PyPSAGBData()
    assert d.interconnector_mw(2025) == 10500.0          # 2025 GB peak import was 9.2 GW
    assert d.interconnector_mw(2028) == 11900.0          # + NeuConnect
    assert sum(d.interconnector_mw_by_market(2025).values()) == d.interconnector_mw(2025)
    assert np.isclose(d.neighbour_price_shape["SEM"].mean(), 1.0)


def test_legacy_fleet_overrides():
    m = GBMarketModel(end=2025, network_every=0)
    agr = [p for p in m.plants if p.tech == "nuclear" and p.retire <= 2030]
    assert agr and all(p.availability == 0.62 for p in agr)
    ccgt = sorted((p for p in m.plants if p.tech == "ccgt"), key=lambda p: p.online)
    assert all(0.46 <= p.efficiency <= 0.54 for p in ccgt)
    assert m.plant_srmc(ccgt[0], 2025) > m.plant_srmc(ccgt[-1], 2025)   # older plant costs more


def test_2025_comparison_table():
    m = GBMarketModel(end=2025, network_every=0)
    r = m.run().loc[2025]
    tab = compare(r, 2025)
    assert {"imports (TWh)", "exports (TWh)", "carbon intensity, NESO basis (g/kWh)"} <= set(tab.index)
    assert 2025 in load_outturn().index
    assert r.export_twh > 5 and r.intensity_neso_g_kwh > r.intensity_g_kwh
