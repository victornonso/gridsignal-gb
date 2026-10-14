"""Bounded, one-shot refresh for a free-tier scheduler; no persistent worker required."""

import json
import logging
import os

from sqlalchemy import text

from pipelines.cli import refresh
from pipelines.ingestion.runner import SOURCES, engine


def main():
    if not os.environ.get("DATABASE_URL"):
        raise RuntimeError("Hosted writer database secret is required")
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    failures = []
    try:
        for source in SOURCES:
            # Stop growth before exhausting a 1 GB free database. No automatic deletion of evidence.
            with engine.connect() as conn:
                size = conn.execute(text("SELECT pg_database_size(current_database())")).scalar_one()
            if size >= 750_000_000:
                raise RuntimeError("Database reached the 750 MB ingestion guard; review storage before resuming")
            try:
                results = refresh(source)
                print(json.dumps({"source": source, "windows": results}, default=str))
                if any(not result["received"] or result["rejected"] for result in results):
                    failures.append(source)
            except Exception:
                logging.exception("Hosted refresh failed for %s", source)
                failures.append(source)
        if failures:
            raise RuntimeError("Sources need attention: " + ", ".join(failures))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
