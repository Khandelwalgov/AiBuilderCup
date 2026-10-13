# Phase 2 validation record

Validation used local PostgreSQL 17, Python 3.12, Vite and Chromium. No paid cloud resources were created. Existing development fixture records were preserved. PostgreSQL tests create and remove isolated schemas rather than truncating the application database.

| Executed command / check | Result |
|---|---|
| `uv run alembic upgrade head` | Applied `fcc8ecdfdfad` on the existing Phase 1 development database |
| `make contracts` | Exported FastAPI OpenAPI and regenerated TypeScript types |
| `make check` | Ruff lint/format, PostgreSQL tests, Alembic drift, ESLint, TypeScript and production build passed |
| `uv run pytest -q` | 42 passed, 1 optional live test skipped |
| `RUN_LIVE_SOURCE_TESTS=1 uv run pytest -q tests/test_pipeline.py::test_live_official_source_capture` | 1 passed; real official PDFs fetched and parsed, no model call |
| `PLAYWRIGHT_BROWSERS_PATH=/tmp/opportunity-browsers make test-e2e` | 6 Chromium journeys passed |
| `pnpm format` | Frontend formatted with repository Prettier configuration |
| `git diff --check` | No whitespace errors |

The full suite includes actual migration upgrade/downgrade/re-upgrade and old-account preservation, strict publication visibility, draft isolation, duplicate ingestion, reverted source content requiring new review, non-admin rejection, forged-citation rejection, immutable publication, source failure preservation, profile ownership, protected mutation CORS preflight and version/fact-snapshot persistence. API evaluation covers national, Rajasthan domicile and Dausa residence rules against one authorized synthetic profile. Unit cases cover nested three-valued AND/OR, stale/future/conflicting facts, income definitions, documentary gaps, substantive disqualifiers, invalid rule types and stable blocker identity.

The live-source test captured 68 pages from the 2024 guidelines and 2025 amendment into a temporary schema, recorded hashes/metadata and correctly returned `extraction_blocked / gemini_not_configured`. That schema is removed afterward; this does not populate the application's admin queue or public catalogue. It proves fetching/parsing/persistence and missing-configuration behavior, not successful Gemini extraction.

Browser journeys cover actual database-backed synthetic discovery/filter/detail, mobile Hindi/navigation, recoverable network failure, default real-only catalogue and unauthenticated profile denial. Profile editing → opportunity → cited eligibility and admin evidence inspection → publication use **explicit test-only API mocks**. No application auth bypass or synthetic extraction provider is shipped. Screenshots were visually inspected for profile, requirement outcomes and candidate review; the screenshots contain fictional test data.

Real Firebase sign-in and real Gemini extraction/publication were not executed: `FIREBASE_PROJECT_ID`, Firebase Application Default Credentials and `GEMINI_API_KEY` were absent. Live extraction quality, amendment interpretation and source completeness remain unmeasured. JSON schema generation and SDK call configuration are tested, including no tools, disabled automatic function calls and rejection of injected role/publication fields. These tests cannot establish that every model output is semantically correct.

Known warnings: FastAPI/Starlette's TestClient emits an httpx deprecation warning; Alembic emits its existing path-separator configuration deprecation warning. Checks pass with these warnings. They do not indicate a tested live account or a deployed service.

Next validation requires configured credentials: sign in, bootstrap an admin, ingest the actual PDFs, inspect/correct the full candidate against both originals, publish it, create a fictional personal profile and evaluate through the browser. Record extraction accuracy and missing conditions before expanding source coverage or implementing scheduling.

Phase 2.5 follow-up (13 October 2026): [live integration record](phase-2.5-validation.md) supersedes the earlier credential assumption. Local ADC exists and refreshed successfully; a selected/configured Firebase project, web config, admin UID and Gemini key remain missing. Expanded checks pass, but no real extraction/publication/authenticated acceptance or deployment has occurred.
