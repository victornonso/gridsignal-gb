import hashlib
import json
import logging
from datetime import datetime, timedelta

from sqlalchemy import MetaData, Table, create_engine, text
from sqlalchemy.dialects.postgresql import insert

from apps.api.app.config import settings
from pipelines.clients.official import OfficialClient
from pipelines.transformations.calendar import settlement_start
from pipelines.validation.contracts import contract_drift
from pipelines.validation.models import CarbonInterval, DemandRecord, FuelOutturn, Share

log = logging.getLogger("gridsignal.ingestion")
engine = create_engine(settings.database_url, pool_pre_ping=True, pool_size=3, max_overflow=2)
metadata = MetaData()
FUEL_MAP = {"CCGT": "gas", "OCGT": "gas", "NPSHYD": "hydro", "PS": "pumped_storage"}
SOURCES = ("carbon", "regional", "mix", "elexon", "demand", "factors")


def hash_record(record):
    return hashlib.sha256(json.dumps(record, sort_keys=True, default=str).encode()).hexdigest()


def table(conn, name, schema="core"):
    key = f"{schema}.{name}"
    if key not in metadata.tables:
        Table(name, metadata, schema=schema, autoload_with=conn)
    return metadata.tables[key]


def upsert(conn, name, record, keys):
    obj = table(conn, name)
    statement = insert(obj).values(**record)
    updates = {k: getattr(statement.excluded, k) for k in record if k not in keys}
    updates["updated_at"] = text("now()")
    result = conn.execute(
        statement.on_conflict_do_update(
            index_elements=keys, set_=updates, where=obj.c.record_hash != statement.excluded.record_hash
        ).returning(text("(xmax=0) AS inserted"))
    ).first()
    return "duplicates" if result is None else ("inserted" if result.inserted else "updated")


def normalise(source, body, start, end):
    """Yield (table, record, unique columns) or validation failure without inventing records."""
    data = body.get("data", [])
    if source == "demand":
        if "records" not in body.get("result", {}):
            return  # Dataset discovery metadata is preserved raw, not treated as a fact.
        data = body["result"]["records"]
    if isinstance(data, dict):
        data = [data]
    for item in data:
        try:
            if source == "carbon":
                c = CarbonInterval.model_validate(item)
                yield (
                    "carbon_observation",
                    dict(
                        region_id=0,
                        period_start=c.start,
                        period_end=c.end,
                        forecast=c.intensity.forecast,
                        actual=c.intensity.actual,
                        intensity_index=c.intensity.index,
                    ),
                    ["region_id", "period_start"],
                )
            elif source == "regional":
                for region in item["regions"]:
                    # The regional endpoint also returns GB as ID 18. National ID 0
                    # comes from /intensity; do not overwrite its estimated actuals.
                    if region["regionid"] == 18:
                        continue
                    c = CarbonInterval.model_validate(
                        {"from": item["from"], "to": item["to"], "intensity": region["intensity"]}
                    )
                    yield (
                        "region",
                        dict(
                            id=region["regionid"],
                            name=region["shortname"],
                            dno=region.get("dnoregion"),
                            scope="region" if region["regionid"] <= 14 else "country",
                        ),
                        ["id"],
                    )
                    yield (
                        "carbon_observation",
                        dict(
                            region_id=region["regionid"],
                            period_start=c.start,
                            period_end=c.end,
                            forecast=c.intensity.forecast,
                            actual=None,
                            intensity_index=c.intensity.index,
                        ),
                        ["region_id", "period_start"],
                    )
                    yield from shares(region.get("generationmix", []), region["regionid"], c.start, c.end)
            elif source == "mix":
                a = datetime.fromisoformat(item["from"].replace("Z", "+00:00"))
                b = datetime.fromisoformat(item["to"].replace("Z", "+00:00"))
                if (b - a).total_seconds() != 1800:
                    raise ValueError("Generation share interval must be half-hourly")
                yield from shares(item["generationmix"], 0, a, b)
            elif source == "elexon":
                e = FuelOutturn.model_validate(item)
                fuel = FUEL_MAP.get(
                    e.fuelType, "imports" if e.fuelType.startswith("INT") else e.fuelType.lower()
                )
                if fuel not in {
                    "biomass",
                    "coal",
                    "gas",
                    "nuclear",
                    "other",
                    "hydro",
                    "solar",
                    "wind",
                    "imports",
                    "oil",
                    "pumped_storage",
                }:
                    raise ValueError(f"Unknown Elexon fuel: {e.fuelType}")
                yield (
                    "generation_outturn",
                    dict(
                        period_start=e.startTime,
                        period_end=e.startTime + timedelta(minutes=30),
                        fuel_id=fuel,
                        source_fuel=e.fuelType,
                        power_mw=e.generation,
                        published_at=e.publishTime,
                    ),
                    ["period_start", "source_fuel", "source_id"],
                )
            elif source == "demand":
                d = DemandRecord.model_validate(item)
                a = settlement_start(d.SETTLEMENT_DATE, d.SETTLEMENT_PERIOD)
                if not start <= a < end:
                    continue
                if d.FORECAST_ACTUAL_INDICATOR not in {"A", "F"}:
                    raise ValueError("Unknown demand observation indicator")
                # Future F rows contain zeros for ND/TSD; retain explicitly as forecasts, never as outturn.
                yield (
                    "demand_observation",
                    dict(
                        settlement_date=d.SETTLEMENT_DATE,
                        settlement_period=d.SETTLEMENT_PERIOD,
                        period_start=a,
                        period_end=a + timedelta(minutes=30),
                        national_mw=d.ND,
                        transmission_mw=d.TSD,
                        observation_kind=d.FORECAST_ACTUAL_INDICATOR,
                    ),
                    ["settlement_date", "settlement_period", "source_id"],
                )
            elif source == "factors":
                for label, value in item.items():
                    if not isinstance(value, (int, float)) or value < 0:
                        raise ValueError("Invalid carbon factor")
                    yield "carbon_factor", dict(label=label, gco2_per_kwh=value), ["label"]
        except (ValueError, KeyError, TypeError) as error:
            yield "quarantine", {"record": item, "error": str(error)}, []


def shares(records, region, start, end):
    validated = [Share.model_validate(r) for r in records]
    if validated and abs(sum(s.perc for s in validated) - 100) > 0.6:
        raise ValueError("Fuel-share total outside 100 +/- 0.6 percentage points")
    for s in validated:
        yield (
            "generation_share",
            dict(
                region_id=region,
                period_start=start,
                period_end=end,
                fuel_id=s.fuel,
                source_fuel=s.fuel,
                share=s.perc,
            ),
            ["region_id", "period_start", "fuel_id", "source_id"],
        )


def ingest(source, start, end):
    if source not in SOURCES:
        raise ValueError("Unknown source")
    stats = dict(received=0, inserted=0, updated=0, rejected=0, duplicates=0)
    with engine.begin() as conn:
        run = conn.execute(
            text(
                "INSERT INTO ops.ingestion_run(source_id,window_start,window_end) VALUES(:s,:a,:b) RETURNING id"
            ),
            dict(s=source, a=start, b=end),
        ).scalar_one()
    client = OfficialClient()
    with engine.connect() as conn:
        locked = conn.execute(text("SELECT pg_try_advisory_lock(hashtext(:s))"), {"s": source}).scalar()
        conn.commit()
        if not locked:
            with conn.begin():
                conn.execute(
                    text("UPDATE ops.ingestion_run SET status='skipped',finished_at=now() WHERE id=:id"),
                    {"id": run},
                )
            return stats
        try:
            raw_ids = []
            # Raw responses survive a later validation/core transaction failure.
            for url, body, code in client.requests(source, start, end):
                with conn.begin():
                    response_id = conn.execute(
                        text(
                            "INSERT INTO raw.api_response(run_id,source_id,url,status_code,body,body_hash) VALUES(:r,:s,:u,:c,CAST(:b AS jsonb),:h) RETURNING id"
                        ),
                        dict(r=run, s=source, u=url, c=code, b=json.dumps(body), h=hash_record(body)),
                    ).scalar_one()
                raw_ids.append((response_id, body))
            with conn.begin():
                conn.execute(text("SELECT core.extend_calendar(:a,:b)"), {"a": start, "b": end})
                for response_id, body in raw_ids:
                    drift = contract_drift(source, body)
                    conn.execute(
                        text(
                            "INSERT INTO ops.quality_result(run_id,test_name,source_id,status,observed,threshold,severity,details) VALUES(:r,'schema_contract',:s,:status,:n,0,:severity,CAST(:d AS jsonb))"
                        ),
                        {
                            "r": run,
                            "s": source,
                            "status": "fail" if drift else "pass",
                            "n": len(drift),
                            "severity": "critical" if drift else "info",
                            "d": json.dumps({"failures": drift[:20]}),
                        },
                    )
                    if drift:
                        for failure in drift:
                            conn.execute(
                                text(
                                    "INSERT INTO raw.quarantine(run_id,response_id,record,error) VALUES(:r,:p,CAST(:b AS jsonb),:e)"
                                ),
                                {
                                    "r": run,
                                    "p": response_id,
                                    "b": json.dumps(failure),
                                    "e": "Source schema contract failed",
                                },
                            )
                        stats["rejected"] += len(drift)
                        continue
                    for name, record, keys in normalise(source, body, start, end):
                        if name == "region":
                            obj = table(conn, "region")
                            stmt = insert(obj).values(**record)
                            conn.execute(
                                stmt.on_conflict_do_update(
                                    index_elements=["id"],
                                    set_={k: getattr(stmt.excluded, k) for k in record if k != "id"},
                                )
                            )
                            continue
                        if name == "quarantine":
                            conn.execute(
                                text(
                                    "INSERT INTO raw.quarantine(run_id,response_id,record,error) VALUES(:r,:p,CAST(:b AS jsonb),:e)"
                                ),
                                dict(r=run, p=response_id, b=json.dumps(record["record"]), e=record["error"]),
                            )
                            stats["rejected"] += 1
                            continue
                        stats["received"] += 1
                        record.update(run_id=run, response_id=response_id)
                        if name == "carbon_factor":
                            obj = table(conn, name)
                            previous = conn.execute(
                                text("SELECT gco2_per_kwh FROM core.carbon_factor WHERE label=:label"), record
                            ).scalar()
                            if previous is not None and float(previous) == record["gco2_per_kwh"]:
                                stats["duplicates"] += 1
                                continue
                            stmt = insert(obj).values(**record)
                            conn.execute(
                                stmt.on_conflict_do_update(
                                    index_elements=keys,
                                    set_={k: getattr(stmt.excluded, k) for k in record if k not in keys},
                                )
                            )
                            stats["inserted" if previous is None else "updated"] += 1
                            continue
                        record["source_id"] = source
                        record["record_hash"] = hash_record(
                            {k: v for k, v in record.items() if k not in {"run_id", "response_id"}}
                        )
                        stats[upsert(conn, name, record, keys)] += 1
                status = "partial" if stats["rejected"] or not stats["received"] else "success"
                conn.execute(
                    text(
                        "INSERT INTO ops.quality_result(run_id,test_name,source_id,status,observed,threshold,severity,details) VALUES(:r,'record_validation',:s,:status,:n,0,:severity,'{}')"
                    ),
                    dict(
                        r=run,
                        s=source,
                        status="fail" if stats["rejected"] else "pass",
                        n=stats["rejected"],
                        severity="critical" if stats["rejected"] else "info",
                    ),
                )
                if status == "success":
                    conn.execute(
                        text(
                            "INSERT INTO ops.ingestion_watermark(source_id,through_at,run_id) VALUES(:s,:b,:r) ON CONFLICT(source_id) DO UPDATE SET through_at=greatest(ops.ingestion_watermark.through_at,excluded.through_at),run_id=excluded.run_id"
                        ),
                        dict(s=source, b=end, r=run),
                    )
                if stats["inserted"] or stats["updated"]:
                    conn.execute(text("SELECT mart.refresh_affected(:s)"), {"s": source})
                conn.execute(
                    text(
                        "UPDATE ops.ingestion_run SET status=:status,finished_at=now(),received=:received,inserted=:inserted,updated=:updated,rejected=:rejected,duplicates=:duplicates WHERE id=:id"
                    ),
                    dict(stats, status=status, id=run),
                )
            log.info(json.dumps({"event": "ingestion", "source": source, "run_id": run, **stats}))
        except Exception as error:
            conn.rollback()
            with conn.begin():
                conn.execute(
                    text(
                        "UPDATE ops.ingestion_run SET status='failed',finished_at=now(),error=:e WHERE id=:id"
                    ),
                    dict(id=run, e=str(error)[:3000]),
                )
            log.exception("Ingestion failed: %s", source)
            raise
        finally:
            client.close()
            conn.execute(text("SELECT pg_advisory_unlock(hashtext(:s))"), {"s": source})
            conn.commit()
    return stats
