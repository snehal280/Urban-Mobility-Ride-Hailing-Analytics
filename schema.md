# Data Dictionary — Urban Mobility Analytics

## Table: `trips`

| Column | Type | Description |
|--------|------|-------------|
| `trip_id` | VARCHAR(36) | Unique trip identifier (UUID, anonymized) |
| `request_time` | TIMESTAMP(TZ) | UTC timestamp when rider requested the trip |
| `pickup_ts` | TIMESTAMP(TZ) | UTC timestamp when driver arrived at pickup |
| `dropoff_ts` | TIMESTAMP(TZ) | UTC timestamp of trip completion |
| `pickup_lat` | FLOAT | Latitude of pickup location (±500m jittered) |
| `pickup_lon` | FLOAT | Longitude of pickup location (±500m jittered) |
| `dropoff_lat` | FLOAT | Latitude of dropoff location (±500m jittered) |
| `dropoff_lon` | FLOAT | Longitude of dropoff location (±500m jittered) |
| `rider_id` | VARCHAR(64) | SHA-256 hashed rider identifier |
| `driver_id` | VARCHAR(64) | SHA-256 hashed driver identifier |
| `distance_km` | FLOAT | Haversine distance of the trip in km |
| `duration_min` | FLOAT | Trip duration in minutes (dropoff_ts - pickup_ts) |
| `fare_amount` | FLOAT | Total fare charged in local currency |
| `payment_type` | VARCHAR(20) | Payment method: cash / card / wallet |
| `surge_multiplier` | FLOAT | Surge pricing multiplier applied (1.0 = no surge) |
| `status` | VARCHAR(20) | Trip outcome: completed / cancelled / no_driver |
| `city` | VARCHAR(50) | City name |
| `zone_id` | VARCHAR(20) | Administrative zone identifier |
| `h3_pickup` | VARCHAR(20) | H3 hex index (resolution 8) for pickup |
| `h3_dropoff` | VARCHAR(20) | H3 hex index (resolution 8) for dropoff |

---

## Table: `drivers`

| Column | Type | Description |
|--------|------|-------------|
| `driver_id` | VARCHAR(64) | SHA-256 hashed driver identifier |
| `driver_status_ts` | TIMESTAMP(TZ) | UTC timestamp of status change |
| `current_status` | VARCHAR(20) | online / offline / on_trip |
| `city` | VARCHAR(50) | City where driver is operating |
| `zone_id` | VARCHAR(20) | Zone driver is currently in |
| `lat` | FLOAT | Driver latitude (approximate) |
| `lon` | FLOAT | Driver longitude (approximate) |
| `shift_start` | TIME | Typical shift start time |
| `shift_end` | TIME | Typical shift end time |

---

## Table: `zones`

| Column | Type | Description |
|--------|------|-------------|
| `zone_id` | VARCHAR(20) | Unique zone identifier |
| `name` | VARCHAR(100) | Zone display name |
| `city` | VARCHAR(50) | City this zone belongs to |
| `geom` | GEOMETRY | Zone polygon in WGS84 (GeoJSON) |
| `centroid_lat` | FLOAT | Zone centroid latitude |
| `centroid_lon` | FLOAT | Zone centroid longitude |
| `area_km2` | FLOAT | Zone area in square km |

---

## Table: `cancellations`

| Column | Type | Description |
|--------|------|-------------|
| `trip_id` | VARCHAR(36) | Reference to trips.trip_id |
| `cancel_time` | TIMESTAMP(TZ) | UTC timestamp of cancellation |
| `cancelled_by` | VARCHAR(20) | rider / driver |
| `cancel_reason` | VARCHAR(100) | Reason code: wait_too_long / price / wrong_pickup / changed_mind / driver_unavailable / other |
| `wait_time_sec` | INT | Seconds waited before cancellation |
| `eta_at_request` | INT | ETA shown to rider (seconds) |

---

## Table: `surge_events`

| Column | Type | Description |
|--------|------|-------------|
| `surge_id` | SERIAL | Auto-increment ID |
| `city` | VARCHAR(50) | City |
| `zone_id` | VARCHAR(20) | Zone where surge was active |
| `start_time` | TIMESTAMP(TZ) | UTC start of surge event |
| `end_time` | TIMESTAMP(TZ) | UTC end of surge event |
| `multiplier` | FLOAT | Peak surge multiplier during event |

---

## Table: `weather`

| Column | Type | Description |
|--------|------|-------------|
| `city` | VARCHAR(50) | City |
| `time` | TIMESTAMP(TZ) | UTC hourly timestamp |
| `temp_c` | FLOAT | Temperature in Celsius |
| `precip_mm` | FLOAT | Precipitation in mm |
| `wind_kmh` | FLOAT | Wind speed in km/h |
| `weather_desc` | VARCHAR(50) | clear / cloudy / rain / heavy_rain / snow |

---

## Table: `events`

| Column | Type | Description |
|--------|------|-------------|
| `event_id` | SERIAL | Auto-increment ID |
| `city` | VARCHAR(50) | City |
| `zone_id` | VARCHAR(20) | Zone where event is held |
| `start_time` | TIMESTAMP(TZ) | UTC start of event |
| `end_time` | TIMESTAMP(TZ) | UTC end of event |
| `event_type` | VARCHAR(50) | concert / sports / festival / conference / other |
| `attendance_estimate` | INT | Estimated attendees |
| `event_name` | VARCHAR(100) | Event name |

---

## Derived / Feature Columns

| Column | Source | Description |
|--------|--------|-------------|
| `hour` | request_time | Hour of day (0–23) |
| `weekday` | request_time | Day of week (0=Mon … 6=Sun) |
| `is_weekend` | weekday | 1 if Sat/Sun |
| `is_holiday` | date lookup | 1 if public holiday |
| `wait_time_min` | pickup_ts - request_time | Minutes from request to pickup |
| `demand` | COUNT(trip_id) per cell/hour | Trip requests per H3 cell per hour |
| `supply` | COUNT(active drivers) per cell/hour | Active drivers per H3 cell per hour |
| `demand_supply_gap` | demand - supply | Shortage (positive) or surplus (negative) |
