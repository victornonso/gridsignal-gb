CREATE SCHEMA ops;
CREATE SCHEMA raw;
CREATE SCHEMA core;
CREATE SCHEMA mart;
CREATE TABLE ops.data_source (
 id text PRIMARY KEY, name text NOT NULL, url text NOT NULL, licence text NOT NULL,
 cadence_minutes integer NOT NULL CHECK(cadence_minutes>0), stale_minutes integer NOT NULL
);
INSERT INTO ops.data_source VALUES
 ('carbon','NESO Carbon Intensity','https://api.carbonintensity.org.uk','CC BY 4.0',30,120),
 ('regional','NESO Regional Intensity','https://api.carbonintensity.org.uk','CC BY 4.0',30,120),
 ('mix','NESO Generation Mix','https://api.carbonintensity.org.uk','CC BY 4.0',30,120),
 ('elexon','Elexon FUELHH','https://data.elexon.co.uk/bmrs/api/v1','Elexon open data',30,120),
 ('demand','NESO Demand Data Update','https://api.neso.energy','NESO Open Data Licence',1440,17280),
 ('factors','NESO Published Carbon Factors','https://api.carbonintensity.org.uk','CC BY 4.0',1440,43200);
CREATE TABLE ops.ingestion_run (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, source_id text NOT NULL REFERENCES ops.data_source,
 started_at timestamptz NOT NULL DEFAULT now(), finished_at timestamptz,
 window_start timestamptz NOT NULL, window_end timestamptz NOT NULL,
 status text NOT NULL DEFAULT 'running' CHECK(status IN ('running','success','failed','partial','skipped')),
 received integer NOT NULL DEFAULT 0, inserted integer NOT NULL DEFAULT 0, updated integer NOT NULL DEFAULT 0,
 rejected integer NOT NULL DEFAULT 0, duplicates integer NOT NULL DEFAULT 0, error text,
 CHECK(window_end>window_start)
);
CREATE INDEX run_source_time ON ops.ingestion_run(source_id,started_at DESC);
CREATE TABLE ops.ingestion_watermark(source_id text PRIMARY KEY REFERENCES ops.data_source, through_at timestamptz NOT NULL, run_id bigint NOT NULL REFERENCES ops.ingestion_run);
CREATE TABLE ops.quality_result(
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, run_id bigint REFERENCES ops.ingestion_run,
 test_name text NOT NULL, source_id text NOT NULL REFERENCES ops.data_source, executed_at timestamptz NOT NULL DEFAULT now(),
 status text NOT NULL CHECK(status IN ('pass','warn','fail')), observed numeric, threshold numeric,
 severity text NOT NULL CHECK(severity IN ('info','warning','critical')), details jsonb NOT NULL DEFAULT '{}'
);
CREATE TABLE raw.api_response(
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, run_id bigint NOT NULL REFERENCES ops.ingestion_run,
 source_id text NOT NULL REFERENCES ops.data_source, url text NOT NULL, retrieved_at timestamptz NOT NULL DEFAULT now(),
 status_code integer NOT NULL, body jsonb NOT NULL, body_hash text NOT NULL
);
CREATE TABLE raw.quarantine(
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, run_id bigint NOT NULL REFERENCES ops.ingestion_run,
 response_id bigint REFERENCES raw.api_response, record jsonb NOT NULL, error text NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE core.region(id integer PRIMARY KEY CHECK(id BETWEEN 0 AND 17),name text NOT NULL,scope text NOT NULL CHECK(scope IN ('national','region','country')),dno text);
INSERT INTO core.region VALUES (0,'Great Britain','national',NULL);
CREATE TABLE core.fuel_type(id text PRIMARY KEY, label text NOT NULL, renewable boolean NOT NULL DEFAULT false, low_carbon boolean NOT NULL DEFAULT false, fossil boolean NOT NULL DEFAULT false, colour text NOT NULL);
INSERT INTO core.fuel_type VALUES
 ('biomass','Biomass',true,true,false,'#989a45'),('coal','Coal',false,false,true,'#6c7075'),
 ('gas','Gas',false,false,true,'#c78a56'),('nuclear','Nuclear',false,true,false,'#9d8bc4'),
 ('other','Other',false,false,false,'#a6adb3'),('hydro','Hydro',true,true,false,'#499eb1'),
 ('solar','Solar',true,true,false,'#e4b44e'),('wind','Wind',true,true,false,'#57b794'),
 ('imports','Imports',false,false,false,'#648bbb'),('oil','Oil',false,false,true,'#a36e66'),
 ('pumped_storage','Pumped storage',false,false,false,'#789fba');
CREATE TABLE core.reporting_calendar(
 period_start timestamptz PRIMARY KEY, period_end timestamptz NOT NULL,
 settlement_date date NOT NULL, settlement_period smallint NOT NULL CHECK(settlement_period BETWEEN 1 AND 50),
 local_hour smallint NOT NULL, weekday smallint NOT NULL, weekend boolean NOT NULL,
 UNIQUE(settlement_date,settlement_period), CHECK(period_end=period_start+interval '30 minutes')
);
CREATE TABLE core.carbon_observation(
 region_id integer NOT NULL REFERENCES core.region, period_start timestamptz NOT NULL,
 period_end timestamptz NOT NULL, forecast numeric CHECK(forecast>=0), actual numeric CHECK(actual>=0), intensity_index text,
 source_id text NOT NULL REFERENCES ops.data_source, run_id bigint NOT NULL REFERENCES ops.ingestion_run,
 response_id bigint NOT NULL REFERENCES raw.api_response, record_hash text NOT NULL,
 first_seen_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(region_id,period_start), CHECK(period_end=period_start+interval '30 minutes'),
 CHECK(forecast IS NOT NULL OR actual IS NOT NULL), CHECK(region_id=0 OR actual IS NULL)
);
CREATE INDEX carbon_time_region ON core.carbon_observation(period_start,region_id) INCLUDE(actual,forecast);
CREATE TABLE core.carbon_revision(
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, region_id integer NOT NULL, period_start timestamptz NOT NULL,
 old_value jsonb NOT NULL, new_value jsonb NOT NULL, run_id bigint NOT NULL REFERENCES ops.ingestion_run,
 changed_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE core.generation_share(
 region_id integer NOT NULL REFERENCES core.region, period_start timestamptz NOT NULL, period_end timestamptz NOT NULL,
 fuel_id text NOT NULL REFERENCES core.fuel_type, source_fuel text NOT NULL,
 share numeric NOT NULL CHECK(share BETWEEN 0 AND 100), source_id text NOT NULL REFERENCES ops.data_source,
 run_id bigint NOT NULL REFERENCES ops.ingestion_run, response_id bigint NOT NULL REFERENCES raw.api_response,
 record_hash text NOT NULL, updated_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(region_id,period_start,fuel_id,source_id), CHECK(period_end=period_start+interval '30 minutes')
);
CREATE TABLE core.generation_outturn(
 period_start timestamptz NOT NULL, period_end timestamptz NOT NULL, fuel_id text NOT NULL REFERENCES core.fuel_type,
 source_fuel text NOT NULL, power_mw numeric NOT NULL, published_at timestamptz,
 source_id text NOT NULL REFERENCES ops.data_source, run_id bigint NOT NULL REFERENCES ops.ingestion_run,
 response_id bigint NOT NULL REFERENCES raw.api_response, record_hash text NOT NULL, updated_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(period_start,source_fuel,source_id), CHECK(period_end>period_start)
);
CREATE TABLE core.demand_observation(
 settlement_date date NOT NULL, settlement_period smallint NOT NULL CHECK(settlement_period BETWEEN 1 AND 50),
 period_start timestamptz NOT NULL, period_end timestamptz NOT NULL, national_mw numeric CHECK(national_mw>=0),
 transmission_mw numeric CHECK(transmission_mw>=0), observation_kind text NOT NULL CHECK(observation_kind IN ('A','F')),
 source_id text NOT NULL REFERENCES ops.data_source, run_id bigint NOT NULL REFERENCES ops.ingestion_run,
 response_id bigint NOT NULL REFERENCES raw.api_response, record_hash text NOT NULL, updated_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(settlement_date,settlement_period,source_id), CHECK(period_end=period_start+interval '30 minutes')
);
CREATE INDEX demand_time ON core.demand_observation(period_start);
CREATE TABLE core.observation_revision(
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, table_name text NOT NULL, record_key jsonb NOT NULL,
 old_value jsonb NOT NULL, new_value jsonb NOT NULL, run_id bigint NOT NULL REFERENCES ops.ingestion_run,
 changed_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE core.carbon_factor(label text PRIMARY KEY, gco2_per_kwh numeric NOT NULL CHECK(gco2_per_kwh>=0), run_id bigint NOT NULL REFERENCES ops.ingestion_run, response_id bigint NOT NULL REFERENCES raw.api_response, updated_at timestamptz NOT NULL DEFAULT now());
CREATE FUNCTION core.track_revision() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF OLD.record_hash IS DISTINCT FROM NEW.record_hash THEN
  IF TG_TABLE_NAME='carbon_observation' THEN
   INSERT INTO core.carbon_revision(region_id,period_start,old_value,new_value,run_id)
   VALUES(OLD.region_id,OLD.period_start,to_jsonb(OLD),to_jsonb(NEW),NEW.run_id);
  ELSE
   INSERT INTO core.observation_revision(table_name,record_key,old_value,new_value,run_id)
   VALUES(TG_TABLE_NAME,jsonb_build_object('period_start',OLD.period_start),to_jsonb(OLD),to_jsonb(NEW),NEW.run_id);
  END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER carbon_revisions BEFORE UPDATE ON core.carbon_observation FOR EACH ROW EXECUTE FUNCTION core.track_revision();
CREATE TRIGGER share_revisions BEFORE UPDATE ON core.generation_share FOR EACH ROW EXECUTE FUNCTION core.track_revision();
CREATE TRIGGER outturn_revisions BEFORE UPDATE ON core.generation_outturn FOR EACH ROW EXECUTE FUNCTION core.track_revision();
CREATE TRIGGER demand_revisions BEFORE UPDATE ON core.demand_observation FOR EACH ROW EXECUTE FUNCTION core.track_revision();
GRANT USAGE ON SCHEMA ops,raw,core,mart TO gridsignal_writer;
GRANT SELECT,INSERT,UPDATE ON ALL TABLES IN SCHEMA ops,raw,core TO gridsignal_writer;
GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA ops,raw,core TO gridsignal_writer;
REVOKE UPDATE ON core.carbon_revision,core.observation_revision FROM gridsignal_writer;
GRANT USAGE ON SCHEMA ops,core,mart TO gridsignal_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA ops,core TO gridsignal_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA mart GRANT SELECT ON TABLES TO gridsignal_reader,gridsignal_writer;
