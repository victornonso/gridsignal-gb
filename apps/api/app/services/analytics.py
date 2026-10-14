from datetime import datetime, timezone

from sqlalchemy import text

from apps.api.app.db.session import read_engine
from apps.api.app.services.source_status import source_statuses

CARBON = """WITH base AS (
 SELECT c.*,CASE WHEN region_id=0 THEN actual ELSE forecast END AS value,
 extract(hour FROM period_start AT TIME ZONE 'Europe/London')::int AS hour,
 extract(isodow FROM period_start AT TIME ZONE 'Europe/London')::int AS weekday,
 (period_start AT TIME ZONE 'Europe/London')::date AS day
 FROM core.carbon_observation c WHERE region_id=:region AND period_start>=:start AND period_start<:end
) """
FORECAST = """WITH base AS (
 SELECT * FROM mart.v_carbon_forecast_errors WHERE period_start>=:start AND period_start<:end
) """

QUERIES = {
    "carbon/latest": "SELECT period_start,period_end,actual,forecast,intensity_index,source_id FROM core.carbon_observation WHERE region_id=:region AND period_start<:end ORDER BY period_start DESC LIMIT 1",
    "carbon/distribution": CARBON
    + "SELECT floor(value/20)*20 AS bucket,count(*) AS observations FROM base WHERE value IS NOT NULL GROUP BY 1 ORDER BY 1",
    "carbon/profile": CARBON
    + "SELECT hour,weekday>5 AS weekend,avg(value) AS value,stddev_samp(value) AS volatility,count(value) AS observations FROM base GROUP BY 1,2 ORDER BY 1,2",
    "carbon/heatmap": CARBON + "SELECT day,hour,avg(value) AS value FROM base GROUP BY 1,2 ORDER BY 1,2",
    "carbon/comparison": """WITH periods AS (
 SELECT CASE WHEN period_start>=:start THEN 'current' ELSE 'previous' END AS period,
 CASE WHEN region_id=0 THEN actual ELSE forecast END AS value,period_start
 FROM core.carbon_observation WHERE region_id=:region AND period_start>=:start-(CAST(:end AS timestamptz)-CAST(:start AS timestamptz)) AND period_start<:end
) SELECT period,avg(value) AS mean,min(value) AS minimum,max(value) AS maximum,stddev_samp(value) AS volatility,
 percentile_cont(0.5) WITHIN GROUP(ORDER BY value) AS p50,percentile_cont(0.95) WITHIN GROUP(ORDER BY value) AS p95,count(value) AS observations,
 CASE WHEN count(value)>0 THEN (array_agg(period_start ORDER BY value DESC NULLS LAST))[1] END AS peak_interval
 FROM periods GROUP BY period""",
    "generation/mix": """SELECT fuel_id,label,colour,renewable,low_carbon,fossil,avg(share) AS share,count(*) AS observations
 FROM mart.v_generation_mix WHERE region_id=:region AND period_start>=:start AND period_start<:end AND (CAST(:fuel AS text) IS NULL OR fuel_id=:fuel)
 GROUP BY fuel_id,label,colour,renewable,low_carbon,fossil ORDER BY share DESC""",
    "generation/summary": """WITH intervals AS (
 SELECT period_start,sum(share) FILTER(WHERE low_carbon) AS low_carbon,sum(share) FILTER(WHERE renewable) AS renewable,
 sum(share) FILTER(WHERE fossil) AS fossil FROM mart.v_generation_mix WHERE region_id=:region AND period_start>=:start AND period_start<:end
 GROUP BY period_start) SELECT avg(low_carbon) AS low_carbon,avg(renewable) AS renewable,avg(fossil) AS fossil FROM intervals""",
    "generation/volatility": """SELECT fuel_id,avg(share) FILTER(WHERE period_start>=:start) AS mean_share,stddev_samp(share) FILTER(WHERE period_start>=:start) AS volatility,min(share) FILTER(WHERE period_start>=:start) AS minimum,max(share) FILTER(WHERE period_start>=:start) AS maximum,
    avg(share) FILTER(WHERE period_start>=:start)-avg(share) FILTER(WHERE period_start<:start) AS change_pp
    FROM core.generation_share WHERE region_id=:region AND period_start>=:start-(CAST(:end AS timestamptz)-CAST(:start AS timestamptz)) AND period_start<:end
    AND (CAST(:fuel AS text) IS NULL OR fuel_id=:fuel) GROUP BY fuel_id ORDER BY volatility DESC NULLS LAST""",
    "generation/profile": """WITH fuel_intervals AS (
    SELECT period_start,fuel_id,sum(power_mw) AS power_mw FROM core.generation_outturn WHERE period_start>=:start AND period_start<:end
    AND (CAST(:fuel AS text) IS NULL OR fuel_id=:fuel) GROUP BY 1,2)
    SELECT extract(hour FROM period_start AT TIME ZONE 'Europe/London')::int AS hour,fuel_id,avg(power_mw) AS power_mw
    FROM fuel_intervals GROUP BY 1,2 ORDER BY 1,2""",
    "demand/summary": """SELECT avg(national_mw) AS mean,min(national_mw) AS minimum,max(national_mw) AS peak,
 stddev_samp(national_mw) AS volatility,avg(transmission_mw) AS transmission_mean,
 percentile_cont(0.95) WITHIN GROUP(ORDER BY national_mw) AS p95,count(*) AS observations
 FROM core.demand_observation WHERE observation_kind='A' AND period_start>=:start AND period_start<:end""",
    "demand/hourly": "SELECT local_hour AS hour,weekend,avg(national_mw) AS national_mw,avg(transmission_mw) AS transmission_mw FROM mart.v_demand_profile WHERE period_start>=:start AND period_start<:end GROUP BY 1,2 ORDER BY 1,2",
    "demand/comparison": """SELECT CASE WHEN period_start>=:start THEN 'current' ELSE 'previous' END AS period,
 avg(national_mw) AS mean,max(national_mw) AS peak,stddev_samp(national_mw) AS volatility
 FROM core.demand_observation WHERE observation_kind='A' AND period_start>=:start-(CAST(:end AS timestamptz)-CAST(:start AS timestamptz)) AND period_start<:end GROUP BY 1""",
    "demand/distribution": "SELECT floor(national_mw/1000)*1000 AS bucket,count(*) AS observations FROM core.demand_observation WHERE observation_kind='A' AND period_start>=:start AND period_start<:end AND national_mw IS NOT NULL GROUP BY 1 ORDER BY 1",
    "regions": "SELECT * FROM core.region ORDER BY id",
    "regions/ranking": """WITH summary AS (
 SELECT r.id,r.name,avg(c.forecast) AS value,stddev_samp(c.forecast) AS volatility,
 percentile_cont(0.95) WITHIN GROUP(ORDER BY c.forecast) AS p95,count(c.forecast) AS observations
 FROM core.region r JOIN core.carbon_observation c ON c.region_id=r.id
 WHERE r.scope='region' AND c.period_start>=:start AND c.period_start<:end GROUP BY r.id
), national AS (SELECT avg(actual) AS value FROM core.carbon_observation WHERE region_id=0 AND period_start>=:start AND period_start<:end)
 SELECT s.*,dense_rank() OVER(ORDER BY s.value) AS rank,ntile(4) OVER(ORDER BY s.value) AS quartile,
 s.value-n.value AS national_difference FROM summary s CROSS JOIN national n ORDER BY s.value""",
    "forecasts/errors": FORECAST
    + """SELECT avg(absolute_error) AS mae,sqrt(avg(power(error,2))) AS rmse,avg(error) AS bias,
 percentile_cont(0.5) WITHIN GROUP(ORDER BY absolute_error) AS median_absolute_error,
 percentile_cont(0.95) WITHIN GROUP(ORDER BY absolute_error) AS p95,count(*) AS paired_observations FROM base""",
    "forecasts/distribution": FORECAST
    + "SELECT floor(error/10)*10 AS bucket,count(*) AS observations FROM base GROUP BY 1 ORDER BY 1",
    "forecasts/hourly": FORECAST
    + "SELECT local_hour AS hour,avg(absolute_error) AS mae,avg(error) AS bias FROM base GROUP BY 1 ORDER BY 1",
    "forecasts/weekday": FORECAST
    + "SELECT weekday,avg(absolute_error) AS mae,avg(error) AS bias FROM base GROUP BY 1 ORDER BY 1",
    "forecasts/revisions": "SELECT region_id,period_start,changed_at,old_value->>'forecast' AS previous_forecast,new_value->>'forecast' AS revised_forecast,old_value->>'actual' AS previous_actual,new_value->>'actual' AS revised_actual FROM core.carbon_revision WHERE period_start>=:start AND period_start<:end ORDER BY changed_at DESC LIMIT :limit OFFSET :offset",
    "operations/sources": "SELECT * FROM mart.v_source_freshness ORDER BY id",
    "operations/ingestion-runs": "SELECT *,extract(epoch FROM finished_at-started_at) AS duration_seconds FROM ops.ingestion_run WHERE started_at>=:start AND started_at<:end ORDER BY started_at DESC LIMIT :limit OFFSET :offset",
    "operations/quality": "SELECT * FROM ops.quality_result WHERE executed_at>=:start AND executed_at<:end ORDER BY executed_at DESC LIMIT :limit OFFSET :offset",
    "operations/health": """SELECT count(*) AS runs,count(*) FILTER(WHERE status='failed') AS failed,
 sum(received) AS received,sum(inserted) AS inserted,sum(updated) AS updated,sum(rejected) AS rejected,sum(duplicates) AS duplicates,
 avg(extract(epoch FROM finished_at-started_at)) AS mean_duration_seconds,
 100.0*count(*) FILTER(WHERE status='failed')/nullif(count(*),0) AS failure_rate
 FROM ops.ingestion_run WHERE started_at>=:start AND started_at<:end""",
    "operations/completeness": """SELECT cal.settlement_date AS day,:region AS region_id,count(*) AS expected,
    count(c.period_start) AS received,count(CASE WHEN :region=0 THEN c.actual ELSE c.forecast END) AS usable,
    round(100.0*count(CASE WHEN :region=0 THEN c.actual ELSE c.forecast END)/nullif(count(*),0),2) AS completeness
    FROM core.reporting_calendar cal LEFT JOIN core.carbon_observation c ON c.period_start=cal.period_start AND c.region_id=:region
    WHERE cal.period_start>=:start AND cal.period_end<=least(CAST(:end AS timestamptz),now())
    GROUP BY cal.settlement_date ORDER BY day""",
    "metadata/fuels": "SELECT * FROM core.fuel_type ORDER BY label",
    "metadata/regions": "SELECT * FROM core.region ORDER BY id",
    "metadata/factors": "SELECT label,gco2_per_kwh,updated_at FROM core.carbon_factor ORDER BY label",
}


def bucket(granularity):
    return {
        "half-hour": "period_start",
        "hour": "date_trunc('hour',period_start)",
        "day": "date_trunc('day',period_start AT TIME ZONE 'Europe/London') AT TIME ZONE 'Europe/London'",
    }[granularity]


def dynamic_query(route, filters):
    time = bucket(filters.granularity)
    order = filters.sort.upper()  # Literal validated; SQL identifiers never come from free-form input.
    if route == "carbon/trend":
        preceding = (
            "6 days"
            if filters.granularity == "day"
            else ("167 hours" if filters.granularity == "hour" else "167 hours 30 minutes")
        )
        monthly = (
            "29 days"
            if filters.granularity == "day"
            else ("719 hours" if filters.granularity == "hour" else "719 hours 30 minutes")
        )
        window_order = "time AT TIME ZONE 'Europe/London'" if filters.granularity == "day" else "time"
        return (
            """WITH base AS (
            SELECT cal.period_start,c.actual,c.forecast,
            CASE WHEN :region=0 THEN c.actual ELSE c.forecast END AS value
            FROM core.reporting_calendar cal LEFT JOIN core.carbon_observation c
            ON c.period_start=cal.period_start AND c.region_id=:region
            WHERE cal.period_start>=:start AND cal.period_start<:end AND cal.period_end<=now()
            ) """
            + f""", grouped AS(SELECT {time} AS time,avg(value) AS value,avg(forecast) AS forecast,avg(actual) AS actual,
        min(value) AS minimum,max(value) AS maximum,stddev_samp(value) AS volatility,count(value) AS observations FROM base GROUP BY 1)
        SELECT *,sum(value*observations) OVER(ORDER BY {window_order} RANGE BETWEEN interval '{preceding}' PRECEDING AND CURRENT ROW)/nullif(sum(observations) OVER(ORDER BY {window_order} RANGE BETWEEN interval '{preceding}' PRECEDING AND CURRENT ROW),0) AS rolling_7d,
        sum(value*observations) OVER(ORDER BY {window_order} RANGE BETWEEN interval '{monthly}' PRECEDING AND CURRENT ROW)/nullif(sum(observations) OVER(ORDER BY {window_order} RANGE BETWEEN interval '{monthly}' PRECEDING AND CURRENT ROW),0) AS rolling_30d,
        value-lag(value) OVER(ORDER BY time) AS change,lead(value) OVER(ORDER BY time) AS next_value FROM grouped ORDER BY time {order} LIMIT :limit OFFSET :offset"""
        )
    if route == "generation/trend":
        return f"SELECT {time} AS time,fuel_id,avg(share) AS share FROM core.generation_share WHERE region_id=:region AND period_start>=:start AND period_start<:end AND (CAST(:fuel AS text) IS NULL OR fuel_id=:fuel) GROUP BY 1,2 ORDER BY 1 {order},2 LIMIT :limit OFFSET :offset"
    if route == "generation/outturn":
        return f"""WITH fuel_intervals AS (
        SELECT period_start,period_end,fuel_id,sum(power_mw) AS power_mw
        FROM core.generation_outturn WHERE period_start>=:start AND period_start<:end
        AND (CAST(:fuel AS text) IS NULL OR fuel_id=:fuel) GROUP BY 1,2,3)
        SELECT {time} AS time,fuel_id,
        sum(power_mw*extract(epoch FROM period_end-period_start)/3600) AS energy_mwh,
        sum(power_mw*extract(epoch FROM period_end-period_start))/nullif(sum(extract(epoch FROM period_end-period_start)),0) AS power_mw
        FROM fuel_intervals GROUP BY 1,2 ORDER BY 1 {order},2 LIMIT :limit OFFSET :offset"""
    if route == "demand/profile":
        return f"SELECT {time} AS time,avg(national_mw) AS national_mw,avg(transmission_mw) AS transmission_mw,max(national_mw) AS peak,count(*) AS observations FROM core.demand_observation WHERE observation_kind='A' AND period_start>=:start AND period_start<:end GROUP BY 1 ORDER BY 1 {order} LIMIT :limit OFFSET :offset"
    if route == "forecasts/comparison":
        return (
            FORECAST
            + f"SELECT {time} AS time,avg(actual) AS actual,avg(forecast) AS forecast,avg(error) AS error,avg(absolute_error) AS mae FROM base GROUP BY 1 ORDER BY 1 {order} LIMIT :limit OFFSET :offset"
        )
    if route == "regions/trend":
        return f"SELECT {time} AS time,region_id,avg(forecast) AS value FROM core.carbon_observation WHERE region_id=ANY(:regions) AND period_start>=:start AND period_start<:end GROUP BY 1,2 ORDER BY 1 {order},2 LIMIT :limit OFFSET :offset"
    if route == "regions/benchmark":
        return f"""WITH aligned AS (
        SELECT c.period_start,c.forecast AS regional,n.actual AS national
        FROM core.carbon_observation c LEFT JOIN core.carbon_observation n ON n.region_id=0 AND n.period_start=c.period_start
        WHERE c.region_id=:region AND c.region_id BETWEEN 1 AND 14 AND c.period_start>=:start AND c.period_start<:end)
        SELECT {time} AS time,avg(regional) AS regional,avg(national) AS national FROM aligned GROUP BY 1 ORDER BY 1 {order} LIMIT :limit OFFSET :offset"""
    if route == "carbon/drilldown":
        return (
            CARBON
            + f"SELECT period_start AS time,actual,forecast,value,intensity_index,source_id,response_id,updated_at,ROW_NUMBER() OVER(ORDER BY value DESC NULLS LAST) AS intensity_rank FROM base ORDER BY time {order} LIMIT :limit OFFSET :offset"
        )
    return QUERIES[route]


def rows_for(conn, route, filters):
    params = filters.model_dump()
    params["regions"] = filters.compare_regions or [1, 2, 3]
    return [dict(r) for r in conn.execute(text(dynamic_query(route, filters)), params).mappings()]


def overview(conn, f):
    # Scalar subqueries preserve each domain's grain and avoid multiplicative joins.
    query = """WITH carbon AS (
      SELECT avg(CASE WHEN region_id=0 THEN actual ELSE forecast END) AS mean,
      stddev_samp(CASE WHEN region_id=0 THEN actual ELSE forecast END) AS volatility,
      min(CASE WHEN region_id=0 THEN actual ELSE forecast END) AS minimum,
      max(CASE WHEN region_id=0 THEN actual ELSE forecast END) AS maximum,
      count(CASE WHEN region_id=0 THEN actual ELSE forecast END) AS usable
      FROM core.carbon_observation WHERE region_id=:region AND period_start>=:start AND period_start<:end
    ), previous AS (
      SELECT avg(CASE WHEN region_id=0 THEN actual ELSE forecast END) AS mean,
      count(CASE WHEN region_id=0 THEN actual ELSE forecast END) AS usable
      FROM core.carbon_observation WHERE region_id=:region
      AND period_start>=:start-(CAST(:end AS timestamptz)-CAST(:start AS timestamptz)) AND period_start<:start
    ), calendar AS (
      SELECT count(*) FILTER(WHERE period_start>=:start AND period_end<=least(CAST(:end AS timestamptz),now())) AS expected,
      count(*) FILTER(WHERE period_start<:start) AS previous_expected
      FROM core.reporting_calendar WHERE period_start>=:start-(CAST(:end AS timestamptz)-CAST(:start AS timestamptz)) AND period_start<:end
    ), latest AS (
      SELECT CASE WHEN region_id=0 THEN actual ELSE forecast END AS value,forecast,period_start
      FROM core.carbon_observation WHERE region_id=:region AND period_start<:end
      AND CASE WHEN region_id=0 THEN actual ELSE forecast END IS NOT NULL ORDER BY period_start DESC LIMIT 1
    )
    SELECT c.*,p.mean AS previous_mean,p.usable AS previous_usable,cal.previous_expected,
      CASE WHEN p.usable>=cal.expected*0.8 THEN c.mean-p.mean END AS change,
      CASE WHEN p.usable>=cal.expected*0.8 THEN 100*(c.mean-p.mean)/nullif(p.mean,0) END AS change_percent,
      100.0*c.usable/nullif(cal.expected,0) AS completeness,cal.expected,
      l.value AS latest,l.forecast AS latest_forecast,l.period_start AS latest_at,
      (SELECT avg(absolute_error) FROM mart.v_carbon_forecast_errors WHERE period_start>=:start AND period_start<:end) AS mae
    FROM carbon c CROSS JOIN previous p CROSS JOIN calendar cal LEFT JOIN latest l ON true"""
    values = dict(conn.execute(text(query), f.model_dump()).mappings().one())
    values.update(rows_for(conn, "generation/summary", f)[0])
    values["demand_peak"] = rows_for(conn, "demand/summary", f)[0].get("peak")
    return [values]


def insights(conn, f):
    values = overview(conn, f)[0]
    result = []
    for metric, observed, comparison, threshold in [
        ("mean_carbon", values.get("mean"), values.get("previous_mean"), 10),
        ("completeness", values.get("completeness"), 99, 99),
    ]:
        if observed is not None and comparison is not None:
            triggered = (
                abs(float(observed) - float(comparison)) >= threshold
                if metric == "mean_carbon"
                else float(observed) < threshold
            )
            if triggered and (metric != "mean_carbon" or values.get("change") is not None):
                result.append(
                    dict(
                        metric=metric,
                        observed=observed,
                        comparison=comparison,
                        threshold=threshold,
                        start=f.start,
                        end=f.end,
                        region=0,
                        source="NESO Carbon Intensity",
                        message="Mean intensity changed against the preceding equivalent period."
                        if metric == "mean_carbon"
                        else "Usable observation coverage is below the reporting threshold.",
                    )
                )
    for s in source_statuses(conn):
        if s["collection_status"] in {"failed", "overdue", "source_delayed", "no_data"}:
            result.append(
                dict(
                    metric="source_freshness" if s["collection_status"] == "source_delayed" else "collection_status",
                    observed=s["age_minutes"] if s["collection_status"] == "source_delayed" else s["collection_status"],
                    comparison=s["stale_minutes"] if s["collection_status"] == "source_delayed" else "successful collection",
                    threshold=s["stale_minutes"] if s["collection_status"] == "source_delayed" else None,
                    start=f.start,
                    end=f.end,
                    region=0,
                    source=s["name"],
                    message={
                        "failed": "The latest collection attempt failed or returned incomplete data.",
                        "overdue": "Collection is overdue beyond its scheduled grace period.",
                        "source_delayed": "Collection succeeded, but the latest available source observation is delayed.",
                        "no_data": "No successful collection with usable observations is available.",
                    }[s["collection_status"]],
                )
            )
    advanced = """WITH recent AS (
      SELECT avg(absolute_error) AS mae FROM mart.v_carbon_forecast_errors WHERE period_start>=:start AND period_start<:end
    ), history AS (
      SELECT percentile_cont(0.95) WITHIN GROUP(ORDER BY absolute_error) AS p95
      FROM mart.v_carbon_forecast_errors WHERE period_start<:start AND period_start>=:start-interval '30 days'
    ) SELECT 'forecast_error' AS metric,r.mae AS observed,h.p95 AS comparison,h.p95 AS threshold,
      'NESO Carbon Intensity' AS source,'Mean forecast-estimate difference exceeds the preceding 30-day p95 absolute error.' AS message
      FROM recent r CROSS JOIN history h WHERE r.mae>h.p95
    UNION ALL
    SELECT 'regional_spread',max(forecast)-min(forecast),150,150,'NESO Regional Intensity',
      'Mean regional intensity spread exceeds 150 gCO₂/kWh.'
    FROM (SELECT region_id,avg(forecast) AS forecast FROM core.carbon_observation
      WHERE region_id BETWEEN 1 AND 14 AND period_start>=:start AND period_start<:end GROUP BY region_id) regions
    HAVING max(forecast)-min(forecast)>150
    UNION ALL
    SELECT 'fuel_composition_change',avg(share) FILTER(WHERE period_start>=:start),avg(share) FILTER(WHERE period_start<:start),10,
      'NESO Generation Mix','A fuel mean share changed by at least 10 percentage points against the preceding period: '||fuel_id
    FROM core.generation_share WHERE region_id=:region AND period_start>=:start-(CAST(:end AS timestamptz)-CAST(:start AS timestamptz)) AND period_start<:end
    GROUP BY fuel_id HAVING abs(avg(share) FILTER(WHERE period_start>=:start)-avg(share) FILTER(WHERE period_start<:start))>=10
    """
    for row in conn.execute(text(advanced), f.model_dump()).mappings():
        result.append(dict(row, start=f.start, end=f.end, region=f.region))
    return result


def query(route, filters):
    with read_engine.connect() as conn:
        if route == "overview":
            rows = overview(conn, filters)
        elif route == "operations/sources":
            rows = source_statuses(conn)
        elif route == "insights":
            rows = insights(conn, filters)
        else:
            rows = rows_for(conn, route, filters)
        sources = rows if route == "operations/sources" else source_statuses(conn)
    return dict(
        rows=rows,
        meta=dict(
            start=filters.start,
            end=filters.end,
            region=filters.region,
            granularity=filters.granularity,
            generated_at=datetime.now(timezone.utc),
            sources=sources,
            count=len(rows),
            limit=filters.limit,
            offset=filters.offset,
            possibly_truncated=len(rows) >= filters.limit,
            caveat="Regional values are estimates/forecasts. National actuals are estimated actuals. Forecast differences are not verified issue-time skill.",
        ),
    )
