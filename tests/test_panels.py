"""Firm panel (Mesa DataCollector) and the tidy auction frame."""
import logging
import warnings

import numpy as np

from ukabm import GBMarketModel, get_scenario
from ukabm.config import TECHS

warnings.filterwarnings("ignore")
logging.disable(logging.INFO)


def _run(end=2027):
    m = GBMarketModel(get_scenario("baseline"), seed=1, end=end, network_every=0)
    return m, m.run()


def test_firm_panel_adds_up_to_the_fleet():
    m, df = _run()
    panel = m.firm_panel()
    assert len(panel) == len(m.gencos) * len(df)
    assert set(panel.firm) == {g.name for g in m.gencos}
    for y in df.index:
        rows = panel[panel.year == y]
        for tech in TECHS:
            assert np.isclose(rows[f"cap_{tech}_mw"].sum() / 1e3, df.loc[y, f"cap_{tech}"])
        assert np.isclose(rows.capacity_mw.sum(), rows[[f"cap_{t}_mw" for t in TECHS]].sum().sum())
    # capacity committed in the panel = plants created by a decision during the run
    added = panel[["added_cfd_mw", "added_cm_mw", "added_merchant_mw"]].sum().sum()
    assert np.isclose(added, sum(p.mw for p in m.plants if p.route in ("cfd", "cm", "merchant")))
    assert np.isclose(added, df.invested_mw.sum())


def test_firm_profit_is_the_sum_of_its_plants():
    m, df = _run(end=2026)
    panel = m.firm_panel()
    for g in m.gencos:
        want = sum(pr for p in m.plants if p.owner is g for (y, pr) in p.history if y == 2026)
        got = float(panel[(panel.firm == g.name) & (panel.year == 2026)].profit_gbp.iloc[0])
        assert np.isclose(got, want)


def test_auction_frame():
    m, df = _run()
    a = m.auctions()
    cfd = a[a.auction == "cfd"]
    assert set(cfd.tech) == {"wind_offshore", "wind_onshore", "solar"} and set(cfd.year) == set(df.index)
    assert np.isclose(cfd.groupby("year").accepted_mw.sum().loc[2025], df.loc[2025, "cfd_awarded_mw"])
    cm = a[(a.auction == "cm_t4") & (a.tech == "all")]
    assert list(cm.delivery) == [y + 4 for y in df.index]
    assert np.isclose(cm.clearing.iloc[-1], df.cm_clearing.iloc[-1])
    assert (cm.clearing <= cm.cap + 1e-9).all()
    by_tech = a[(a.auction == "cm_t4") & (a.tech != "all")]
    assert np.isclose(by_tech.new_mw.sum(), cm.new_mw.sum())
