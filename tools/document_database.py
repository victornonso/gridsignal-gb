"""Generate dictionaries from the migrated database and application metric definitions."""

from pathlib import Path

from sqlalchemy import create_engine, text

from apps.api.app.config import settings
from apps.api.app.main import metrics
from apps.api.app.services.analytics import QUERIES


def main():
    with create_engine(settings.migration_database_url).connect() as conn:
        columns = (
            conn.execute(
                text(
                    "SELECT table_schema,table_name,column_name,data_type,is_nullable,column_default FROM information_schema.columns WHERE table_schema IN ('raw','core','mart','ops') ORDER BY table_schema,table_name,ordinal_position"
                )
            )
            .mappings()
            .all()
        )
        constraints = (
            conn.execute(
                text(
                    "SELECT n.nspname AS schema,t.relname AS name,c.conname,pg_get_constraintdef(c.oid) AS definition FROM pg_constraint c JOIN pg_class t ON t.oid=c.conrelid JOIN pg_namespace n ON n.oid=t.relnamespace WHERE n.nspname IN ('raw','core','ops') ORDER BY 1,2,3"
                )
            )
            .mappings()
            .all()
        )
    doc = [
        "# Data dictionary",
        "",
        "Generated from migrated PostgreSQL metadata. Source mappings and grain rules are described in `source-contracts.md` and `architecture.md`.",
        "",
    ]
    current = None
    for r in columns:
        key = f"{r['table_schema']}.{r['table_name']}"
        if key != current:
            doc.extend([f"## {key}", "", "| Column | Type | Nullable | Default |", "|---|---|---|---|"])
            current = key
        doc.append(
            f"| {r['column_name']} | {r['data_type']} | {r['is_nullable']} | {r['column_default'] or '—'} |"
        )
    doc.extend(["", "## Keys and constraints", ""])
    for r in constraints:
        doc.append(f"- `{r['schema']}.{r['name']}.{r['conname']}`: `{r['definition']}`")
    Path("docs/data-dictionary.md").write_text("\n".join(doc) + "\n", encoding="utf-8")
    doc = [
        "# Metric catalogue",
        "",
        "All calculations execute in PostgreSQL; API query identifiers below map directly to `apps/api/app/services/analytics.py`.",
        "",
    ]
    routes = {
        "carbon_intensity": ["carbon/comparison", "carbon/profile", "carbon/distribution"],
        "generation_share": ["generation/mix", "generation/summary"],
        "generation_outturn": ["generation/outturn"],
        "national_demand": ["demand/summary", "demand/profile"],
        "forecast_errors": ["forecasts/errors", "forecasts/comparison"],
        "completeness": ["operations/completeness"],
    }
    for metric in metrics()["rows"]:
        doc.extend([f"## {metric['metric']}", ""])
        for key, value in metric.items():
            if key != "metric":
                doc.append(f"- **{key.replace('_', ' ').title()}**: {value}")
        doc.extend(
            [
                "- **Null handling**: unavailable measurements remain null; aggregates exclude nulls; denominators use usable/paired counts as appropriate.",
                "- **Quality assumptions**: validated source fields, database constraints, source-specific interval rules; gaps are not imputed.",
                "- **Tests**: `pipelines/tests/test_contracts.py`, `db/tests/test_database.py`, endpoint verification and responsive browser tests.",
                "",
            ]
        )
        for route in routes[metric["metric"]]:
            doc.append(f"### `{route}`")
            if route in QUERIES:
                doc.extend(["", "```sql", QUERIES[route], "```", ""])
            else:
                doc.extend(
                    [
                        "",
                        "Dynamic SQL is in `dynamic_query()`; granularity is selected from a fixed whitelist, and all analytical values remain bound parameters.",
                        "",
                    ]
                )
    doc.extend(
        [
            "## Further analytical outputs",
            "",
            "| Output | SQL definition |",
            "|---|---|",
            "| Volatility | `STDDEV_SAMP` of available interval values |",
            "| Regional rank | `DENSE_RANK` by ascending mean forecast across IDs 1–14 |",
            "| Regional quartile | `NTILE(4)` on regional mean forecast |",
            "| Error percentiles | `PERCENTILE_CONT(0.5/0.95)` over absolute paired errors |",
            "| Rolling intensity | Observation-count-weighted trailing mean; gaps remain missing |",
            "| Peak demand | Maximum available national-demand outturn, MW |",
            "| Failure rate | Failed runs / recorded runs × 100, selected operational interval |",
            "| Freshness | Server clock − latest source observation time; source-specific threshold |",
            "| Revision count | Append-only rows from observed source-state changes |",
            "",
        ]
    )
    Path("docs/metric-catalogue.md").write_text("\n".join(doc) + "\n", encoding="utf-8")
    print("Database dictionary and metric catalogue generated from implementation.")


if __name__ == "__main__":
    main()
