"""Multi-seed ensembles: one annual results CSV per scenario in long format (column `seed`).

    python scripts/run_ensemble.py                                   # baseline, no_cfd, heat_push x 5 seeds
    python scripts/run_ensemble.py baseline --seeds 1 2 --end 2030 --jobs 2
"""
import argparse
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ukabm import run_ensemble  # noqa: E402


def main():
    p = argparse.ArgumentParser()
    p.add_argument("scenarios", nargs="*", default=["baseline", "no_cfd", "heat_push"])
    p.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3, 4, 5])
    p.add_argument("--end", type=int, default=2050)
    p.add_argument("--network-every", type=int, default=5)
    p.add_argument("--jobs", type=int, default=os.cpu_count() or 1)
    a = p.parse_args()
    out = ROOT / "results"
    out.mkdir(exist_ok=True)
    for name in a.scenarios:
        t0 = time.time()
        ens = run_ensemble(name, a.seeds, jobs=min(a.jobs, len(a.seeds)), end=a.end, network_every=a.network_every)
        ens.to_csv(out / f"ensemble_{name}.csv")
        last = ens.loc[a.end]
        print(f"{name}: {len(a.seeds)} seeds in {time.time() - t0:.0f}s  price{a.end} "
              f"{last.price_twa.min():.1f}-{last.price_twa.max():.1f}  CI{a.end} "
              f"{last.intensity_g_kwh.min():.1f}-{last.intensity_g_kwh.max():.1f} g/kWh", flush=True)


if __name__ == "__main__":   # required: worker processes re-import this file
    main()
