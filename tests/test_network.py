import logging
import warnings
from types import SimpleNamespace

import numpy as np
import pandas as pd

from ukabm import GBMarketModel
from ukabm.data import PyPSAGBData
from ukabm.data.pypsagb import AVAIL_B5, AVAIL_SCOT, BOUNDARY_LINKS, BOUNDARY_MW, BOUNDARY_NORTH, HVDC_STEPS
from ukabm.network import redispatch

warnings.filterwarnings("ignore")
logging.disable(logging.INFO)


def _toy(link_mw, wind_bid=-40.0, gas_offer=80.0, S=3):
    """Zone N: 300 MW wind scheduled, no demand. Zone S: 300 MW demand, idle 500 MW gas."""
    data = SimpleNamespace(buses=pd.DataFrame({"name": ["N", "S"], "x": [0.0, 0.0], "y": [1.0, 0.0]}),
                           zone_demand_share=pd.Series({"N": 0.0, "S": 1.0}))
    plants = [SimpleNamespace(pid=1, zone="N"), SimpleNamespace(pid=2, zone="S")]
    blocks = [SimpleNamespace(key=1), SimpleNamespace(key=2)]
    sched = np.tile([300.0, 0.0], (S, 1))
    avail = np.tile([300.0, 500.0], (S, 1))
    offers = np.tile([0.0, gas_offer], (S, 1))
    bids = np.tile([wind_bid, 40.0], (S, 1))
    links = pd.DataFrame([dict(name="NS", bus0="N", bus1="S", p_nom=link_mw)])
    return redispatch(data, plants, blocks, np.full(S, 300.0), sched, avail, offers, bids, links)


def test_redispatch_toy_constrained_boundary():
    out = _toy(100.0)
    # 200 MW of wind turned down behind the boundary, replaced by 200 MW of gas in the south
    assert np.allclose(out["down"][:, 0], 200.0) and np.allclose(out["up"][:, 1], 200.0)
    assert np.allclose(out["up"].sum(1), out["down"].sum(1))          # energy balance, no shedding
    # cost = offer x up - bid x down = 80*200 + 40*200 (CfD top-up lost on curtailed wind)
    assert np.allclose(out["cost_h"], 24000.0)
    assert np.allclose(out["shed"], 0.0)
    zp = out["zonal_price"].iloc[0]
    assert zp["S"] > zp["N"]                                         # locational signal


def test_redispatch_toy_shedding_reported_not_costed():
    # southern gas only 50 MW: 100 MW over the link + 50 MW gas < 300 MW demand -> 150 MW shed
    from ukabm import network
    data = SimpleNamespace(buses=pd.DataFrame({"name": ["N", "S"], "x": [0.0, 0.0], "y": [1.0, 0.0]}),
                           zone_demand_share=pd.Series({"N": 0.0, "S": 1.0}))
    plants = [SimpleNamespace(pid=1, zone="N"), SimpleNamespace(pid=2, zone="S")]
    blocks = [SimpleNamespace(key=1), SimpleNamespace(key=2)]
    out = network.redispatch(data, plants, blocks, np.array([300.0]), np.array([[300.0, 0.0]]),
                             np.array([[300.0, 50.0]]), np.array([[0.0, 80.0]]), np.array([[-40.0, 40.0]]),
                             pd.DataFrame([dict(name="NS", bus0="N", bus1="S", p_nom=100.0)]))
    assert np.allclose(out["shed"], 150.0)
    assert np.allclose(out["cost_h"], 80.0 * 50 + 40.0 * 200)        # VoLL not in the redispatch cost


def test_redispatch_toy_unconstrained_costs_nothing():
    out = _toy(1000.0)
    assert np.allclose(out["cost_h"], 0.0) and np.allclose(out["up"], 0.0) and np.allclose(out["down"], 0.0)


def test_boundary_capabilities_by_year():
    d = PyPSAGBData()
    prev = None
    for y in range(2025, 2041):
        links = d.links_for_year(y).set_index("name").p_nom
        for bnd, (ac, hvdc) in BOUNDARY_LINKS.items():
            ys, mw = zip(*BOUNDARY_MW[bnd])
            total = links[ac] + sum(links[h] for h in hvdc)
            # boundary total meets the interpolated capability (it can exceed it when an HVDC
            # link energises ahead of the interpolated path, because the AC part never shrinks)
            assert total >= float(np.interp(y, ys, mw)) - 1e-6
            assert links[ac] >= 500.0
        if prev is not None:
            assert (links.reindex(prev.index) >= prev - 1e-6).all()       # no link loses capacity
        prev = links
    l25 = d.links_for_year(2025).set_index("name").p_nom
    assert l25["EGL1"] == 0 and l25["Z7-Z2"] == 0 and l25["WesternHVDC"] == 2250
    l31 = d.links_for_year(2031).set_index("name").p_nom
    assert l31["EGL1"] == 2000 and l31["Z7-Z2"] == 6000
    assert set(HVDC_STEPS) <= set(l31.index)


def test_boundary_cuts_match_listed_crossings():
    # every link with capacity that crosses a boundary cut is listed, so no route bypasses a boundary
    d = PyPSAGBData()
    for y in range(2025, 2041):
        links = d.links_for_year(y)
        links = links[links.p_nom > 0]
        for bnd, north in BOUNDARY_NORTH.items():
            cut = links[links.bus0.isin(north) != links.bus1.isin(north)]
            ac, hvdc = BOUNDARY_LINKS[bnd]
            assert set(cut.name) <= {ac, *hvdc}, (y, bnd, set(cut.name))
            ys, mw = zip(*BOUNDARY_MW[bnd])
            assert cut.p_nom.sum() >= float(np.interp(y, ys, mw)) - 1e-6
    l25 = d.links_for_year(2025).set_index("name")
    b5 = [n for n in l25.index if (l25.bus0[n] in BOUNDARY_NORTH["B5"]) != (l25.bus1[n] in BOUNDARY_NORTH["B5"])
          and l25.p_nom[n] > 0]
    assert np.isclose(l25.p_nom[b5].sum(), 4300.0)            # B5 2025 capability, nothing on top


def test_b5_available_share_over_whole_cut():
    d = PyPSAGBData()
    hours = np.array([24 * k * 30 + 12 for k in range(12)])
    for y in (2025, 2029, 2031, 2036):
        links = d.links_for_year(y)
        cap = links.set_index("name").p_nom
        a = d.link_availability(y, links, hours)
        ac, hvdc = BOUNDARY_LINKS["B5"]
        total = cap[ac] + sum(cap[h] for h in hvdc)
        avail = a[ac] * cap[ac] + sum(a[h] * cap[h] for h in hvdc)
        month = pd.to_datetime(f"{d.profile_year}-01-01") + pd.to_timedelta(d.profiles.doy.values[hours] - 1, unit="D")
        frac = np.asarray(AVAIL_B5)[month.month - 1] * (0.76 if y == 2025 else 1.0)
        # exact where the AC link can absorb the difference; never above the B5 share
        assert (avail.values <= frac * total + 1e-6).all()
        ok = a[ac].values > 0
        assert np.allclose(avail.values[ok], (frac * total)[ok])


def test_network_sample_skips_empty_strata():
    m = GBMarketModel(end=2025, network_every=0, network_hours=96)
    m.prof = m.prof.copy()
    m.prof["wind_cf"] = 0.3                                          # flat: every hour in one stratum
    hours, w = m.network_sample(2025)
    assert len(hours) == 12 and np.isclose(w.sum(), m.H)


def test_link_availability_profile():
    d = PyPSAGBData()
    links = d.links_for_year(2025)
    hours = np.array([0, 24 * 200, 24 * 340])      # January, July, December
    a25, a26 = d.link_availability(2025, links, hours), d.link_availability(2026, links, hours)
    assert a25.shape == (3, len(links)) and ((a25 > 0) & (a25 <= 1)).all().all()
    scot = BOUNDARY_LINKS["B6"][0]
    assert np.allclose(a25[scot], 0.76 * a26[scot])                   # 2025 upgrade outages
    assert np.allclose(a26[scot], np.asarray(AVAIL_SCOT)[[0, 6, 11]])
    assert a26[scot].iloc[1] < a26[scot].iloc[0]                      # summer maintenance
    assert np.allclose(a25["Z10-Z8"], a26["Z10-Z8"])                 # English link: no 2025 derate


def test_network_sample_stratified_weights():
    m = GBMarketModel(end=2025, network_every=0, network_hours=96)
    hours, w = m.network_sample(2025)
    assert len(set(hours)) == len(hours) == 96
    assert np.isclose(w.sum(), m.H)                                   # weights annualise to 8760 h
    cf = m.prof.wind_cf.values
    assert cf[hours].min() < np.quantile(cf, 0.125) and cf[hours].max() > np.quantile(cf, 0.875)


def test_bm_bid_prices_by_support():
    m = GBMarketModel(end=2025, network_every=0)
    plants = m.active(2025)
    blocks = [SimpleNamespace(key=p.pid) for p in plants]
    price = np.full(4, 60.0)
    bids = m.bm_bids(plants, blocks, price, 2025)
    for j, p in enumerate(plants):
        if p.tech == "nuclear":
            assert (bids[:, j] == -300.0).all()
        elif p.tech == "ccgt":
            assert np.allclose(bids[:, j], m.plant_srmc(p, 2025)) and bids[0, j] > 0
        elif p.tech.startswith("wind") and p.support == "ro":
            assert np.allclose(bids[:, j], -m.policy.ro_value)
        elif p.tech.startswith("wind") and p.support == "cfd" and p.cfd_end >= 2025:
            assert np.allclose(bids[:, j], -(p.strike - 60.0))
    # above the strike the CfD bid is positive: turning down saves the payback
    cfd = [j for j, p in enumerate(plants) if p.support == "cfd" and p.tech.startswith("wind") and p.cfd_end >= 2025]
    hi = m.bm_bids(plants, blocks, np.full(4, 500.0), 2025)
    assert cfd and all(np.allclose(hi[:, j], 500.0 - plants[j].strike) and hi[0, j] > 0 for j in cfd)


def test_network_stage_2025_constraint_cost_and_post_bm_mix():
    r = GBMarketModel(end=2025, network_every=1).run().loc[2025]
    # outturn 2025: GBP 1.83bn incl. ~0.54bn BM premia, 10.4 TWh renewable turn-down (LCP Delta 2026)
    assert 0.8 < r.constraint_cost_bn < 2.5
    assert 5.0 < r.curtailment_twh < 15.0
    assert r.network_shed_twh < 0.05
    # redispatch turns wind down and gas up, so post-BM CI is higher
    assert r.bm_net_wind_onshore + r.bm_net_wind_offshore < 0 < r.bm_net_ccgt + r.bm_net_ocgt
    assert r.intensity_neso_post_bm_g_kwh > r.intensity_neso_g_kwh
