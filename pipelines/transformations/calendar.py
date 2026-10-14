from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

LONDON = ZoneInfo("Europe/London")


def settlement_start(day: date, period: int) -> datetime:
    start = datetime.combine(day, time(), LONDON).astimezone(timezone.utc)
    end = datetime.combine(day + timedelta(days=1), time(), LONDON).astimezone(timezone.utc)
    if not 1 <= period <= int((end - start).total_seconds() / 1800):
        raise ValueError("Settlement period does not exist on this British settlement date")
    return start + timedelta(minutes=30 * (period - 1))


def calendar_rows(start: datetime, end: datetime):
    cursor = start.astimezone(timezone.utc).replace(second=0, microsecond=0)
    cursor = cursor.replace(minute=cursor.minute // 30 * 30)
    while cursor < end:
        local = cursor.astimezone(LONDON)
        midnight = datetime.combine(local.date(), time(), LONDON).astimezone(timezone.utc)
        yield dict(
            period_start=cursor,
            period_end=cursor + timedelta(minutes=30),
            settlement_date=local.date(),
            settlement_period=int((cursor - midnight).total_seconds() / 1800) + 1,
            local_hour=local.hour,
            weekday=local.isoweekday(),
            weekend=local.isoweekday() > 5,
        )
        cursor += timedelta(minutes=30)
