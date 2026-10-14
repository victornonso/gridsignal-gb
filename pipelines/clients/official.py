import time
from datetime import timedelta
from uuid import UUID

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from apps.api.app.config import settings


class OfficialClient:
    def __init__(self):
        self.client = httpx.Client(
            timeout=45,
            headers={"Accept": "application/json", "User-Agent": "GridSignal/0.1 (electricity analytics)"},
            follow_redirects=True,
        )
        self.last_request = 0.0

    @retry(
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        retry=retry_if_exception_type((httpx.TransportError, httpx.HTTPStatusError)),
        reraise=True,
    )
    def get(self, url, params=None):
        time.sleep(max(0, 1.05 - (time.monotonic() - self.last_request)))
        response = self.client.get(url, params=params)
        self.last_request = time.monotonic()
        if response.status_code == 429:
            time.sleep(min(float(response.headers.get("Retry-After", "5")), 60))
        response.raise_for_status()
        body = response.json()
        if body.get("success") is False or "error" in body:
            raise ValueError(f"Source returned error: {body.get('error')}")
        return str(response.url), body, response.status_code

    def requests(self, source, start, end):
        a = start.strftime("%Y-%m-%dT%H:%MZ")
        b = end.strftime("%Y-%m-%dT%H:%MZ")
        carbon = "https://api.carbonintensity.org.uk"
        routes = {
            "carbon": f"/intensity/{a}/{b}",
            "regional": f"/regional/intensity/{a}/{b}",
            "mix": f"/generation/{a}/{b}",
            "factors": "/intensity/factors",
        }
        if source in routes:
            yield self.get(carbon + routes[source])
        elif source == "elexon":
            yield self.get(
                "https://data.elexon.co.uk/bmrs/api/v1/datasets/FUELHH",
                {"publishDateTimeFrom": a, "publishDateTimeTo": b, "format": "json"},
            )
        elif source == "demand":
            metadata = self.get(
                "https://api.neso.energy/api/3/action/package_show", {"id": "historic-demand-data"}
            )
            yield metadata
            for resource in metadata[1]["result"]["resources"]:
                name = resource.get("name", "")
                year = name.rsplit(" ", 1)[-1]
                if not year.isdigit() or not start.year <= int(year) <= end.year:
                    continue
                resource_id = str(UUID(resource["id"]))
                offset = 0
                while True:
                    # Only trusted metadata UUIDs and validated ISO dates enter source SQL.
                    query = (
                        f'SELECT * FROM "{resource_id}" WHERE "SETTLEMENT_DATE">=\'{(start - timedelta(days=1)).date().isoformat()}\' '
                        f"AND \"SETTLEMENT_DATE\"<='{(end + timedelta(days=1)).date().isoformat()}' "
                        f'ORDER BY "SETTLEMENT_DATE","SETTLEMENT_PERIOD" LIMIT 1000 OFFSET {offset}'
                    )
                    result = self.get(
                        "https://api.neso.energy/api/3/action/datastore_search_sql", {"sql": query}
                    )
                    yield result
                    rows = result[1]["result"]["records"]
                    offset += len(rows)
                    if len(rows) < 1000:
                        break
            offset = 0
            while True:
                result = self.get(
                    "https://api.neso.energy/api/3/action/datastore_search",
                    {
                        "resource_id": settings.neso_resource_id,
                        "limit": 1000,
                        "offset": offset,
                        "sort": "SETTLEMENT_DATE asc, SETTLEMENT_PERIOD asc",
                    },
                )
                yield result
                rows = result[1]["result"]["records"]
                offset += len(rows)
                if not rows or offset >= result[1]["result"].get("total", offset):
                    break
        else:
            raise ValueError("Unknown source")

    def close(self):
        self.client.close()
