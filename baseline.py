"""
Baseline forecasting models:
  - Naive (last-week same-hour)
  - Rolling average
  - Exponential smoothing (ETS)
"""

from typing import Optional

import numpy as np
import pandas as pd
from loguru import logger

try:
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    STATSMODELS_OK = True
except ImportError:
    STATSMODELS_OK = False
    logger.warning("statsmodels not found; ETS baseline unavailable.")


class NaiveModel:
    """Naive seasonal forecast: last-week same-hour value."""
    def __init__(self, seasonal_period: int = 168):  # 168h = 1 week
        self.seasonal_period = seasonal_period
        self.history: Optional[np.ndarray] = None

    def fit(self, series: pd.Series) -> "NaiveModel":
        self.history = series.values.copy()
        return self

    def predict(self, n_steps: int) -> np.ndarray:
        preds = []
        for i in range(n_steps):
            idx = -(self.seasonal_period - i % self.seasonal_period)
            preds.append(self.history[idx] if abs(idx) <= len(self.history) else self.history[-1])
        return np.array(preds)


class RollingAverageModel:
    """Rolling window average forecast."""
    def __init__(self, window: int = 168):
        self.window = window
        self.last_values: Optional[np.ndarray] = None

    def fit(self, series: pd.Series) -> "RollingAverageModel":
        self.last_values = series.values[-self.window:]
        return self

    def predict(self, n_steps: int) -> np.ndarray:
        return np.full(n_steps, self.last_values.mean())


class ETSModel:
    """Exponential Smoothing (Holt-Winters) model."""
    def __init__(self, seasonal_periods: int = 24, trend: str = "add", seasonal: str = "add"):
        self.seasonal_periods = seasonal_periods
        self.trend    = trend
        self.seasonal = seasonal
        self._model   = None

    def fit(self, series: pd.Series) -> "ETSModel":
        if not STATSMODELS_OK:
            raise ImportError("statsmodels required for ETSModel")
        self._model = ExponentialSmoothing(
            series,
            trend=self.trend,
            seasonal=self.seasonal,
            seasonal_periods=self.seasonal_periods,
        ).fit(optimized=True)
        return self

    def predict(self, n_steps: int) -> np.ndarray:
        return self._model.forecast(n_steps).values


def fit_all_baselines(series: pd.Series, horizon: int = 24) -> dict:
    """Fit all baseline models and return predictions dict."""
    results = {}
    
    naive = NaiveModel().fit(series)
    results["naive"] = naive.predict(horizon)
    
    rolling = RollingAverageModel(window=168).fit(series)
    results["rolling_avg"] = rolling.predict(horizon)
    
    if STATSMODELS_OK and len(series) >= 48:
        try:
            ets = ETSModel(seasonal_periods=24).fit(series)
            results["ets"] = ets.predict(horizon)
        except Exception as e:
            logger.warning(f"ETS failed: {e}")
    
    return results
