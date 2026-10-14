"""Verify anonymous deployed analytics and actual hosted PostgreSQL data."""

import json
from datetime import datetime, timezone
from pathlib import Path

import httpx
import psycopg
from psycopg import sql

from apps.api.app.main import ROUTES


def main():
    root = Path(__file__).resolve().parents[1]
    config = json.loads((root / ".local/hosted.json").read_text())
    report = {"verified_at": datetime.now(timezone.utc).isoformat(), "endpoints": {}, "counts": {}}
    with httpx.Client(timeout=90) as client:
        response = client.get("https://gridsignal-gb.vercel.app/")
        response.raise_for_status()
        assert "GridSignal" in response.text
        report["anonymous_dashboard"] = response.status_code
        response = client.get("https://gridsignal-api.onrender.com/api/v1/health/ready")
        response.raise_for_status()
        report["api_readiness"] = response.status_code
        params = {"start": "2026-10-07T00:00Z", "end": "2026-10-14T00:00Z", "limit": 500}
        for route in ROUTES:
            response = client.get("https://gridsignal-api.onrender.com/api/v1/" + route, params=params)
            response.raise_for_status()
            report["endpoints"][route] = {"status": response.status_code,
                                           "rows": len(response.json().get("rows", []))}
        response = client.options("https://gridsignal-api.onrender.com/api/v1/overview", headers={
            "Origin": "https://gridsignal-gb.vercel.app", "Access-Control-Request-Method": "GET"})
        assert response.headers.get("access-control-allow-origin") == "https://gridsignal-gb.vercel.app"
        report["cors"] = "verified"
    with psycopg.connect(config["database_url"].replace("postgresql+psycopg://", "postgresql://", 1)) as conn:
        conn.execute("SET TRANSACTION READ ONLY")
        for name in ["core.carbon_observation", "core.generation_share", "core.generation_outturn",
                     "core.demand_observation", "raw.api_response", "raw.quarantine"]:
            report["counts"][name] = conn.execute(sql.SQL("SELECT count(*) FROM {}").format(
                sql.Identifier(*name.split(".")))).fetchone()[0]
        report["database_bytes"] = conn.execute("SELECT pg_database_size(current_database())").fetchone()[0]
        report["successful_sources"] = [row[0] for row in conn.execute(
            "SELECT DISTINCT source_id FROM ops.ingestion_run WHERE status='success' ORDER BY source_id")]
    assert len(report["successful_sources"]) == 6
    assert all(report["counts"][name] > 0 for name in report["counts"] if name != "raw.quarantine")
    (root / "docs/hosted-verification.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({key: value for key, value in report.items() if key != "endpoints"}, indent=2))
    print("Verified analytical routes:", len(report["endpoints"]))


if __name__ == "__main__":
    main()
