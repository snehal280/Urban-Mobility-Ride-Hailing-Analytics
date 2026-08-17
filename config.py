"""Global configuration and path constants."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ─── Project root ────────────────────────────────────────────
ROOT_DIR = Path(__file__).resolve().parent.parent.parent

# ─── Data paths ──────────────────────────────────────────────
DATA_SAMPLE_DIR = ROOT_DIR / "data_sample"
DATA_RAW_DIR    = ROOT_DIR / "data" / "raw"
DATA_PROC_DIR   = ROOT_DIR / "data" / "processed"
DATA_PROC_DIR.mkdir(parents=True, exist_ok=True)
DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)

# ─── Output paths ────────────────────────────────────────────
OUTPUTS_DIR = ROOT_DIR / "outputs"
FIGURES_DIR = OUTPUTS_DIR / "figures"
MAPS_DIR    = OUTPUTS_DIR / "maps"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)
MAPS_DIR.mkdir(parents=True, exist_ok=True)

# ─── Dashboard exports ───────────────────────────────────────
DASHBOARD_EXPORTS_DIR = ROOT_DIR / "dashboards" / "exports"
DASHBOARD_EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

# ─── Models ──────────────────────────────────────────────────
MODELS_DIR = ROOT_DIR / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# ─── Database settings ───────────────────────────────────────
DB_HOST     = os.getenv("DB_HOST", "localhost")
DB_PORT     = int(os.getenv("DB_PORT", "5432"))
DB_NAME     = os.getenv("DB_NAME", "mobility_db")
DB_USER     = os.getenv("DB_USER", "analyst")
DB_PASSWORD = os.getenv("DB_PASSWORD", "analytics2024")
DATABASE_URL = (
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# ─── H3 settings ─────────────────────────────────────────────
H3_RESOLUTION = 8  # ~460m edge length

# ─── Demand-Supply settings ───────────────────────────────────
DEMAND_SUPPLY_THRESHOLD = 1.5   # ratio above which gap is significant
SURGE_THRESHOLD         = 1.2   # surge multiplier threshold

# ─── Forecasting settings ────────────────────────────────────
FORECAST_HORIZON_HOURS = 24
FORECAST_CV_SPLITS     = 5

# ─── Visualization settings ──────────────────────────────────
MAP_CENTER  = [12.9716, 77.5946]   # Default: Bangalore
MAP_ZOOM    = 11
COLOR_SCALE = "YlOrRd"              # Demand heatmap color scale
