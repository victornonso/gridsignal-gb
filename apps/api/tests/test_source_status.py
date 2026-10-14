from datetime import datetime, timedelta, timezone

import pytest

from apps.api.app.config import Settings
from apps.api.app.services.source_status import classify_source

NOW = datetime(2026, 10, 14, 16, tzinfo=timezone.utc)


def source():
    return dict(id="carbon", cadence_minutes=30, stale_minutes=120, stale=True,
                observed_at=NOW.replace(hour=13), last_success_at=NOW.replace(hour=13, minute=55),
                last_run_status="success", last_run_started_at=NOW.replace(hour=13, minute=54),
                )


def test_old_observations_between_hosted_runs_are_awaiting_not_failed():
    result = classify_source(source(), NOW, interval_hours=6)
    assert result["collection_status"] == "awaiting_update"
    assert result["stale"] is True
    assert result["next_scheduled_at"] == NOW.replace(hour=18, minute=23)


@pytest.mark.parametrize("time,state", [("19:22", "awaiting_update"), ("19:24", "overdue")])
def test_scheduled_job_has_bounded_queue_grace(time, state):
    hour, minute = map(int, time.split(":"))
    result = classify_source(source(), NOW.replace(hour=hour, minute=minute), interval_hours=6)
    assert result["collection_status"] == state
    assert result["collection_deadline_at"] == NOW.replace(hour=19, minute=23)


@pytest.mark.parametrize("status", ["failed", "partial"])
def test_latest_failed_attempt_is_not_hidden_by_schedule(status):
    row = source()
    row.update(last_run_status=status, last_run_started_at=NOW - timedelta(minutes=5))
    assert classify_source(row, NOW, 6)["collection_status"] == "failed"


def test_old_failure_does_not_override_a_later_success():
    row = source()
    row.update(last_run_status="failed", last_run_started_at=NOW.replace(hour=12))
    assert classify_source(row, NOW, 6)["collection_status"] == "awaiting_update"


@pytest.mark.parametrize("age,state", [(5, "collecting"), (16, "overdue")])
def test_running_attempt_has_a_bounded_lifetime(age, state):
    row = source()
    row.update(last_run_status="running", last_run_started_at=NOW - timedelta(minutes=age))
    assert classify_source(row, NOW, 6)["collection_status"] == state


def test_recent_collection_with_old_upstream_data_remains_a_warning():
    row = source()
    row.update(last_success_at=NOW - timedelta(minutes=1), last_run_started_at=NOW - timedelta(minutes=2))
    assert classify_source(row, NOW, 6)["collection_status"] == "source_delayed"


def test_no_success_or_observations_is_not_presented_as_normal_waiting():
    row = source()
    row.update(last_success_at=None, observed_at=None, last_run_started_at=None, last_run_status=None)
    assert classify_source(row, NOW, 6)["collection_status"] == "no_data"


def test_pre_midnight_slot_uses_previous_utc_day():
    now = NOW.replace(hour=0, minute=10)
    row = source()
    row.update(last_success_at=now - timedelta(hours=4), observed_at=now - timedelta(hours=4, minutes=30),
               last_run_started_at=now - timedelta(hours=4, minutes=1))
    result = classify_source(row, now, 6)
    assert result["collection_status"] == "awaiting_update"
    assert result["next_scheduled_at"] == now.replace(minute=23)


def test_local_worker_uses_source_cadence_instead_of_hosted_cron():
    assert classify_source(source(), NOW)["collection_status"] == "overdue"


def test_fresh_observations_and_successful_collection_are_current():
    row = source()
    row["stale"] = False
    assert classify_source(row, NOW, 6)["collection_status"] == "current"


@pytest.mark.parametrize("value", ["0", "6"])
def test_collection_interval_accepts_real_environment_strings(monkeypatch, value):
    monkeypatch.setenv("COLLECTION_INTERVAL_HOURS", value)
    assert Settings(_env_file=None).collection_interval_hours == int(value)


def test_collection_interval_rejects_an_unrepresentable_utc_schedule():
    with pytest.raises(ValueError):
        Settings(_env_file=None, collection_interval_hours=5)
