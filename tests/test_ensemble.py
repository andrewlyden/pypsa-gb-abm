import logging
import warnings

import numpy as np
import pandas as pd

from ukabm import bands, run_ensemble


def test_bands_statistics():
    ens = pd.DataFrame({"seed": [1, 2, 3, 1, 2, 3], "x": [1.0, 2.0, 6.0, 4.0, 5.0, 9.0]},
                       index=pd.Index([2025, 2025, 2025, 2026, 2026, 2026], name="year"))
    b = bands(ens, ["x"])
    assert list(b.loc[2025, "x"][["min", "median", "max", "mean"]]) == [1.0, 2.0, 6.0, 3.0]
    assert b.loc[2026, ("x", "median")] == 5.0


def test_ensemble_long_format_and_seed_reproducibility():
    ens = run_ensemble("baseline", [1, 2], end=2026, network_every=0)
    assert sorted(ens.seed.unique()) == [1, 2]
    assert len(ens) == 4 and sorted(ens.index.unique()) == [2025, 2026]
    again = run_ensemble("baseline", [1], end=2026, network_every=0)
    a = ens[ens.seed == 1].drop(columns="seed")
    np.testing.assert_allclose(a.values.astype(float), again.drop(columns="seed").values.astype(float), equal_nan=True)
    # different seeds give different agent paths (initial vintages, siting, bids)
    b = ens[ens.seed == 2].drop(columns="seed")
    assert not np.allclose(a.values.astype(float), b.values.astype(float), equal_nan=True)


def test_ensemble_restores_caller_warning_and_logging_state():
    logging.disable(logging.NOTSET)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        filters_before = list(warnings.filters)
        run_ensemble("baseline", [1], end=2025, network_every=0)
        assert warnings.filters == filters_before
    assert logging.root.manager.disable == logging.NOTSET


def test_ensemble_parallel_matches_serial():
    par = run_ensemble("baseline", [1, 2], jobs=2, end=2025, network_every=0)
    ser = run_ensemble("baseline", [1, 2], jobs=1, end=2025, network_every=0)
    pd.testing.assert_frame_equal(par, ser)
