"""Network-constrained redispatch on the PyPSA-GB zonal network (PyPSA + HiGHS).

Given the copperplate market outcome for a sample of hours, build a zonal PyPSA network
(20 zones, inter-zonal transfer links from PyPSA-GB data/network/zonal with year-dependent
capacities, see PyPSAGBData.links_for_year) and re-dispatch it at least balancing cost, in the
style of the Balancing Mechanism: each plant's market schedule can be turned down at its *bid*
price and its remaining headroom turned up at its *offer* price. Implemented with two PyPSA
generators per plant: "s" (capacity = market schedule, cost = bid) and "h" (capacity = available
minus schedule, cost = offer). Redispatch cost = objective - sum(bid * schedule). Zonal shadow
prices give a locational signal used by investors (hook for REMA-style locational pricing).
"""
from __future__ import annotations

import logging
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)


def redispatch(data, plants, blocks, demand_h, schedule, avail, offers, bids, links, link_pu=None, injection=None):
    """Least-cost BM-style redispatch for the sample hours.

    demand_h: (S,) GB demand net of interconnector imports, MW. schedule, avail, offers, bids: (S, B)
    arrays for *blocks* (plant blocks only). links: inter-zonal links for the year; link_pu: optional
    (S, links) DataFrame of available capacity share per hour (outages/maintenance). injection: optional
    (S, zones) DataFrame of fixed net injections (interconnector imports minus exports at their landing
    zones), MW; demand_h is then GB demand excluding them.
    Returns dict with per-hour redispatch cost (GBP, bids/offers only), up/down volumes (S, B), load
    shed behind constraints (S,), flows, zonal prices.
    """
    try:
        import pypsa
    except ImportError:  # pragma: no cover
        log.warning("PyPSA not installed: skipping network stage")
        return None
    logging.getLogger("pypsa").setLevel(logging.ERROR)
    logging.getLogger("linopy").setLevel(logging.ERROR)
    S = len(demand_h)
    n = pypsa.Network()
    n.set_snapshots(pd.RangeIndex(S))
    for _, b in data.buses.iterrows():
        n.add("Bus", b["name"], x=b.x, y=b.y, carrier="AC")
    for _, l in links.iterrows():
        if l.p_nom > 0:
            pu = link_pu[l["name"]].values if link_pu is not None else 1.0
            n.add("Link", l["name"], bus0=l.bus0, bus1=l.bus1, p_nom=l.p_nom, p_max_pu=pu, p_min_pu=-pu,
                  efficiency=1.0)
    for z, s in data.zone_demand_share.items():
        inj = injection[z].values if injection is not None and z in injection else 0.0
        if s > 0 or np.any(inj != 0):
            n.add("Load", f"load_{z}", bus=z, p_set=demand_h * s - inj)
            n.add("Generator", f"shed_{z}", bus=z, p_nom=1e5, marginal_cost=6000.0)
    pmap = {p.pid: p for p in plants}
    head = np.clip(avail - schedule, 0.0, None)
    names = []
    for j, b in enumerate(blocks):
        p = pmap.get(b.key)
        if p is None:
            continue
        for tag, cap, cost in (("s", schedule[:, j], bids[:, j]), ("h", head[:, j], offers[:, j])):
            if cap.max() <= 1e-6:
                continue
            n.add("Generator", f"{tag}{b.key}", bus=p.zone, p_nom=float(cap.max()),
                  p_max_pu=cap / cap.max(), marginal_cost=cost)
            names.append((f"{tag}{b.key}", tag, j))
    n.optimize(solver_name="highs", solver_options={"output_flag": False}, progress=False,
               include_objective_constant=False)
    gen = n.generators_t.p
    up, down = np.zeros_like(schedule), np.zeros_like(schedule)
    cost_h = np.zeros(S)
    for name, tag, j in names:
        g = gen[name].values
        if tag == "s":
            down[:, j] = schedule[:, j] - g
            cost_h -= bids[:, j] * down[:, j]
        else:
            up[:, j] = g
            cost_h += offers[:, j] * g
    # Load the network cannot serve (shed at 6000 GBP/MWh in the LP) is reported separately and
    # left out of the redispatch cost: in the BM it would be resolved by actions this stage holds
    # fixed (interconnector counter-trades, storage), not by paying VoLL.
    shed = gen[[c for c in gen.columns if c.startswith("shed_")]].sum(axis=1).values
    return {"cost_h": cost_h, "up": up, "down": down, "shed": shed,
            "zonal_price": n.buses_t.marginal_price, "flows": n.links_t.p0}
