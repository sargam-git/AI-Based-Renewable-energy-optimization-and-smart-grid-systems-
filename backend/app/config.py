"""Paths and non-secret defaults. All electrical values are explicitly simulated."""
from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
DATA = Path(os.getenv("HELIOGRID_DATA_DIR", BACKEND / "data"))
MODELS = Path(os.getenv("HELIOGRID_MODEL_DIR", BACKEND / "trained_models"))
DB_PATH = Path(os.getenv("HELIOGRID_DB", DATA / "heliogrid.db"))
DATA.mkdir(parents=True, exist_ok=True)
MODELS.mkdir(parents=True, exist_ok=True)
DATABASE_URL = f"sqlite:///{DB_PATH}"
SITE = "Indore educational microgrid"
TIMEZONE = "Asia/Kolkata (fixed UTC+05:30, no DST)"
SIM_START = "2026-11-01T10:00:00"
DATA_NOTICE = "Reproducible synthetic data. No live hardware, real weather feed, or certified grid control."
SOLAR_CAPACITY = 650.0
WIND_CAPACITY = 450.0
TRANSFORMER_KVA = 1000.0
