"""
LightGBM demand forecasting model.
Trained per zone on time-series features + exogenous regressors.
"""

import pickle
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from loguru import logger

try:
    import lightgbm as lgb
    LGBM_OK = True
except ImportError:
    LGBM_OK = False
    logger.warning("lightgbm not installed.")

from src.utils.config import MODELS_DIR, FORECAST_HORIZON_HOURS


FEATURE_COLS = [
    "hour", "weekday", "is_weekend", "is_holiday",
    "month", "week",
    # Lagged demand
    "demand_lag1", "demand_lag24", "demand_lag168",
    # Rolling stats
    "demand_roll_mean_24", "demand_roll_std_24",
    "demand_roll_mean_168",
    # Exogenous
    "temp_c", "precip_mm", "wind_kmh",
    "is_event_hour",
    "avg_surge",
]


def build_features(hourly: pd.DataFrame) -> pd.DataFrame:
    """Build feature matrix from hourly demand DataFrame."""
    df = hourly.sort_values("hour").copy()
    df["hour_of_day"] = df["hour"].dt.hour
    df["weekday"]     = df["hour"].dt.weekday
    df["is_weekend"]  = (df["weekday"] >= 5).astype(int)
    df["month"]       = df["hour"].dt.month
    df["week"]        = df["hour"].dt.isocalendar().week.astype(int)

    # Lag features
    for lag in [1, 24, 168]:
        df[f"demand_lag{lag}"] = df["demand"].shift(lag)
    # Rolling features
    df["demand_roll_mean_24"]  = df["demand"].shift(1).rolling(24).mean()
    df["demand_roll_std_24"]   = df["demand"].shift(1).rolling(24).std()
    df["demand_roll_mean_168"] = df["demand"].shift(1).rolling(168).mean()

    # Fill exogenous if missing
    for col in ["temp_c", "precip_mm", "wind_kmh", "is_event_hour", "avg_surge", "is_holiday"]:
        if col not in df.columns:
            df[col] = 0

    df = df.rename(columns={"hour_of_day": "hour"})
    df = df.dropna(subset=["demand_lag1", "demand_lag24"])
    return df


class LGBMDemandForecaster:
    """LightGBM-based hourly demand forecaster per zone."""

    def __init__(self, zone_id: str = "all", n_estimators: int = 500,
                 learning_rate: float = 0.05, num_leaves: int = 63):
        self.zone_id       = zone_id
        self.n_estimators  = n_estimators
        self.learning_rate = learning_rate
        self.num_leaves    = num_leaves
        self.model         = None
        self.feature_cols: List[str] = []

    def fit(self, df: pd.DataFrame, target: str = "demand") -> "LGBMDemandForecaster":
        if not LGBM_OK:
            raise ImportError("lightgbm is required")
        feat_df = build_features(df)
        available = [c for c in FEATURE_COLS if c in feat_df.columns]
        self.feature_cols = available
        X = feat_df[available]
        y = feat_df[target]
        self.model = lgb.LGBMRegressor(
            n_estimators=self.n_estimators,
            learning_rate=self.learning_rate,
            num_leaves=self.num_leaves,
            min_child_samples=10,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
        )
        self.model.fit(X, y)
        logger.info(f"LightGBM fitted for zone={self.zone_id}, features={available}")
        return self

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        feat_df = build_features(df)
        X = feat_df[[c for c in self.feature_cols if c in feat_df.columns]]
        return self.model.predict(X).clip(min=0)

    def save(self, path: Optional[Path] = None) -> Path:
        path = path or MODELS_DIR / f"lgbm_{self.zone_id}.pkl"
        with open(path, "wb") as f:
            pickle.dump(self, f)
        logger.info(f"Model saved: {path}")
        return path

    @classmethod
    def load(cls, path: Path) -> "LGBMDemandForecaster":
        with open(path, "rb") as f:
            return pickle.load(f)

    def feature_importance(self) -> pd.DataFrame:
        if self.model is None:
            raise ValueError("Model not fitted")
        return pd.DataFrame({
            "feature":   self.feature_cols,
            "importance": self.model.feature_importances_,
        }).sort_values("importance", ascending=False)
