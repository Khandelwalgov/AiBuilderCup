.PHONY: setup db migrate seed api web contracts check test-e2e test-product-e2e preflight gemini-smoke extraction-smoke
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
	cd apps/api && uv run ruff check . ../../infra/deploy.py ../../infra/deploy_frontend.py ../../infra/corpus_job.py ../../infra/worker_secret.py ../../infra/production_gate.py ../../infra/smoke.py ../../scripts/release_container_check.py ../../scripts/product_e2e_server.py && uv run ruff format --check . ../../infra/deploy.py ../../infra/deploy_frontend.py ../../infra/corpus_job.py ../../infra/worker_secret.py ../../infra/production_gate.py ../../infra/smoke.py ../../scripts/release_container_check.py ../../scripts/product_e2e_server.py && uv run pytest && uv run alembic check
	cd apps/web && pnpm lint && pnpm typecheck && pnpm build
test-e2e:
	cd apps/web && pnpm exec playwright test

# Requires the explicitly local fictional Firebase Auth emulator; see docs/real-user-acceptance.md.
test-product-e2e:
	cd apps/web && pnpm exec playwright test --config playwright.product.config.ts

preflight:
	cd apps/api && uv run python -m opportunity_platform.operations.readiness

# One bounded paid-model probe; does not fetch sources or publish anything.
gemini-smoke:
	cd apps/api && uv run python -m opportunity_platform.operations.gemini_smoke

extraction-smoke:
	cd apps/api && uv run python -m opportunity_platform.operations.extraction_smoke

# Plan by default; explicit opt-in creates only disposable random test schemas.
finale-demo:
	cd apps/api && uv run python ../../scripts/finale_demo.py $(ARGS)

release-local:
	$(MAKE) preflight
	$(MAKE) contracts
	$(MAKE) check
	$(MAKE) test-e2e

# Public acquisition only: no model calls, publication or product-database writes.
# Override with CORPUS_ARGS='--dry-run' or '--source rajasthan-scholarships'.
.PHONY: corpus-collect corpus-update corpus-verify corpus-report
corpus-collect:
	cd apps/api && uv run python -m opportunity_platform.corpus.cli collect $(CORPUS_ARGS)

corpus-update:
	cd apps/api && uv run python -m opportunity_platform.corpus.cli update $(CORPUS_ARGS)

corpus-verify:
	cd apps/api && uv run python -m opportunity_platform.corpus.cli verify $(CORPUS_ARGS)

corpus-report:
	cd apps/api && uv run python -m opportunity_platform.corpus.cli report $(CORPUS_ARGS)
