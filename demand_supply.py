"""
Demand-Supply gap computation.
Computes demand, supply, gap, and significance per H3 cell or zone per hour.
"""

import pandas as pd
import numpy as np
from loguru import logger

from src.utils.config import DEMAND_SUPPLY_THRESHOLD
from src.utils.helpers import compute_zscore


def compute_demand(
    trips: pd.DataFrame,
    time_unit: str = "h",
    spatial_col: str = "h3_pickup",
) -> pd.DataFrame:
    """
    Compute demand (trip requests) per spatial unit per time window.

    Returns DataFrame with columns:
        hour, <spatial_col>, city, demand, completed, cancelled
    """
    trips = trips.copy()
    trips["hour"] = trips["request_time"].dt.floor(time_unit)

    demand = (
        trips.groupby(["hour", spatial_col, "city"])
        .agg(
            demand=("trip_id", "count"),
            completed=("status", lambda x: (x == "completed").sum()),
            cancelled=("status", lambda x: (x == "cancelled").sum()),
            avg_surge=("surge_multiplier", "mean"),
        )
        .reset_index()
    )
    logger.info(f"Computed demand: {len(demand):,} spatial-time cells.")
    return demand


def compute_supply(
    drivers: pd.DataFrame,
    spatial_col: str = "zone_id",
    time_unit: str = "h",
) -> pd.DataFrame:
    """
    Estimate supply (available drivers) per spatial unit per time window.
    """
    drivers = drivers.copy()
    drivers["hour"] = pd.to_datetime(drivers["driver_status_ts"], utc=True).dt.floor(time_unit)

    supply = (
        drivers[drivers["current_status"].isin(["online", "on_trip"])]
        .groupby(["hour", spatial_col, "city"])
        .agg(
            active_drivers=("driver_id", "nunique"),
            available_drivers=("driver_id",
                lambda x: drivers.loc[
                    x.index[drivers.loc[x.index, "current_status"] == "online"],
                    "driver_id"
                ].nunique()),
        )
        .reset_index()
    )
    logger.info(f"Computed supply: {len(supply):,} cells.")
    return supply


def compute_gap(
    demand: pd.DataFrame,
    supply: pd.DataFrame,
    spatial_col: str = "zone_id",
) -> pd.DataFrame:
    """
    Merge demand and supply; compute gap and significance.
    """
    gap_df = demand.merge(
        supply[["hour", spatial_col, "city", "available_drivers"]],
        on=["hour", spatial_col, "city"],
        how="left",
    )
    gap_df["available_drivers"] = gap_df["available_drivers"].fillna(0)
    gap_df["gap"]   = gap_df["demand"] - gap_df["available_drivers"]
    gap_df["ratio"] = gap_df["demand"] / gap_df["available_drivers"].replace(0, np.nan)

    # Z-score significance per cell across time
    gap_df["gap_zscore"] = gap_df.groupby(spatial_col)["gap"].transform(compute_zscore)
    gap_df["is_significant_shortage"] = (
        (gap_df["ratio"] > DEMAND_SUPPLY_THRESHOLD) | (gap_df["gap_zscore"] > 1.5)
    ).astype(int)

    logger.info(
        f"Significant shortages: "
        f"{gap_df['is_significant_shortage'].sum():,} / {len(gap_df):,} cell-hours."
    )
    return gap_df


def aggregate_gap_for_map(
    gap_df: pd.DataFrame,
    spatial_col: str = "zone_id",
    top_hours: int = 24,
) -> pd.DataFrame:
    """
    Return pivot-friendly DataFrame for animated choropleth map.
    Columns: spatial_col, hour (str), demand, supply, gap, ratio
    """
    subset = gap_df.copy()
    subset["hour_str"] = subset["hour"].dt.strftime("%Y-%m-%d %H:00")
    return subset[[spatial_col, "hour_str", "city", "demand", "available_drivers", "gap", "ratio", "gap_zscore"]]
