.PHONY: setup db migrate ingest backfill api dashboard test backup
setup:
	uv sync --extra dev
	cd apps/dashboard && npm ci
db:
	docker compose up -d db
migrate:
	uv run alembic upgrade head
ingest:
	uv run gridsignal ingest --source all
backfill:
	uv run gridsignal backfill --source all --start $(START) --end $(END)
api:
	uv run uvicorn apps.api.app.main:app --port 8001
dashboard:
	cd apps/dashboard && npm run dev
test:
	uv run pytest -q
	cd apps/dashboard && npm run typecheck
backup:
	docker compose --profile backup run --rm backup

