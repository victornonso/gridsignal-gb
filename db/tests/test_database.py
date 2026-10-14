import os
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from apps.api.app.services.analytics import QUERIES
from pipelines.ingestion.runner import upsert, upsert_batch
from pipelines.transformations.calendar import calendar_rows

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DB_TESTS") != "1", reason="Explicit isolated transactional DB integration tests"
)


@pytest.fixture
def connection(isolated_database):
    engine = create_engine(isolated_database["migration"])
    with engine.connect() as conn:
        transaction = conn.begin()
        yield conn
        transaction.rollback()
    engine.dispose()


def make_lineage(conn):
    a = datetime(1990, 1, 1, tzinfo=timezone.utc)
    run = conn.execute(
        text(
            "INSERT INTO ops.ingestion_run(source_id,window_start,window_end) VALUES('carbon',:a,:b) RETURNING id"
        ),
        {"a": a, "b": a + timedelta(days=1)},
    ).scalar_one()
    raw = conn.execute(
        text(
            "INSERT INTO raw.api_response(run_id,source_id,url,status_code,body,body_hash) VALUES(:r,'carbon','test://isolated-fixture',200,'{}','fixture') RETURNING id"
        ),
        {"r": run},
    ).scalar_one()
    return a, run, raw


def test_idempotent_upsert_and_revision_tracking(connection):
    a, run, raw = make_lineage(connection)
    record = dict(
        region_id=0,
        period_start=a,
        period_end=a + timedelta(minutes=30),
        actual=100,
        forecast=110,
        intensity_index="moderate",
        source_id="carbon",
        run_id=run,
        response_id=raw,
        record_hash="version-1",
    )
    assert upsert(connection, "carbon_observation", record, ["region_id", "period_start"]) == "inserted"
    assert upsert(connection, "carbon_observation", record, ["region_id", "period_start"]) == "duplicates"
    record.update(actual=105, record_hash="version-2")
    assert upsert(connection, "carbon_observation", record, ["region_id", "period_start"]) == "updated"
    row = connection.execute(
        text("SELECT old_value->>'actual',new_value->>'actual' FROM core.carbon_revision WHERE run_id=:r"),
        {"r": run},
    ).one()
    assert row == ("100", "105")


def test_batch_preserves_repeated_key_revisions_and_duplicate_counts(connection):
    a, run, raw = make_lineage(connection)
    base = dict(region_id=0, period_start=a, period_end=a + timedelta(minutes=30),
                actual=100, forecast=110, source_id="carbon", run_id=run,
                response_id=raw, record_hash="first")
    records = [dict(base), dict(base, actual=105, record_hash="second"),
               dict(base, actual=105, record_hash="second"),
               dict(base, period_start=a + timedelta(minutes=30), period_end=a + timedelta(hours=1))]
    assert upsert_batch(connection, "carbon_observation", records, ["region_id", "period_start"]) == {
        "inserted": 2, "updated": 1, "duplicates": 1,
    }
    assert connection.execute(text("SELECT count(*) FROM core.carbon_revision WHERE run_id=:r"),
                              {"r": run}).scalar_one() == 1


def test_forecast_metrics_exclude_null_pairs(connection):
    a, run, raw = make_lineage(connection)
    for index, (actual, forecast) in enumerate([(100, 110), (100, 80), (None, 150)]):
        record = dict(
            region_id=0,
            period_start=a + timedelta(minutes=30 * index),
            period_end=a + timedelta(minutes=30 * (index + 1)),
            actual=actual,
            forecast=forecast,
            source_id="carbon",
            run_id=run,
            response_id=raw,
            record_hash=str(index),
        )
        upsert(connection, "carbon_observation", record, ["region_id", "period_start"])
    row = (
        connection.execute(text(QUERIES["forecasts/errors"]), {"start": a, "end": a + timedelta(days=1)})
        .mappings()
        .one()
    )
    assert float(row["mae"]) == 15
    assert float(row["bias"]) == -5
    assert float(row["rmse"]) == pytest.approx(250**0.5)
    assert row["paired_observations"] == 2


def test_constraints_reject_invalid_carbon(connection):
    a, run, raw = make_lineage(connection)
    with pytest.raises(DBAPIError), connection.begin_nested():
        upsert(
            connection,
            "carbon_observation",
            dict(
                region_id=0,
                period_start=a,
                period_end=a + timedelta(minutes=30),
                actual=-1,
                forecast=10,
                source_id="carbon",
                run_id=run,
                response_id=raw,
                record_hash="bad",
            ),
            ["region_id", "period_start"],
        )


def test_reader_cannot_write_or_read_raw(isolated_database):
    engine = create_engine(isolated_database["reader"])
    with engine.connect() as conn:
        assert not conn.execute(
            text("SELECT has_table_privilege(current_user,'core.carbon_observation','INSERT')")
        ).scalar()
        assert not conn.execute(text("SELECT has_schema_privilege(current_user,'raw','USAGE')")).scalar()
    engine.dispose()


def test_completeness_counts_missing_not_just_received(connection):
    a, run, raw = make_lineage(connection)
    for row in list(calendar_rows(a, a + timedelta(hours=1))):
        connection.execute(
            text(
                "INSERT INTO core.reporting_calendar(period_start,period_end,settlement_date,settlement_period,local_hour,weekday,weekend) VALUES(:period_start,:period_end,:settlement_date,:settlement_period,:local_hour,:weekday,:weekend) ON CONFLICT DO NOTHING"
            ),
            row,
        )
    record = dict(
        region_id=0,
        period_start=a,
        period_end=a + timedelta(minutes=30),
        actual=100,
        forecast=110,
        source_id="carbon",
        run_id=run,
        response_id=raw,
        record_hash="only-one",
    )
    upsert(connection, "carbon_observation", record, ["region_id", "period_start"])
    row = connection.execute(
        text(
            "SELECT expected,usable,completeness FROM mart.v_data_completeness WHERE day='1990-01-01' AND region_id=0"
        )
    ).one()
    assert row == (2, 1, 50)


def test_failed_ingestion_keeps_raw_and_does_not_advance_watermark(isolated_database, monkeypatch):
    from pipelines.clients.official import OfficialClient
    from pipelines.ingestion import runner

    writer = create_engine(isolated_database["writer"])
    monkeypatch.setattr(runner, "engine", writer)
    # Reflect each isolated database independently.
    monkeypatch.setattr(runner, "metadata", __import__("sqlalchemy").MetaData())

    def interrupted(self, source, start, end):
        yield "https://test.invalid/isolated", {"data": []}, 200
        raise TimeoutError("isolated interrupted ingestion")

    monkeypatch.setattr(OfficialClient, "requests", interrupted)
    a = datetime(2026, 1, 1, tzinfo=timezone.utc)
    with pytest.raises(TimeoutError):
        runner.ingest("carbon", a, a + timedelta(days=1))
    with writer.connect() as conn:
        assert (
            conn.execute(
                text("SELECT count(*) FROM raw.api_response WHERE url='https://test.invalid/isolated'")
            ).scalar()
            == 1
        )
        assert (
            conn.execute(text("SELECT status FROM ops.ingestion_run ORDER BY id DESC LIMIT 1")).scalar()
            == "failed"
        )
        assert (
            conn.execute(
                text("SELECT count(*) FROM ops.ingestion_watermark WHERE source_id='carbon'")
            ).scalar()
            == 0
        )
        assert conn.execute(text("SELECT count(*) FROM core.carbon_observation")).scalar() == 0
    writer.dispose()


def test_source_lock_skips_overlapping_ingestion(isolated_database, monkeypatch):
    from pipelines.ingestion import runner

    writer = create_engine(isolated_database["writer"])
    admin = create_engine(isolated_database["migration"])
    monkeypatch.setattr(runner, "engine", writer)
    a = datetime(2026, 1, 1, tzinfo=timezone.utc)
    with admin.connect() as conn:
        conn.execute(text("SELECT pg_advisory_lock(hashtext('carbon'))"))
        conn.commit()
        try:
            result = runner.ingest("carbon", a, a + timedelta(days=1))
            assert result["received"] == 0
            assert (
                conn.execute(text("SELECT status FROM ops.ingestion_run ORDER BY id DESC LIMIT 1")).scalar()
                == "skipped"
            )
        finally:
            conn.execute(text("SELECT pg_advisory_unlock(hashtext('carbon'))"))
            conn.commit()
    writer.dispose()
    admin.dispose()


def test_older_elexon_publication_cannot_replace_newer_outturn(connection):
    a, run, raw = make_lineage(connection)
    row = dict(
        period_start=a,
        period_end=a + timedelta(minutes=30),
        fuel_id="gas",
        source_fuel="CCGT",
        power_mw=200,
        published_at=a + timedelta(hours=2),
        source_id="elexon",
        run_id=run,
        response_id=raw,
        record_hash="newer",
    )
    assert (
        upsert(connection, "generation_outturn", row, ["period_start", "source_fuel", "source_id"])
        == "inserted"
    )
    row.update(power_mw=100, published_at=a + timedelta(hours=1), record_hash="older")
    assert (
        upsert(connection, "generation_outturn", row, ["period_start", "source_fuel", "source_id"])
        == "duplicates"
    )
    assert (
        connection.execute(
            text("SELECT power_mw FROM core.generation_outturn WHERE period_start=:a AND source_fuel='CCGT'"),
            {"a": a},
        ).scalar()
        == 200
    )


def test_rolling_days_across_bst_end_do_not_depend_on_server_timezone(connection):
    from zoneinfo import ZoneInfo

    from apps.api.app.schemas.analytics import Filters
    from apps.api.app.services.analytics import dynamic_query

    _, run, raw = make_lineage(connection)
    london = ZoneInfo("Europe/London")
    a = datetime(2025, 10, 22, tzinfo=london)
    b = datetime(2025, 10, 30, tzinfo=london)
    connection.execute(text("SET LOCAL TIME ZONE 'UTC'"))
    connection.execute(text("SELECT core.extend_calendar(:a,:b)"), {"a": a, "b": b})
    for day in range(8):
        start = a + timedelta(days=day)
        row = dict(
            region_id=0,
            period_start=start,
            period_end=start + timedelta(minutes=30),
            actual=day,
            forecast=day,
            source_id="carbon",
            run_id=run,
            response_id=raw,
            record_hash=str(day),
        )
        upsert(connection, "carbon_observation", row, ["region_id", "period_start"])
    filters = Filters(start=a, end=b, granularity="day")
    rows = (
        connection.execute(text(dynamic_query("carbon/trend", filters)), filters.model_dump())
        .mappings()
        .all()
    )
    assert float(rows[-2]["rolling_7d"]) == 3.0
    assert float(rows[-1]["rolling_7d"]) == 4.0


def test_completeness_obeys_exclusive_partial_day_end(connection):
    a, run, raw = make_lineage(connection)
    for row in calendar_rows(a, a + timedelta(hours=1)):
        connection.execute(
            text(
                "INSERT INTO core.reporting_calendar(period_start,period_end,settlement_date,settlement_period,local_hour,weekday,weekend) VALUES(:period_start,:period_end,:settlement_date,:settlement_period,:local_hour,:weekday,:weekend)"
            ),
            row,
        )
    values = dict(
        region_id=0,
        period_start=a,
        period_end=a + timedelta(minutes=30),
        actual=100,
        forecast=110,
        source_id="carbon",
        run_id=run,
        response_id=raw,
        record_hash="coverage",
    )
    upsert(connection, "carbon_observation", values, ["region_id", "period_start"])
    rows = (
        connection.execute(
            text(QUERIES["operations/completeness"]),
            {"start": a, "end": a + timedelta(minutes=30), "region": 0},
        )
        .mappings()
        .all()
    )
    assert len(rows) == 1
    assert rows[0]["expected"] == 1 and rows[0]["usable"] == 1
    assert float(rows[0]["completeness"]) == 100


def test_generation_statistics_exclude_previous_comparison_period(connection):
    a, run, raw = make_lineage(connection)
    for start, share in [(a - timedelta(minutes=30), 80), (a, 20)]:
        row = dict(
            region_id=0,
            period_start=start,
            period_end=start + timedelta(minutes=30),
            fuel_id="wind",
            source_fuel="wind",
            share=share,
            source_id="mix",
            run_id=run,
            response_id=raw,
            record_hash=str(share),
        )
        upsert(connection, "generation_share", row, ["region_id", "period_start", "fuel_id", "source_id"])
    row = (
        connection.execute(
            text(QUERIES["generation/volatility"]),
            {"start": a, "end": a + timedelta(minutes=30), "region": 0, "fuel": None},
        )
        .mappings()
        .one()
    )
    assert float(row["mean_share"]) == 20
    assert float(row["minimum"]) == 20 and float(row["maximum"]) == 20
    assert float(row["change_pp"]) == -60
