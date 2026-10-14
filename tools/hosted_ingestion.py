"""Seed a bounded reporting period without exposing hosted credentials in shell arguments."""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=7)
    args = parser.parse_args()
    if not 1 <= args.days <= 14:
        raise SystemExit("Initial hosted history must be between 1 and 14 days")
    root = Path(__file__).resolve().parents[1]
    config = json.loads((root / ".local/hosted.json").read_text())
    end = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    start = end - timedelta(days=args.days)
    env = dict(os.environ, DATABASE_URL=config["database_url"])
    with (root / ".local/hosted-ingestion.log").open("w") as log:
        result = subprocess.run([
            sys.executable, "-m", "pipelines.cli", "backfill", "--source", "all",
            "--start", start.isoformat(), "--end", end.isoformat(),
        ], env=env, cwd=root, stdout=log, stderr=log, timeout=600)
    if result.returncode:
        raise SystemExit("Hosted ingestion failed; diagnostic saved locally")
    print(json.dumps({"start": start.isoformat(), "end": end.isoformat(), "status": "complete"}))


if __name__ == "__main__":
    main()
