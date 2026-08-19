"""
Time series visualization for demand, fares and forecasts.
"""

from pathlib import Path
from typing import Optional

import pandas as pd
import numpy as np

from loguru import logger
from src.utils.config import FIGURES_DIR


def plot_demand_time_series(
    trips: pd.DataFrame,
    freq: str = "h",
    output_path: Optional[Path] = None,
) -> str:
    """Plot overall hourly demand time series with weekday/weekend overlay."""
    import plotly.graph_objects as go

    df = trips.copy()
    df["hour"] = pd.to_datetime(df["request_time"]).dt.floor(freq)
    hourly = df.groupby(["hour"]).size().reset_index(name="demand")
    hourly["is_weekend"] = pd.to_datetime(hourly["hour"]).dt.weekday >= 5

    weekday = hourly[~hourly["is_weekend"]]
    weekend = hourly[hourly["is_weekend"]]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=weekday["hour"], y=weekday["demand"],
        name="Weekday", line=dict(color="#4FC3F7", width=1.5), opacity=0.8
    ))
    fig.add_trace(go.Scatter(
        x=weekend["hour"], y=weekend["demand"],
        name="Weekend", line=dict(color="#FF7043", width=1.5), opacity=0.8
    ))

    fig.update_layout(
        title="Hourly Ride Demand: Weekday vs Weekend",
        xaxis_title="Time",
        yaxis_title="Trip Requests",
        template="plotly_dark",
        legend=dict(orientation="h", y=1.02),
        font_family="Inter, sans-serif",
        height=450,
    )

    output_path = output_path or FIGURES_DIR / "demand_time_series.html"
    fig.write_html(str(output_path))
    fig.write_image(str(FIGURES_DIR / "demand_time_series.png"), width=1400, height=450)
    logger.info(f"Saved demand time series: {output_path}")
    return str(output_path)


def plot_fare_vs_distance(
    trips: pd.DataFrame,
    output_path: Optional[Path] = None,
) -> str:
    """Scatter plot of fare vs distance with regression line."""
    import plotly.express as px
    import plotly.graph_objects as go
    from sklearn.linear_model import LinearRegression

    df = trips[trips["status"] == "completed"].dropna(
        subset=["fare_amount", "distance_km"]
    ).copy()
    df = df[df["distance_km"] < 50]  # Remove extreme outliers

    # Regression line
    X = df[["distance_km"]].values
    y = df["fare_amount"].values
    reg = LinearRegression().fit(X, y)
    x_range = np.linspace(X.min(), X.max(), 100)
    y_pred  = reg.predict(x_range.reshape(-1, 1))

    fig = px.scatter(
        df.sample(min(10_000, len(df)), random_state=42),
        x="distance_km", y="fare_amount",
        color="surge_multiplier",
        color_continuous_scale="YlOrRd",
        opacity=0.5,
        title=f"Fare vs Distance  (R²={reg.score(X, y):.3f})",
        labels={"distance_km": "Distance (km)", "fare_amount": "Fare (INR)"},
        template="plotly_dark",
    )
    fig.add_trace(go.Scatter(
        x=x_range, y=y_pred,
        mode="lines", name="Regression",
        line=dict(color="white", width=2, dash="dash")
    ))
    fig.update_layout(font_family="Inter, sans-serif", height=500)

    output_path = output_path or FIGURES_DIR / "fare_vs_distance.html"
    fig.write_html(str(output_path))
    fig.write_image(str(FIGURES_DIR / "fare_vs_distance.png"), width=1200, height=500)
    return str(output_path)


def plot_forecast_vs_actual(
    actual: pd.Series,
    predicted: pd.Series,
    lower: Optional[pd.Series] = None,
    upper: Optional[pd.Series] = None,
    output_path: Optional[Path] = None,
) -> str:
    """Plot observed vs predicted demand with optional confidence bands."""
    import plotly.graph_objects as go
    from src.utils.helpers import mae, rmse, mape

    mae_v  = mae(actual.values,  predicted.values)
    rmse_v = rmse(actual.values, predicted.values)
    mape_v = mape(actual.values, predicted.values)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=actual.index, y=actual,
        name="Actual", line=dict(color="#4FC3F7", width=2)
    ))
    fig.add_trace(go.Scatter(
        x=predicted.index, y=predicted,
        name="Forecast", line=dict(color="#FF7043", width=2, dash="dot")
    ))
    if lower is not None and upper is not None:
        fig.add_trace(go.Scatter(
            x=list(upper.index) + list(lower.index[::-1]),
            y=list(upper.values) + list(lower.values[::-1]),
            fill="toself", fillcolor="rgba(255,112,67,0.15)",
            line=dict(color="rgba(255,255,255,0)"),
            name="95% CI"
        ))
    fig.update_layout(
        title=f"Demand Forecast vs Actual  |  MAE={mae_v:.1f}  RMSE={rmse_v:.1f}  MAPE={mape_v:.1f}%",
        xaxis_title="Time",
        yaxis_title="Trip Requests / Hour",
        template="plotly_dark",
        font_family="Inter, sans-serif",
        height=450,
    )

    output_path = output_path or FIGURES_DIR / "forecast_vs_actual.html"
    fig.write_html(str(output_path))
    fig.write_image(str(FIGURES_DIR / "forecast_vs_actual.png"), width=1400, height=450)
    return str(output_path)
