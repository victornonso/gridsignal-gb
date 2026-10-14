# GridSignal requirements and verification status

Last reviewed: 14 October 2026. Status vocabulary: Not started / In progress / Implemented / Tested / Blocked. This file describes actual evidence, not a claim that the full original brief is finished.

| Requirement | Status | Evidence / remaining work |
|---|---|---|
| Monorepo, Git, configuration | Implemented | `apps/`, `pipelines/`, `db/`, `infrastructure/`, lockfiles |
| GitHub repository | Implemented | Private `victornonso/gridsignal-gb`; initial source push pending final checks |
| Python 3.12 environment | Tested | Isolated uv-managed Python 3.12.15 and dependency installation |
| PostgreSQL 18 provisioning | Tested | Native isolated PostgreSQL 18.6, database and separated roles created automatically |
| Docker Compose PostgreSQL 18 | Blocked | Docker Desktop cannot initialise its inference socket; Compose files written, actual container startup/build not verified |
| Four schemas, keys, indexes, constraints | Tested | Alembic `0001` applied; database integration tests |
| Raw response preservation | Tested | Real JSONB source responses persisted with run/URL/hash lineage |
| Carbon national adapter | Tested | Real October 2026 backfill |
| Regional adapter | Tested | 14 regions + three countries; aggregate GB ID 18 excluded |
| Generation-share adapter | Tested | Source percentage validation and persisted shares |
| Elexon FUELHH adapter | Tested | Real publication-window backfill; signed interconnector values retained |
| NESO daily demand adapter | Tested | Pagination, A/F distinction, settlement mapping |
| Historic demand discovery | Tested | `package_show` discovery and real 2025 one-day backfill (48 rows) |
| Published factors | Tested | 14 genuine published factors ingested |
| Retry, backoff, pacing, timeouts | Implemented | HTTPX + Tenacity; reliability test expansion in progress |
| Source locking and transactional upserts | Tested | Advisory locks, hash-sensitive upsert integration test |
| Append-only revision tracking | Tested | Rollback-isolated before/after revision test; no invented production revisions |
| Invalid-record quarantine | Tested | Negative carbon, invalid shares, source-schema validation tests |
| Watermarks / failed-window retry | Implemented | Successful-transaction watermark, CLI `--failed-only`; failure-path tests in progress |
| Missing-window backfill | Implemented | CLI `--missing-only`, selected region controls missing-window detection |
| Schedulers and reconciliation | Implemented | APScheduler jobs; actual unattended propagation test pending |
| Quality framework | Implemented | Persisted field/interval/share validation, completeness, freshness, uniqueness, revision, calendar and alignment checks |
| Carbon analytical SQL | Tested | Descriptive KPIs, profiles, distributions, period comparisons and rolling windows |
| Generation analytical SQL | Tested | Fuel shares/classification and interval-correct outturn aggregation |
| Demand analytical SQL | Tested | A-only profiles, extrema, volatility and prior-period comparison |
| Forecast analytical SQL | Tested | Paired MAE/RMSE/bias/percentiles test with null exclusion |
| Regional SQL | Tested | Ranking, quartiles, volatility, p95, multi-region trend |
| Operational SQL | Tested | Actual run counters, source freshness, completeness, quality results |
| Required views / materialized marts | Tested | Eight views and four materialized marts applied and refreshed |
| FastAPI required routes | Tested | All analytical route queries return HTTP 200 in `docs/verification.json` |
| API validation, CORS, reader credentials | Tested | Bounded dates/regions/sort, no public maintenance routes, reader privileges tested |
| Connection pooling / structured logs | Implemented | SQLAlchemy pool, per-request JSON timing and failure handling |
| Seven dashboard screens | Tested (desktop) | Genuine screenshots in `docs/screenshots`; tablet/mobile rerun in progress |
| Licensed regional map | Tested (desktop) | NESO 2024 polygons, explicit mapping and documented projection/simplification |
| URL filters / region selection / comparison | Tested (desktop) | Navigation/filter and comparison browser tests passed after fixes |
| CSV export | Tested (desktop) | Filtered export download tested; explicit API bounds |
| Run drilldown | Tested (desktop) | Real operational run dialog |
| Chart drilldown / tooltips | Implemented | Date click → half-hour range; ECharts tooltips; dedicated interaction checks pending |
| Error/empty/stale states | Tested (desktop) | API-outage test verifies explicit unavailable state and no substitute data |
| Responsive navigation | In progress | Mobile/tablet Chromium tests configured; first attempted WebKit was unavailable |
| Accessible tables / focus / reduced motion | Implemented | Semantic tables, skip link, focus CSS, reduced animation; accessibility audit pending |
| CI lint, test, build, Docker validation | Implemented | GitHub workflow; hosted execution not yet verified |
| Performance evidence | Tested locally | Real 20-request API samples and EXPLAIN output in verification JSON; not a cloud SLA |
| Documentation and metric catalogue | In progress | Architecture, contracts, methodology, deployment written; dictionary/catalogue generated from implementation next |
| Production deployment | Blocked | Vercel account available; persistent backend/database/worker host authentication and billing choice needed |
| HTTPS, hosted backups and production monitoring | Blocked | Depend on deployment destination; local backup profile implemented |
| Portfolio case study | In progress | Actual screenshots and evidence available; no production URL invented |

## Local runtime

Dashboard: `http://127.0.0.1:3001`. API docs: `http://127.0.0.1:8001/docs`. Native PostgreSQL: loopback port 5440. Credentials are in ignored `.env`; database files and logs are in ignored `.local/`. No production data is fabricated. The portfolio at victorokeke.co.uk has not been changed by this separate project build.

## Outstanding acceptance work

Complete remaining chart interactions, accessibility and reliability checks; rerun desktop/tablet/mobile suites; write final counts and requirement evidence; commit/push; inspect CI; deploy full topology when authenticated hosting is available. Docker Desktop recovery must not reset or delete the user's existing Docker volumes. Native database verification does not count as a successful Docker build.
