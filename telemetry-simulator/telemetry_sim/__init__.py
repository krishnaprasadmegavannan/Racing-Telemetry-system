"""Vehicle telemetry simulator that stands in for the ESP32 + sensor node."""
from .config import SCHEMA_VERSION, SimConfig
from .faults import FaultInjector
from .scenarios import Phase, get_playlist
from .simulator import Simulator

__all__ = ["SCHEMA_VERSION", "SimConfig", "FaultInjector", "Phase", "get_playlist", "Simulator"]
