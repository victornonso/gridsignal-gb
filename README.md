# GridSignal

**Great Britain electricity intelligence.**

[Live workspace](https://gridsignal-gb.vercel.app/) · [API documentation](https://gridsignal-api.onrender.com/docs) · [Victor Okeke](https://victorokeke.co.uk/)

GridSignal connects official electricity-system observations to a seven-screen analytical workspace: carbon intensity, generation composition, metered outturn, national/transmission demand, regional comparisons, forecast differences and data operations.

The project combines reproducible data engineering with PostgreSQL analytics, a read-only FastAPI service and a bespoke Next.js/ECharts interface. Every displayed production metric comes from persisted official-source observations.

![GridSignal overview](docs/screenshots/overview-desktop.png)

## What you can investigate

- How carbon intensity changes over time, by British hour, weekday and region.
- Which fuels contribute to published generation shares and metered MW outturn.
- How national and transmission demand differ across periods.
- How published national forecasts differ from estimated actual intensity.
- Whether the underlying sources are fresh, complete and consistently ingested.

## Architecture

Official APIs → Python adapters → raw PostgreSQL JSONB → validation/quarantine → core facts → SQL analytical marts → FastAPI → Next.js.

| Layer | Implementation |
|---|---|
| Data | Python 3.12, HTTPX, Pydantic, SQLAlchemy, APScheduler |
| Database | PostgreSQL 18, Alembic, four schemas, constraints, indexes, revisions |
| Analytics | CTEs, window functions, ranks, quantiles, rolling means, materialized views |
| API | FastAPI, parameterised SQL, read-only role, pooled connections, OpenAPI |
| Workspace | Next.js App Router, TypeScript, Tailwind, Apache ECharts, TanStack Query |
| Verification | Pytest, PostgreSQL integration tests, Playwright desktop/tablet/mobile |
| Delivery | Docker Compose, GitHub Actions, deployment configurations |

## Official sources

- [NESO Carbon Intensity API](https://carbon-intensity.github.io/api-definitions/): national estimates, regional forecasts, generation shares and published carbon factors. CC BY 4.0.
- [Elexon Insights](https://bmrs.elexon.co.uk/api-documentation): half-hourly metered generation outturn by fuel, with publication timestamps.
- [NESO Data Portal](https://www.neso.energy/data-portal/api-guidance): daily and yearly historic demand resources, settlement dates and periods. NESO Open Data Licence.
- [NESO DNO boundaries](https://www.neso.energy/data-portal/gis-boundaries-gb-dno-license-areas): licensed 2024 regional geometry, transformed and simplified with documented provenance.

Contracts and genuine samples are in [source-contracts.md](docs/source-contracts.md). Raw acquisition evidence is preserved independently in PostgreSQL.

## Local setup — Windows / Docker Desktop

Requirements: Docker Desktop with Linux containers, Python 3.12+, uv, Node.js 22+, Git. The agent-created checkout is already initialised; cloning is only necessary on another machine.

```powershell
git clone https://github.com/victornonso/gridsignal-gb.git
cd gridsignal-gb
Copy-Item .env.example .env
# Set unique local passwords and corresponding URLs in .env.
uv sync --extra dev
cd apps/dashboard
npm ci
cd ../..
docker compose up -d db
uv run alembic upgrade head
uv run gridsignal ingest --source all --start 2026-10-01 --end 2026-10-14
```

Run API, dashboard and worker in separate terminals:

```powershell
uv run uvicorn apps.api.app.main:app --host 127.0.0.1 --port 8001
```

```powershell
cd apps/dashboard
npm run dev
```

```powershell
uv run gridsignal worker --run-now
```

Dashboard: `http://127.0.0.1:3001`. API/OpenAPI: `http://127.0.0.1:8001/docs`. Database: `localhost:5440/gridsignal_db`.

To run the full topology in containers: `docker compose up --build -d`. The migration service runs before the API/worker. `docker compose --profile tools up -d pgadmin` adds pgAdmin at `http://127.0.0.1:5051`; register host `db`, port `5432`, database `gridsignal_db`, and the appropriate role. Do not expose pgAdmin publicly.

Docker Desktop failed to initialise on the initial build machine. An isolated native PostgreSQL 18 fallback was provisioned and verified there using `tools/local_postgres.py`; its data lives in ignored `.local/pgdata`. Native binaries are not committed. Both Docker image builds and PostgreSQL-container integration checks subsequently passed in GitHub Actions; the local Desktop startup issue remains separate.

## Backfills and operations

```powershell
uv run gridsignal backfill --source carbon --start 2026-10-01 --end 2026-10-14
uv run gridsignal backfill --source demand --start 2025-10-12 --end 2025-10-13
uv run gridsignal backfill --source regional --start 2026-10-01 --end 2026-10-14 --missing-only --region 13
uv run gridsignal backfill --source all --start 2026-10-01 --end 2026-10-14 --failed-only
uv run gridsignal quality
docker compose logs -f worker
docker compose --profile backup run --rm backup
```

Backfills use bounded windows and hash-sensitive upserts. Repeating a window does not duplicate current-state observations. Yearly demand resources are discovered from official metadata; recent demand is reconciled with the daily publication. A `--region` argument controls the missing-window completeness check; fetched regional responses preserve all reported regions for provenance.

For a safe restart use `docker compose down` (keeps the data volume), then `docker compose up -d`. Removing the named volume is destructive and is not part of ordinary reset/restart instructions. Restore backups only into a separate verified target database first.

## Verification

```powershell
uv run ruff check .
$env:RUN_DB_TESTS='1'
uv run pytest -q
uv run python tools/verify_system.py
cd apps/dashboard
npm run lint
npm run typecheck
npm run build
npx playwright install chromium
npm run test:e2e
```

Database integration tests use rollback-isolated synthetic records; production ingestion never uses those fixtures. Browser tests query the real locally persisted system and capture authentic screenshots. Verification JSON contains actual API status, row counts, local performance samples and a query plan. Tests and completion status are recorded in [implementation-status.md](docs/implementation-status.md).

## API

Analytical routes are under `/api/v1`: overview, carbon, generation, demand, regional, forecast, operations, metadata and CSV export. Use `start`, `end` (timezone-aware, exclusive), `region`, `fuel`, `granularity`, `regions` (comparison IDs), `sort`, `limit`, and `offset`. The maximum date range is 366 days; result limits are enforced. The API has no public ingestion or maintenance endpoints.

`/health/live` verifies process liveness. `/health/ready` verifies database/schema connectivity. Source availability is separately exposed in `/operations/sources`; a ready process does not imply every source is fresh.

## Analytical limits

- Carbon intensity is not total emissions. National “actual” intensity is an estimate; regional values are published forecasts/estimates.
- Published forecast differences are not verified issue-time forecast skill.
- Fuel percentages and metered MW outturn come from different definitions and remain separate.
- ND/TSD are not interchangeable; only A-indicated demand rows enter outturn analytics.
- Missing observations remain missing. Comparison highlights require sufficient previous-period coverage.
- Geographic boundaries are approximate published DNO areas, not serviceability polygons.
- Local API timings are measurements on the initial machine, not cloud performance guarantees.

## Deployment and documentation

The public workspace runs on Vercel with a Render Free API and Neon Free PostgreSQL 18. GitHub Actions collects official observations every six hours; half-hourly source resolution is preserved. Render can take about a minute to wake after inactivity. Free quotas apply. The repository retains the continuous Docker worker for local development. See [free-tier operations](infrastructure/deployment/free-tier.md) and [hosted verification](docs/hosted-verification.json).

See [deployment guide](infrastructure/deployment/README.md), [architecture](docs/architecture.md), [data dictionary](docs/data-dictionary.md), [metric catalogue](docs/metric-catalogue.md), [methodology](docs/methodology.md) and [implementation status](docs/implementation-status.md).
