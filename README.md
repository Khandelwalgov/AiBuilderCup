# Opportunity Intelligence · Phase 2

Working name: **Unclaimed**. React + TypeScript/Vite → FastAPI → PostgreSQL, with Firebase Authentication and server-side Google GenAI extraction. Phase 2 adds an official-source ingestion, human review, publication and deterministic personal eligibility pipeline while preserving the Phase 1 interface.

**Validation status:** the official PDFs were fetched and parsed live. Gemini and real Firebase sign-in require credentials that were unavailable during implementation. No real opportunity was extracted, reviewed or published during validation. The normal public catalogue is therefore empty; it never substitutes synthetic records. Automated extraction/review tests use clearly fictional data confined to tests.

## Local setup

Prerequisites: Docker Desktop, Python 3.12+, `uv` 0.11.28, Node.js 24+, `pnpm` 11.25.0. From the repository root:

```sh
cp apps/api/.env.example apps/api/.env
cp apps/web/.env.example apps/web/.env.local
make setup
make db
make migrate
make seed       # optional, six clearly fictional development examples
make contracts
```

Start `make api` and `make web` in separate terminals. Open [the app](http://127.0.0.1:5173), [API docs](http://127.0.0.1:8000/docs) or [readiness](http://127.0.0.1:8000/health). Migrations preserve Phase 1 records. `docker compose stop` retains the database volume. Use `UV_CACHE_DIR=/tmp/opportunity-uv-cache` if the default cache is restricted.

Normal discovery exposes only the explicitly selected, reviewed real version. To inspect the old fixtures locally, set `ENABLE_DEVELOPMENT_CATALOGUE=true` in the API environment and optionally `VITE_ENABLE_DEVELOPMENT_CATALOGUE=true` in the web environment, restart, then open `/discover?development=true`. Development mode exposes synthetic records only, labels them, and cannot publish or evaluate them. Both switches default to false; never enable them for production.

## Credentials and first administrator

1. In Firebase, register a web app, enable Google Authentication, and authorize localhost/127.0.0.1 and the deployment domain. Set `VITE_FIREBASE_API_KEY`, `VITE_FIREBASE_AUTH_DOMAIN`, `VITE_FIREBASE_PROJECT_ID`, and `VITE_FIREBASE_APP_ID` in `apps/web/.env.local`.
2. Set the same `FIREBASE_PROJECT_ID` in `apps/api/.env`. Configure appropriately authorized Application Default Credentials (`gcloud auth application-default login`, or a credential file **outside** this repository). The API validates Firebase ID tokens with revocation checking; there is no auth bypass.
3. Set server-only `GEMINI_API_KEY` and `GEMINI_MODEL`. The configured default is `gemini-3.8-flash`; select a model available to your project. The locked SDK is `google-genai` 2.29.0. Extraction uses JSON schema output, Pydantic validation, and exact recorded-page quote checks. No private profile facts are sent to Gemini.
4. Restart the servers, sign in, then grant the first administrator from a trusted operator terminal with database and Firebase IAM access:

```sh
cd apps/api
uv run python -m opportunity_platform.admin.bootstrap --project-id YOUR_PROJECT_ID --uid YOUR_FIREBASE_UID
# To revoke:
uv run python -m opportunity_platform.admin.bootstrap --project-id YOUR_PROJECT_ID --uid YOUR_FIREBASE_UID --revoke
```

Bootstrap verifies that the Firebase account exists and is enabled, updates the database role, and writes an audit event. The command requires operator privileges; no HTTP route, browser field or caller-supplied role grants admin access. Refresh the app after role changes. Backend authorization rechecks the database on every admin request.

`CORS_ORIGINS` is a JSON list; authenticated PUT/POST and OPTIONS preflight are supported. `VITE_API_BASE_URL` stays blank for the local Vite proxy, or holds the HTTPS API origin at build time. `VITE_*` configuration is public: never place server secrets there.

## Official source and execution

One source-specific adapter, `depwd-pre-matric`, targets **only the pre-matric scholarship section and applicable common conditions**, combining these official DEPwD documents:

- [Official scholarship index](https://depwd.gov.in/en/scholarship/).
- [Full guidelines, 25 September 2024](https://cdnbbsr.s3waas.gov.in/s3e58aea67b01fa747687f038dfde066f6/uploads/2024/09/202409261656732428.pdf).
- [Amendment, 4 September 2025](https://cdnbbsr.s3waas.gov.in/s3e58aea67b01fa747687f038dfde066f6/uploads/2025/09/202509111852335844.pdf).

The live check parsed 61 + 7 PDF pages. This is selected-document coverage, **not** a claim that the application round is open or that all subsequent amendments have been discovered. Reviewers must check the official index for completeness before publication. See [source policy](docs/source-policy.md).

A signed-in administrator can open `/admin` and click **Ingest source**, or run:

```sh
cd apps/api
uv run python -m opportunity_platform.ingestion.service \
  --source depwd-pre-matric --actor-uid YOUR_FIREBASE_UID
```

Fetches enforce host allowlists, robots checks, HTTPS validation, size/page limits, timeouts and bounded retries. Runs, source fingerprints and text snapshots are persisted. A per-source advisory lock and configurable minimum interval serialize and rate-limit runs. Identical consecutive bytes reuse the snapshot and latest candidate without another model call; a reversion to older captured bytes creates a fresh review candidate; failed extraction can retry the same snapshot after configuration is fixed. Rejected candidates do not automatically reappear on unchanged input.

A missing key produces `extraction_blocked / gemini_not_configured` after saving the fetched snapshot. Invalid model output/citations produce `extraction_failed`. Neither creates a public record. A fetch failure updates source freshness diagnostics and leaves the last published version intact.

## Complete configured journey

1. Administrator ingests the official source at `/admin`.
2. Open the candidate; inspect original-document links, captured page text, proposed rules, metadata citations, review flags, and differences from the current publication. Correct the structured JSON if needed; edits are validated against captured evidence.
3. Add a review note and confirm completeness/flags, then approve, reject, or request further review. Approval atomically writes immutable reviewed rules/citations and moves the published-version pointer. A newer draft cannot displace the published version.
4. Sign in as a personal user. At `/profile`, enter **fictional demo information only**, adding relevant facts progressively. Blank values are unknown; user facts remain unverified. Income requires the exact definition and period from the rule; no household sum is inferred.
5. Browse `/discover`, open a reviewed opportunity and click **Check my eligibility**. The backend evaluates stored typed rules against only the caller's profile and persists the rule version, fact snapshot, engine version and result time.
6. Inspect satisfied, not satisfied and unknown requirements, original clauses, facts used and next steps. Missing documents remain evidence gaps. A substantive failure remains a failure even when an unrelated document is added. All-satisfied results are preliminary potential matches, never official approval or verified application readiness.

The review editor is an advanced JSON interface with evidence alongside it. English/Hindi navigation, forms and outcome labels are localized; original policy passages and deterministic explanations retain English/source language. There is no conversational AI assistant in this milestone.

## API and persistence

All resource endpoints are under `/v1`; see generated `/docs` for schemas.

| Endpoints | Access / purpose |
|---|---|
| `GET /opportunities`, `/opportunity-facets`, `/opportunities/{id}` | Public, reviewed real versions; explicit gated development mode |
| `GET /me` | Firebase caller identity and server-resolved admin role |
| `GET/PUT /profile/me`, `GET /people/{id}` | Firebase caller's own profile only; other profiles return 404 |
| `POST /opportunities/{id}/evaluate` | Caller-owned facts against published real rules |
| `GET /admin/sources`, `POST /admin/sources/{key}/ingest` | Database-authorized administrators only |
| `GET /admin/ingestion-runs` | Privileged run diagnostics |
| `GET /admin/reviews`, `GET/POST /admin/reviews/{id}` | Admin queue, evidence, diff, correction and publication |

Migration `fcc8ecdfdfad` extends `57d3f03c34e3`: explicit publication pointer/state, version extraction/snapshot/category, server-managed admin role, snapshots, ingestion runs, candidate reviews and audit events. Old rows remain draft/unpublished. Services enforce immutability; no DB trigger protects against a privileged SQL operator. Public catalogue counts include only currently selected reviewed real publications, never drafts or fixtures.

Domain code lives in `ingestion/`, `admin/`, `profiles/`, `eligibility/`; `workflows.py` adapts HTTP. Closed typed rules support nested AND/OR, numeric comparisons, membership, geography, dates, income contexts and evidence prerequisites. No expressions are executed. Stable blocker hashes and fact keys prepare the future unlock graph. Household/business rule contexts currently return unknown pending authorized context support.

## Checks and reproducibility

```sh
make check
make contracts
# Generated files must match the backend; do not edit them by hand.
cd apps/web
pnpm exec playwright install chromium
pnpm exec playwright test
# Optional live network check, from apps/api:
RUN_LIVE_SOURCE_TESTS=1 uv run pytest -q tests/test_pipeline.py::test_live_official_source_capture
```

`make check` runs Ruff, PostgreSQL integration tests, Alembic drift detection, ESLint, TypeScript and production build. Tests use isolated schemas, removed afterward, without truncating application data. Set `TEST_DATABASE_URL` for a separate database; the role needs schema creation permission. The migration test upgrades the actual Phase 1 schema, preserves an existing account, checks drift and exercises downgrade/re-upgrade. Browser tests start local servers if necessary; existing API servers must have `ENABLE_DEVELOPMENT_CATALOGUE=true` for fixture regressions. Run `make migrate seed` first.

Browser profile/evaluation tests use explicitly mocked auth/API responses confined to tests; other browser journeys use the actual database-backed public API. Backend tests override identity only inside tests and exercise actual PostgreSQL services, permissions, review/publication, source failures, unknown outcomes and exact evidence validation. The opt-in live test fetches the real PDFs with extraction intentionally unconfigured. Live Gemini output quality and real Firebase login are **not** validated by test doubles. See [validation record](docs/phase-2-validation.md) for executed results.

## Limits and next milestone

No cloud resources were provisioned or deployed; [deployment preparation](infra/README.md) remains available. Add the new server environment variables when deploying and choose a request timeout adequate for synchronous ingestion. There is no scheduler, automatic selective re-evaluation, notification delivery, full PDF binary archive/GCS integration, document upload/verification, family consent workflow, business UI, application submission or graph planner. Public text snapshots and binary hashes are saved in PostgreSQL; original binaries are not retained. Unexpected process termination may roll back a run rather than leaving durable crash history.

Data export/deletion and verified-document correction flows are not implemented. Use synthetic personal information only. Do not onboard real sensitive data before retention, export/deletion and consent controls are ready. Source failure warnings appear in detail; manual checks are the only freshness guarantee. Exact quotation matching prevents fabricated quotes, but cannot prove semantic extraction correctness—human review is essential.

**Next milestone:** configure Firebase/Gemini, measure extraction on these real documents and complete a live reviewed-publication demo. Then add secure synthetic-document verification and one shared-blocker action that updates several version-aware evaluations. Preserve the existing architecture and truthful coverage boundaries. [Phase 2 decisions](docs/decisions/0002-reviewed-intelligence.md) supersede Phase 1 publication behavior.

Phase 2.5 adds bounded model requests, sanitized failure codes, evidence preservation, production configuration guards and a plan-first deployment runner. See [live integration validation](docs/phase-2.5-validation.md) and [deployment procedure](infra/README.md). Run `make preflight` before attempting live acceptance; configuration readiness does not prove Firebase permissions or Gemini access.

Phase 2.6: [live integration audit](docs/live-integration-audit.md) records selected-project configuration/IAM checks, real Gemini failures, the Firebase initial-state query fix, regression results and exact user actions. A passing configuration preflight does not establish working Google sign-in or a generated/published opportunity.

Phase 2.7 confirms existing Google/admin configuration and adds `make gemini-smoke` for one bounded real generation probe. The latest [audit update](docs/live-integration-audit.md) records the continuing provider 503, schema-scoped ingestion locks, regression results and pending genuine draft. A smoke failure must stop full extraction; no source data is fabricated.


## Explicit extraction providers

Gemini remains the default (`AI_EXTRACTION_PROVIDER=gemini`), using `GEMINI_API_KEY` / `GEMINI_MODEL`. For authorized development only, explicitly set `AI_EXTRACTION_PROVIDER=openai`, `OPENAI_API_KEY` and `OPENAI_MODEL=gpt-5.6-terra` in ignored `apps/api/.env`. Restart the API after configuration changes. Neither provider falls back to the other. Keys are backend-only; never use `VITE_OPENAI_API_KEY` or place an OpenAI key in the Gemini slot. `make preflight` checks the selected provider's configuration; `make extraction-smoke` makes one small real request and exits nonzero on failure.

OpenAI uses a strict transport schema while original Pydantic/citation validation still decides whether a draft can be created. Source hashes, provider/model/extractor identity and token usage are persisted on runs/versions; failed public-source output is explicitly unvalidated privileged diagnostics, never a publishable version. Repeated identity/snapshot processing is idempotent and cannot move the publication pointer. See [provider decision](docs/decisions/0006-explicit-extraction-providers.md).

**Current validation:** one genuine DEPwD draft exists in `/admin`, unpublished and requiring substantive human review. Gemini's free-tier alternative was documented but not live-tested because the replaced Google key is unavailable. See the current [integration audit](docs/live-integration-audit.md) for measured calls, costs, tests and identified review gaps.

## Nightfall product workflows

The local app now includes household creation/primary selection and guardian-authorized dependent profiles (`/family`), role-protected business profiles (`/businesses`), and the version-aware Unlock Graph/checklist (`/plan`). Start with a personal profile. Dependent profile edits use `/people/{id}/edit`; authorization is checked by the backend. Household income is never inferred or summed. Unregistered businesses need no GST/Udyam identifier. Invited adult connections remain unavailable.

Plans use only current real publications. With no approved records, the plan correctly shows empty coverage. Shared information/evidence dependencies persist as reusable actions; substantive failures remain separate. Age-correction simulations are hypothetical and save nothing. Actual fact edits selectively preserve and recompute previous assessments. Fresh/renewal is chosen per opportunity when checking eligibility.

English/Hindi cited explanations are local and deterministic. Gemini can optionally classify generic question concepts when `AI_ASSISTANT_LIVE_ENABLED=true` and a valid Gemini key is configured; no raw question/profile is sent. This flag defaults false and no new live AI call was made overnight. OpenAI remains an explicit extraction-only development provider, with no automatic fallback.

Two real draft candidates remain private in `/admin`. The Post-Matric candidate is **manual curation of an existing capture**, not a fresh fetch/AI extraction; its provider metadata says so. Review every requirement and amendment before publication. The admin UI now offers structured corrections and document-specific evidence; advanced JSON is optional. See [Nightfall progress](docs/overnight-progress.md), [draft correction report](docs/nightfall-draft-corrections.md) and [subject/planner decision](docs/decisions/0007-authorized-subject-planning.md). No cloud deployment occurred.
