from fastapi.testclient import TestClient

from apps.api.app.main import app

client = TestClient(app, raise_server_exceptions=False)


def test_liveness():
    assert client.get("/api/v1/health/live").json()["status"] == "ok"


def test_bounded_filter_validation():
    assert client.get("/api/v1/carbon/trend?region=999").status_code == 422
    assert client.get("/api/v1/carbon/trend?start=2020-01-01T00:00Z&end=2026-01-01T00:00Z").status_code == 422
    assert (
        client.get("/api/v1/carbon/trend?start=2026-10-01T00:00:00&end=2026-10-02T00:00:00").status_code
        == 422
    )
    assert client.get("/api/v1/carbon/trend?regions=1,99").status_code == 422
    assert client.get("/api/v1/carbon/trend?sort=DROP%20TABLE").status_code == 422


def test_no_public_maintenance_routes():
    assert client.post("/api/v1/ingest").status_code == 404
    assert client.post("/api/v1/overview").status_code == 405


def test_metric_metadata_defines_limits():
    r = client.get("/api/v1/metadata/metrics")
    assert r.status_code == 200
    assert all("limitation" in row for row in r.json()["rows"])


def test_openapi_contains_required_routes():
    paths = client.get("/openapi.json").json()["paths"]
    for route in [
        "overview",
        "carbon/latest",
        "generation/outturn",
        "demand/summary",
        "regions/{region_id}/performance",
        "operations/quality",
        "forecasts/errors",
    ]:
        assert "/api/v1/" + route in paths
