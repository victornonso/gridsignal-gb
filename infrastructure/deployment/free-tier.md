# Free-tier deployment

The hosted deployment uses Vercel for Next.js, Render Free for FastAPI, Neon Free for PostgreSQL 18, and GitHub Actions for periodic ingestion. The continuous local/Docker worker remains available for development and future paid hosting.

## Provisioning order

1. Sign in to Render and Neon. Use free plans only; do not add or upgrade paid resources.
2. Create a Neon PostgreSQL 18 project in a region near Render Frankfurt, with database `gridsignal_db`. Enable scale to zero. Provision separate reader and writer login roles and run Alembic with the database owner credential. Preserve the existing least-privilege grants. Use direct TLS connection strings with the `postgresql+psycopg://` scheme; the API sends PostgreSQL connection options that must be checked before choosing any transaction pooler.
3. Backfill a modest reporting window and measure database size before enabling scheduled ingestion. A full copy of local raw history is not required.
4. Deploy the root `render.yaml`. Set only `READ_DATABASE_URL` and the exact Vercel origin in `CORS_ORIGINS`; do not give the public API migration or writer credentials. There is no paid worker or Render database in this Blueprint. Readiness must pass before releasing the dashboard.
5. Configure Vercel's `NEXT_PUBLIC_API_URL` directly to the HTTPS Render API `/api/v1` endpoint and verify CORS/cold-start handling. Requests allow 90 seconds, with a delayed connecting message in chart panels and the existing bounded query retry. A direct API URL avoids a frontend proxy cutting off a cold start early. Verify the real hosted behaviour before release.
6. Store the Neon writer URL in the repository's `HOSTED_WRITER_DATABASE_URL` Actions secret. Check remaining account-wide Actions minutes, caches/artifacts and billing settings first. Set `HOSTED_INGESTION_ENABLED=true` only after an authenticated manual workflow succeeds.

## Refresh and limits

The hosted workflow runs every six hours, with a ten-minute job timeout and concurrency protection. It resumes from existing source watermarks and retains half-hourly observations: collection frequency is separate from observation resolution. This is a deliberate reduction from the local worker's 30-minute collection cadence. Source freshness indicators remain visible and must not be suppressed to suggest live collection.

At most four scheduled jobs per day means up to 1,240 job minutes in a 31-day month at the timeout, plus manual runs, CI and other repository usage. Private repositories share the account's included minutes; verify the remaining allowance rather than assuming this project owns it. Scheduled workflows can be delayed. Disable the workflow if allowances are insufficient. Do not automatically make the repository public or purchase additional minutes.

The ingestion entry point checks database size before each source and stops at 750 MB; this is a conservative guard, not a guaranteed storage cap. A single ingestion can exceed it, and PostgreSQL/WAL/provider accounting differs. Monitor Neon compute, transfer and storage allowances separately. No evidence is automatically deleted. Review archival/retention before expanding history. Continuous public traffic can exhaust free compute even if storage remains small.

Render Free sleeps after 15 idle minutes and shares 750 monthly instance hours with other free services. If a payment method already exists, included bandwidth/build allowances can incur supplementary charges: inspect account billing controls before deployment. Free-tier selection alone is not proof of zero possible charges. Do not add keep-alive traffic to defeat idle suspension.

## Status

Configuration is prepared; hosted provisioning, credentials, quota checks, role verification, hosted cold-start verification and public deployment are still pending. Local/Compose verification does not establish hosted compatibility.

## Official references (reviewed 14 October 2026)

- https://render.com/docs/free
- https://render.com/docs/faq
- https://neon.com/blog/neon-free-plan-1-gb-per-project
- https://neon.com/blog/postgres-18
- https://docs.github.com/en/billing/reference/product-usage-included
