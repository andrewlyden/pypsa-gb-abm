"""Wholesale market operation: bid formation, uniform-price clearing, storage and flexible demand.

GB copperplate day-ahead/within-day abstraction (one price per hour). Network effects are
assessed afterwards by ukabm.network (balancing-mechanism style redispatch), mirroring
PyPSA-GB's two-stage wholesale -> balancing workflow.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.special import erfc


@dataclass
class Block:
    """An offer block: one plant (or aggregated plant group) in a given year."""
    key: int              # plant id
    price: np.ndarray | float  # GBP/MWh offer price, scalar or hourly array
    avail: np.ndarray | float  # MW available, scalar or hourly array
    demand_bid: bool = False   # buy-back block standing for a price-responsive bid (e.g. exports)


def clear(demand: np.ndarray, blocks: list[Block], voll: float = 6000.0,
          scarcity_sigma: float = 2500.0, scarcity_on: bool = True):
    """Uniform-price clearing for every hour (vectorised).

    Returns price[h], dispatch[h, b] (ordered like *blocks*), unserved[h].
    Scarcity: an ORDC-style adder VOLL*LOLP(margin), LOLP ~ 0.5*erfc(margin/(sigma*sqrt2)).
    The margin is total offered volume minus demand. Buy-back blocks (``demand_bid``) appear on
    both sides, so it is physical supply minus the remaining demand. A buy-back block whose
    price is below the adder is accepted in full before the merit order is cleared. A
    price-responsive bid is therefore never served above its price, also in scarcity hours.
    """
    H = len(demand)
    P0 = np.empty((H, len(blocks)))
    Q0 = np.empty((H, len(blocks)))
    for i, b in enumerate(blocks):
        P0[:, i] = np.broadcast_to(b.price, (H,))
        Q0[:, i] = np.broadcast_to(b.avail, (H,))
    order = np.argsort(P0, axis=1, kind="stable")          # hourly merit order
    P = np.take_along_axis(P0, order, axis=1)
    Q = np.take_along_axis(Q0, order, axis=1)
    d = np.maximum(demand, 0.0)
    pre = np.zeros_like(Q)        # buy-back volume accepted because of the scarcity adder
    adder = np.zeros(H)
    if scarcity_on:
        margin = Q.sum(axis=1) - d
        lolp = 0.5 * erfc(margin / (scarcity_sigma * np.sqrt(2)))
        adder = np.minimum(voll * lolp, voll)
        bid = np.array([b.demand_bid for b in blocks])[order]
        pre = np.where(bid & (P < adder[:, None]), Q, 0.0)
        Q = Q - pre
        d = d - pre.sum(axis=1)   # leaves margin, and so the adder, unchanged
    cum = np.cumsum(Q, axis=1)
    total = cum[:, -1]
    idx = (cum < d[:, None]).sum(axis=1)  # first block meeting demand
    short = idx >= len(blocks)
    idx_c = np.minimum(idx, len(blocks) - 1)
    price = P[np.arange(H), idx_c].copy()
    price[short] = voll
    disp_sorted = np.clip(d[:, None] - (cum - Q), 0.0, Q) + pre
    unserved = np.maximum(d - total, 0.0)
    # Blocks with negative price run even if demand is low: they are "must-run"; excess spilt
    price = np.maximum(price, adder)
    dispatch = np.empty_like(disp_sorted)
    np.put_along_axis(dispatch, order, disp_sorted, axis=1)
    return price, dispatch, unserved


def storage_arbitrage(price: np.ndarray, p_mw: float, hours: float, eff: float, min_spread: float = 5.0):
    """Daily price-taking arbitrage heuristic for an aggregated storage fleet.

    Charges in the cheapest *n* hours of each day and discharges in the dearest *n* hours
    (n = duration) when the spread covers losses. Returns net injection (+discharge) MW per hour.
    Perfect foresight of the first-pass price within the day (an optimistic assumption).
    """
    H = len(price)
    net = np.zeros(H)
    n = max(int(round(hours)), 1)
    for s in range(0, H - 23, 24):
        p = price[s:s + 24]
        o = np.argsort(p)
        lo, hi = o[:n], o[::-1][:n]
        if p[hi].mean() * eff - p[lo].mean() > min_spread:
            net[s + lo] -= p_mw
            net[s + hi] += p_mw * eff
    return net


def shift_to_cheapest(energy_per_day: np.ndarray, price: np.ndarray, max_mw: float, hours_window=None):
    """Place daily flexible energy (MWh/day) into each day's cheapest hours, up to max_mw."""
    H = len(price)
    load = np.zeros(H)
    for k, s in enumerate(range(0, H - 23, 24)):
        e = energy_per_day[k] if k < len(energy_per_day) else 0.0
        p = price[s:s + 24].copy()
        if hours_window is not None:
            mask = np.ones(24, bool)
            mask[list(hours_window)] = False
            p[mask] = np.inf
        for h in np.argsort(p):
            if e <= 0 or not np.isfinite(p[h]):
                break
            q = min(max_mw, e)
            load[s + h] += q
            e -= q
    return load


def valley_fill(energy_per_day: np.ndarray, signal: np.ndarray, max_mw: float, hours_window=None):
    """Water-filling of daily flexible energy onto the lowest values of *signal* (e.g. residual
    load), so a large smart-charging fleet flattens the valley instead of herding into one hour."""
    H = len(signal)
    load = np.zeros(H)
    for k, s in enumerate(range(0, H - 23, 24)):
        E = energy_per_day[k] if k < len(energy_per_day) else 0.0
        if E <= 0:
            continue
        r = signal[s:s + 24].astype(float).copy()
        cap = np.full(24, max_mw)
        if hours_window is not None:
            m = np.zeros(24, bool)
            m[list(hours_window)] = True
            cap[~m] = 0.0
        E = min(E, cap.sum())
        lo, hi = r.min(), r.max() + E / max(cap.max(), 1e-9) + 1
        for _ in range(50):
            L = 0.5 * (lo + hi)
            if np.clip(L - r, 0, cap).sum() > E:
                hi = L
            else:
                lo = L
        load[s:s + 24] = np.clip(lo - r, 0, cap)
    return load
