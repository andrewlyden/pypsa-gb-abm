"""Run scenarios and save annual results + selected hourly data.

    python scripts/run_scenarios.py                       # all scenarios, 2025-2050
    python scripts/run_scenarios.py baseline --end 2030   # quick check
"""
import argparse
import logging
import pickle
import sys
import time
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
warnings.filterwarnings("ignore")
logging.disable(logging.INFO)

from ukabm import GBMarketModel, SCENARIOS, get_scenario  # noqa: E402

p = argparse.ArgumentParser()
p.add_argument("scenarios", nargs="*", default=list(SCENARIOS))
p.add_argument("--end", type=int, default=2050)
p.add_argument("--seed", type=int, default=42)
p.add_argument("--network-every", type=int, default=5)
p.add_argument("--pypsa-gb", default=None, help="path to a PyPSA-GB clone (else bundled snapshot)")
a = p.parse_args()
out = ROOT / "results"
out.mkdir(exist_ok=True)
data = None
if a.pypsa_gb:
    from ukabm.data import PyPSAGBData
    data = PyPSAGBData(a.pypsa_gb)
for name in a.scenarios:
    t0 = time.time()
    m = GBMarketModel(get_scenario(name), data=data, end=a.end, seed=a.seed, network_every=a.network_every)
    r = m.run()
    r.to_csv(out / f"annual_{name}.csv")
    keep = {y: m.hourly[y] for y in m.hourly if y % 5 == 0}
    extra = {"hourly": keep, "network": m.network_results, "cm_log": getattr(m, "cm_log", []),
             "buses": m.data.buses, "links": m.data.links_for_year(m.network_results.get("year", a.end))}
    with open(out / f"detail_{name}.pkl", "wb") as f:
        pickle.dump(extra, f)
    print(f"{name}: {time.time() - t0:.0f}s  price2050={r.price_twa.iloc[-1]:.1f}  "
          f"CI2050={r.intensity_g_kwh.iloc[-1]:.1f} g/kWh  LOLE={r.lole_h.sum()} h", flush=True)
