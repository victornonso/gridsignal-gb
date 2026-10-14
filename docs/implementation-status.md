# GridSignal requirements and verification status

Last reviewed: 14 October 2026. Status vocabulary: Not started / In progress / Implemented / Tested / Blocked. This file describes actual evidence, not a claim that the full original brief is finished.

| Requirement | Status | Evidence / remaining work |
|---|---|---|
| Monorepo, Git, configuration | Implemented | `apps/`, `pipelines/`, `db/`, `infrastructure/`, lockfiles |
| GitHub repository | Implemented | Private `victornonso/gridsignal-gb`; source pushed, first full CI run passed |
| Python 3.12 environment | Tested | Isolated uv-managed Python 3.12.15 and dependency installation |
| PostgreSQL 18 provisioning | Tested | Native isolated PostgreSQL 18.6, database and separated roles created automatically |
| Docker / PostgreSQL container verification | Tested in CI; local Desktop blocked | PostgreSQL 18, migrations, API, worker and dashboard started together in Compose; all six adapters succeeded and the proxied overview returned persisted data. Local Desktop remains blocked separately. |
| Four schemas, keys, indexes, constraints | Tested | Alembic `0001` and `0002` applied; database integration tests |
| Raw response preservation | Tested | Real JSONB source responses persisted with run/URL/hash lineage |
| Carbon national adapter | Tested | Real October 2026 backfill |
| Regional adapter | Tested | 14 regions + three countries; aggregate GB ID 18 excluded |
| Generation-share adapter | Tested | Source percentage validation and persisted shares |
| Elexon FUELHH adapter | Tested | Real publication-window backfill; signed interconnector values retained |
| NESO daily demand adapter | Tested | Pagination, A/F distinction, settlement mapping |
| Historic demand discovery | Tested | `package_show` discovery and real 2025 one-day backfill (48 rows) |
| Published factors | Tested | 14 genuine published factors ingested |
| Retry, backoff, pacing, timeouts | Tested | Timeout retry, provider error, malformed contract and unknown-fuel tests |
| Source locking and transactional upserts | Tested | Advisory locks, hash-sensitive upsert integration test |
| Append-only revision tracking | Tested | Rollback-isolated before/after revision test; no invented production revisions |
| Invalid-record quarantine | Tested | Negative carbon, invalid shares, source-schema validation tests |
| Watermarks / failed-window retry | Tested / implemented | Interrupted ingestion test preserves raw data, rolls back facts and leaves watermark unchanged; failed-window CLI implemented |
| Missing-window backfill | Implemented | CLI `--missing-only`, selected region controls missing-window detection |
| Schedulers and reconciliation | Tested / implemented | Immediate scheduled jobs for all six adapters ran successfully and newer observations/revisions reached SQL/API; 30-minute/daily/six-hour cadences configured |
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
| Seven dashboard screens | Tested | All seven screens passed desktop/tablet/mobile Chromium checks with genuine data and screenshots |
| Licensed regional map | Tested (desktop) | NESO 2024 polygons, explicit mapping and documented projection/simplification |
| URL filters / region selection / comparison | Tested (desktop) | Navigation/filter and comparison browser tests passed after fixes |
| CSV export | Tested (desktop) | Filtered export download tested; explicit API bounds |
| Run drilldown | Tested (desktop) | Real operational run dialog |
| Chart drilldown / tooltips | Implemented | Date click → half-hour range; ECharts tooltips; dedicated interaction checks pending |
| Error/empty/stale states | Tested (desktop) | API-outage test verifies explicit unavailable state and no substitute data |
| Responsive navigation | Tested | Desktop/tablet/mobile navigation, filters, exports and drilldowns passed; native WebKit was not tested |
| Accessible tables / focus / reduced motion | Implemented | Semantic tables, skip link, focus CSS, reduced animation; accessibility audit pending |
| CI lint, test, build, Docker validation | Tested | First full GitHub Actions run 38540112974 passed all three jobs including real backfill, API, 30 browser checks and Docker builds; final refinement run tracked separately |
| Performance evidence | Tested locally | Real 20-request API samples and EXPLAIN output in verification JSON; not a cloud SLA |
| Documentation and metric catalogue | Implemented | Architecture, contracts, methodology, database-generated dictionary/catalogue, ADR, deployment, README and case study |
| Production deployment | Blocked | Vercel account available; persistent backend/database/worker host authentication and billing choice needed |
| HTTPS, hosted backups and production monitoring | Blocked | Depend on deployment destination; local backup profile implemented |
| Portfolio case study | Implemented | `docs/case-study.md` with genuine screenshots/findings and explicit deployment status |

## Local runtime

Dashboard: `http://127.0.0.1:3001`. API docs: `http://127.0.0.1:8001/docs`. Native PostgreSQL: loopback port 5440. Credentials are in ignored `.env`; database files and logs are in ignored `.local/`. No production data is fabricated. The portfolio at victorokeke.co.uk has not been changed by this separate project build.

## Outstanding acceptance work

Local final refinement verification is complete. Push and inspect the final CI result, then deploy the full topology when authenticated persistent hosting and its budget are available. Docker Desktop recovery must not reset or delete the user's existing Docker volumes. Native database verification does not count as a successful Docker build.

## Verification snapshot

32 local Python/API/database tests passed. The final 30-check production-browser suite also passed (59.4 seconds). The first complete responsive suite passed 30 browser checks, and the first hosted CI run passed all jobs. Database tests now create and remove a separate temporary PostgreSQL database, so even failed-ingestion tests cannot contaminate production operational counters. A real repeated historical carbon window returned 49 duplicates with zero inserts or updates. CSV export now streams all filtered rows from a repeatable-read snapshot. The latest source refinements require the final verification run recorded in `verification-report.md`.

Interactive browser opening is now blocked by a saved browser permission; the final automated run had completed before this rejection. Further browser work requires restoring permission. The final evidence snapshot is in `verification-report.md`.
