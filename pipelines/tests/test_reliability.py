from datetime import datetime, timezone

import httpx
import pytest
from tenacity import stop_after_attempt, wait_none

from pipelines.clients.official import OfficialClient
from pipelines.ingestion.runner import normalise


def test_timeout_is_retried_without_mock_fallback(monkeypatch):
    client = OfficialClient()
    calls = []

    def failed(request):
        calls.append(request.url)
        raise httpx.ReadTimeout("isolated test timeout", request=request)

    client.client.close()
    client.client = httpx.Client(transport=httpx.MockTransport(failed))
    monkeypatch.setattr("pipelines.clients.official.time.sleep", lambda _: None)
    with pytest.raises(httpx.ReadTimeout):
        OfficialClient.get.retry_with(stop=stop_after_attempt(2), wait=wait_none())(
            client, "https://test.invalid/source"
        )
    assert len(calls) == 2
    client.close()


def test_source_error_is_not_successful_data():
    client = OfficialClient()
    client.client.close()
    client.client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={"success": False, "error": "source unavailable"})
        )
    )
    with pytest.raises(ValueError, match="Source returned error"):
        client.get("https://test.invalid/source")
    client.close()


def test_total_share_drift_quarantines_interval():
    a = datetime(2026, 10, 1, tzinfo=timezone.utc)
    body = {
        "data": [
            {
                "from": "2026-10-01T00:00Z",
                "to": "2026-10-01T00:30Z",
                "generationmix": [{"fuel": "wind", "perc": 30}],
            }
        ]
    }
    rows = list(normalise("mix", body, a, a))
    assert rows[0][0] == "quarantine"


def test_unknown_elexon_fuel_is_not_silently_classified():
    a = datetime(2026, 10, 1, tzinfo=timezone.utc)
    rows = list(
        normalise(
            "elexon",
            {"data": [{"startTime": "2026-10-01T00:00Z", "fuelType": "UNKNOWN_NEW_FUEL", "generation": 20}]},
            a,
            a,
        )
    )
    assert rows[0][0] == "quarantine"
