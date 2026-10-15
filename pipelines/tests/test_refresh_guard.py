from tools.refresh_guard import SOURCES, needs_refresh


def healthy():
    return [dict(id=source, collection_status="current", last_success_at="2026-10-15T11:00:00Z") for source in SOURCES]


def test_healthy_sources_do_not_repeat_collection():
    assert not needs_refresh(healthy())


def test_failed_or_overdue_sources_trigger_recovery():
    for status in ["failed", "overdue", "no_data"]:
        rows = healthy()
        rows[0]["collection_status"] = status
        assert needs_refresh(rows)


def test_missing_source_is_not_reported_as_healthy():
    assert needs_refresh(healthy()[:-1])


def test_upstream_delay_does_not_cause_repeated_collection():
    rows = healthy()
    rows[0]["collection_status"] = "source_delayed"
    assert not needs_refresh(rows)


def test_collection_already_in_progress_is_not_duplicated():
    rows = healthy()
    rows[0]["collection_status"] = "collecting"
    assert not needs_refresh(rows)
