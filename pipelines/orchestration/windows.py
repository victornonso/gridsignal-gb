from datetime import datetime, timedelta


def extraction_windows(source: str, end: datetime, watermark: datetime | None):
    """Bounded reconciliation/catch-up windows; resume from persisted progress after outages."""
    end = end.replace(minute=end.minute // 30 * 30, second=0, microsecond=0)
    lookback = timedelta(days=32 if source == "demand" else 2)
    start = end - lookback
    if source != "factors" and watermark is not None and watermark < start:
        start = watermark - timedelta(hours=1)
        start = start.replace(minute=start.minute // 30 * 30, second=0, microsecond=0)
        # A long outage is caught up across successive runs, without one unbounded job.
        end = min(end, start + timedelta(days=7))
    if source in {"demand", "factors"}:
        return [(start, end)]
    windows = []
    while start < end:
        stop = min(start + timedelta(days=1), end)
        windows.append((start, stop))
        start = stop
    return windows
