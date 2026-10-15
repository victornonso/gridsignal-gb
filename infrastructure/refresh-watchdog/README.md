# Independent refresh watchdog

The primary GitHub workflow collects every six hours. An hourly GitHub catch-up
check now retries overdue or failed collections without repeating healthy pulls.
GitHub cron delivery remains best-effort, so this Worker provides a separate
Cloudflare Cron Trigger at minute 47 of every hour.

The Worker reads public source observability, skips healthy collections, checks
for an existing workflow run, and dispatches only the GridSignal ingestion
workflow with `mode=due`. The workflow checks freshness again after queuing.
Database credentials remain in GitHub Actions; the Worker receives none.
No HTTP trigger or public administration endpoint is exposed.

## Deployment status

Source and automated tests are prepared. The Cloudflare Worker is **not deployed
or authorised yet**. The GitHub hourly recovery check is enabled independently
when the accompanying workflow change is pushed.

## Machine authentication

Use a GitHub App installed on **only `victornonso/gridsignal-gb`**, with repository
Actions read/write and the mandatory read-only metadata permission. No contents
write, organisation permissions or webhook subscriptions are needed. The Worker
signs a short-lived App JWT and mints an installation token restricted to this
repository for each recovery attempt. There is no expiring personal token that
requires periodic manual replacement.

Store these in Cloudflare's encrypted Worker secrets:

- `GITHUB_APP_ID`
- `GITHUB_INSTALLATION_ID`
- `GITHUB_APP_PRIVATE_KEY` (PKCS#1 or PKCS#8 PEM)

`GITHUB_ACTIONS_TOKEN` is an optional alternative for controlled testing; do not
copy a broad account credential into the Worker.

## Free deployment

Use the existing Cloudflare account's Workers Free plan. No paid subscription,
database or always-on server is required. Deploy `wrangler.jsonc` using the
official Wrangler CLI after account authorisation, then verify its Cron Trigger
and a real scheduled execution. A new trigger can take up to 15 minutes to
propagate. Never report the independent scheduler as active before that check.

Verify locally with:

```sh
node --test infrastructure/refresh-watchdog/watchdog.test.mjs
```

The tests cover healthy-source skipping, missing/overdue sources, an unavailable
status API, active-run suppression, dispatch scoping, authentication failure and
cryptographically verified GitHub App JWTs. Native GitHub recovery and independent
Cloudflare recovery still depend on upstream source availability; gaps and
collection failures remain visible instead of being relabelled as fresh.

References:
- https://developers.cloudflare.com/workers/configuration/cron-triggers/
- https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/authenticating-as-a-github-app-installation
