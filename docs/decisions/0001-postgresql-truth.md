# ADR 0001 — PostgreSQL as the analytical boundary

Status: accepted.

GridSignal uses PostgreSQL as the single calculation layer. Views and parameterised SQL define metrics; FastAPI serialises them; ECharts renders them. This prevents conflicting calculations in notebooks, APIs and browser components. Raw JSONB and versioned current-state facts preserve provenance without adding a queue or distributed stream platform.

PostGIS is unnecessary for the current map because no spatial joins or geographic calculations are performed. The licensed boundary geometry is a presentation layer joined by verified region ID. Add PostGIS when an actual spatial analytical requirement exists.

dbt is not included: a compact, migration-managed SQL model set currently provides clearer ownership than another transformation runtime. Revisit when independently deployed model dependency graphs or larger analytical teams justify it.
