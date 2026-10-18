# Local verification — 18 October 2026

Application baseline: local master `0b8237e4f2122a3c5ccd7e2b3b5383c419b37d48` (bounded Gemini payload-string transport). Initial checks required no application changes. After the separately authorized real request, a small backend-only change added sanitized inner-validation paths/types and an offline regression test. No UI changes. The request used e713eac, before that diagnostic change.

## Results

| Check | Result |
|---|---|
| Backend Ruff check | Passed, `src tests` |
| Backend Ruff format | Passed, 131 files already formatted |
| Full backend pytest | **347 passed, 9 skipped**, 38.91 seconds after the diagnostic change; six Alembic deprecation warnings (initial baseline: 346 passed) |
| Focused `test_gemini_transport.py` | **28 passed**, 0.16 seconds after the diagnostic change; offline serialization/provider responses only |
| Existing local neural model subset | **5 passed**, 3.88 seconds; `test_neural.py` plus existing-pinned-model research retrieval test |
| Frontend ESLint | Passed |
| TypeScript | Passed |
| Production frontend build | Passed; existing large-chunk warning is advisory |
| Standard Playwright suite | **38 passed**, 19.5 seconds; local servers, mixed endpoint checks and mocked UI responses |
| TEAM pages 1/12 plan | Generated locally; original hash and plaintext validated; **zero Google requests** |

The full-suite nine skips were four opt-in real-archive cases, four model-dependent cases (subsequently exercised separately with existing local weights), and one opt-in live official-source capture. The archive and live capture opt-ins were not run; no new crawling/OCR was requested. The five separate model tests include the four previously skipped cases plus another existing local-model test. Do not add the focused runs to 347 as if they were all distinct tests.

Both `DATABASE_URL` and `TEST_DATABASE_URL` were explicitly set to `postgresql+psycopg://opportunity:local-development-only@localhost:5432/opportunity`; a launcher validated both hosts against localhost/127.0.0.1/::1 before running checks. Backend fixtures created and removed random local `test_<uuid>` schemas. Regression tests did not modify production application data or the Gemini reservation schema. The subsequent separately authorized genuine attempt inserted two local reservation rows, retained the prior six, and recorded zero USD; no candidate/catalogue data was written. The local browser API used this same explicit local database configuration.

The initial sandboxed run could not connect to localhost PostgreSQL or bind browser servers. Those environment failures were resolved by running the same guarded commands with local-network permission. They were not application regressions. Final commands completed successfully.

Reproduction (run from repository root with the same explicit local URL in both database variables):

```sh
export DATABASE_URL='postgresql+psycopg://opportunity:local-development-only@localhost:5432/opportunity'
export TEST_DATABASE_URL="$DATABASE_URL"
export ENVIRONMENT=development
apps/api/.venv/bin/python -c 'import os; from sqlalchemy.engine import make_url; assert all(make_url(os.environ[k]).host in {"localhost", "127.0.0.1", "::1"} for k in ("DATABASE_URL", "TEST_DATABASE_URL"))'
cd apps/api
.venv/bin/ruff check src tests
.venv/bin/ruff format --check src tests
.venv/bin/pytest -q
.venv/bin/pytest -q tests/test_gemini_transport.py
NEURAL_TEST_MODEL_DIRECTORY=/private/tmp/unclaimed-embedding-model .venv/bin/pytest -q \
  tests/test_neural.py \
  tests/test_research_completion.py::test_local_multilingual_research_retrieval_with_existing_pinned_model
cd ../web
pnpm lint
pnpm typecheck
pnpm build
PLAYWRIGHT_BROWSERS_PATH=/tmp/opportunity-browsers pnpm exec playwright test
```

The model path is an existing local resource; do not download replacements automatically. Browser tests are not a substitute for actual Firebase Google Sign-In acceptance. No hosted acceptance was repeated because Neon is paused.

## Gemini status

The completed genuine attempt is recorded in `evidence/gemini-team-e713eac.json`. One countTokens and one generation ran; no further calls were authorized. The final diagnostic code was tested offline only.

The new Google-facing envelope and strict inner/source validation passed offline. The plan uses Google GenAI SDK 2.29.0. Three previous document attempts returned HTTP 400; the operator separately reports a simple payload-string diagnostic returned HTTP 200. Neither metadata/countTokens nor that diagnostic establishes successful ingestion of this TEAM document. **Generation has now succeeded in the separately authorized attempt, but validated government-document extraction remains unproven:** its inner contract rejected the output. See `evidence/gemini-team-e713eac.json`.

See `gemini-next-attempt-plan.md` for the preserved one-attempt authorization. It is consumed; the local daily reservation cap is now reached. No independent review, repair, fallback, import or publication was run.

## Public-repository safety and access

The configured remote is `https://github.com/Khandelwalgov/AiBuilderCup`. An anonymous GET returned **404** during this pass: public accessibility is not established (private, missing or renamed repositories can all return 404). No push, visibility change or upload was attempted.

A local scan checked 399 tracked files and 958 reachable Git history blobs for the exact configured backend secrets and private-key markers. Public localhost development credentials were explicitly classified as development defaults. No exact configured-secret or private-key marker matches remained after excluding the documented public localhost defaults; no tracked private-path findings were found. Ignored corpus blobs, private document storage, live evidence and `.env` files were not tracked. This is a scoped scan, not proof that all possible secrets/PII have been detected. Untracked operator diagnostic scripts were neither executed nor committed.

## Preserved production baseline and blockers

No production requests or mutations. Last known deployed commit `038594fb823136e6468cfaef79cd80e503800a0c`, Cloud Run `opportunity-api-00013-zoj`, Hosting `375a1c14fd8ab1fe`. Historical counts remain 96 research listings, 85 provisional comparison records across 11 programme parents, six unpublished policy drafts and zero published eligibility policies; this pass did not query current counts.

Immediate blockers: operator-reported Neon pause; missing qualifying document-generation evidence; repository inaccessible anonymously. Submission PDF/video remain uncreated. Presentation work was stopped on the operator's subsequent instruction to focus on coding. Team details supplied: OutOfTokens; Govind Khandelwal (leader), Divija Kejriwal. No public presentation file was authored or uploaded.
