from datetime import datetime, timedelta, timezone

from pipelines.orchestration.windows import extraction_windows


def test_worker_uses_watermark_to_catch_up_after_long_outage():
    end = datetime(2026, 10, 14, 10, 17, tzinfo=timezone.utc)
    watermark = end - timedelta(days=15)
    windows = extraction_windows("carbon", end, watermark)
    assert windows[0][0] < watermark
    assert windows[-1][1] < end
    assert all((b - a) <= timedelta(days=1) for a, b in windows)
    assert sum((b - a for a, b in windows), timedelta()) == timedelta(days=7)


def test_recent_source_reconciles_two_days_on_half_hour_boundaries():
    end = datetime(2026, 10, 14, 10, 17, tzinfo=timezone.utc)
    windows = extraction_windows("regional", end, end - timedelta(hours=1))
    assert windows[0][0] == datetime(2026, 10, 12, 10, tzinfo=timezone.utc)
    assert windows[-1][1] == datetime(2026, 10, 14, 10, tzinfo=timezone.utc)
