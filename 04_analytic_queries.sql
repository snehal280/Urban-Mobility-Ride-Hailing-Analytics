-- ============================================================
-- Urban Mobility Analytics - Example Analytic Queries
-- ============================================================

-- Q1: Hourly demand by zone (basic)
SELECT
    DATE_TRUNC('hour', request_time) AS hour,
    zone_id,
    COUNT(*)                         AS requests
FROM trips
GROUP BY 1, 2
ORDER BY 1, requests DESC;

-- Q2: Peak hours by weekday
SELECT weekday, hour_of_day, city, SUM(total_requests) AS total_requests
FROM vw_peak_hours_weekday
GROUP BY weekday, hour_of_day, city
ORDER BY weekday, total_requests DESC;

-- Q3: Top 5 pickup zones in the last 7 days
SELECT
    zone_id,
    z.name AS zone_name,
    city,
    COUNT(*) AS pickups
FROM trips t
JOIN zones z USING (zone_id)
WHERE request_time >= NOW() - INTERVAL '7 days'
  AND status = 'completed'
GROUP BY zone_id, z.name, city
ORDER BY pickups DESC
LIMIT 5;

-- Q4: Cancellation rate by zone and hour
SELECT
    zone_id,
    hour_of_day,
    total_requests,
    total_cancellations,
    cancel_rate_pct
FROM vw_cancellation_rate
ORDER BY cancel_rate_pct DESC
LIMIT 20;

-- Q5: Driver utilization summary
SELECT
    city,
    COUNT(DISTINCT driver_id)       AS total_drivers,
    AVG(trips_completed)            AS avg_trips_per_driver,
    AVG(utilization_pct)            AS avg_utilization_pct,
    AVG(total_earnings)             AS avg_earnings
FROM vw_driver_utilization
GROUP BY city
ORDER BY avg_utilization_pct DESC;

-- Q6: Demand-Supply gap — top 10 worst shortage moments
SELECT
    hour,
    city,
    zone_id,
    demand,
    supply,
    gap,
    demand_supply_ratio
FROM vw_demand_supply_gap
WHERE supply > 0
ORDER BY demand_supply_ratio DESC
LIMIT 10;

-- Q7: Revenue by payment type
SELECT
    payment_type,
    city,
    COUNT(*)                        AS trips,
    ROUND(SUM(fare_amount)::NUMERIC, 2) AS total_revenue,
    ROUND(AVG(fare_amount)::NUMERIC, 2) AS avg_fare
FROM trips
WHERE status = 'completed'
GROUP BY payment_type, city
ORDER BY total_revenue DESC;

-- Q8: Surge event impact on cancellations
SELECT
    se.zone_id,
    se.city,
    se.multiplier          AS surge_multiplier,
    COUNT(t.trip_id)       AS trips_during_surge,
    SUM(CASE WHEN t.status = 'cancelled' THEN 1 ELSE 0 END) AS cancellations,
    ROUND(
        SUM(CASE WHEN t.status = 'cancelled' THEN 1 ELSE 0 END)::NUMERIC
        / NULLIF(COUNT(t.trip_id),0) * 100, 2
    ) AS cancel_rate_pct
FROM surge_events se
JOIN trips t
    ON t.zone_id = se.zone_id
    AND t.request_time BETWEEN se.start_time AND se.end_time
GROUP BY se.zone_id, se.city, se.multiplier
ORDER BY surge_multiplier DESC, cancel_rate_pct DESC;

-- Q9: Weather-driven demand anomalies
SELECT
    w.city,
    w.hour,
    w.precip_mm,
    w.weather_desc,
    w.demand,
    -- Z-score of demand for this city/hour-of-day across all weeks
    (w.demand - AVG(w.demand) OVER (PARTITION BY w.city, EXTRACT(HOUR FROM w.hour)))
        / NULLIF(STDDEV(w.demand) OVER (PARTITION BY w.city, EXTRACT(HOUR FROM w.hour)), 0)
        AS demand_zscore
FROM vw_weather_demand w
ORDER BY demand_zscore DESC
LIMIT 20;

-- Q10: OD (Origin-Destination) flow matrix
SELECT
    pickup_zone.name  AS origin_zone,
    dropoff_zone.name AS destination_zone,
    COUNT(*)          AS trips,
    ROUND(AVG(t.distance_km)::NUMERIC, 2) AS avg_km,
    ROUND(AVG(t.fare_amount)::NUMERIC, 2) AS avg_fare
FROM trips t
JOIN zones pickup_zone  ON t.zone_id = pickup_zone.zone_id
JOIN zones dropoff_zone ON h3_dropoff_to_zone_id(t.h3_dropoff) = dropoff_zone.zone_id
WHERE t.status = 'completed'
GROUP BY 1, 2
HAVING COUNT(*) > 100
ORDER BY trips DESC
LIMIT 20;

-- Q11: Holiday demand comparison
SELECT
    request_date,
    city,
    COUNT(*)    AS total_requests,
    AVG(surge_multiplier) AS avg_surge,
    -- Add holiday flag join here from a holiday lookup table
    CASE WHEN request_date IN (
        '2024-01-01', '2024-01-26', '2024-08-15', '2024-10-02',
        '2024-12-25', '2024-10-24'
    ) THEN 'holiday' ELSE 'regular' END AS day_type
FROM trips
GROUP BY request_date, city
ORDER BY request_date;

-- Q12: Trip outlier detection (duration or fare)
SELECT
    trip_id,
    duration_min,
    distance_km,
    fare_amount,
    surge_multiplier,
    (fare_amount - AVG(fare_amount) OVER ()) / NULLIF(STDDEV(fare_amount) OVER (), 0) AS fare_zscore,
    (duration_min - AVG(duration_min) OVER ()) / NULLIF(STDDEV(duration_min) OVER (), 0) AS dur_zscore
FROM trips
WHERE status = 'completed'
HAVING ABS(fare_zscore) > 3 OR ABS(dur_zscore) > 3;
