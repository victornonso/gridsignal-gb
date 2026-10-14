# Data dictionary

Generated from migrated PostgreSQL metadata. Source mappings and grain rules are described in `source-contracts.md` and `architecture.md`.

## core.carbon_factor

| Column | Type | Nullable | Default |
|---|---|---|---|
| label | text | NO | — |
| gco2_per_kwh | numeric | NO | — |
| run_id | bigint | NO | — |
| response_id | bigint | NO | — |
| updated_at | timestamp with time zone | NO | now() |
## core.carbon_observation

| Column | Type | Nullable | Default |
|---|---|---|---|
| region_id | integer | NO | — |
| period_start | timestamp with time zone | NO | — |
| period_end | timestamp with time zone | NO | — |
| forecast | numeric | YES | — |
| actual | numeric | YES | — |
| intensity_index | text | YES | — |
| source_id | text | NO | — |
| run_id | bigint | NO | — |
| response_id | bigint | NO | — |
| record_hash | text | NO | — |
| first_seen_at | timestamp with time zone | NO | now() |
| updated_at | timestamp with time zone | NO | now() |
## core.carbon_revision

| Column | Type | Nullable | Default |
|---|---|---|---|
| id | bigint | NO | — |
| region_id | integer | NO | — |
| period_start | timestamp with time zone | NO | — |
| old_value | jsonb | NO | — |
| new_value | jsonb | NO | — |
| run_id | bigint | NO | — |
| changed_at | timestamp with time zone | NO | now() |
## core.demand_observation

| Column | Type | Nullable | Default |
|---|---|---|---|
| settlement_date | date | NO | — |
| settlement_period | smallint | NO | — |
| period_start | timestamp with time zone | NO | — |
| period_end | timestamp with time zone | NO | — |
| national_mw | numeric | YES | — |
| transmission_mw | numeric | YES | — |
| observation_kind | text | NO | — |
| source_id | text | NO | — |
| run_id | bigint | NO | — |
| response_id | bigint | NO | — |
| record_hash | text | NO | — |
| updated_at | timestamp with time zone | NO | now() |
## core.fuel_type

| Column | Type | Nullable | Default |
|---|---|---|---|
| id | text | NO | — |
| label | text | NO | — |
| renewable | boolean | NO | false |
| low_carbon | boolean | NO | false |
| fossil | boolean | NO | false |
| colour | text | NO | — |
## core.generation_outturn

| Column | Type | Nullable | Default |
|---|---|---|---|
| period_start | timestamp with time zone | NO | — |
| period_end | timestamp with time zone | NO | — |
| fuel_id | text | NO | — |
| source_fuel | text | NO | — |
| power_mw | numeric | NO | — |
| published_at | timestamp with time zone | YES | — |
| source_id | text | NO | — |
| run_id | bigint | NO | — |
| response_id | bigint | NO | — |
| record_hash | text | NO | — |
| updated_at | timestamp with time zone | NO | now() |
## core.generation_share

| Column | Type | Nullable | Default |
|---|---|---|---|
| region_id | integer | NO | — |
| period_start | timestamp with time zone | NO | — |
| period_end | timestamp with time zone | NO | — |
| fuel_id | text | NO | — |
| source_fuel | text | NO | — |
| share | numeric | NO | — |
| source_id | text | NO | — |
| run_id | bigint | NO | — |
| response_id | bigint | NO | — |
| record_hash | text | NO | — |
| updated_at | timestamp with time zone | NO | now() |
## core.observation_revision

| Column | Type | Nullable | Default |
|---|---|---|---|
| id | bigint | NO | — |
| table_name | text | NO | — |
| record_key | jsonb | NO | — |
| old_value | jsonb | NO | — |
| new_value | jsonb | NO | — |
| run_id | bigint | NO | — |
| changed_at | timestamp with time zone | NO | now() |
## core.region

| Column | Type | Nullable | Default |
|---|---|---|---|
| id | integer | NO | — |
| name | text | NO | — |
| scope | text | NO | — |
| dno | text | YES | — |
## core.reporting_calendar

| Column | Type | Nullable | Default |
|---|---|---|---|
| period_start | timestamp with time zone | NO | — |
| period_end | timestamp with time zone | NO | — |
| settlement_date | date | NO | — |
| settlement_period | smallint | NO | — |
| local_hour | smallint | NO | — |
| weekday | smallint | NO | — |
| weekend | boolean | NO | — |
## mart.v_carbon_forecast_errors

| Column | Type | Nullable | Default |
|---|---|---|---|
| region_id | integer | YES | — |
| period_start | timestamp with time zone | YES | — |
| period_end | timestamp with time zone | YES | — |
| forecast | numeric | YES | — |
| actual | numeric | YES | — |
| intensity_index | text | YES | — |
| source_id | text | YES | — |
| run_id | bigint | YES | — |
| response_id | bigint | YES | — |
| record_hash | text | YES | — |
| first_seen_at | timestamp with time zone | YES | — |
| updated_at | timestamp with time zone | YES | — |
| error | numeric | YES | — |
| absolute_error | numeric | YES | — |
| local_hour | integer | YES | — |
| weekday | integer | YES | — |
## mart.v_daily_carbon_performance

| Column | Type | Nullable | Default |
|---|---|---|---|
| region_id | integer | YES | — |
| day | date | YES | — |
| mean_intensity | numeric | YES | — |
| minimum | numeric | YES | — |
| maximum | numeric | YES | — |
| volatility | numeric | YES | — |
| intervals | bigint | YES | — |
| rolling_7d | numeric | YES | — |
| rolling_30d | numeric | YES | — |
| day_change | numeric | YES | — |
## mart.v_data_completeness

| Column | Type | Nullable | Default |
|---|---|---|---|
| day | date | YES | — |
| region_id | integer | YES | — |
| expected | bigint | YES | — |
| received | bigint | YES | — |
| usable | bigint | YES | — |
| completeness | numeric | YES | — |
## mart.v_demand_profile

| Column | Type | Nullable | Default |
|---|---|---|---|
| settlement_date | date | YES | — |
| settlement_period | smallint | YES | — |
| period_start | timestamp with time zone | YES | — |
| period_end | timestamp with time zone | YES | — |
| national_mw | numeric | YES | — |
| transmission_mw | numeric | YES | — |
| observation_kind | text | YES | — |
| source_id | text | YES | — |
| run_id | bigint | YES | — |
| response_id | bigint | YES | — |
| record_hash | text | YES | — |
| updated_at | timestamp with time zone | YES | — |
| local_hour | smallint | YES | — |
| weekday | smallint | YES | — |
| weekend | boolean | YES | — |
## mart.v_generation_mix

| Column | Type | Nullable | Default |
|---|---|---|---|
| region_id | integer | YES | — |
| period_start | timestamp with time zone | YES | — |
| period_end | timestamp with time zone | YES | — |
| fuel_id | text | YES | — |
| source_fuel | text | YES | — |
| share | numeric | YES | — |
| source_id | text | YES | — |
| run_id | bigint | YES | — |
| response_id | bigint | YES | — |
| record_hash | text | YES | — |
| updated_at | timestamp with time zone | YES | — |
| label | text | YES | — |
| renewable | boolean | YES | — |
| low_carbon | boolean | YES | — |
| fossil | boolean | YES | — |
| colour | text | YES | — |
## mart.v_hourly_carbon_profile

| Column | Type | Nullable | Default |
|---|---|---|---|
| region_id | integer | YES | — |
| hour | integer | YES | — |
| weekend | boolean | YES | — |
| intensity | numeric | YES | — |
| observations | bigint | YES | — |
## mart.v_regional_carbon_comparison

| Column | Type | Nullable | Default |
|---|---|---|---|
| id | integer | YES | — |
| name | text | YES | — |
| mean_intensity | numeric | YES | — |
| volatility | numeric | YES | — |
| rank | bigint | YES | — |
| quartile | integer | YES | — |
| p95 | double precision | YES | — |
## mart.v_source_freshness

| Column | Type | Nullable | Default |
|---|---|---|---|
| id | text | YES | — |
| name | text | YES | — |
| url | text | YES | — |
| licence | text | YES | — |
| cadence_minutes | integer | YES | — |
| stale_minutes | integer | YES | — |
| observed_at | timestamp with time zone | YES | — |
| last_success_at | timestamp with time zone | YES | — |
| age_minutes | numeric | YES | — |
| stale | boolean | YES | — |
## ops.data_source

| Column | Type | Nullable | Default |
|---|---|---|---|
| id | text | NO | — |
| name | text | NO | — |
| url | text | NO | — |
| licence | text | NO | — |
| cadence_minutes | integer | NO | — |
| stale_minutes | integer | NO | — |
## ops.ingestion_run

| Column | Type | Nullable | Default |
|---|---|---|---|
| id | bigint | NO | — |
| source_id | text | NO | — |
| started_at | timestamp with time zone | NO | now() |
| finished_at | timestamp with time zone | YES | — |
| window_start | timestamp with time zone | NO | — |
| window_end | timestamp with time zone | NO | — |
| status | text | NO | 'running'::text |
| received | integer | NO | 0 |
| inserted | integer | NO | 0 |
| updated | integer | NO | 0 |
| rejected | integer | NO | 0 |
| duplicates | integer | NO | 0 |
| error | text | YES | — |
## ops.ingestion_watermark

| Column | Type | Nullable | Default |
|---|---|---|---|
| source_id | text | NO | — |
| through_at | timestamp with time zone | NO | — |
| run_id | bigint | NO | — |
## ops.quality_result

| Column | Type | Nullable | Default |
|---|---|---|---|
| id | bigint | NO | — |
| run_id | bigint | YES | — |
| test_name | text | NO | — |
| source_id | text | NO | — |
| executed_at | timestamp with time zone | NO | now() |
| status | text | NO | — |
| observed | numeric | YES | — |
| threshold | numeric | YES | — |
| severity | text | NO | — |
| details | jsonb | NO | '{}'::jsonb |
## raw.api_response

| Column | Type | Nullable | Default |
|---|---|---|---|
| id | bigint | NO | — |
| run_id | bigint | NO | — |
| source_id | text | NO | — |
| url | text | NO | — |
| retrieved_at | timestamp with time zone | NO | now() |
| status_code | integer | NO | — |
| body | jsonb | NO | — |
| body_hash | text | NO | — |
## raw.quarantine

| Column | Type | Nullable | Default |
|---|---|---|---|
| id | bigint | NO | — |
| run_id | bigint | NO | — |
| response_id | bigint | YES | — |
| record | jsonb | NO | — |
| error | text | NO | — |
| created_at | timestamp with time zone | NO | now() |

## Keys and constraints

- `core.carbon_factor.carbon_factor_gco2_per_kwh_check`: `CHECK ((gco2_per_kwh >= (0)::numeric))`
- `core.carbon_factor.carbon_factor_gco2_per_kwh_not_null`: `NOT NULL gco2_per_kwh`
- `core.carbon_factor.carbon_factor_label_not_null`: `NOT NULL label`
- `core.carbon_factor.carbon_factor_pkey`: `PRIMARY KEY (label)`
- `core.carbon_factor.carbon_factor_response_id_fkey`: `FOREIGN KEY (response_id) REFERENCES raw.api_response(id)`
- `core.carbon_factor.carbon_factor_response_id_not_null`: `NOT NULL response_id`
- `core.carbon_factor.carbon_factor_run_id_fkey`: `FOREIGN KEY (run_id) REFERENCES ops.ingestion_run(id)`
- `core.carbon_factor.carbon_factor_run_id_not_null`: `NOT NULL run_id`
- `core.carbon_factor.carbon_factor_updated_at_not_null`: `NOT NULL updated_at`
- `core.carbon_observation.carbon_observation_actual_check`: `CHECK ((actual >= (0)::numeric))`
- `core.carbon_observation.carbon_observation_check`: `CHECK ((period_end = (period_start + '00:30:00'::interval)))`
- `core.carbon_observation.carbon_observation_check1`: `CHECK (((forecast IS NOT NULL) OR (actual IS NOT NULL)))`
- `core.carbon_observation.carbon_observation_check2`: `CHECK (((region_id = 0) OR (actual IS NULL)))`
- `core.carbon_observation.carbon_observation_first_seen_at_not_null`: `NOT NULL first_seen_at`
- `core.carbon_observation.carbon_observation_forecast_check`: `CHECK ((forecast >= (0)::numeric))`
- `core.carbon_observation.carbon_observation_period_end_not_null`: `NOT NULL period_end`
- `core.carbon_observation.carbon_observation_period_start_not_null`: `NOT NULL period_start`
- `core.carbon_observation.carbon_observation_pkey`: `PRIMARY KEY (region_id, period_start)`
- `core.carbon_observation.carbon_observation_record_hash_not_null`: `NOT NULL record_hash`
- `core.carbon_observation.carbon_observation_region_id_fkey`: `FOREIGN KEY (region_id) REFERENCES core.region(id)`
- `core.carbon_observation.carbon_observation_region_id_not_null`: `NOT NULL region_id`
- `core.carbon_observation.carbon_observation_response_id_fkey`: `FOREIGN KEY (response_id) REFERENCES raw.api_response(id)`
- `core.carbon_observation.carbon_observation_response_id_not_null`: `NOT NULL response_id`
- `core.carbon_observation.carbon_observation_run_id_fkey`: `FOREIGN KEY (run_id) REFERENCES ops.ingestion_run(id)`
- `core.carbon_observation.carbon_observation_run_id_not_null`: `NOT NULL run_id`
- `core.carbon_observation.carbon_observation_source_id_fkey`: `FOREIGN KEY (source_id) REFERENCES ops.data_source(id)`
- `core.carbon_observation.carbon_observation_source_id_not_null`: `NOT NULL source_id`
- `core.carbon_observation.carbon_observation_updated_at_not_null`: `NOT NULL updated_at`
- `core.carbon_revision.carbon_revision_changed_at_not_null`: `NOT NULL changed_at`
- `core.carbon_revision.carbon_revision_id_not_null`: `NOT NULL id`
- `core.carbon_revision.carbon_revision_new_value_not_null`: `NOT NULL new_value`
- `core.carbon_revision.carbon_revision_old_value_not_null`: `NOT NULL old_value`
- `core.carbon_revision.carbon_revision_period_start_not_null`: `NOT NULL period_start`
- `core.carbon_revision.carbon_revision_pkey`: `PRIMARY KEY (id)`
- `core.carbon_revision.carbon_revision_region_id_not_null`: `NOT NULL region_id`
- `core.carbon_revision.carbon_revision_run_id_fkey`: `FOREIGN KEY (run_id) REFERENCES ops.ingestion_run(id)`
- `core.carbon_revision.carbon_revision_run_id_not_null`: `NOT NULL run_id`
- `core.demand_observation.demand_observation_check`: `CHECK ((period_end = (period_start + '00:30:00'::interval)))`
- `core.demand_observation.demand_observation_national_mw_check`: `CHECK ((national_mw >= (0)::numeric))`
- `core.demand_observation.demand_observation_observation_kind_check`: `CHECK ((observation_kind = ANY (ARRAY['A'::text, 'F'::text])))`
- `core.demand_observation.demand_observation_observation_kind_not_null`: `NOT NULL observation_kind`
- `core.demand_observation.demand_observation_period_end_not_null`: `NOT NULL period_end`
- `core.demand_observation.demand_observation_period_start_not_null`: `NOT NULL period_start`
- `core.demand_observation.demand_observation_pkey`: `PRIMARY KEY (settlement_date, settlement_period, source_id)`
- `core.demand_observation.demand_observation_record_hash_not_null`: `NOT NULL record_hash`
- `core.demand_observation.demand_observation_response_id_fkey`: `FOREIGN KEY (response_id) REFERENCES raw.api_response(id)`
- `core.demand_observation.demand_observation_response_id_not_null`: `NOT NULL response_id`
- `core.demand_observation.demand_observation_run_id_fkey`: `FOREIGN KEY (run_id) REFERENCES ops.ingestion_run(id)`
- `core.demand_observation.demand_observation_run_id_not_null`: `NOT NULL run_id`
- `core.demand_observation.demand_observation_settlement_date_not_null`: `NOT NULL settlement_date`
- `core.demand_observation.demand_observation_settlement_period_check`: `CHECK (((settlement_period >= 1) AND (settlement_period <= 50)))`
- `core.demand_observation.demand_observation_settlement_period_not_null`: `NOT NULL settlement_period`
- `core.demand_observation.demand_observation_source_id_fkey`: `FOREIGN KEY (source_id) REFERENCES ops.data_source(id)`
- `core.demand_observation.demand_observation_source_id_not_null`: `NOT NULL source_id`
- `core.demand_observation.demand_observation_transmission_mw_check`: `CHECK ((transmission_mw >= (0)::numeric))`
- `core.demand_observation.demand_observation_updated_at_not_null`: `NOT NULL updated_at`
- `core.fuel_type.fuel_type_colour_not_null`: `NOT NULL colour`
- `core.fuel_type.fuel_type_fossil_not_null`: `NOT NULL fossil`
- `core.fuel_type.fuel_type_id_not_null`: `NOT NULL id`
- `core.fuel_type.fuel_type_label_not_null`: `NOT NULL label`
- `core.fuel_type.fuel_type_low_carbon_not_null`: `NOT NULL low_carbon`
- `core.fuel_type.fuel_type_pkey`: `PRIMARY KEY (id)`
- `core.fuel_type.fuel_type_renewable_not_null`: `NOT NULL renewable`
- `core.generation_outturn.generation_outturn_check`: `CHECK ((period_end > period_start))`
- `core.generation_outturn.generation_outturn_fuel_id_fkey`: `FOREIGN KEY (fuel_id) REFERENCES core.fuel_type(id)`
- `core.generation_outturn.generation_outturn_fuel_id_not_null`: `NOT NULL fuel_id`
- `core.generation_outturn.generation_outturn_period_end_not_null`: `NOT NULL period_end`
- `core.generation_outturn.generation_outturn_period_start_not_null`: `NOT NULL period_start`
- `core.generation_outturn.generation_outturn_pkey`: `PRIMARY KEY (period_start, source_fuel, source_id)`
- `core.generation_outturn.generation_outturn_power_mw_not_null`: `NOT NULL power_mw`
- `core.generation_outturn.generation_outturn_record_hash_not_null`: `NOT NULL record_hash`
- `core.generation_outturn.generation_outturn_response_id_fkey`: `FOREIGN KEY (response_id) REFERENCES raw.api_response(id)`
- `core.generation_outturn.generation_outturn_response_id_not_null`: `NOT NULL response_id`
- `core.generation_outturn.generation_outturn_run_id_fkey`: `FOREIGN KEY (run_id) REFERENCES ops.ingestion_run(id)`
- `core.generation_outturn.generation_outturn_run_id_not_null`: `NOT NULL run_id`
- `core.generation_outturn.generation_outturn_source_fuel_not_null`: `NOT NULL source_fuel`
- `core.generation_outturn.generation_outturn_source_id_fkey`: `FOREIGN KEY (source_id) REFERENCES ops.data_source(id)`
- `core.generation_outturn.generation_outturn_source_id_not_null`: `NOT NULL source_id`
- `core.generation_outturn.generation_outturn_updated_at_not_null`: `NOT NULL updated_at`
- `core.generation_share.generation_share_check`: `CHECK ((period_end = (period_start + '00:30:00'::interval)))`
- `core.generation_share.generation_share_fuel_id_fkey`: `FOREIGN KEY (fuel_id) REFERENCES core.fuel_type(id)`
- `core.generation_share.generation_share_fuel_id_not_null`: `NOT NULL fuel_id`
- `core.generation_share.generation_share_period_end_not_null`: `NOT NULL period_end`
- `core.generation_share.generation_share_period_start_not_null`: `NOT NULL period_start`
- `core.generation_share.generation_share_pkey`: `PRIMARY KEY (region_id, period_start, fuel_id, source_id)`
- `core.generation_share.generation_share_record_hash_not_null`: `NOT NULL record_hash`
- `core.generation_share.generation_share_region_id_fkey`: `FOREIGN KEY (region_id) REFERENCES core.region(id)`
- `core.generation_share.generation_share_region_id_not_null`: `NOT NULL region_id`
- `core.generation_share.generation_share_response_id_fkey`: `FOREIGN KEY (response_id) REFERENCES raw.api_response(id)`
- `core.generation_share.generation_share_response_id_not_null`: `NOT NULL response_id`
- `core.generation_share.generation_share_run_id_fkey`: `FOREIGN KEY (run_id) REFERENCES ops.ingestion_run(id)`
- `core.generation_share.generation_share_run_id_not_null`: `NOT NULL run_id`
- `core.generation_share.generation_share_share_check`: `CHECK (((share >= (0)::numeric) AND (share <= (100)::numeric)))`
- `core.generation_share.generation_share_share_not_null`: `NOT NULL share`
- `core.generation_share.generation_share_source_fuel_not_null`: `NOT NULL source_fuel`
- `core.generation_share.generation_share_source_id_fkey`: `FOREIGN KEY (source_id) REFERENCES ops.data_source(id)`
- `core.generation_share.generation_share_source_id_not_null`: `NOT NULL source_id`
- `core.generation_share.generation_share_updated_at_not_null`: `NOT NULL updated_at`
- `core.observation_revision.observation_revision_changed_at_not_null`: `NOT NULL changed_at`
- `core.observation_revision.observation_revision_id_not_null`: `NOT NULL id`
- `core.observation_revision.observation_revision_new_value_not_null`: `NOT NULL new_value`
- `core.observation_revision.observation_revision_old_value_not_null`: `NOT NULL old_value`
- `core.observation_revision.observation_revision_pkey`: `PRIMARY KEY (id)`
- `core.observation_revision.observation_revision_record_key_not_null`: `NOT NULL record_key`
- `core.observation_revision.observation_revision_run_id_fkey`: `FOREIGN KEY (run_id) REFERENCES ops.ingestion_run(id)`
- `core.observation_revision.observation_revision_run_id_not_null`: `NOT NULL run_id`
- `core.observation_revision.observation_revision_table_name_not_null`: `NOT NULL table_name`
- `core.region.region_id_check`: `CHECK (((id >= 0) AND (id <= 17)))`
- `core.region.region_id_not_null`: `NOT NULL id`
- `core.region.region_name_not_null`: `NOT NULL name`
- `core.region.region_pkey`: `PRIMARY KEY (id)`
- `core.region.region_scope_check`: `CHECK ((scope = ANY (ARRAY['national'::text, 'region'::text, 'country'::text])))`
- `core.region.region_scope_not_null`: `NOT NULL scope`
- `core.reporting_calendar.reporting_calendar_check`: `CHECK ((period_end = (period_start + '00:30:00'::interval)))`
- `core.reporting_calendar.reporting_calendar_local_hour_not_null`: `NOT NULL local_hour`
- `core.reporting_calendar.reporting_calendar_period_end_not_null`: `NOT NULL period_end`
- `core.reporting_calendar.reporting_calendar_period_start_not_null`: `NOT NULL period_start`
- `core.reporting_calendar.reporting_calendar_pkey`: `PRIMARY KEY (period_start)`
- `core.reporting_calendar.reporting_calendar_settlement_date_not_null`: `NOT NULL settlement_date`
- `core.reporting_calendar.reporting_calendar_settlement_date_settlement_period_key`: `UNIQUE (settlement_date, settlement_period)`
- `core.reporting_calendar.reporting_calendar_settlement_period_check`: `CHECK (((settlement_period >= 1) AND (settlement_period <= 50)))`
- `core.reporting_calendar.reporting_calendar_settlement_period_not_null`: `NOT NULL settlement_period`
- `core.reporting_calendar.reporting_calendar_weekday_not_null`: `NOT NULL weekday`
- `core.reporting_calendar.reporting_calendar_weekend_not_null`: `NOT NULL weekend`
- `ops.data_source.data_source_cadence_minutes_check`: `CHECK ((cadence_minutes > 0))`
- `ops.data_source.data_source_cadence_minutes_not_null`: `NOT NULL cadence_minutes`
- `ops.data_source.data_source_id_not_null`: `NOT NULL id`
- `ops.data_source.data_source_licence_not_null`: `NOT NULL licence`
- `ops.data_source.data_source_name_not_null`: `NOT NULL name`
- `ops.data_source.data_source_pkey`: `PRIMARY KEY (id)`
- `ops.data_source.data_source_stale_minutes_not_null`: `NOT NULL stale_minutes`
- `ops.data_source.data_source_url_not_null`: `NOT NULL url`
- `ops.ingestion_run.ingestion_run_check`: `CHECK ((window_end > window_start))`
- `ops.ingestion_run.ingestion_run_duplicates_not_null`: `NOT NULL duplicates`
- `ops.ingestion_run.ingestion_run_id_not_null`: `NOT NULL id`
- `ops.ingestion_run.ingestion_run_inserted_not_null`: `NOT NULL inserted`
- `ops.ingestion_run.ingestion_run_pkey`: `PRIMARY KEY (id)`
- `ops.ingestion_run.ingestion_run_received_not_null`: `NOT NULL received`
- `ops.ingestion_run.ingestion_run_rejected_not_null`: `NOT NULL rejected`
- `ops.ingestion_run.ingestion_run_source_id_fkey`: `FOREIGN KEY (source_id) REFERENCES ops.data_source(id)`
- `ops.ingestion_run.ingestion_run_source_id_not_null`: `NOT NULL source_id`
- `ops.ingestion_run.ingestion_run_started_at_not_null`: `NOT NULL started_at`
- `ops.ingestion_run.ingestion_run_status_check`: `CHECK ((status = ANY (ARRAY['running'::text, 'success'::text, 'failed'::text, 'partial'::text, 'skipped'::text])))`
- `ops.ingestion_run.ingestion_run_status_not_null`: `NOT NULL status`
- `ops.ingestion_run.ingestion_run_updated_not_null`: `NOT NULL updated`
- `ops.ingestion_run.ingestion_run_window_end_not_null`: `NOT NULL window_end`
- `ops.ingestion_run.ingestion_run_window_start_not_null`: `NOT NULL window_start`
- `ops.ingestion_watermark.ingestion_watermark_pkey`: `PRIMARY KEY (source_id)`
- `ops.ingestion_watermark.ingestion_watermark_run_id_fkey`: `FOREIGN KEY (run_id) REFERENCES ops.ingestion_run(id)`
- `ops.ingestion_watermark.ingestion_watermark_run_id_not_null`: `NOT NULL run_id`
- `ops.ingestion_watermark.ingestion_watermark_source_id_fkey`: `FOREIGN KEY (source_id) REFERENCES ops.data_source(id)`
- `ops.ingestion_watermark.ingestion_watermark_source_id_not_null`: `NOT NULL source_id`
- `ops.ingestion_watermark.ingestion_watermark_through_at_not_null`: `NOT NULL through_at`
- `ops.quality_result.quality_result_details_not_null`: `NOT NULL details`
- `ops.quality_result.quality_result_executed_at_not_null`: `NOT NULL executed_at`
- `ops.quality_result.quality_result_id_not_null`: `NOT NULL id`
- `ops.quality_result.quality_result_pkey`: `PRIMARY KEY (id)`
- `ops.quality_result.quality_result_run_id_fkey`: `FOREIGN KEY (run_id) REFERENCES ops.ingestion_run(id)`
- `ops.quality_result.quality_result_severity_check`: `CHECK ((severity = ANY (ARRAY['info'::text, 'warning'::text, 'critical'::text])))`
- `ops.quality_result.quality_result_severity_not_null`: `NOT NULL severity`
- `ops.quality_result.quality_result_source_id_fkey`: `FOREIGN KEY (source_id) REFERENCES ops.data_source(id)`
- `ops.quality_result.quality_result_source_id_not_null`: `NOT NULL source_id`
- `ops.quality_result.quality_result_status_check`: `CHECK ((status = ANY (ARRAY['pass'::text, 'warn'::text, 'fail'::text])))`
- `ops.quality_result.quality_result_status_not_null`: `NOT NULL status`
- `ops.quality_result.quality_result_test_name_not_null`: `NOT NULL test_name`
- `raw.api_response.api_response_body_hash_not_null`: `NOT NULL body_hash`
- `raw.api_response.api_response_body_not_null`: `NOT NULL body`
- `raw.api_response.api_response_id_not_null`: `NOT NULL id`
- `raw.api_response.api_response_pkey`: `PRIMARY KEY (id)`
- `raw.api_response.api_response_retrieved_at_not_null`: `NOT NULL retrieved_at`
- `raw.api_response.api_response_run_id_fkey`: `FOREIGN KEY (run_id) REFERENCES ops.ingestion_run(id)`
- `raw.api_response.api_response_run_id_not_null`: `NOT NULL run_id`
- `raw.api_response.api_response_source_id_fkey`: `FOREIGN KEY (source_id) REFERENCES ops.data_source(id)`
- `raw.api_response.api_response_source_id_not_null`: `NOT NULL source_id`
- `raw.api_response.api_response_status_code_not_null`: `NOT NULL status_code`
- `raw.api_response.api_response_url_not_null`: `NOT NULL url`
- `raw.quarantine.quarantine_created_at_not_null`: `NOT NULL created_at`
- `raw.quarantine.quarantine_error_not_null`: `NOT NULL error`
- `raw.quarantine.quarantine_id_not_null`: `NOT NULL id`
- `raw.quarantine.quarantine_pkey`: `PRIMARY KEY (id)`
- `raw.quarantine.quarantine_record_not_null`: `NOT NULL record`
- `raw.quarantine.quarantine_response_id_fkey`: `FOREIGN KEY (response_id) REFERENCES raw.api_response(id)`
- `raw.quarantine.quarantine_run_id_fkey`: `FOREIGN KEY (run_id) REFERENCES ops.ingestion_run(id)`
- `raw.quarantine.quarantine_run_id_not_null`: `NOT NULL run_id`
