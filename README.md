# 🚗 Urban Mobility & Ride-Hailing Analytics

> **Answering the central question:** _When, where, and why does ride demand increase?_

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Power BI](https://img.shields.io/badge/Power%20BI-Dashboard-orange)](dashboards/)
[![Docker](https://img.shields.io/badge/Docker-Ready-brightgreen)](Dockerfile)

---

## 📌 Project Overview

This project provides a **complete, reproducible analytics pipeline** for Uber/Ola-style ride-hailing data. It covers:

- **Data Engineering**: Ingestion, cleaning, enrichment (weather, events), H3 geospatial indexing
- **Exploratory Data Analysis**: Demand patterns, fare trends, cancellations, driver utilization
- **Demand–Supply Heatmaps**: Where and when demand outstrips supply
- **Forecasting**: Baseline (ETS, naive) + advanced (LightGBM, Prophet) models per zone
- **Dashboards**: Power BI 5-page dashboard + interactive HTML maps

---

## 🎯 Project Objectives

| # | Analysis Task |
|---|---------------|
| 1 | Peak demand hours (city / zone / weekday / holiday) |
| 2 | Weekday vs weekend demand patterns |
| 3 | Pickup & dropoff hotspots, OD flows |
| 4 | Fare trends by time, zone, distance, dynamic pricing |
| 5 | Trip duration & distance distributions; outlier detection |
| 6 | Driver utilization (active drivers, idle time) |
| 7 | Cancellation patterns (who/when/correlates) |
| 8 | Surge pricing timing and demand-supply relation |
| 9 | Short-term hourly demand forecasting per zone |
| 10 | Demand–Supply Gap heatmap (animated by hour) |

---

## 🗂️ Repository Structure

```
urban-mobility-analytics/
├── data_sample/              # Anonymized sample CSVs and Parquet files
│   ├── trips_sample.csv
│   ├── drivers_sample.csv
│   ├── zones_sample.geojson
│   ├── weather_sample.csv
│   ├── events_sample.csv
│   ├── cancellations_sample.csv
│   ├── surge_events_sample.csv
│   └── schema.md             # Data dictionary
├── sql/
│   ├── 01_create_tables.sql
│   ├── 02_ingest_data.sql
│   ├── 03_aggregations.sql
│   └── 04_analytic_queries.sql
├── src/
│   ├── etl/
│   │   ├── __init__.py
│   │   ├── loader.py         # CSV/Parquet loader with chunking
│   │   ├── cleaner.py        # Data quality & normalization
│   │   └── enricher.py       # Join weather, events, H3 index
│   ├── features/
│   │   ├── __init__.py
│   │   ├── time_features.py  # Hour, weekday, holiday flags
│   │   ├── geo_features.py   # H3 indexing, spatial joins
│   │   └── demand_supply.py  # Gap computation
│   ├── models/
│   │   ├── __init__.py
│   │   ├── baseline.py       # Naive, rolling avg, ETS
│   │   ├── lgbm_model.py     # LightGBM demand forecaster
│   │   ├── prophet_model.py  # Prophet forecaster
│   │   └── evaluator.py      # MAE, RMSE, MAPE + cross-val
│   ├── viz/
│   │   ├── __init__.py
│   │   ├── heatmaps.py       # Folium / Plotly heatmaps
│   │   ├── time_series.py    # Demand time series charts
│   │   └── geo_maps.py       # Choropleth, OD flow maps
│   └── utils/
│       ├── __init__.py
│       ├── config.py         # Paths, constants
│       └── helpers.py        # Shared utility functions
├── notebooks/
│   ├── 01_data_exploration.ipynb
│   ├── 02_feature_engineering.ipynb
│   ├── 03_driver_utilization.ipynb
│   ├── 04_demand_supply_heatmap.ipynb
│   └── 05_forecasting.ipynb
├── dashboards/
│   ├── powerbi_guide.md
│   ├── powerbi_template_instructions.md
│   └── exports/              # Pre-aggregated CSVs for Power BI
│       ├── hourly_zone_demand.csv
│       ├── driver_utilization_summary.csv
│       ├── cancellation_summary.csv
│       ├── surge_summary.csv
│       └── forecast_output.csv
├── outputs/
│   ├── figures/              # Static PNG exports
│   └── maps/                 # Interactive HTML maps
├── tests/
│   ├── test_data_sanity.py
│   ├── test_etl.py
│   └── test_features.py
├── .github/
│   └── workflows/
│       └── ci.yml
├── requirements.txt
├── environment.yml
├── Dockerfile
├── docker-compose.yml
├── .gitignore
├── LICENSE
└── README.md
```

---

## 📊 Data Schema

See [data_sample/schema.md](data_sample/schema.md) for the full data dictionary.

| Table | Key Fields |
|-------|------------|
| `trips` | trip_id, request_time, pickup/dropoff lat/lon, fare, surge_multiplier, status |
| `drivers` | driver_id, current_status, zone_id, shift_start/end |
| `zones` | zone_id, geom (GeoJSON), name |
| `cancellations` | trip_id, cancel_time, cancelled_by, cancel_reason |
| `surge_events` | city, zone_id, start_time, end_time, multiplier |
| `weather` | city, time, temp_c, precip_mm, wind_kmh |
| `events` | city, start_time, end_time, event_type, attendance_estimate |

---

## ⚡ Quick Start

### Option 1: Local Python Environment

```bash
# 1. Clone the repo
git clone https://github.com/your-org/urban-mobility-analytics.git
cd urban-mobility-analytics

# 2. Create and activate environment
conda env create -f environment.yml
conda activate urban-mobility

# OR with pip
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # Linux/Mac
pip install -r requirements.txt

# 3. Generate sample data
python src/etl/loader.py --generate-sample

# 4. Run ETL pipeline
python src/etl/cleaner.py
python src/etl/enricher.py

# 5. Launch notebooks
jupyter lab notebooks/
```

### Option 2: Docker

```bash
docker-compose up --build
# Navigate to http://localhost:8888 for JupyterLab
```

### Option 3: Run SQL Aggregations

```bash
# With PostgreSQL running:
psql -U postgres -d mobility_db -f sql/01_create_tables.sql
psql -U postgres -d mobility_db -f sql/02_ingest_data.sql
psql -U postgres -d mobility_db -f sql/03_aggregations.sql
```

---

## 🔑 Key Results Summary

| Insight | Finding (example on sample data) |
|---------|----------------------------------|
| Peak demand hour | 8–9 AM and 5–7 PM on weekdays |
| Highest demand zone | Downtown (Zone 01) — 3.2× avg demand |
| Weekend uplift | +18% Saturday vs weekday average |
| Rain impact | +22% demand when precip > 5 mm |
| Cancellation rate | 12.4% overall; 28% driver-cancelled in surge areas |
| Forecast accuracy | LightGBM: MAPE 8.3%, RMSE 14.2 trips/hr |
| Demand–Supply gap | Peaks at 6 PM Friday — 2.4× supply deficit |

---

## 📈 Notebooks Guide

| Notebook | Description | Runtime |
|----------|-------------|--------|
| `01_data_exploration.ipynb` | Full EDA: distributions, time series, maps | ~5 min |
| `02_feature_engineering.ipynb` | H3 indexing, time features, weather join | ~3 min |
| `03_driver_utilization.ipynb` | Active drivers, idle time, trips/driver | ~3 min |
| `04_demand_supply_heatmap.ipynb` | Animated heatmap, gap analysis | ~5 min |
| `05_forecasting.ipynb` | Baseline + LightGBM + Prophet, metrics | ~10 min |

---

## 🗺️ Power BI Dashboard

See [dashboards/powerbi_guide.md](dashboards/powerbi_guide.md) for full setup instructions.

Pages:
1. **Overview** — KPIs, city-level demand trend
2. **Demand Heatmap** — Choropleth by zone, hour slicer
3. **Supply Analysis** — Driver utilization, idle time
4. **Surge & Cancellations** — Surge timing, cancel rate waterfall
5. **Forecasts** — Observed vs predicted, model metrics

---

## 🔒 Privacy & Ethics

- All `rider_id` and `driver_id` values are SHA-256 hashed. No PII is included.
- Coordinates are snapped to zone centroids (±500m jitter) to prevent address inference.
- **Known biases**: Underserved zones may show low demand due to low supply (not low latent demand). Model should not be used to further reduce supply in such areas.

---

## 📄 License

MIT License. See [LICENSE](LICENSE).

---

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/my-analysis`)
3. Commit changes (`git commit -m 'Add zone-level surge analysis'`)
4. Push and open a Pull Request

---

*Built with Python 3.10+, pandas, geopandas, h3, plotly, folium, LightGBM, Prophet, SQLAlchemy, Power BI*
