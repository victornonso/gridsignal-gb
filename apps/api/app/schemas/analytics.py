from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from fastapi import HTTPException, Query
from pydantic import BaseModel, Field


class Filters(BaseModel):
    start: datetime
    end: datetime
    region: int = 0
    fuel: str | None = None
    granularity: Literal["half-hour", "hour", "day"] = "day"
    compare_regions: list[int] = Field(default_factory=list)
    limit: int = 500
    offset: int = 0
    sort: Literal["asc", "desc"] = "asc"


def get_filters(
    start: datetime | None = None,
    end: datetime | None = None,
    region: int = Query(0, ge=0, le=17),
    fuel: str | None = Query(None, max_length=40),
    granularity: Literal["half-hour", "hour", "day"] = "day",
    regions: str = Query("", max_length=80),
    limit: int = Query(500, ge=1, le=10000),
    offset: int = Query(0, ge=0, le=100000),
    sort: Literal["asc", "desc"] = "asc",
):
    b = end or datetime.now(timezone.utc)
    a = start or b - timedelta(days=7)
    if not a.tzinfo or not b.tzinfo:
        raise HTTPException(422, "Dates must include a UTC offset")
    if not a < b or (b - a).days > 366:
        raise HTTPException(422, "Select a positive range of at most 366 days")
    try:
        ids = [int(x) for x in regions.split(",") if x]
        if len(ids) > 14 or any(x < 1 or x > 14 for x in ids):
            raise ValueError()
    except ValueError:
        raise HTTPException(422, "Compare up to 14 subnational region IDs (1–14)") from None
    return Filters(
        start=a,
        end=b,
        region=region,
        fuel=fuel,
        granularity=granularity,
        compare_regions=ids,
        limit=limit,
        offset=offset,
        sort=sort,
    )


class AnalyticsResult(BaseModel):
    rows: list[dict[str, Any]]
    meta: dict[str, Any]


class Health(BaseModel):
    status: str
    database: str | None = None
