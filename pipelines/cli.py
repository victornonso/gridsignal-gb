import argparse
import json
import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.blocking import BlockingScheduler
from sqlalchemy import text

from pipelines.ingestion.runner import SOURCES, engine, ingest


def parse_date(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return result.replace(tzinfo=timezone.utc) if not result.tzinfo else result


def refresh(source):
    end = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    start = end - timedelta(days=2 if source != "demand" else 32)
    result = ingest(source, start, end)
    from pipelines.validation.quality import check_quality

    check_quality()
    return result


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="GridSignal official-source pipeline")
    parser.add_argument("command", choices=["ingest", "backfill", "worker", "quality"])
    parser.add_argument("--source", choices=[*SOURCES, "all"], default="all")
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--region", type=int)
    parser.add_argument("--missing-only", action="store_true")
    parser.add_argument("--failed-only", action="store_true")
    parser.add_argument(
        "--run-now", action="store_true", help="Start scheduled jobs immediately as well as at normal cadence"
    )
    args = parser.parse_args()
    if args.command == "worker":
        scheduler = BlockingScheduler(timezone="UTC")
        for source in SOURCES:
            scheduler.add_job(
                refresh,
                "interval",
                minutes=1440 if source in {"demand", "factors"} else 30,
                args=[source],
                id=source,
                max_instances=1,
                coalesce=True,
                misfire_grace_time=300,
                **({"next_run_time": datetime.now(timezone.utc)} if args.run_now else {}),
            )
        scheduler.add_job(
            lambda: [refresh(s) for s in SOURCES[:4]], "interval", hours=6, id="reconcile", max_instances=1
        )
        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            scheduler.shutdown(wait=True)
            engine.dispose()
        return
    if args.command == "quality":
        from pipelines.validation.quality import check_quality

        print(json.dumps(check_quality(), default=str))
        return
    end = parse_date(args.end) if args.end else datetime.now(timezone.utc)
    start = parse_date(args.start) if args.start else end - timedelta(days=7)
    sources = SOURCES if args.source == "all" else [args.source]
    for source in sources:
        windows = []
        if args.failed_only:
            with engine.connect() as conn:
                windows = list(
                    conn.execute(
                        text(
                            "SELECT window_start,window_end FROM ops.ingestion_run WHERE source_id=:s AND status IN ('failed','partial') AND window_start>=:a AND window_end<=:b"
                        ),
                        dict(s=source, a=start, b=end),
                    )
                )
        else:
            cursor = start
            while cursor < end:
                stop = min(cursor + timedelta(days=1), end)
                windows.append((cursor, stop))
                cursor = stop
        if source in {"demand", "factors"} and not args.failed_only:
            windows = [(start, end)]
        for a, b in windows:
            if args.missing_only and source in {"carbon", "regional"}:
                with engine.connect() as conn:
                    count = conn.execute(
                        text(
                            "SELECT count(*) FROM core.carbon_observation WHERE region_id=:r AND period_start>=:a AND period_start<:b"
                        ),
                        dict(r=args.region or (0 if source == "carbon" else 1), a=a, b=b),
                    ).scalar()
                if count >= int((b - a).total_seconds() / 1800):
                    continue
            print(json.dumps({"source": source, "start": str(a), "end": str(b), **ingest(source, a, b)}))
    from pipelines.validation.quality import check_quality

    check_quality()


if __name__ == "__main__":
    main()
