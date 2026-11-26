"""ukabm: a modular agent-based model of the GB electricity market linked to PyPSA-GB data,
with hooks for heat, gas, hydrogen and EV demand."""
__version__ = "0.1.0"
from .model import GBMarketModel  # noqa: F401
from .scenarios import SCENARIOS, get_scenario  # noqa: F401
from .ensemble import run_ensemble, bands  # noqa: F401
