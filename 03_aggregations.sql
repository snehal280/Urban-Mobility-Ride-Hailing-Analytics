-- ============================================================
-- Urban Mobility Analytics - Aggregation Queries
-- ============================================================

-- 1. Hourly demand by zone (base query)
CREATE OR REPLACE VIEW vw_hourly_demand_zone AS
SELECT
    DATE_TRUNC('hour', request_time)    AS hour,
    city,
    zone_id,
    COUNT(*)                            AS requests,
    COUNT(*) FILTER (WHERE status = 'completed')  AS completed_trips,
    COUNT(*) FILTER (WHERE status = 'cancelled')  AS cancellations,
    AVG(surge_multiplier)               AS avg_surge,
    AVG(fare_amount) FILTER (WHERE status='completed') AS avg_fare
FROM trips
GROUP BY 1, 2, 3;

-- 2. Peak hours by weekday
CREATE OR REPLACE VIEW vw_peak_hours_weekday AS
SELECT
    EXTRACT(DOW FROM hour)  AS weekday,  -- 0=Sun...6=Sat
    EXTRACT(HOUR FROM hour) AS hour_of_day,
    city,
    SUM(requests)           AS total_requests,
    RANK() OVER (
        PARTITION BY EXTRACT(DOW FROM hour), city
        ORDER BY SUM(requests) DESC
    ) AS demand_rank
FROM vw_hourly_demand_zone
GROUP BY 1, 2, 3
ORDER BY weekday, total_requests DESC;

-- 3. Demand vs Supply gap per zone/hour
CREATE OR REPLACE VIEW vw_demand_supply_gap AS
SELECT
    d.hour,
    d.city,
    d.zone_id,
    d.requests                              AS demand,
    COALESCE(s.available_drivers, 0)        AS supply,
    d.requests - COALESCE(s.available_drivers, 0) AS gap,
    CASE
        WHEN COALESCE(s.available_drivers, 0) = 0 THEN NULL
        ELSE d.requests::FLOAT / s.available_drivers
    END                                     AS demand_supply_ratio
FROM mv_hourly_demand  d
LEFT JOIN mv_hourly_supply s
    ON d.hour = s.hour AND d.city = s.city AND d.zone_id = s.zone_id;

-- 4. Driver utilization aggregates
CREATE OR REPLACE VIEW vw_driver_utilization AS
WITH driver_trips AS (
    SELECT
        t.driver_id,
        t.city,
        COUNT(*)            AS trips_completed,
        SUM(t.duration_min) AS total_drive_minutes,
        SUM(t.fare_amount)  AS total_earnings,
        MIN(t.pickup_ts)    AS first_trip,
        MAX(t.dropoff_ts)   AS last_trip
    FROM trips t
    WHERE t.status = 'completed'
      AND t.driver_id IS NOT NULL
    GROUP BY t.driver_id, t.city
)
SELECT
    driver_id,
    city,
    trips_completed,
    total_drive_minutes,
    total_earnings,
    ROUND(total_earnings::NUMERIC / NULLIF(trips_completed,0), 2) AS avg_fare_per_trip,
    EXTRACT(EPOCH FROM (last_trip - first_trip)) / 60.0           AS total_shift_minutes,
    ROUND(total_drive_minutes / NULLIF(
        EXTRACT(EPOCH FROM (last_trip - first_trip)) / 60.0, 0
    ) * 100, 1) AS utilization_pct
FROM driver_trips;

-- 5. Cancellation rate by zone and hour
CREATE OR REPLACE VIEW vw_cancellation_rate AS
SELECT
    zone_id,
    city,
    EXTRACT(HOUR FROM request_time)  AS hour_of_day,
    EXTRACT(DOW  FROM request_time)  AS weekday,
    COUNT(*)                         AS total_requests,
    SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) AS total_cancellations,
    ROUND(
        SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END)::NUMERIC / COUNT(*) * 100,
        2
    ) AS cancel_rate_pct,
    AVG(CASE WHEN c.cancelled_by = 'rider'  THEN 1.0 ELSE 0 END) AS rider_cancel_share,
    AVG(CASE WHEN c.cancelled_by = 'driver' THEN 1.0 ELSE 0 END) AS driver_cancel_share
FROM trips t
LEFT JOIN cancellations c USING (trip_id)
GROUP BY 1, 2, 3, 4
ORDER BY cancel_rate_pct DESC;

-- 6. Surge event summary
CREATE OR REPLACE VIEW vw_surge_summary AS
SELECT
    se.city,
    se.zone_id,
    DATE_TRUNC('hour', se.start_time) AS surge_hour,
    MAX(se.multiplier)                AS peak_multiplier,
    SUM(EXTRACT(EPOCH FROM (se.end_time - se.start_time)) / 60) AS total_surge_minutes,
    COUNT(DISTINCT se.surge_id)       AS surge_events_count
FROM surge_events se
GROUP BY 1, 2, 3
ORDER BY peak_multiplier DESC;

-- 7. Fare analysis by zone and hour
CREATE OR REPLACE VIEW vw_fare_analysis AS
SELECT
    zone_id,
    city,
    EXTRACT(HOUR FROM request_time)   AS hour_of_day,
    ROUND(AVG(fare_amount)::NUMERIC, 2)    AS avg_fare,
    ROUND(MEDIAN(fare_amount)::NUMERIC, 2) AS median_fare,
    ROUND(STDDEV(fare_amount)::NUMERIC, 2) AS stddev_fare,
    MIN(fare_amount)                       AS min_fare,
    MAX(fare_amount)                       AS max_fare,
    ROUND(AVG(distance_km)::NUMERIC, 2)    AS avg_distance_km,
    ROUND(AVG(fare_amount / NULLIF(distance_km, 0))::NUMERIC, 2) AS avg_fare_per_km,
    AVG(surge_multiplier)                  AS avg_surge_multiplier
FROM trips
WHERE status = 'completed'
  AND fare_amount > 0
  AND distance_km > 0
GROUP BY 1, 2, 3
ORDER BY avg_fare DESC;

-- 8. Weather impact on demand
CREATE OR REPLACE VIEW vw_weather_demand AS
SELECT
    w.city,
    DATE_TRUNC('hour', w.time)  AS hour,
    w.temp_c,
    w.precip_mm,
    w.wind_kmh,
    w.weather_desc,
    COALESCE(d.requests, 0)     AS demand,
    COALESCE(d.avg_surge, 1.0)  AS avg_surge
FROM weather w
LEFT JOIN mv_hourly_demand d
    ON w.city = d.city AND DATE_TRUNC('hour', w.time) = d.hour
ORDER BY w.time;

-- 9. Top K demand zones (rolling 30 days)
CREATE OR REPLACE VIEW vw_top_demand_zones AS
SELECT
    zone_id,
    city,
    z.name                          AS zone_name,
    SUM(d.requests)                 AS total_requests,
    RANK() OVER (PARTITION BY d.city ORDER BY SUM(d.requests) DESC) AS demand_rank,
    AVG(d.avg_fare)                 AS avg_fare,
    AVG(d.avg_surge)                AS avg_surge
FROM mv_hourly_demand d
JOIN zones z USING (zone_id)
WHERE d.hour >= NOW() - INTERVAL '30 days'
GROUP BY d.zone_id, d.city, z.name
ORDER BY total_requests DESC;
