# Deployment

GridSignal requires persistent PostgreSQL 18, an API process, and an unattended ingestion worker. Vercel can host the Next.js frontend; it does not replace the persistent worker or database.

## Railway deployment topology

1. PostgreSQL service: official `postgres:18` image; persistent volume at `/var/lib/postgresql`; `POSTGRES_DB=gridsignal_db`. Use generated secret passwords. Disable public database exposure after migrations when private networking is available.
2. API service: repository-root Dockerfile `infrastructure/docker/api.Dockerfile`; start `uvicorn apps.api.app.main:app --host 0.0.0.0 --port $PORT`; readiness `/api/v1/health/ready`.
3. Worker service: same image, start `gridsignal worker`; no public domain. Set only writer database credentials.
4. Frontend: import `apps/dashboard` into Vercel; set `NEXT_PUBLIC_API_URL=https://<verified-api-domain>/api/v1` before building.

Provision roles with `infrastructure/docker/init-roles.sh` (or equivalent administrative SQL), then run `alembic upgrade head` under the migration role. Never supply the administrative connection string as the API reader credential. API `READ_DATABASE_URL` and worker `DATABASE_URL` use `postgresql+psycopg://` URLs with the separated roles. `CORS_ORIGINS` must contain the exact deployed frontend origin.

Backfill an initial reporting window with `gridsignal backfill --source all --start <date> --end <date>`. Confirm every source in `/api/v1/operations/sources` and inspect failed windows before enabling periodic work.

Railway billing is subscription plus resource usage; persistent worker CPU/RAM and PostgreSQL volume usage are billable. No hosting purchase or subscription is authorised by this configuration alone. Verified documentation: https://docs.railway.com/pricing/plans and https://docs.railway.com/volumes/reference (reviewed 14 October 2026).

## Backups and restoration

Schedule daily `pg_dump -Fc` to a separate encrypted storage destination. The local Compose backup profile writes timestamped archives in ignored `backups/`. Keep at least seven daily backups and test restoration into a separate database with `pg_restore --no-owner --dbname <isolated-target>`. Do not treat an attached volume as a backup. Hosted backup automation requires the selected provider/storage credentials.

## Release checks

Run CI, migrate, verify readiness, seed/backfill, enable worker, deploy frontend with its correct API URL, inspect all seven screens, then verify HTTPS and source freshness. Deploy no public frontend that points at localhost or substitutes static snapshots for the API.
