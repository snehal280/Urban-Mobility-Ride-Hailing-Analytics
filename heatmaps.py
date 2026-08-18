"""
Heatmap generators for pickup density and demand-supply gap.
Outputs: static PNG and interactive HTML.
"""

from pathlib import Path
from typing import Optional

import pandas as pd
import numpy as np
from loguru import logger

from src.utils.config import FIGURES_DIR, MAPS_DIR, MAP_CENTER, MAP_ZOOM


def pickup_density_folium(
    trips: pd.DataFrame,
    lat_col: str = "pickup_lat",
    lon_col: str = "pickup_lon",
    output_path: Optional[Path] = None,
    max_points: int = 20_000,
) -> str:
    """
    Create a Folium heatmap of pickup density.
    Returns path to saved HTML file.
    """
    import folium
    from folium.plugins import HeatMap

    df = trips[[lat_col, lon_col]].dropna()
    if len(df) > max_points:
        df = df.sample(max_points, random_state=42)

    heat_data = df[[lat_col, lon_col]].values.tolist()

    m = folium.Map(location=MAP_CENTER, zoom_start=MAP_ZOOM, tiles="CartoDB dark_matter")
    HeatMap(
        heat_data,
        min_opacity=0.3,
        radius=10,
        blur=8,
        gradient={0.4: "blue", 0.65: "lime", 1.0: "red"},
    ).add_to(m)

    folium.TileLayer("CartoDB dark_matter").add_to(m)
    
    output_path = output_path or MAPS_DIR / "pickup_density_heatmap.html"
    m.save(str(output_path))
    logger.info(f"Saved heatmap: {output_path}")
    return str(output_path)


def demand_supply_gap_folium(
    gap_df: pd.DataFrame,
    zones_gdf,
    spatial_col: str = "zone_id",
    output_path: Optional[Path] = None,
) -> str:
    """
    Create an animated Folium choropleth map of demand-supply gap by zone.
    """
    import folium
    import geopandas as gpd
    import json

    # Aggregate to peak hour per zone
    peak = (
        gap_df.sort_values("gap", ascending=False)
        .groupby(spatial_col)
        .first()
        .reset_index()
    )

    # Merge with geodata
    merged = zones_gdf.merge(peak, on=spatial_col, how="left")
    merged["gap"] = merged["gap"].fillna(0)

    m = folium.Map(location=MAP_CENTER, zoom_start=MAP_ZOOM, tiles="CartoDB positron")

    folium.Choropleth(
        geo_data=merged.__geo_interface__,
        data=merged,
        columns=[spatial_col, "gap"],
        key_on=f"feature.properties.{spatial_col}",
        fill_color="YlOrRd",
        fill_opacity=0.7,
        line_opacity=0.2,
        legend_name="Demand-Supply Gap (trips/hour)",
        nan_fill_color="white",
    ).add_to(m)

    output_path = output_path or MAPS_DIR / "demand_supply_gap.html"
    m.save(str(output_path))
    logger.info(f"Saved demand-supply gap map: {output_path}")
    return str(output_path)


def hourly_heatmap_plotly(
    trips: pd.DataFrame,
    output_path: Optional[Path] = None,
) -> str:
    """
    Create a Plotly heatmap: weekday (y) vs hour (x) vs demand (color).
    """
    import plotly.express as px
    import plotly.graph_objects as go

    trips = trips.copy()
    trips["hour"]    = pd.to_datetime(trips["request_time"]).dt.hour
    trips["weekday"] = pd.to_datetime(trips["request_time"]).dt.day_name()

    pivot = (
        trips.groupby(["weekday", "hour"])
        .size()
        .reset_index(name="demand")
        .pivot(index="weekday", columns="hour", values="demand")
    )
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    pivot = pivot.reindex([d for d in day_order if d in pivot.index])

    fig = px.imshow(
        pivot,
        labels=dict(x="Hour of Day", y="Day of Week", color="Trip Requests"),
        color_continuous_scale="YlOrRd",
        aspect="auto",
        title="Demand Heatmap: Hour of Day vs Day of Week",
    )
    fig.update_layout(
        template="plotly_dark",
        title_font_size=18,
        font_family="Inter, sans-serif",
    )

    output_path = output_path or FIGURES_DIR / "demand_hourly_heatmap.html"
    fig.write_html(str(output_path))
    fig.write_image(str(FIGURES_DIR / "demand_hourly_heatmap.png"), width=1200, height=500)
    logger.info(f"Saved hourly heatmap: {output_path}")
    return str(output_path)


def animated_pickup_map(
    trips: pd.DataFrame,
    n_hours: int = 24,
    output_path: Optional[Path] = None,
) -> str:
    """
    Create an animated Plotly scatter map of pickup locations by hour.
    """
    import plotly.express as px

    df = trips.copy()
    df["hour"] = pd.to_datetime(df["request_time"]).dt.hour.astype(str).str.zfill(2) + ":00"
    df = df.dropna(subset=["pickup_lat", "pickup_lon"])
    df = df[df["status"] == "completed"].head(30_000)

    fig = px.scatter_mapbox(
        df,
        lat="pickup_lat",
        lon="pickup_lon",
        animation_frame="hour",
        color="surge_multiplier",
        color_continuous_scale="YlOrRd",
        size_max=5,
        zoom=10,
        mapbox_style="carto-darkmatter",
        title="Animated Pickup Locations by Hour (colored by surge multiplier)",
        opacity=0.6,
    )
    fig.update_layout(template="plotly_dark", height=600)

    output_path = output_path or MAPS_DIR / "animated_pickup_map.html"
    fig.write_html(str(output_path))
    logger.info(f"Saved animated map: {output_path}")
    return str(output_path)
