# GridSignal verification report

Verified locally on 14 October 2026. The production build was served by Next.js standalone and queried the running FastAPI/PostgreSQL system.

## Completed verification

- 34 Python/API/database tests passed, including real temporary-database migrations, isolated failure/rollback tests, source locks and revision ordering.
- 30 Playwright checks passed against the production build across desktop, tablet and mobile Chromium (59.4 seconds). All seven screens, navigation, date/region/resolution filters, comparisons, operational drilldowns, CSV downloads and explicit outage states passed.
- 38 analytical API routes returned HTTP 200. Process liveness/readiness and metadata were also checked.
- Full filtered CSV export returned 336 rows matching the SQL count even when the table request included a limit of 10 and offset of 50.
- A repeated historical carbon window produced 49 duplicates, zero inserts, zero updates and zero rejected records.
- Scheduled worker jobs fetched real source changes and persisted both new observations and revisions.
- Python lint, frontend lint, TypeScript checks and the Next.js production build passed.
- First hosted CI run 38540112974 passed Python/database, frontend/Docker and end-to-end jobs. Final refinement CI includes a full Docker Compose integration job and is recorded after execution.

## Persisted row counts

| Relation | Rows |
|---|---:|
| `core.carbon_observation` | 11,556 |
| `core.generation_share` | 104,004 |
| `core.generation_outturn` | 12,840 |
| `core.demand_observation` | 1,584 |
| `core.carbon_revision` | 108 |
| `ops.ingestion_run` | 66 |
| `ops.quality_result` | 360 |
| `raw.api_response` | 76 |
| `raw.quarantine` | 0 |
| `core.observation_revision` | 506 |

## Measured local API performance

20 sequential HTTP requests per route; warm pool, loaded data. These are local measurements, not production guarantees.

| Route | Median ms | p95 ms |
|---|---:|---:|
| `overview` | 15.56 | 19.18 |
| `carbon/trend` | 9.63 | 11.68 |
| `regions/ranking` | 14.16 | 18.1 |

The actual query-plan JSON, source timestamps and route-level evidence are in `verification.json`.

## Contract and data evidence

Official NESO Carbon Intensity, regional, mix, factor and demand APIs and Elexon FUELHH were executed successfully. Historical NESO resource discovery and a 2025 backfill were also exercised. Original HTTP JSON responses are stored in `raw.api_response`; source contracts and genuine samples are versioned in `docs/contracts/`. Regional map geometry has a verified official source, licence and transformation record.

## Deployment status

- GitHub: private repository `https://github.com/victornonso/gridsignal-gb`.
- Local dashboard: `http://127.0.0.1:3001`.
- Local API docs: `http://127.0.0.1:8001/docs`.
- Public deployment: **not deployed**. Authenticated persistent PostgreSQL/API/worker hosting and a budget are still required. Vercel authentication is available for the frontend, but a disconnected frontend is not being published as the complete application.
- Local Docker Desktop cannot initialise its inference socket. Native PostgreSQL 18 is verified locally; both Docker image builds and a PostgreSQL container were verified independently in CI.
- A saved browser permission blocked subsequent interactive preview opening. The recorded 30-check production browser run had already completed successfully before that block. No browser workaround was used.

## Remaining operational acceptance

Provision authenticated persistent hosting, migrate and backfill its database, configure exact production origins/secrets, run the worker, deploy the frontend against that API, verify HTTPS and production freshness, configure hosted backup storage/retention and repeat the deployment smoke checks. Native Safari/WebKit was not tested; tablet/mobile checks used Chromium device emulation. Full historical issue-time forecast skill is unsupported because the source does not provide those retained vintages.

## Additional container verification

Compose integration passed in GitHub Actions runs 38542021445 and 38542328487: the entire topology built and started from `.env.example`; readiness and frontend responses succeeded; all six source adapters recorded successful ingestion; the frontend's same-origin overview returned a non-null value from PostgreSQL. Logs are retained as CI artifacts. The final methodology-panel inverse text has a source-verified contrast ratio of 7.62:1 after a small style correction; its local interactive preview was not reopened because browser permission was blocked.

## Timezone regression checks

A PostgreSQL regression test verifies observation-weighted seven-day windows across the 2025 British clock change under a UTC database session. Three frontend unit tests verify British reporting-date labels independently of device timezone, 23/25-hour filter boundaries, and the distinction between missing and genuine zero values. These tests passed locally.

Two additional database regression checks confirm that completeness obeys an exclusive partial-day end, and that current-period generation statistics exclude the preceding comparison period. The local Python/API/database total is 34 passing tests; frontend unit tests total 3.

Two orchestration unit tests verify bounded watermark-based recovery after a long outage and half-hour-aligned recent reconciliation windows.

## Final CI result

GitHub Actions run **38545434778**, source commit **565b81a**, passed all four jobs: Python/database, frontend (including its three unit tests), end-to-end browser verification, and complete Docker Compose integration. CI provisioned fresh PostgreSQL 18, applied migrations, ingested official data and verified the running system. No public deployment URL is claimed.
