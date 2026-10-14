# Verified source contracts

Contract requests executed on 14 October 2026; response samples are in `docs/contracts/`. Production ingestion stores independent original responses in PostgreSQL. Samples are genuine public API responses, not invented fixtures.

## NESO Carbon Intensity

Documentation: https://carbon-intensity.github.io/api-definitions/

Verified `/intensity`, `/intensity/{from}/{to}`, `/regional`, `/regional/intensity/{from}/{to}`, `/generation`, `/generation/{from}/{to}`, `/intensity/factors` under `https://api.carbonintensity.org.uk`.

National `data` is a list of `{from,to,intensity:{forecast,actual,index}}`. UTC timestamp strings use `Z`. Forecast and estimated actual may be null. Regional intervals contain a `regions` array with `regionid`, `shortname`, `dnoregion`, `intensity.forecast`, `intensity.index`, and `generationmix` of `{fuel,perc}`. Regional actual fields are absent. Live regional responses also contain GB ID 18, beyond the documented 14 regions and three countries. It is excluded; GB national rows come from `/intensity` at internal ID 0.

Current generation uses `data` as an object; historical generation uses a list. Both are normalised. Fuel shares are percentages; tolerance is 100 ± 0.6 percentage points because published categories are rounded. Values outside individual 0–100 bounds or total tolerance are quarantined. Published factors are label→numeric maps in `data[0]`.

Historical endpoints include their boundary interval in observed responses, causing 49 rows for a nominal 24-hour request. Primary keys and hash-sensitive upserts deduplicate adjacent windows. Backfills use conservative one-day windows rather than unverified large range requests. Null estimated actuals remain null. CC BY 4.0 attribution retained.

## Elexon Insights FUELHH

Documentation: https://bmrs.elexon.co.uk/api-documentation and https://developer.data.elexon.co.uk/

Verified `https://data.elexon.co.uk/bmrs/api/v1/datasets/FUELHH` using `publishDateTimeFrom`, `publishDateTimeTo`, `format=json`. A trial `settlementDate` parameter did not restrict the response and is not used. Records contain `dataset`, `publishTime`, `startTime`, `settlementDate`, `settlementPeriod`, `fuelType`, `generation`.

`generation` is signed reported power in MW. `startTime` is offset-aware UTC; a FUELHH observation lasts 30 minutes. Publication windows are distinct from observation windows. Preserve both timestamps and source fuel labels. CCGT and OCGT map to gas; NPSHYD to hydro; PS to pumped storage; `INT*` labels to imports, while preserving each interconnector separately. Negative interconnector values are legitimate, not validation failures. Outturn covers metered generation and does not imply complete embedded generation coverage.

One-day publication queries returned up to 980 rows (20 labels × 49 intervals) in verification, with no continuation token in sampled responses. The adapter uses bounded windows. Late revisions outside the routine reconciliation lookback require an explicit backfill.

## NESO CKAN Demand Data Update

Documentation: https://www.neso.energy/data-portal/api-guidance

Verified `https://api.neso.energy/api/3/action/datastore_search`, resource `177f6fa4-ae49-4182-81ea-0c6b35f26ca6`. Response uses `success`, `result.fields`, `result.records`, `result.total`, pagination by `limit` and `offset`. Live resource metadata and records were inspected. Pages are fetched in stable settlement-date/period order with 1,000-row limits.

Required fields: `SETTLEMENT_DATE` (ISO date), `SETTLEMENT_PERIOD` (1–50), `ND` (MW), `TSD` (MW), `FORECAST_ACTUAL_INDICATOR` (`A`/`F`). Future `F` rows can contain zero ND/TSD alongside embedded generation forecasts. They retain the F indicator and are excluded from outturn analytics. ND and TSD remain separate definitions; TSD includes additional system requirements. Settlement date uses the British civil day, not UTC date. Period starts are mapped using Europe/London and actual 46/48/50 half-hour day lengths.

The daily resource covers a rolling publication window, not indefinite history. CKAN `package_show?id=historic-demand-data` was also verified and discovers yearly historical resources, including 2026 ID `8a4a771c-3929-4e56-93ad-cdf13219dea5`. The adapter discovers selected yearly resources, extracts bounded dates through verified `datastore_search_sql`, then reconciles with the daily resource. A genuine 2025 one-day backfill inserted 48 rows. Historic resources omit the A/F indicator and are explicitly interpreted as historical outturn.

## Rate limits and failures

No numerical rate-limit contract was established from the sampled public documentation. The clients conservatively pace at one request per second, respect bounded `Retry-After`, use 45-second timeouts and four exponential-backoff attempts. This is a client safety policy, not a claim about provider capacity. Transport failures are recorded explicitly; no fallback synthetic production dataset is supplied.

## Geographic boundaries

NESO 2024 DNO GeoJSON resource `1c6a7dc0-1b6c-443a-bc67-5f7125649434` was downloaded from the official portal. Its projected CRS is EPSG:27700; it was transformed to EPSG:4326 and topology-preservingly simplified at 150 metres for display. `docs/boundary-provenance.json` records the source hash, licence, mapping and transformation. DNO areas are approximate licensed regions, not precise serviceability polygons. All 14 GSP-letter mappings are explicit and checked against published area labels.

Elexon revisions are applied in ascending publication order. An older published version cannot overwrite a newer current fact; this is covered by an isolated database test.
