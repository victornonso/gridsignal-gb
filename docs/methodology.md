# Analytical methodology

## Reporting periods and missingness

Observations use timezone-aware timestamps. Equal half-hour observations permit arithmetic interval means. British reporting days, hour profiles and weekday/weekend groups use Europe/London. DST days have 46, 48 or 50 intervals. The reporting calendar contains every expected interval in acquired windows; missing usable values count against coverage. Source freshness is observation age, not the age of a successful HTTP request.

Global date filters represent British calendar days, with an exclusive next-midnight end. The API requires timezone-aware instants and limits positive requests to 366 days. Granularity identifiers and sort directions are validated enumerations. Pagination and CSV exports have explicit row bounds.

## Carbon

National actual is an estimated actual value supplied by NESO. Regional values are published forecasts/estimates; no regional actual field is invented. Intensity in gCO₂/kWh is not total emissions. Descriptive distributions and volatility use available observations without imputation. Trailing averages describe the data available inside the selected period; they are not claimed as complete windows when prior coverage is absent.

Preceding-period comparison uses the same elapsed duration. Coverage is reported with observation counts; percentage-change highlights require at least 80% of the expected prior-period observations. A mean from a sparse previous period must not be treated as a fully comparable baseline.

## Generation and demand

Carbon API fuel shares remain percentages. Period composition is the unweighted mean of equal half-hour percentages, not a generation- or demand-weighted energy share. Low-carbon means biomass, nuclear, hydro, solar and wind; renewable excludes nuclear; fossil includes coal, gas and oil. Imports/other/pumped storage remain unclassified in these aggregate shares rather than assuming their provenance.

Elexon outturn retains signed interconnector power. Source labels are combined into a common fuel within each interval before duration-weighted aggregation. MWh is calculated only with valid source interval duration: MW × hours. Metered generation does not cover all embedded generation.

NESO demand analytics include A-indicated outturn rows only, preserving national and transmission system demand separately. The daily publication is not described as live demand telemetry. Forecast-only zero ND/TSD rows cannot become actual low-demand events.

## Forecast evaluation

Only paired non-null national forecast/estimated-actual intervals enter error metrics. Error = forecast − estimated actual. MAE = mean absolute error, RMSE = sqrt(mean squared error), bias = mean signed error. Median and p95 use PostgreSQL continuous percentiles. Published values may be revised. Retained snapshots support observed revision inspection but do not reconstruct historical issue-time forecast vintages that were never acquired. Therefore this is published forecast–estimate difference analysis, not verified forecast skill.

## Regional analysis

Rankings use only IDs 1–14; countries and GB are overlapping scopes and are excluded. Regional forecasts are not population-weighted and are not aggregated into a national actual. Region-versus-national difference is a descriptive benchmark between different estimation series, not a causal finding. Map boundaries are published approximate DNO areas with documented simplification.

## Quality and insights

Pydantic checks timestamps, nullability, intervals, shares, fuel mapping and demand fields. Database constraints protect keys, referential integrity, intervals and bounds. Quarantine records remain outside analytical facts. Post-ingestion checks persist validation, completeness and source freshness. Further cross-source checks and drift coverage are tracked in the implementation matrix.

Deterministic insights compare SQL metrics with explicit thresholds. They report the measured quantity and reference without inventing causal explanations. Refresh reads persisted data; only the separately scheduled worker fetches external data.
