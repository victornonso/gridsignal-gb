import json

from sqlalchemy import text

from pipelines.ingestion.runner import engine


def check_quality():
    checks = []
    with engine.begin() as conn:
        for row in conn.execute(text("SELECT * FROM mart.v_source_freshness")).mappings():
            status = "warn" if row["stale"] else "pass"
            checks.append(
                dict(
                    source_id=row["id"],
                    test_name="freshness",
                    status=status,
                    observed=row["age_minutes"],
                    threshold=row["stale_minutes"],
                    severity="warning",
                    details=json.dumps({"latest": str(row["observed_at"])}),
                )
            )
        for row in conn.execute(
            text(
                "SELECT region_id,sum(expected) AS expected,sum(usable) AS usable FROM mart.v_data_completeness WHERE day>=current_date-7 AND day<current_date GROUP BY region_id"
            )
        ).mappings():
            pct = 100 * row["usable"] / row["expected"] if row["expected"] else 0
            checks.append(
                dict(
                    source_id="carbon" if row["region_id"] == 0 else "regional",
                    test_name="calendar_completeness",
                    status="pass" if pct >= 99 else "warn",
                    observed=pct,
                    threshold=99,
                    severity="warning",
                    details=json.dumps({"region_id": row["region_id"]}),
                )
            )
        for result in checks:
            conn.execute(
                text(
                    "INSERT INTO ops.quality_result(test_name,source_id,status,observed,threshold,severity,details) VALUES(:test_name,:source_id,:status,:observed,:threshold,:severity,CAST(:details AS jsonb))"
                ),
                result,
            )
        definitions = [
            (
                "carbon",
                "interval_integrity",
                "SELECT count(*) FROM core.carbon_observation WHERE period_end<>period_start+interval '30 minutes' OR forecast<0 OR actual<0",
                0,
                "critical",
            ),
            (
                "mix",
                "fuel_share_totals",
                "SELECT count(*) FROM (SELECT region_id,period_start,source_id FROM core.generation_share GROUP BY 1,2,3 HAVING abs(sum(share)-100)>0.6) q",
                0,
                "critical",
            ),
            (
                "carbon",
                "current_state_uniqueness",
                "SELECT count(*) FROM (SELECT region_id,period_start FROM core.carbon_observation GROUP BY 1,2 HAVING count(*)>1) q",
                0,
                "critical",
            ),
            (
                "demand",
                "settlement_calendar_mapping",
                "SELECT count(*) FROM core.demand_observation d LEFT JOIN core.reporting_calendar c USING(period_start) WHERE c.period_start IS NULL OR d.settlement_date<>c.settlement_date OR d.settlement_period<>c.settlement_period",
                0,
                "critical",
            ),
            (
                "carbon",
                "revision_integrity",
                "SELECT count(*) FROM core.carbon_revision WHERE old_value->>'record_hash'=new_value->>'record_hash'",
                0,
                "critical",
            ),
            (
                "elexon",
                "cross_source_alignment",
                "SELECT count(*) FROM core.carbon_observation c WHERE c.region_id=0 AND c.actual IS NOT NULL AND c.period_start>=now()-interval '7 days' AND c.period_end<now()-interval '2 hours' AND NOT EXISTS(SELECT 1 FROM core.generation_outturn g WHERE g.period_start=c.period_start)",
                0,
                "warning",
            ),
        ]
        for source, name, query, threshold, severity in definitions:
            observed = conn.execute(text(query)).scalar()
            result = dict(
                source_id=source,
                test_name=name,
                status="pass" if observed <= threshold else ("fail" if severity == "critical" else "warn"),
                observed=observed,
                threshold=threshold,
                severity=severity,
                details="{}",
            )
            conn.execute(
                text(
                    "INSERT INTO ops.quality_result(test_name,source_id,status,observed,threshold,severity,details) VALUES(:test_name,:source_id,:status,:observed,:threshold,:severity,CAST(:details AS jsonb))"
                ),
                result,
            )
            checks.append(result)
    return checks
