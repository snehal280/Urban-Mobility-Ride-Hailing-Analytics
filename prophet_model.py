"""
Prophet demand forecasting model.
"""

import pickle
from pathlib import Path
from typing import Optional

import pandas as pd
from loguru import logger

try:
    from prophet import Prophet
    PROPHET_OK = True
except ImportError:
    PROPHET_OK = False
    logger.warning("prophet not installed.")

from src.utils.config import MODELS_DIR


class ProphetDemandForecaster:
    """Prophet-based hourly demand forecaster."""

    def __init__(self, zone_id: str = "all",
                 yearly_seasonality: bool = True,
                 weekly_seasonality: bool = True,
                 daily_seasonality: bool = True,
                 changepoint_prior_scale: float = 0.05):
        if not PROPHET_OK:
            raise ImportError("prophet library required")
        self.zone_id = zone_id
        self.model = Prophet(
            yearly_seasonality=yearly_seasonality,
            weekly_seasonality=weekly_seasonality,
            daily_seasonality=daily_seasonality,
            changepoint_prior_scale=changepoint_prior_scale,
        )
        self._fitted = False

    def fit(self, df: pd.DataFrame, target: str = "demand") -> "ProphetDemandForecaster":
        """df must have 'hour' (datetime) and target columns."""
        prophet_df = df[["hour", target]].rename(columns={"hour": "ds", target: "y"})
        prophet_df["ds"] = pd.to_datetime(prophet_df["ds"]).dt.tz_localize(None)
        self.model.fit(prophet_df)
        self._fitted = True
        logger.info(f"Prophet fitted for zone={self.zone_id}")
        return self

    def predict(self, horizon_hours: int = 24) -> pd.DataFrame:
        """Return DataFrame with ds, yhat, yhat_lower, yhat_upper."""
        future = self.model.make_future_dataframe(periods=horizon_hours, freq="h")
        forecast = self.model.predict(future)
        forecast["yhat"] = forecast["yhat"].clip(lower=0)
        return forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].tail(horizon_hours)

    def save(self, path: Optional[Path] = None) -> Path:
        path = path or MODELS_DIR / f"prophet_{self.zone_id}.pkl"
        with open(path, "wb") as f:
            pickle.dump(self, f)
        return path

    @classmethod
    def load(cls, path: Path) -> "ProphetDemandForecaster":
        with open(path, "rb") as f:
            return pickle.load(f)
