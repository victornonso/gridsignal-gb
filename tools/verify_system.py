"""Measure real API responses and persisted row counts; write reproducible verification evidence."""

import json
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from sqlalchemy import create_engine, text

from apps.api.app.config import settings
from apps.api.app.main import ROUTES


def main():
    report = {
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "endpoints": {},
        "counts": {},
        "performance": {},
    }
    with httpx.Client(base_url="http://127.0.0.1:8001/api/v1/", timeout=25) as client:
        params = {"start": "2026-10-01T00:00Z", "end": "2026-10-14T08:00Z", "limit": 500}
        for route in ROUTES:
            started = time.perf_counter()
            r = client.get(route, params=params)
            report["endpoints"][route] = {
                "status": r.status_code,
                "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                "rows": len(r.json().get("rows", [])),
            }
            if r.status_code != 200:
                print("FAIL", route, r.text[:300])
        for route in ["overview", "carbon/trend", "regions/ranking"]:
            durations = []
            for _ in range(20):
                started = time.perf_counter()
                r = client.get(route, params=params)
                r.raise_for_status()
                durations.append((time.perf_counter() - started) * 1000)
            report["performance"][route] = {
                "requests": 20,
                "p50_ms": round(statistics.median(durations), 2),
                "p95_ms": round(sorted(durations)[18], 2),
                "scope": "local HTTP, warm pool, loaded data",
            }
    with create_engine(settings.read_database_url).connect() as conn:
        for name in [
            "core.carbon_observation",
            "core.generation_share",
            "core.generation_outturn",
            "core.demand_observation",
            "core.carbon_revision",
            "ops.ingestion_run",
            "ops.quality_result",
        ]:
            report["counts"][name] = conn.execute(text(f"SELECT count(*) FROM {name}")).scalar()
        report["counts"]["raw.api_response"] = "Requires migration/writer role; checked separately."
        report["source_status"] = [
            dict(r) for r in conn.execute(text("SELECT * FROM mart.v_source_freshness")).mappings()
        ]
        report["query_plan"] = conn.execute(
            text(
                "EXPLAIN (ANALYZE,BUFFERS,FORMAT JSON) SELECT avg(actual) FROM core.carbon_observation WHERE region_id=0 AND period_start>='2026-10-01' AND period_start<'2026-10-14'"
            )
        ).scalar()
    path = Path("docs/verification.json")
    path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    failures = [k for k, v in report["endpoints"].items() if v["status"] != 200]
    print(
        json.dumps(
            {"failed_endpoints": failures, "counts": report["counts"], "performance": report["performance"]},
            indent=2,
        )
    )
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
