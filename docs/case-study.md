# GridSignal — electricity system intelligence

## The problem

Great Britain electricity data is distributed across providers with different observation grains, publication cadences and definitions. A chart that mixes forecast intensity, metered generation and demand without preserving these distinctions can support a confident but incorrect conclusion.

GridSignal creates a connected investigation workflow while retaining the source and meaning of each series.

## The system

Six ingestion adapters cover national carbon, regional estimates, generation mix, metered fuel outturn, demand and published carbon factors. Raw response JSONB, ingestion lineage, hash-sensitive facts and append-only revisions support traceability. PostgreSQL views calculate analytical outputs; FastAPI exposes bounded read-only queries; Next.js presents them in seven workspaces.

## Analytical questions

- When does carbon intensity vary most, and what does the selected observation coverage support?
- How do fuel composition and metered generation differ across reporting periods?
- Which electricity regions have higher published forecast intensity or variability?
- How large are published national forecast–estimate differences, and when do they occur?
- Is the evidence sufficiently fresh and complete to interpret?

## Important technical decisions

British settlement periods are mapped from local civil midnight to UTC, including 46- and 50-period days. Regional ID 18 returned by the API is excluded to preserve national actuals at internal ID 0. Demand F rows containing zero outturn fields cannot enter A-only analytics. CCGT/OCGT outturn is combined within an interval before time aggregation. Missing data is represented explicitly; null actuals are not replaced with forecasts.

The regional map uses NESO’s licensed 2024 DNO polygons, transformed from EPSG:27700 to EPSG:4326 with documented topology-preserving simplification. No regional geometry is fabricated.

## Interface

![Overview](screenshots/overview-desktop.png)

![Regional intelligence](screenshots/regional-desktop.png)

![Mobile overview](screenshots/overview-mobile.png)

URL filters support reproducible views. Region comparisons, date drilldowns, CSV exports, accessible data tables and operational run inspection connect summary views to evidence. Source failures produce explicit unavailable states, not substituted values.

## Verification and findings

The actual verification snapshot is `verification.json`. It records row counts, endpoint responses, performance samples and an execution plan. At the initial 7–13 October 2026 national selection, the locally verified overview showed a mean intensity of approximately 91.4 gCO₂/kWh, mean low-carbon interval share of 71.4%, and a published forecast–estimate MAE of 10.4 gCO₂/kWh. These values describe that selection and data snapshot; they are not permanent product metrics or causal claims.

The first complete responsive browser suite passed 30 checks across desktop, tablet and mobile Chromium. Python tests include settlement calendars, source parsing, source failure handling, constraints, idempotence, revisions, paired error calculations and role separation. Further test totals and changes are recorded in the implementation status and final verification report.

## Deployment and limitations

The [public workspace](https://gridsignal-gb.vercel.app/) runs on Vercel, with a read-only FastAPI service on Render and PostgreSQL 18 on Neon. Docker Compose reproduces the database, migrations, API, continuous worker and frontend for development. GitHub Actions provides hosted collection and container verification.

### Separate collection from recovery orchestration

The hosted collection cadence is six hours, preserving half-hour source intervals while bounding compute and storage use on free infrastructure. Hourly GitHub catch-up checks evaluate whether collection is due before installing ingestion dependencies or contacting the providers.

A Cloudflare Worker supplies an independent hourly scheduling path. It reads public source observability and dispatches the same GitHub ingestion workflow in due-only mode when a collection is overdue, failed or missing. The workflow checks freshness again after queuing. Active runs suppress duplicate dispatch, workflow concurrency coordinates execution, and source-specific PostgreSQL locks protect writes.

This is independent scheduling, not independent ingestion infrastructure: GitHub remains the execution layer. Provider outages, GitHub execution availability and service quotas remain dependencies. Healthy collection and delayed upstream observations alone do not initiate repeated recovery.

### Keep recovery credentials narrowly scoped

The Worker authenticates through a GitHub App installed on `victornonso/gridsignal-gb` only, with Actions read/write and mandatory read-only metadata. Its private key is encrypted in Cloudflare, and short-lived installation tokens are minted for each check. Authentication is exercised even when collection is healthy so revoked access is visible early.

Database writer credentials remain in GitHub Actions. The Worker has no database access or public administration endpoint. Separate reader, writer and migration roles isolate public analytics from acquisition and schema changes.

### Treat freshness as a source contract

Observation time describes the period measured; publication time describes when a provider released a value; collection time describes when GridSignal acquired it. A successful collection does not imply that a new observation was published. Operational status therefore distinguishes scheduled waiting, failed attempts and overdue collection from observation age and upstream publication delay.

NESO carbon and regional forecasts update every thirty minutes; Elexon FUELHH publishes half-hourly metered outturn. The NESO demand publication updates daily with settlement-data latency. Published carbon factors are reference values rather than a live measurement stream. These distinctions prevent a single freshness rule from assigning the same meaning to every source.

Human-readable timestamps and consistent numerical precision make operational evidence readable. Heatmap tooltips identify the reporting date, hour, intensity and unit. Missing observations remain separate from measured zeros and remain visible in completeness calculations.

Forecast issue-time vintages are not retrospectively reconstructed. Regional values are estimates. Metered outturn has incomplete embedded coverage. DNO boundaries are approximate and published at a different cadence from analytical observations.

## Engineering decisions

Source contracts are part of the analytical model. National aggregates remain separate from regional series, Elexon acquisition follows publication timestamps, and demand outturn calculations accept only A-indicated rows. Original fuel categories and measurement units remain available throughout the pipeline.

Revision order is part of correctness. Elexon publication timestamps determine which current outturn can replace another, and database regression tests verify publication ordering. Raw responses and current-state deduplication solve different problems and are both retained.

The calendar is an analytical dataset. A continuous expected-interval calendar supports missing-data denominators and daylight-saving mapping, while source timestamps and successful-ingestion timestamps serve different freshness questions.

## Recovery verification

Eight automated watchdog tests cover healthy-source skipping, recovery eligibility, active-run suppression, dispatch scoping, authentication failures, the absence of a public HTTP administration endpoint and cryptographically verified App JWTs. A deployed scheduled-handler test on 15 October 2026 returned `healthy` after authenticating with the encrypted App credentials. Handler behaviour, timer delivery and upstream publication are separate verification boundaries; this result is not a claim of uninterrupted operation.

## Next engineering stage

Source-specific collection schedules will align acquisition with each publication cycle, using measured release buffers rather than assuming exact publication minutes. Separate last-check and last-new-observation reporting will make the distinction visible to users. The current hosted collection interval remains six hours, even for feeds with half-hour source resolution.

Further work focuses on cold-start measurement and longer historical comparisons within a documented retention budget.

## Performance and validation

The local verification snapshot measured overview p95 at approximately 19 ms, carbon trend at 12 ms and regional ranking at 18 ms, from 20 sequential warm-pool HTTP requests per route. See the exact sampling scope and query plan in `verification.json`; these measurements are not hosted service guarantees.

The final local suite passed 34 Python/API/database tests and 30 production-browser checks across three device profiles. CI independently started the complete Compose topology and verified that every source ingested successfully and that the dashboard's same-origin API returned a persisted latest-intensity value.
