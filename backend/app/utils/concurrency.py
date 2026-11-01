"""Serialize simulation state transitions within this single-worker application."""
from threading import RLock
simulation_lock=RLock()
