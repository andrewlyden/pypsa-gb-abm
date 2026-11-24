"""Build data/pypsagb_snapshot from a local PyPSA-GB clone.

    python scripts/extract_pypsagb_snapshot.py /path/to/PyPSA-GB [--year 2024]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ukabm.data.pypsagb import PyPSAGBData  # noqa: E402

p = argparse.ArgumentParser()
p.add_argument("root")
p.add_argument("--year", type=int, default=2024)
a = p.parse_args()
d = PyPSAGBData(a.root, profile_year=a.year)
d.save_snapshot()
print("snapshot written; profile stats:\n", d.profiles.describe().T)
print(d.zone_tech_share.round(3))
