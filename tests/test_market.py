import numpy as np

from ukabm.market import Block, clear, storage_arbitrage, valley_fill


def test_merit_order_price_and_dispatch():
    d = np.array([50.0, 150.0, 260.0])
    blocks = [Block(1, 10.0, 100.0), Block(2, 50.0, 100.0), Block(3, 90.0, 50.0)]
    p, disp, uns = clear(d, blocks, voll=1000, scarcity_on=False)
    assert list(p) == [10.0, 50.0, 1000.0]
    assert np.allclose(disp.sum(1), [50, 150, 250])
    assert np.allclose(uns, [0, 0, 10])


def test_hourly_varying_offer_prices():
    d = np.array([100.0, 100.0])
    blocks = [Block(1, np.array([10.0, 90.0]), 100.0), Block(2, 50.0, 100.0)]
    p, disp, _ = clear(d, blocks, scarcity_on=False)
    assert list(p) == [10.0, 50.0]
    assert np.allclose(disp[:, 0], [100, 0])


def test_storage_buys_low_sells_high():
    price = np.tile(np.r_[np.full(12, 10.0), np.full(12, 100.0)], 2)
    net = storage_arbitrage(price, 10.0, 2, 0.9)
    assert (price * net).sum() > 0
    assert net.min() == -10.0


def test_valley_fill_conserves_energy():
    sig = np.tile(np.r_[np.arange(12), np.arange(12)[::-1]], 3).astype(float)
    load = valley_fill(np.array([30.0, 30.0, 30.0]), sig, 10.0)
    assert np.isclose(load.sum(), 90.0, rtol=1e-3)
    assert load.max() <= 10.0 + 1e-9
