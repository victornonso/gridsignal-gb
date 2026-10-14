CREATE VIEW mart.v_carbon_forecast_errors AS
SELECT *, forecast-actual AS error, abs(forecast-actual) AS absolute_error,
 extract(hour FROM period_start AT TIME ZONE 'Europe/London')::int AS local_hour,
 extract(isodow FROM period_start AT TIME ZONE 'Europe/London')::int AS weekday
FROM core.carbon_observation WHERE region_id=0 AND actual IS NOT NULL AND forecast IS NOT NULL;
CREATE VIEW mart.v_daily_carbon_performance AS
WITH daily AS (
 SELECT region_id,(period_start AT TIME ZONE 'Europe/London')::date AS day,
 avg(CASE WHEN region_id=0 THEN actual ELSE forecast END) AS mean_intensity,
 min(CASE WHEN region_id=0 THEN actual ELSE forecast END) AS minimum,
 max(CASE WHEN region_id=0 THEN actual ELSE forecast END) AS maximum,
 stddev_samp(CASE WHEN region_id=0 THEN actual ELSE forecast END) AS volatility,
 count(CASE WHEN region_id=0 THEN actual ELSE forecast END) AS intervals
 FROM core.carbon_observation GROUP BY 1,2
)
SELECT *,avg(mean_intensity) OVER(PARTITION BY region_id ORDER BY day RANGE BETWEEN interval '6 days' PRECEDING AND CURRENT ROW) AS rolling_7d,
 avg(mean_intensity) OVER(PARTITION BY region_id ORDER BY day RANGE BETWEEN interval '29 days' PRECEDING AND CURRENT ROW) AS rolling_30d,
 mean_intensity-lag(mean_intensity) OVER(PARTITION BY region_id ORDER BY day) AS day_change
FROM daily;
CREATE VIEW mart.v_hourly_carbon_profile AS
SELECT region_id,extract(hour FROM period_start AT TIME ZONE 'Europe/London')::int AS hour,
 extract(isodow FROM period_start AT TIME ZONE 'Europe/London')>5 AS weekend,
 avg(CASE WHEN region_id=0 THEN actual ELSE forecast END) AS intensity,count(*) AS observations
FROM core.carbon_observation GROUP BY 1,2,3;
CREATE VIEW mart.v_regional_carbon_comparison AS
SELECT r.id,r.name,avg(c.forecast) AS mean_intensity,stddev_samp(c.forecast) AS volatility,
 dense_rank() OVER(ORDER BY avg(c.forecast)) AS rank,
 ntile(4) OVER(ORDER BY avg(c.forecast)) AS quartile,
 percentile_cont(0.95) WITHIN GROUP(ORDER BY c.forecast) AS p95
FROM core.region r JOIN core.carbon_observation c ON c.region_id=r.id WHERE r.scope='region' GROUP BY r.id;
CREATE VIEW mart.v_generation_mix AS
SELECT g.*,f.label,f.renewable,f.low_carbon,f.fossil,f.colour FROM core.generation_share g JOIN core.fuel_type f ON f.id=g.fuel_id;
CREATE VIEW mart.v_demand_profile AS
SELECT d.*,c.local_hour,c.weekday,c.weekend FROM core.demand_observation d
JOIN core.reporting_calendar c USING(period_start) WHERE d.observation_kind='A';
CREATE VIEW mart.v_data_completeness AS
SELECT c.settlement_date AS day,r.id AS region_id,count(*) AS expected,
 count(o.period_start) AS received,
 count(CASE WHEN r.id=0 THEN o.actual ELSE o.forecast END) AS usable,
 round(100.0*count(CASE WHEN r.id=0 THEN o.actual ELSE o.forecast END)/nullif(count(*),0),2) AS completeness
FROM core.reporting_calendar c CROSS JOIN core.region r
LEFT JOIN core.carbon_observation o ON o.period_start=c.period_start AND o.region_id=r.id
WHERE c.period_end<=now() GROUP BY 1,2;
CREATE VIEW mart.v_source_freshness AS
WITH latest AS (
 SELECT 'carbon' AS source_id,max(period_start) AS observed_at FROM core.carbon_observation WHERE region_id=0
 UNION ALL SELECT 'regional',max(period_start) FROM core.carbon_observation WHERE region_id BETWEEN 1 AND 14
 UNION ALL SELECT 'mix',max(period_start) FROM core.generation_share WHERE region_id=0
 UNION ALL SELECT 'elexon',max(period_start) FROM core.generation_outturn
 UNION ALL SELECT 'demand',max(period_start) FROM core.demand_observation WHERE observation_kind='A'
 UNION ALL SELECT 'factors',max(updated_at) FROM core.carbon_factor
)
SELECT s.*,l.observed_at,r.finished_at AS last_success_at,
 extract(epoch FROM now()-l.observed_at)/60 AS age_minutes,
 l.observed_at IS NULL OR l.observed_at<now()-s.stale_minutes*interval '1 minute' AS stale
FROM ops.data_source s LEFT JOIN latest l ON s.id=l.source_id
LEFT JOIN LATERAL(SELECT finished_at FROM ops.ingestion_run WHERE source_id=s.id AND status='success' ORDER BY finished_at DESC LIMIT 1) r ON true;
CREATE MATERIALIZED VIEW mart.mv_daily_national_performance AS SELECT * FROM mart.v_daily_carbon_performance WHERE region_id=0;
CREATE UNIQUE INDEX daily_national_key ON mart.mv_daily_national_performance(day);
CREATE MATERIALIZED VIEW mart.mv_regional_period_summary AS SELECT * FROM mart.v_regional_carbon_comparison;
CREATE UNIQUE INDEX regional_summary_key ON mart.mv_regional_period_summary(id);
CREATE MATERIALIZED VIEW mart.mv_generation_daily_mix AS
SELECT region_id,(period_start AT TIME ZONE 'Europe/London')::date AS day,fuel_id,source_id,avg(share) AS mean_share,count(*) AS intervals
FROM core.generation_share GROUP BY 1,2,3,4;
CREATE UNIQUE INDEX generation_daily_key ON mart.mv_generation_daily_mix(region_id,day,fuel_id,source_id);
CREATE MATERIALIZED VIEW mart.mv_forecast_error_distribution AS
SELECT floor(error/10)*10 AS bucket,count(*) AS observations FROM mart.v_carbon_forecast_errors GROUP BY 1;
CREATE UNIQUE INDEX forecast_distribution_key ON mart.mv_forecast_error_distribution(bucket);
GRANT SELECT ON ALL TABLES IN SCHEMA mart TO gridsignal_reader,gridsignal_writer;
-- A controlled SECURITY DEFINER routine lets the writer refresh only explicitly named marts.
CREATE FUNCTION mart.refresh_affected(source text) RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,mart AS $$
BEGIN
 IF source='carbon' THEN
  REFRESH MATERIALIZED VIEW mart.mv_daily_national_performance;
  REFRESH MATERIALIZED VIEW mart.mv_forecast_error_distribution;
 ELSIF source='regional' THEN
  REFRESH MATERIALIZED VIEW mart.mv_regional_period_summary;
 END IF;
 IF source IN ('mix','regional') THEN REFRESH MATERIALIZED VIEW mart.mv_generation_daily_mix; END IF;
END $$;
REVOKE ALL ON FUNCTION mart.refresh_affected(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION mart.refresh_affected(text) TO gridsignal_writer;

