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


def test_export_bid_curtailed_when_scarcity_price_exceeds_it():
    # 10 GW domestic demand, 15 GW supply at 80, 500 MW export bid at 100. The merit price is 80,
    # but the scarcity adder at a 5 GW margin is above 100, so the export must not be served.
    x = 500.0
    blocks = [Block(1, 80.0, 15000.0), Block(-11, 100.0, x, demand_bid=True)]
    p, disp, uns = clear(np.array([10000.0 + x]), blocks, voll=6000.0)
    assert p[0] > 100.0
    assert np.isclose(x - disp[0, 1], 0.0)                     # export fully curtailed
    assert np.isclose(disp[0, 0], 10000.0) and uns[0] == 0.0  # domestic demand still met
    # without the adder the same export is served at the merit price
    p0, disp0, _ = clear(np.array([10000.0 + x]), blocks, voll=6000.0, scarcity_on=False)
    assert p0[0] == 80.0 and np.isclose(x - disp0[0, 1], x)
    # a high export bid stays above the adder and is served; the adder itself is unchanged
    hi = [Block(1, 80.0, 15000.0), Block(-11, 1000.0, x, demand_bid=True)]
    p2, disp2, _ = clear(np.array([10000.0 + x]), hi, voll=6000.0)
    assert np.isclose(p2[0], p[0]) and np.isclose(x - disp2[0, 1], x)
    assert np.isclose(disp2[0, 0], 10000.0 + x)


def test_zero_availability_override_is_honoured():
    m = GBMarketModel(end=2025, network_every=0)
    p = next(p for p in m.plants if p.tech == "nuclear" and p.active(2025))
    p.availability = 0.0
    b = next(b for b in m.blocks([p], 2025))
    assert np.all(np.asarray(b.avail) == 0.0)


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


def test_levy_and_demand_exclude_exports():
    # CfD/RO/CM costs are recovered from GB supplier volumes only; exports are not GB demand
    m = GBMarketModel(end=2025, network_every=0)
    res = m.run_market(2025, m.active(2025))
    dom = (res["base"] + res["heat"] + res["ev"] + res["h2"]).sum()
    assert np.isclose(res["demand_domestic"].sum(), dom)
    r = m.run().loc[2025]
    assert r.export_twh > 5
    assert np.isclose(r.demand_twh, dom / 1e6)
    assert np.isclose(r.levy_gbp_mwh, (r.cfd_cost_bn + r.ro_cost_bn + r.cm_cost_bn) * 1e9 / (r.demand_twh * 1e6))
