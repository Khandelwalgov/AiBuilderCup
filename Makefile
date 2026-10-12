.PHONY: setup db migrate seed api web contracts check test-e2e
setup:
	cd apps/api && uv sync --locked
	cd apps/web && pnpm install --frozen-lockfile
db:
	docker compose up -d --wait db
migrate:
	cd apps/api && uv run alembic upgrade head
seed:
	cd apps/api && uv run python -m opportunity_platform.seed --fixtures ../../data/fixtures/opportunities.json
api:
	cd apps/api && uv run uvicorn opportunity_platform.main:app --reload --host 127.0.0.1
web:
	cd apps/web && pnpm dev
contracts:
	cd apps/api && uv run python ../../scripts/export_openapi.py
	cd apps/web && pnpm generate
check:
	cd apps/api && uv run ruff check . && uv run ruff format --check . && uv run pytest && uv run alembic check
	cd apps/web && pnpm lint && pnpm typecheck && pnpm build
test-e2e:
	cd apps/web && pnpm exec playwright test
