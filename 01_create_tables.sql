-- ============================================================
-- Urban Mobility Analytics - DDL: Create Tables
-- Compatible with: PostgreSQL 14+ / AWS Redshift
-- ============================================================

-- Enable PostGIS extension (PostgreSQL only)
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- ZONES
-- ============================================================
CREATE TABLE IF NOT EXISTS zones (
    zone_id         VARCHAR(20)  PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,
    city            VARCHAR(50)  NOT NULL,
    geom            GEOMETRY(POLYGON, 4326),
    centroid_lat    DOUBLE PRECISION,
    centroid_lon    DOUBLE PRECISION,
    area_km2        DOUBLE PRECISION,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_zones_city    ON zones(city);
CREATE INDEX IF NOT EXISTS idx_zones_geom    ON zones USING GIST(geom);

-- ============================================================
-- TRIPS
-- ============================================================
CREATE TABLE IF NOT EXISTS trips (
    trip_id           VARCHAR(36)  PRIMARY KEY,
    request_time      TIMESTAMPTZ  NOT NULL,
    pickup_ts         TIMESTAMPTZ,
    dropoff_ts        TIMESTAMPTZ,
    pickup_lat        DOUBLE PRECISION,
    pickup_lon        DOUBLE PRECISION,
    dropoff_lat       DOUBLE PRECISION,
    dropoff_lon       DOUBLE PRECISION,
    rider_id          VARCHAR(64)  NOT NULL,
    driver_id         VARCHAR(64),
    distance_km       DOUBLE PRECISION,
    duration_min      DOUBLE PRECISION,
    fare_amount       DOUBLE PRECISION,
    payment_type      VARCHAR(20),
    surge_multiplier  DOUBLE PRECISION DEFAULT 1.0,
    status            VARCHAR(20)  NOT NULL CHECK (status IN ('completed','cancelled','no_driver')),
    city              VARCHAR(50),
    zone_id           VARCHAR(20)  REFERENCES zones(zone_id),
    h3_pickup         VARCHAR(20),
    h3_dropoff        VARCHAR(20),
    -- Derived time features (materialized at load time)
    request_hour      SMALLINT GENERATED ALWAYS AS (EXTRACT(HOUR FROM request_time)) STORED,
    request_weekday   SMALLINT GENERATED ALWAYS AS (EXTRACT(DOW  FROM request_time)) STORED,
    request_date      DATE     GENERATED ALWAYS AS (DATE(request_time)) STORED
)
PARTITION BY RANGE (request_time);

-- Create monthly partitions (example for 12 months)
DO $$
DECLARE
    start_date DATE := '2024-01-01';
    end_date   DATE;
    i          INT;
BEGIN
    FOR i IN 0..11 LOOP
        end_date := start_date + INTERVAL '1 month';
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS trips_%s PARTITION OF trips
             FOR VALUES FROM (%L) TO (%L)',
            TO_CHAR(start_date, 'YYYY_MM'),
            start_date,
            end_date
        );
        start_date := end_date;
    END LOOP;
END;
$$;

CREATE INDEX IF NOT EXISTS idx_trips_request_time ON trips(request_time);
CREATE INDEX IF NOT EXISTS idx_trips_zone_id      ON trips(zone_id);
CREATE INDEX IF NOT EXISTS idx_trips_city         ON trips(city);
CREATE INDEX IF NOT EXISTS idx_trips_status       ON trips(status);
CREATE INDEX IF NOT EXISTS idx_trips_h3_pickup    ON trips(h3_pickup);
CREATE INDEX IF NOT EXISTS idx_trips_driver_id    ON trips(driver_id);

-- ============================================================
-- DRIVERS
-- ============================================================
CREATE TABLE IF NOT EXISTS drivers (
    driver_id         VARCHAR(64)  NOT NULL,
    driver_status_ts  TIMESTAMPTZ  NOT NULL,
    current_status    VARCHAR(20)  NOT NULL CHECK (current_status IN ('online','offline','on_trip')),
    city              VARCHAR(50),
    zone_id           VARCHAR(20)  REFERENCES zones(zone_id),
    lat               DOUBLE PRECISION,
    lon               DOUBLE PRECISION,
    shift_start       TIME,
    shift_end         TIME,
    PRIMARY KEY (driver_id, driver_status_ts)
)
PARTITION BY RANGE (driver_status_ts);

-- Create monthly partitions
DO $$
DECLARE
    start_date DATE := '2024-01-01';
    end_date   DATE;
    i          INT;
BEGIN
    FOR i IN 0..11 LOOP
        end_date := start_date + INTERVAL '1 month';
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS drivers_%s PARTITION OF drivers
             FOR VALUES FROM (%L) TO (%L)',
            TO_CHAR(start_date, 'YYYY_MM'),
            start_date,
            end_date
        );
        start_date := end_date;
    END LOOP;
END;
$$;

CREATE INDEX IF NOT EXISTS idx_drivers_ts      ON drivers(driver_status_ts);
CREATE INDEX IF NOT EXISTS idx_drivers_zone    ON drivers(zone_id);
CREATE INDEX IF NOT EXISTS idx_drivers_status  ON drivers(current_status);

-- ============================================================
-- CANCELLATIONS
-- ============================================================
CREATE TABLE IF NOT EXISTS cancellations (
    trip_id          VARCHAR(36)  PRIMARY KEY REFERENCES trips(trip_id),
    cancel_time      TIMESTAMPTZ  NOT NULL,
    cancelled_by     VARCHAR(20)  NOT NULL CHECK (cancelled_by IN ('rider','driver')),
    cancel_reason    VARCHAR(100),
    wait_time_sec    INT,
    eta_at_request   INT
);

CREATE INDEX IF NOT EXISTS idx_cancel_time     ON cancellations(cancel_time);
CREATE INDEX IF NOT EXISTS idx_cancel_by       ON cancellations(cancelled_by);

-- ============================================================
-- SURGE EVENTS
-- ============================================================
CREATE TABLE IF NOT EXISTS surge_events (
    surge_id     SERIAL        PRIMARY KEY,
    city         VARCHAR(50)   NOT NULL,
    zone_id      VARCHAR(20)   REFERENCES zones(zone_id),
    start_time   TIMESTAMPTZ   NOT NULL,
    end_time     TIMESTAMPTZ   NOT NULL,
    multiplier   DOUBLE PRECISION NOT NULL DEFAULT 1.0
);

CREATE INDEX IF NOT EXISTS idx_surge_time      ON surge_events(start_time, end_time);
CREATE INDEX IF NOT EXISTS idx_surge_zone      ON surge_events(zone_id);

-- ============================================================
-- WEATHER
-- ============================================================
CREATE TABLE IF NOT EXISTS weather (
    city          VARCHAR(50)  NOT NULL,
    time          TIMESTAMPTZ  NOT NULL,
    temp_c        DOUBLE PRECISION,
    precip_mm     DOUBLE PRECISION,
    wind_kmh      DOUBLE PRECISION,
    weather_desc  VARCHAR(50),
    PRIMARY KEY (city, time)
);

CREATE INDEX IF NOT EXISTS idx_weather_time    ON weather(time);

-- ============================================================
-- EVENTS (Local Events)
-- ============================================================
CREATE TABLE IF NOT EXISTS events (
    event_id            SERIAL        PRIMARY KEY,
    city                VARCHAR(50)   NOT NULL,
    zone_id             VARCHAR(20)   REFERENCES zones(zone_id),
    start_time          TIMESTAMPTZ   NOT NULL,
    end_time            TIMESTAMPTZ   NOT NULL,
    event_type          VARCHAR(50),
    attendance_estimate INT,
    event_name          VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS idx_events_time     ON events(start_time);
CREATE INDEX IF NOT EXISTS idx_events_zone     ON events(zone_id);

-- ============================================================
-- MATERIALIZED VIEWS (Pre-aggregated)
-- ============================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_hourly_demand AS
SELECT
    DATE_TRUNC('hour', request_time)  AS hour,
    city,
    zone_id,
    h3_pickup                         AS h3_index,
    COUNT(*)                          AS requests,
    COUNT(*) FILTER (WHERE status = 'completed')  AS completed,
    COUNT(*) FILTER (WHERE status = 'cancelled')  AS cancelled,
    COUNT(*) FILTER (WHERE status = 'no_driver')  AS no_driver,
    AVG(surge_multiplier)             AS avg_surge,
    AVG(fare_amount) FILTER (WHERE status = 'completed') AS avg_fare,
    AVG(duration_min) FILTER (WHERE status = 'completed') AS avg_duration,
    AVG(distance_km) FILTER (WHERE status = 'completed')  AS avg_distance
FROM trips
GROUP BY 1, 2, 3, 4
WITH DATA;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_hourly_demand
    ON mv_hourly_demand(hour, city, zone_id);

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_hourly_supply AS
SELECT
    DATE_TRUNC('hour', driver_status_ts) AS hour,
    city,
    zone_id,
    COUNT(DISTINCT driver_id) FILTER (WHERE current_status IN ('online','on_trip')) AS active_drivers,
    COUNT(DISTINCT driver_id) FILTER (WHERE current_status = 'online') AS available_drivers
FROM drivers
GROUP BY 1, 2, 3
WITH DATA;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_hourly_supply
    ON mv_hourly_supply(hour, city, zone_id);
