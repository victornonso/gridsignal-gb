# Metric catalogue

All calculations execute in PostgreSQL; API query identifiers below map directly to `apps/api/app/services/analytics.py`.

## carbon_intensity

- **Unit**: gCO₂/kWh
- **Grain**: region × half hour
- **Aggregation**: Arithmetic mean over equal 30-minute intervals; nulls excluded
- **Source**: NESO Carbon Intensity
- **Limitation**: National estimated actual; regional forecast. Not total emissions.
- **Null handling**: unavailable measurements remain null; aggregates exclude nulls; denominators use usable/paired counts as appropriate.
- **Quality assumptions**: validated source fields, database constraints, source-specific interval rules; gaps are not imputed.
- **Tests**: `pipelines/tests/test_contracts.py`, `db/tests/test_database.py`, endpoint verification and responsive browser tests.

### `carbon/comparison`

```sql
WITH periods AS (
 SELECT CASE WHEN period_start>=:start THEN 'current' ELSE 'previous' END AS period,
 CASE WHEN region_id=0 THEN actual ELSE forecast END AS value,period_start
 FROM core.carbon_observation WHERE region_id=:region AND period_start>=:start-(CAST(:end AS timestamptz)-CAST(:start AS timestamptz)) AND period_start<:end
) SELECT period,avg(value) AS mean,min(value) AS minimum,max(value) AS maximum,stddev_samp(value) AS volatility,
 percentile_cont(0.5) WITHIN GROUP(ORDER BY value) AS p50,percentile_cont(0.95) WITHIN GROUP(ORDER BY value) AS p95,count(value) AS observations,
 CASE WHEN count(value)>0 THEN (array_agg(period_start ORDER BY value DESC NULLS LAST))[1] END AS peak_interval
 FROM periods GROUP BY period
```

### `carbon/profile`

```sql
WITH base AS (
 SELECT c.*,CASE WHEN region_id=0 THEN actual ELSE forecast END AS value,
 extract(hour FROM period_start AT TIME ZONE 'Europe/London')::int AS hour,
 extract(isodow FROM period_start AT TIME ZONE 'Europe/London')::int AS weekday,
 (period_start AT TIME ZONE 'Europe/London')::date AS day
 FROM core.carbon_observation c WHERE region_id=:region AND period_start>=:start AND period_start<:end
) SELECT hour,weekday>5 AS weekend,avg(value) AS value,stddev_samp(value) AS volatility,count(value) AS observations FROM base GROUP BY 1,2 ORDER BY 1,2
```

### `carbon/distribution`

```sql
WITH base AS (
 SELECT c.*,CASE WHEN region_id=0 THEN actual ELSE forecast END AS value,
 extract(hour FROM period_start AT TIME ZONE 'Europe/London')::int AS hour,
 extract(isodow FROM period_start AT TIME ZONE 'Europe/London')::int AS weekday,
 (period_start AT TIME ZONE 'Europe/London')::date AS day
 FROM core.carbon_observation c WHERE region_id=:region AND period_start>=:start AND period_start<:end
) SELECT floor(value/20)*20 AS bucket,count(*) AS observations FROM base WHERE value IS NOT NULL GROUP BY 1 ORDER BY 1
```

## generation_share

- **Unit**: %
- **Grain**: region × half hour × fuel
- **Aggregation**: Mean of source-reported shares; not weighted by electricity consumption
- **Source**: NESO Generation Mix
- **Limitation**: Period average composition, not share of period energy.
- **Null handling**: unavailable measurements remain null; aggregates exclude nulls; denominators use usable/paired counts as appropriate.
- **Quality assumptions**: validated source fields, database constraints, source-specific interval rules; gaps are not imputed.
- **Tests**: `pipelines/tests/test_contracts.py`, `db/tests/test_database.py`, endpoint verification and responsive browser tests.

### `generation/mix`

```sql
SELECT fuel_id,label,colour,renewable,low_carbon,fossil,avg(share) AS share,count(*) AS observations
 FROM mart.v_generation_mix WHERE region_id=:region AND period_start>=:start AND period_start<:end AND (CAST(:fuel AS text) IS NULL OR fuel_id=:fuel)
 GROUP BY fuel_id,label,colour,renewable,low_carbon,fossil ORDER BY share DESC
```

### `generation/summary`

```sql
WITH intervals AS (
 SELECT period_start,sum(share) FILTER(WHERE low_carbon) AS low_carbon,sum(share) FILTER(WHERE renewable) AS renewable,
 sum(share) FILTER(WHERE fossil) AS fossil FROM mart.v_generation_mix WHERE region_id=:region AND period_start>=:start AND period_start<:end
 GROUP BY period_start) SELECT avg(low_carbon) AS low_carbon,avg(renewable) AS renewable,avg(fossil) AS fossil FROM intervals
```

## generation_outturn

- **Unit**: MW / MWh
- **Grain**: half hour × source fuel
- **Aggregation**: Duration-weighted average MW; energy is MW × valid interval hours
- **Source**: Elexon FUELHH
- **Limitation**: Metered generation; embedded coverage incomplete; interconnectors can be signed.
- **Null handling**: unavailable measurements remain null; aggregates exclude nulls; denominators use usable/paired counts as appropriate.
- **Quality assumptions**: validated source fields, database constraints, source-specific interval rules; gaps are not imputed.
- **Tests**: `pipelines/tests/test_contracts.py`, `db/tests/test_database.py`, endpoint verification and responsive browser tests.

### `generation/outturn`

Dynamic SQL is in `dynamic_query()`; granularity is selected from a fixed whitelist, and all analytical values remain bound parameters.

## national_demand

- **Unit**: MW
- **Grain**: settlement date × period
- **Aggregation**: Mean / min / max of A-indicated rows; ND and TSD separate
- **Source**: NESO Demand Data Update
- **Limitation**: Periodically published outturn; F rows excluded.
- **Null handling**: unavailable measurements remain null; aggregates exclude nulls; denominators use usable/paired counts as appropriate.
- **Quality assumptions**: validated source fields, database constraints, source-specific interval rules; gaps are not imputed.
- **Tests**: `pipelines/tests/test_contracts.py`, `db/tests/test_database.py`, endpoint verification and responsive browser tests.

### `demand/summary`

```sql
SELECT avg(national_mw) AS mean,min(national_mw) AS minimum,max(national_mw) AS peak,
 stddev_samp(national_mw) AS volatility,avg(transmission_mw) AS transmission_mean,
 percentile_cont(0.95) WITHIN GROUP(ORDER BY national_mw) AS p95,count(*) AS observations
 FROM core.demand_observation WHERE observation_kind='A' AND period_start>=:start AND period_start<:end
```

### `demand/profile`

Dynamic SQL is in `dynamic_query()`; granularity is selected from a fixed whitelist, and all analytical values remain bound parameters.

## forecast_errors

- **Unit**: gCO₂/kWh
- **Grain**: paired national half hour
- **Aggregation**: MAE, sqrt(mean squared error), forecast minus actual bias; null pairs excluded
- **Source**: NESO Carbon Intensity
- **Limitation**: Published contemporaneous forecast-estimate differences; issue-time versions unavailable.
- **Null handling**: unavailable measurements remain null; aggregates exclude nulls; denominators use usable/paired counts as appropriate.
- **Quality assumptions**: validated source fields, database constraints, source-specific interval rules; gaps are not imputed.
- **Tests**: `pipelines/tests/test_contracts.py`, `db/tests/test_database.py`, endpoint verification and responsive browser tests.

### `forecasts/errors`

```sql
WITH base AS (
 SELECT * FROM mart.v_carbon_forecast_errors WHERE period_start>=:start AND period_start<:end
) SELECT avg(absolute_error) AS mae,sqrt(avg(power(error,2))) AS rmse,avg(error) AS bias,
 percentile_cont(0.5) WITHIN GROUP(ORDER BY absolute_error) AS median_absolute_error,
 percentile_cont(0.95) WITHIN GROUP(ORDER BY absolute_error) AS p95,count(*) AS paired_observations FROM base
```

### `forecasts/comparison`

Dynamic SQL is in `dynamic_query()`; granularity is selected from a fixed whitelist, and all analytical values remain bound parameters.

## completeness

- **Unit**: %
- **Grain**: region × reporting period
- **Aggregation**: Usable intervals / expected elapsed calendar intervals × 100
- **Source**: PostgreSQL reporting calendar
- **Limitation**: British days contain 46, 48 or 50 intervals.
- **Null handling**: unavailable measurements remain null; aggregates exclude nulls; denominators use usable/paired counts as appropriate.
- **Quality assumptions**: validated source fields, database constraints, source-specific interval rules; gaps are not imputed.
- **Tests**: `pipelines/tests/test_contracts.py`, `db/tests/test_database.py`, endpoint verification and responsive browser tests.

### `operations/completeness`

```sql
SELECT day,region_id,expected,received,usable,completeness FROM mart.v_data_completeness WHERE day>=(CAST(:start AS timestamptz) AT TIME ZONE 'Europe/London')::date AND day<(CAST(:end AS timestamptz) AT TIME ZONE 'Europe/London')::date+1 AND region_id=:region ORDER BY day
```

## Further analytical outputs

| Output | SQL definition |
|---|---|
| Volatility | `STDDEV_SAMP` of available interval values |
| Regional rank | `DENSE_RANK` by ascending mean forecast across IDs 1–14 |
| Regional quartile | `NTILE(4)` on regional mean forecast |
| Error percentiles | `PERCENTILE_CONT(0.5/0.95)` over absolute paired errors |
| Rolling intensity | Observation-count-weighted trailing mean; gaps remain missing |
| Peak demand | Maximum available national-demand outturn, MW |
| Failure rate | Failed runs / recorded runs × 100, selected operational interval |
| Freshness | Server clock − latest source observation time; source-specific threshold |
| Revision count | Append-only rows from observed source-state changes |

