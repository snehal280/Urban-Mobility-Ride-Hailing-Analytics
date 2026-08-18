"""Shared utility functions."""

import hashlib
import math
from datetime import datetime, timezone
from typing import Optional, Tuple

import numpy as np
import pandas as pd
from loguru import logger


def hash_id(value: str) -> str:
    """SHA-256 hash an identifier for anonymization."""
    return hashlib.sha256(str(value).encode()).hexdigest()[:16]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compute haversine distance in km between two lat/lon points."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def to_utc(ts: pd.Series) -> pd.Series:
    """Normalize a pandas timestamp series to UTC."""
    if ts.dt.tz is None:
        return ts.dt.tz_localize("UTC")
    return ts.dt.tz_convert("UTC")


def add_time_features(df: pd.DataFrame, ts_col: str = "request_time") -> pd.DataFrame:
    """Add standard time features derived from a timestamp column."""
    ts = df[ts_col]
    df = df.copy()
    df["hour"]       = ts.dt.hour
    df["weekday"]    = ts.dt.weekday        # 0=Mon ... 6=Sun
    df["is_weekend"] = (df["weekday"] >= 5).astype(int)
    df["date"]       = ts.dt.date
    df["month"]      = ts.dt.month
    df["week"]       = ts.dt.isocalendar().week.astype(int)
    return df


def add_holiday_flag(df: pd.DataFrame, country: str = "IN", date_col: str = "date") -> pd.DataFrame:
    """Add is_holiday flag using pyholidays."""
    try:
        import holidays
        holiday_set = holidays.country_holidays(country)
        df = df.copy()
        df["is_holiday"] = df[date_col].apply(lambda d: int(d in holiday_set))
    except ImportError:
        logger.warning("pyholidays not installed; setting is_holiday=0")
        df["is_holiday"] = 0
    return df


def remove_outliers_iqr(df: pd.DataFrame, col: str, multiplier: float = 3.0) -> pd.DataFrame:
    """Remove outliers beyond multiplier * IQR from Q1/Q3."""
    Q1 = df[col].quantile(0.25)
    Q3 = df[col].quantile(0.75)
    IQR = Q3 - Q1
    mask = (df[col] >= Q1 - multiplier * IQR) & (df[col] <= Q3 + multiplier * IQR)
    n_removed = (~mask).sum()
    logger.info(f"Outlier removal [{col}]: removed {n_removed} rows ({n_removed/len(df)*100:.2f}%)")
    return df[mask].copy()


def compute_zscore(series: pd.Series) -> pd.Series:
    """Standardize a series to z-scores."""
    mu, sigma = series.mean(), series.std()
    if sigma == 0:
        return pd.Series(np.zeros(len(series)), index=series.index)
    return (series - mu) / sigma


def mae(actual: np.ndarray, predicted: np.ndarray) -> float:
    return float(np.mean(np.abs(actual - predicted)))


def rmse(actual: np.ndarray, predicted: np.ndarray) -> float:
    return float(np.sqrt(np.mean((actual - predicted) ** 2)))


def mape(actual: np.ndarray, predicted: np.ndarray, eps: float = 1e-8) -> float:
    return float(np.mean(np.abs((actual - predicted) / (np.abs(actual) + eps))) * 100)
