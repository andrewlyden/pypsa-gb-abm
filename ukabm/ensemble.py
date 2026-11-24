"""Multi-seed (Monte-Carlo) ensembles.

ABM outcomes are path-dependent: the seed drives initial-fleet vintages and CfD/RO split, CfD bid noise,
siting draws, the order in which GenCos take merchant decisions, and household-agent attributes and
boiler-replacement draws. It does NOT vary weather/demand (one ESPENI year, fixed synthetic temperature),
fuel or carbon paths, or the network-stage sample hours. Ensembles therefore show agent/path uncertainty
only, not weather or macro uncertainty.
"""
from __future__ import annotations

import logging
import warnings
from concurrent.futures import ProcessPoolExecutor

import pandas as pd

from .model import GBMarketModel
from .scenarios import get_scenario


def _run_one(args):
    name, seed, kw = args
    warnings.filterwarnings("ignore")
    logging.disable(logging.INFO)
    r = GBMarketModel(get_scenario(name), seed=seed, **kw).run()
    r.insert(0, "seed", seed)
    return r


def run_ensemble(scenario: str, seeds, jobs: int = 1, **model_kw) -> pd.DataFrame:
    """Run *scenario* once per seed; return annual results stacked in long format
    (index = year, column `seed`). `model_kw` is passed to GBMarketModel (end, network_every, ...)."""
    tasks = [(scenario, int(s), model_kw) for s in seeds]
    if jobs > 1:
        with ProcessPoolExecutor(max_workers=jobs) as ex:
            out = list(ex.map(_run_one, tasks))
    else:
        out = [_run_one(t) for t in tasks]
    return pd.concat(out)


def bands(ens: pd.DataFrame, cols) -> pd.DataFrame:
    """Per-year ensemble statistics for `cols`: columns MultiIndex (col, stat) with
    stat in min, median, max, mean. With few seeds report min-max, not percentiles."""
    g = ens.groupby(level=0)[list(cols)]
    return pd.concat({"min": g.min(), "median": g.median(), "max": g.max(), "mean": g.mean()},
                     axis=1).swaplevel(axis=1).sort_index(axis=1)
