"""Separate upstream observation age from collection execution and its schedule."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from apps.api.app.config import settings


def classify_source(source, now, interval_hours=0, minute=23, grace_minutes=60):
    now = now.astimezone(timezone.utc)
    success = source.get("last_success_at")
    observed = source.get("observed_at")
    started = source.get("last_run_started_at")
    run_status = source.get("last_run_status")
    if interval_hours:
        day = now.replace(hour=0, minute=minute, second=0, microsecond=0)
        period = timedelta(hours=interval_hours)
        due = day + ((now - day) // period) * period
        next_due = due + period
        deadline = due + timedelta(minutes=grace_minutes)
        overdue = success is None or success < due
        if overdue:
            next_due = due
    else:
        period = timedelta(minutes=source["cadence_minutes"])
        next_due = success + period if success else None
        deadline = next_due + timedelta(minutes=grace_minutes) if next_due else None
        overdue = deadline is not None and now > deadline
    latest_attempt = started is not None and (success is None or started > success)
    if latest_attempt and run_status in {"failed", "partial"}:
        state = "failed"
    elif latest_attempt and run_status == "running":
        state = "overdue" if now - started > timedelta(minutes=15) else "collecting"
    elif not success or not observed:
        state = "no_data"
    elif overdue and deadline and now > deadline:
        state = "overdue"
    elif source["stale"] and success - observed > timedelta(minutes=source["stale_minutes"]):
        state = "source_delayed"
    else:
        state = "awaiting_update" if source["stale"] else "current"
    return dict(source, collection_status=state, next_scheduled_at=next_due,
                collection_deadline_at=deadline)


def source_statuses(conn):
    rows = conn.execute(text("""
        SELECT s.*,r.status AS last_run_status,r.started_at AS last_run_started_at,
               r.finished_at AS last_run_finished_at
        FROM mart.v_source_freshness s
        LEFT JOIN LATERAL (
          SELECT status,started_at,finished_at FROM ops.ingestion_run
          WHERE source_id=s.id AND status<>'skipped' ORDER BY started_at DESC,id DESC LIMIT 1
        ) r ON true ORDER BY s.id
    """)).mappings()
    now = datetime.now(timezone.utc)
    return [classify_source(dict(row), now, settings.collection_interval_hours,
                            settings.collection_schedule_minute, settings.collection_grace_minutes)
            for row in rows]
