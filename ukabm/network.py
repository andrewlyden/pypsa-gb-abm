"""Network-constrained redispatch on the PyPSA-GB zonal network (PyPSA + HiGHS).

Given the copperplate market outcome for a sample of hours, build a zonal PyPSA network
(20 zones, 31 inter-zonal transfer links from PyPSA-GB data/network/zonal), place each plant's
availability and offer at its zone, and solve a least-cost dispatch. The cost difference to the
unconstrained dispatch approximates balancing-mechanism constraint costs; zonal shadow prices
give a locational signal used by investors (hook for REMA-style locational pricing).
"""
from __future__ import annotations

import logging
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)


def redispatch(data, plants, blocks, demand_h, hours, ic_mw=0.0):
    try:
        import pypsa
    except ImportError:  # pragma: no cover
        log.warning("PyPSA not installed: skipping network stage")
        return None
    logging.getLogger("pypsa").setLevel(logging.ERROR)
    logging.getLogger("linopy").setLevel(logging.ERROR)
    n = pypsa.Network()
    n.set_snapshots(pd.RangeIndex(len(hours)))
    for _, b in data.buses.iterrows():
        n.add("Bus", b["name"], x=b.x, y=b.y, carrier="AC")
    for _, l in data.links.iterrows():
        n.add("Link", l["name"], bus0=l.bus0, bus1=l.bus1, p_nom=l.p_nom, p_min_pu=-1, efficiency=1.0)
    zshare = data.zone_demand_share
    for z, s in zshare.items():
        if s > 0:
            n.add("Load", f"load_{z}", bus=z, p_set=demand_h[hours] * s)
            n.add("Generator", f"shed_{z}", bus=z, p_nom=1e5, marginal_cost=6000.0)
    pmap = {p.pid: p for p in plants}
    for b in blocks:
        p = pmap.get(b.key)
        if p is None:
            continue
        av = np.broadcast_to(b.avail, demand_h.shape)[hours]
        if av.max() <= 0:
            continue
        n.add("Generator", f"g{b.key}", bus=p.zone, p_nom=float(av.max()),
              p_max_pu=av / av.max(), marginal_cost=np.broadcast_to(b.price, demand_h.shape)[hours] if np.ndim(b.price) else float(b.price))
    n.optimize(solver_name="highs", solver_options={"output_flag": False}, progress=False,
               include_objective_constant=False)
    zp = n.buses_t.marginal_price
    gen = n.generators_t.p
    out = {
        "cost_constrained": float(n.objective),
        "zonal_price_mean": zp.mean(),
        "flows": n.links_t.p0,
        "gen": gen,
    }
    return out
