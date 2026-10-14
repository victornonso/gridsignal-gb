import csv
import io
import json
import logging
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from apps.api.app.config import settings
from apps.api.app.db.session import read_engine
from apps.api.app.schemas.analytics import AnalyticsResult, Filters, Health, get_filters
from apps.api.app.services.analytics import QUERIES, query, rows_for

log = logging.getLogger("gridsignal.api")
logging.basicConfig(level=logging.INFO, format="%(message)s")


@asynccontextmanager
async def lifespan(app):
    yield
    read_engine.dispose()


app = FastAPI(
    title="GridSignal GB API",
    version="0.1.0",
    lifespan=lifespan,
    description="Official electricity observations analysed in PostgreSQL. All timestamps are offset-aware.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_methods=["GET"],
    allow_headers=["Accept", "Content-Type"],
)
requests = defaultdict(deque)


@app.middleware("http")
async def controls(request: Request, call_next):
    started = time.monotonic()
    key = request.client.host if request.client else "unknown"
    bucket = requests[key]
    while bucket and bucket[0] < started - 60:
        bucket.popleft()
    if len(bucket) >= settings.requests_per_minute:
        return JSONResponse(
            {"detail": "Request limit reached; retry shortly."},
            status_code=429,
            headers={"Retry-After": "60"},
        )
    bucket.append(started)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    log.info(
        json.dumps(
            {
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": round((time.monotonic() - started) * 1000, 2),
            }
        )
    )
    if len(requests) > 10000:
        for ip in list(requests):
            if not requests[ip] or requests[ip][-1] < started - 120:
                requests.pop(ip, None)
    return response


@app.exception_handler(SQLAlchemyError)
async def database_error(request, error):
    log.error("Database query failed", exc_info=error)
    return JSONResponse(
        {"detail": "Persisted analytics are temporarily unavailable. Please retry."}, status_code=503
    )


@app.get("/api/v1/health/live", response_model=Health)
def live():
    return {"status": "ok"}


@app.get("/api/v1/health/ready", response_model=Health)
def ready():
    with read_engine.connect() as conn:
        conn.execute(text("SELECT 1 FROM ops.data_source LIMIT 1"))
    return {"status": "ok", "database": "connected"}


ROUTES = [
    *QUERIES,
    "overview",
    "carbon/trend",
    "generation/trend",
    "generation/outturn",
    "demand/profile",
    "forecasts/comparison",
    "regions/trend",
    "regions/benchmark",
    "carbon/drilldown",
    "insights",
]


def endpoint(route):
    def handler(filters: Filters = Depends(get_filters)):
        return query(route, filters)

    handler.__name__ = route.replace("/", "_")
    return handler


for route in ROUTES:
    app.add_api_route(
        "/api/v1/" + route,
        endpoint(route),
        methods=["GET"],
        response_model=AnalyticsResult,
        tags=[route.split("/")[0]],
    )


@app.get("/api/v1/regions/{region_id}/performance", response_model=AnalyticsResult)
def regional_performance(region_id: int, filters: Filters = Depends(get_filters)):
    if not 1 <= region_id <= 14:
        raise HTTPException(422, "Select one of the 14 subnational regions")
    return query("carbon/trend", filters.model_copy(update={"region": region_id}))


@app.get("/api/v1/operations/ingestion-runs/{run_id}", response_model=AnalyticsResult)
def run_detail(run_id: int):
    with read_engine.connect() as conn:
        rows = [
            dict(r)
            for r in conn.execute(
                text("SELECT * FROM ops.ingestion_run WHERE id=:id"), {"id": run_id}
            ).mappings()
        ]
    if not rows:
        raise HTTPException(404, "Ingestion run not found")
    return {"rows": rows, "meta": {"run_id": run_id}}


@app.get("/api/v1/metadata/metrics", response_model=AnalyticsResult)
def metrics():
    return {
        "rows": [
            {
                "metric": "carbon_intensity",
                "unit": "gCO₂/kWh",
                "grain": "region × half hour",
                "aggregation": "Arithmetic mean over equal 30-minute intervals; nulls excluded",
                "source": "NESO Carbon Intensity",
                "limitation": "National estimated actual; regional forecast. Not total emissions.",
            },
            {
                "metric": "generation_share",
                "unit": "%",
                "grain": "region × half hour × fuel",
                "aggregation": "Mean of source-reported shares; not weighted by electricity consumption",
                "source": "NESO Generation Mix",
                "limitation": "Period average composition, not share of period energy.",
            },
            {
                "metric": "generation_outturn",
                "unit": "MW / MWh",
                "grain": "half hour × source fuel",
                "aggregation": "Duration-weighted average MW; energy is MW × valid interval hours",
                "source": "Elexon FUELHH",
                "limitation": "Metered generation; embedded coverage incomplete; interconnectors can be signed.",
            },
            {
                "metric": "national_demand",
                "unit": "MW",
                "grain": "settlement date × period",
                "aggregation": "Mean / min / max of A-indicated rows; ND and TSD separate",
                "source": "NESO Demand Data Update",
                "limitation": "Periodically published outturn; F rows excluded.",
            },
            {
                "metric": "forecast_errors",
                "unit": "gCO₂/kWh",
                "grain": "paired national half hour",
                "aggregation": "MAE, sqrt(mean squared error), forecast minus actual bias; null pairs excluded",
                "source": "NESO Carbon Intensity",
                "limitation": "Published contemporaneous forecast-estimate differences; issue-time versions unavailable.",
            },
            {
                "metric": "completeness",
                "unit": "%",
                "grain": "region × reporting period",
                "aggregation": "Usable intervals / expected elapsed calendar intervals × 100",
                "source": "PostgreSQL reporting calendar",
                "limitation": "British days contain 46, 48 or 50 intervals.",
            },
        ],
        "meta": {},
    }


@app.get("/api/v1/export/{dataset}")
def export(dataset: str, filters: Filters = Depends(get_filters)):
    allowed = {
        "carbon": "carbon/drilldown",
        "generation": "generation/trend",
        "outturn": "generation/outturn",
        "demand": "demand/profile",
        "regions": "regions/ranking",
        "forecasts": "forecasts/comparison",
        "operations": "operations/ingestion-runs",
        "quality": "operations/quality",
    }
    if dataset not in allowed:
        raise HTTPException(404, "Unknown export dataset")

    def stream():
        current = filters.model_copy(update={"limit": 10000, "offset": 0})
        # One repeatable-read snapshot keeps paged exports consistent during ingestion.
        with read_engine.connect().execution_options(isolation_level="REPEATABLE READ") as conn:
            first = True
            while True:
                rows = rows_for(conn, allowed[dataset], current)
                if not rows:
                    break
                buffer = io.StringIO()
                writer = csv.DictWriter(buffer, fieldnames=rows[0].keys())
                if first:
                    writer.writeheader()
                    first = False
                for row in rows:
                    writer.writerow(
                        {
                            k: ("'" + v if isinstance(v, str) and v.startswith(("=", "+", "-", "@")) else v)
                            for k, v in row.items()
                        }
                    )
                yield buffer.getvalue()
                # Aggregate queries without pagination are single-page results.
                if len(rows) < 10000 or allowed[dataset] == "regions/ranking":
                    break
                current = current.model_copy(update={"offset": current.offset + 10000})

    return StreamingResponse(
        stream(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="gridsignal-{dataset}.csv"',
            "X-Export-Scope": "all-filtered-results",
            "X-Export-Page-Size": "10000",
        },
    )
