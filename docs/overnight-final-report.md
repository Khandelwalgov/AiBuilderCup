# Nightfall final report — 15 October 2026

The existing product was preserved and extended with household/dependent and business workflows, a persisted shared-action planner and interactive Unlock Graph, safe what-if preview, progressive profile questions, structured policy review, a cohesive responsive design, and local English/Hindi cited explanations. **This is a tested local implementation, not a deployed or fully authenticated live acceptance claim.**

Two genuine official-source candidates are in the administrator queue. Neither is published. Nightfall made **zero live model calls**, spent no additional AI budget, created no administrator, provisioned no cloud resources and deployed nothing. Pre-existing uncommitted integration/provider/auth work was preserved in the first milestone commit.

## Feature matrix

“DB tests” below means real local PostgreSQL in disposable isolated schemas with fictional identities/policies. “Browser contract” means explicitly mocked identity/API responses confined to tests, not actual Firebase acceptance.

| Feature | Code complete | Live working | Tests | Remaining blocker |
|---|---|---|---|---|
| Authentication | Existing verified-token foundations retained | Prior user-reported Google login; not observed as an authenticated browser journey overnight | Token/admin boundaries and localized errors | Real sign-in acceptance with fictional test accounts |
| Personal profile | Yes, progressive optional questions and provenance | Local DB service; populated browser contract | Persistence, isolation, relevant-fact refresh | Real Firebase UI acceptance |
| Household creation | Yes, naming, primary preference, multiple households | Local DB service + browser contract | Owner isolation | Real authenticated acceptance |
| Managed dependent | Yes, explicit guardian assertion, dated relationship, editing and self-revocation | Local DB service + browser contract | Cross-account denial, revoked access, retained history | Genuine guardian assertions are user responsibility; adult invitations remain P1 |
| Household matching | Partial: explicit authorized context, no inferred income | Isolated evaluation | Personal/household contexts differ; unauthorized facts unknown | Scheme-specific sibling/twin/income logic remains unknown |
| Business profiles | Yes, unregistered status, supported facts, membership roles | Local DB service + browser contract | Viewer/editor/owner isolation | Real authenticated acceptance |
| Business matching | Common subject-aware engine implemented | No reviewed real business coverage | Generic typed engine and business permission tests | No real business opportunity; registration-location/complex income semantics limited |
| Official-source ingestion | Existing live capture/extraction preserved; second adapter added | Prior 68-page capture/OpenAI extraction; second draft is offline manual curation | Providers, idempotency, failures, actual saved-page citations | Gemini key/service; further model calls require authorization |
| Admin review | Structured corrections, categories, contexts and document evidence | Two actual persisted drafts corrected through audited service | Exact evidence, optimistic hash, role/immutability guards; mocked browser review | Human substantive review; complex rule editing still uses optional JSON |
| Publication | Yes, explicit human approval and per-document evidence required | Zero real publications, intentionally | Isolated review/version tests | Human approval and completeness review |
| Opportunity discovery | Yes, real-only publication pointer and gated fixtures | Actual API returns zero real records | Actual DB/browser discovery, filtering, empty/error states | Approved real records |
| Individual eligibility | Yes, typed rules, evidence unknowns, scoped fresh/renewal | Isolated DB + browser contract | Known blockers, unknowns, citations, context separation | Real published-source authenticated acceptance |
| Shared blockers | Yes, explicit compatible dependencies, income context retained | Isolated two-opportunity scenario | Shared evidence, tree-shape independence, distinct income definitions | Enough genuinely reviewed compatible real rules |
| Action planner | Yes, persisted links and authorized pending/in-progress status | Isolated DB + browser contract | Progress cannot verify evidence; obsolete version links removed | Real multi-opportunity acceptance |
| Unlock Graph | Yes, interactive dependency map, selected evidence, accessible checklist | Rendered fictional browser contract | Desktop/mobile graph and citation panels | Real populated acceptance; graph does not render every fact as a separate node |
| What-if simulation | Yes, hypothetical age correction only | Isolated DB + browser contract | No facts/evaluations/actions saved; restrictions/evidence preserved | Broader simulations deliberately not implemented |
| Version re-evaluation | Relevant fact edits automatic; source-version refresh explicit | Isolated fictional amendment flow | Previous snapshots retained, current links replaced, unrelated facts skipped | No automatic scheduler/alerts; real publication pending |
| English/Hindi AI explanations | Partial: local cited explanations; optional Gemini intent classification | Local explanations tested; zero new AI calls | Citation/permission tests; mocked Gemini gets generic concepts only | Valid Gemini key/live acceptance; unrestricted generative explanations not implemented |
| UI redesign | Cohesive shell, dashboard, discovery, profile, contexts, graph and structured admin | Actual public/empty states; fictional populated contracts rendered | Four widths EN/HI, overflow/runtime checks, keyboard focus | Real authenticated populated acceptance; not a full WCAG certification |
| Production build | Web build and locked API image pass | Local non-root container health/DB smoke | Lint/types/build, migration drift, container auth boundaries | Hosted configuration |
| Cloud deployment readiness | Plan-first workflow and release docs prepared | No deployment | Local plan, configuration guards, Docker/public smoke | Explicit project/region/budget/database/IAM/secrets/deploy approval |

## Real source data and safeguards

- Pre-Matric candidate: `9588fed8-1f25-423d-8b5f-890636e68695`. **Draft**; 17 requirement groups, nine document citations, 36 total validated citations. Original OpenAI `gpt-5.6-terra` extraction/provider/hash/usage is unchanged. Original eight-group extraction is retained in the first correction's `CandidateReview.before`; three audited correction entries now exist. Class IX/X, full-time enrollment and school recognition are typed. Repeated class and renewal conditions are distinct. Unsupported income, household and exception interpretations remain unknown.
- Post-Matric candidate: `db51eb5b-5972-4d5a-8b13-85144f2f62d5`. **Draft**; 20 conditions, eight document citations, 34 total validated citations. Provider `manual-curation`, model/usage absent, extractor `depwd-post-matric-curation-v1`. It reuses the existing official capture; no new fetch or AI generation is claimed. Its adapter-associated snapshot records original-capture reuse provenance.
- Both snapshots contain the same captured 68-page official bundle and hash `32d14860c90b70276d91d12eb4e23d8f2eed4851c9f2798b103d060f93214446`. All 70 citations were checked against the actual stored URL/page text. Both snapshot/source associations passed. Exact quotation does not prove semantic completeness.
- Two component adapters cover one selected document bundle, not two independent monitored portals or comprehensive coverage. Zero real publications. Six existing clearly synthetic development catalogue records remain preserved and excluded from normal discovery.
- No real draft was regenerated, approved or published. Original snapshots, audit/review history and previous data remain. No personal profiles were overwritten for acceptance testing. Actual publication is the user's decision.
- New future extraction schemas carry document evidence and policy/application-context tags through conversion. Version identifiers are now `policy-candidate-v3` (Gemini) / `policy-candidate-openai-v2` (OpenAI); historical extraction metadata remains unchanged. A future explicitly initiated ingestion may therefore generate a new candidate even with unchanged bytes. Do not initiate it without an authorized model budget.

Final read-only evidence: `.live-validation/nightfall-source-audit.json`. Original/corrected draft artifacts: `.live-validation/nightfall-original-draft.json` and `.live-validation/nightfall-corrected-draft.json`.

## Executed validation

| Command/check actually executed | Final result |
|---|---|
| `uv run alembic upgrade head` (API directory) | Additive local migrations applied, existing data retained |
| `make contracts` | OpenAPI/TypeScript regenerated from backend |
| `make preflight` | Configuration checks pass; explicit local extraction provider OpenAI; not proof of external permissions |
| `make check` | Passed: Ruff, PostgreSQL tests, Alembic drift, ESLint/types/build |
| Backend `pytest` | **99 passed, one optional live-source test skipped**, zero failures |
| `PLAYWRIGHT_BROWSERS_PATH=/tmp/opportunity-browsers make test-e2e` | 14 passed; no final browser failures |
| Focused PostgreSQL tests | Draft provenance, workspace permissions/revocation, planner/simulation/context/version/assistant cases passed |
| Focused browser contracts after screenshot refinement | Five passed after final UI/screenshot refinement |
| `docker build --pull=false -t opportunity-api:nightfall apps/api` | Final schema-versioned image built with frozen dependencies and normal TLS; public smoke passed |
| Native and container public smoke | `/live`, `/health`, `/v1/opportunities` 200; anonymous admin/workspace access 401; real catalogue total zero |
| Container inspection | UID 1000, no `/app/.env`, no embedded Gemini/OpenAI key; smoke container removed |
| `python infra/deploy.py --config .live-validation/nightfall-deploy-plan-config.json` | Plan only; illustrative public placeholders; zero cloud commands |
| `uv run python ../../scripts/product_smoke.py --api-url http://127.0.0.1:8000` | Public-only smoke passed after restoring API |
| Same script at `http://127.0.0.1:18080` | Final image public smoke passed |
| `git diff --check` | Passed before milestone commits |

Browser breakdown: nine actual public/database/unauthenticated-state journeys (including one controlled network failure), four mocked populated API contracts, and one localized-error unit check. None proves a real Firebase-authenticated private journey. Backend AI/source tests use mocks except the offline validation of genuinely captured public pages. The optional new live fetch test was skipped; there were no new live model/fetch calls.

Temporary lint/type issues were fixed before passing checks, including an untyped capability response and a missing frontend action mutation binding. One public smoke attempt ran while the test server had shut down; the normal server was restored and smoke passed. Existing Starlette/httpx and Alembic deprecation warnings remain; no failing tests were discarded. New dependencies: **none**.

## Migrations and modules

Nightfall added `b81f7a40c621` (requirement category/application context) and `c92d8b51d732` (explicit household owner, business description, action identity/details). Existing `a70d81ea2f20` provider provenance was preserved in the first integration checkpoint commit. Upgrade/downgrade/re-upgrade and old-account preservation pass; Alembic reports no drift.

Core changes: `subjects/service.py`, `planning/service.py`, `profiles/dashboard.py`, `eligibility/{rules,engine,service,refresh}.py`, `assistant/service.py`, `ingestion/{schemas,adapters,curated_depwd,gemini,providers}.py`, `admin/service.py`, models/workflows/config, generated contracts, and React shell/profile/admin/discovery/workspace/assistant components and styles. The exact file manifest follows at the end.

## Visual artifacts

Ignored directory `.live-validation/ui/`: 56 real public/protected-empty-state captures across 1440/1024/390/320px and EN/HI, plus populated fictional contract screenshots. Dashboard desktop, Hindi narrow discovery, family, graph desktop/Hindi mobile, profile and admin output were inspected. Earlier full-page screenshots captured fixed navigation at the scrolled offset; tests now scroll to top and explicitly use 1440px for populated desktop captures.

Useful files: `dashboard-en-1440.png`, `discover-hi-320.png`, `family-populated-contract-1440.png`, `business-populated-contract-1440.png`, `graph-populated-contract-1440.png`, `graph-populated-contract-hi-320.png`, `profile-populated-contract-1440.png`, `eligibility-populated-contract-1440.png`, `admin-populated-contract-1440.png`. These contain fictional/public data, not real authenticated acceptance.

## Remaining work and release boundaries

Human source review/publication, true Firebase private acceptance, a successful authorized Gemini call and cloud deployment are outstanding. Household income/sibling/twin interpretation remains unknown; no real business source is reviewed. The assistant generates deterministic local explanations and optionally uses Gemini for intent only. Adult invitations, private document upload/verification, export/deletion, scheduled refresh/notifications and application submission remain unavailable. Use fictional personal information. No measured impact/approval/accuracy claims were invented.

Deployment needs explicit production project/region/cost approval, hosted PostgreSQL/Cloud SQL connection, runtime/migration IAM, pinned secrets, Firebase domains, HTTPS CORS/API origin and approved operator execution. Budget alerts are not a cap. See `docs/submission-readiness.md` and `infra/README.md`. The optional authenticated smoke script refuses existing profiles and must use a dedicated fictional account; that mode was prepared but **not run**.

## Five things the user should do after waking up

1. **Substantively review both real drafts at `http://127.0.0.1:5173/admin`.** Inspect amendments, document evidence, benefit/slot/renewal/income uncertainties and later notices. Correct as needed; approve only if ready. No approval has been given on your behalf.
2. Sign in with a dedicated fictional account and exercise `/profile` → `/family` → `/businesses` → `/plan`. Test a separate account's access denial and guardian revocation. Confirm published-source matching/citations, task progress and non-saving simulation. Current main-database public coverage is zero until step 1.
3. Restore a valid Gemini key/select an available model, then authorize a bounded live smoke/acceptance request. Keep `AI_ASSISTANT_LIVE_ENABLED=false` until intended; OpenAI extraction remains explicit and no automatic provider fallback occurs. Do not reuse the old test budget implicitly.
4. Review deployment prerequisites and authorize exact production project, region, database size, budget, IAM and pinned secrets before any `--execute`/provisioning command. The reviewed local image is `opportunity-api:nightfall`; the plan-only file is `.live-validation/nightfall-deploy-plan.txt`.
5. Rehearse `docs/demo-script.md`, verify truthful coverage/limitations, and record the three-minute submission after the real acceptance gates pass. Run `make preflight`, `make contracts`, `make check`, `make test-e2e` from `/Users/govind/Projects/AIBuildersCup`; see `docs/submission-readiness.md`.

## Local commits

- `b86e37e` — Preserve live integration and correct draft document provenance; add subject foundations.
- `25ecb99` — Implement authorized household and business contexts, reusable unlock planner and responsive civic UI.
- `958bb59` — Add source-backed second draft, scoped renewal rules, bilingual explanations and safe action progress.
- `4b2c876` — Preserve extraction policy contexts and verify final accessible review workflows.
- The release-documentation commit is listed in `.live-validation/nightfall-commits.txt`, generated after the report checkpoint. Use `git log --oneline fb9902e..HEAD` for the complete local history. Nothing was pushed.

## Final executed checkpoint

Backend: **99 passed, one skipped**. Full browser suite: **14 passed**, then five focused checks passed after final UI/screenshot refinement. Frontend lint/type/build and migration drift passed. Seventy actual saved-page citations validated; zero real publications. Final image ID: `sha256:d89481b76187bb37aa4929df886ccd4dc8e5fa3df93ee5d3b6140940774fc79d`. The final image smoke passed; default provider Gemini, `policy-candidate-v3`, live assistant disabled, UID 1000 and no embedded keys. Structured results: `.live-validation/nightfall-validation-summary.json`; commit list: `.live-validation/nightfall-commits.txt`. No new live AI call, deployment, cloud resource, admin or additional model expenditure.

## Exact changed-file manifest

- [.env.example](/Users/govind/Projects/AIBuildersCup/.env.example)
- [DESIGN.md](/Users/govind/Projects/AIBuildersCup/DESIGN.md)
- [Makefile](/Users/govind/Projects/AIBuildersCup/Makefile)
- [README.md](/Users/govind/Projects/AIBuildersCup/README.md)
- [apps/api/.env.example](/Users/govind/Projects/AIBuildersCup/apps/api/.env.example)
- [apps/api/Dockerfile](/Users/govind/Projects/AIBuildersCup/apps/api/Dockerfile)
- [apps/api/alembic/versions/a70d81ea2f20_extraction_provider_provenance.py](/Users/govind/Projects/AIBuildersCup/apps/api/alembic/versions/a70d81ea2f20_extraction_provider_provenance.py)
- [apps/api/alembic/versions/b81f7a40c621_requirement_context.py](/Users/govind/Projects/AIBuildersCup/apps/api/alembic/versions/b81f7a40c621_requirement_context.py)
- [apps/api/alembic/versions/c92d8b51d732_subject_workspaces.py](/Users/govind/Projects/AIBuildersCup/apps/api/alembic/versions/c92d8b51d732_subject_workspaces.py)
- [apps/api/src/opportunity_platform/admin/service.py](/Users/govind/Projects/AIBuildersCup/apps/api/src/opportunity_platform/admin/service.py)
- [apps/api/src/opportunity_platform/assistant/__init__.py](/Users/govind/Projects/AIBuildersCup/apps/api/src/opportunity_platform/assistant/__init__.py)
- [apps/api/src/opportunity_platform/assistant/service.py](/Users/govind/Projects/AIBuildersCup/apps/api/src/opportunity_platform/assistant/service.py)
- [apps/api/src/opportunity_platform/core/config.py](/Users/govind/Projects/AIBuildersCup/apps/api/src/opportunity_platform/core/config.py)
- [apps/api/src/opportunity_platform/db/models.py](/Users/govind/Projects/AIBuildersCup/apps/api/src/opportunity_platform/db/models.py)
- [apps/api/src/opportunity_platform/eligibility/engine.py](/Users/govind/Projects/AIBuildersCup/apps/api/src/opportunity_platform/eligibility/engine.py)
- [apps/api/src/opportunity_platform/eligibility/refresh.py](/Users/govind/Projects/AIBuildersCup/apps/api/src/opportunity_platform/eligibility/refresh.py)
- [apps/api/src/opportunity_platform/eligibility/rules.py](/Users/govind/Projects/AIBuildersCup/apps/api/src/opportunity_platform/eligibility/rules.py)
- [apps/api/src/opportunity_platform/eligibility/service.py](/Users/govind/Projects/AIBuildersCup/apps/api/src/opportunity_platform/eligibility/service.py)
- [apps/api/src/opportunity_platform/ingestion/adapters.py](/Users/govind/Projects/AIBuildersCup/apps/api/src/opportunity_platform/ingestion/adapters.py)
- [apps/api/src/opportunity_platform/ingestion/curated_depwd.py](/Users/govind/Projects/AIBuildersCup/apps/api/src/opportunity_platform/ingestion/curated_depwd.py)
- [apps/api/src/opportunity_platform/ingestion/gemini.py](/Users/govind/Projects/AIBuildersCup/apps/api/src/opportunity_platform/ingestion/gemini.py)
- [apps/api/src/opportunity_platform/ingestion/openai.py](/Users/govind/Projects/AIBuildersCup/apps/api/src/opportunity_platform/ingestion/openai.py)
- [apps/api/src/opportunity_platform/ingestion/providers.py](/Users/govind/Projects/AIBuildersCup/apps/api/src/opportunity_platform/ingestion/providers.py)
- [apps/api/src/opportunity_platform/ingestion/schemas.py](/Users/govind/Projects/AIBuildersCup/apps/api/src/opportunity_platform/ingestion/schemas.py)
- [apps/api/src/opportunity_platform/ingestion/service.py](/Users/govind/Projects/AIBuildersCup/apps/api/src/opportunity_platform/ingestion/service.py)
- [apps/api/src/opportunity_platform/operations/extraction_smoke.py](/Users/govind/Projects/AIBuildersCup/apps/api/src/opportunity_platform/operations/extraction_smoke.py)
- [apps/api/src/opportunity_platform/operations/gemini_smoke.py](/Users/govind/Projects/AIBuildersCup/apps/api/src/opportunity_platform/operations/gemini_smoke.py)
- [apps/api/src/opportunity_platform/operations/readiness.py](/Users/govind/Projects/AIBuildersCup/apps/api/src/opportunity_platform/operations/readiness.py)
- [apps/api/src/opportunity_platform/opportunities/schemas.py](/Users/govind/Projects/AIBuildersCup/apps/api/src/opportunity_platform/opportunities/schemas.py)
- [apps/api/src/opportunity_platform/opportunities/service.py](/Users/govind/Projects/AIBuildersCup/apps/api/src/opportunity_platform/opportunities/service.py)
- [apps/api/src/opportunity_platform/planning/__init__.py](/Users/govind/Projects/AIBuildersCup/apps/api/src/opportunity_platform/planning/__init__.py)
- [apps/api/src/opportunity_platform/planning/service.py](/Users/govind/Projects/AIBuildersCup/apps/api/src/opportunity_platform/planning/service.py)
- [apps/api/src/opportunity_platform/profiles/dashboard.py](/Users/govind/Projects/AIBuildersCup/apps/api/src/opportunity_platform/profiles/dashboard.py)
- [apps/api/src/opportunity_platform/profiles/service.py](/Users/govind/Projects/AIBuildersCup/apps/api/src/opportunity_platform/profiles/service.py)
- [apps/api/src/opportunity_platform/subjects/__init__.py](/Users/govind/Projects/AIBuildersCup/apps/api/src/opportunity_platform/subjects/__init__.py)
- [apps/api/src/opportunity_platform/subjects/service.py](/Users/govind/Projects/AIBuildersCup/apps/api/src/opportunity_platform/subjects/service.py)
- [apps/api/src/opportunity_platform/workflows.py](/Users/govind/Projects/AIBuildersCup/apps/api/src/opportunity_platform/workflows.py)
- [apps/api/tests/conftest.py](/Users/govind/Projects/AIBuildersCup/apps/api/tests/conftest.py)
- [apps/api/tests/test_curated_depwd.py](/Users/govind/Projects/AIBuildersCup/apps/api/tests/test_curated_depwd.py)
- [apps/api/tests/test_document_evidence.py](/Users/govind/Projects/AIBuildersCup/apps/api/tests/test_document_evidence.py)
- [apps/api/tests/test_gemini_sdk.py](/Users/govind/Projects/AIBuildersCup/apps/api/tests/test_gemini_sdk.py)
- [apps/api/tests/test_gemini_smoke.py](/Users/govind/Projects/AIBuildersCup/apps/api/tests/test_gemini_smoke.py)
- [apps/api/tests/test_openai_provider.py](/Users/govind/Projects/AIBuildersCup/apps/api/tests/test_openai_provider.py)
- [apps/api/tests/test_pipeline.py](/Users/govind/Projects/AIBuildersCup/apps/api/tests/test_pipeline.py)
- [apps/api/tests/test_workspaces.py](/Users/govind/Projects/AIBuildersCup/apps/api/tests/test_workspaces.py)
- [apps/web/src/app/App.tsx](/Users/govind/Projects/AIBuildersCup/apps/web/src/app/App.tsx)
- [apps/web/src/app/auth-errors.ts](/Users/govind/Projects/AIBuildersCup/apps/web/src/app/auth-errors.ts)
- [apps/web/src/features/admin/Admin.tsx](/Users/govind/Projects/AIBuildersCup/apps/web/src/features/admin/Admin.tsx)
- [apps/web/src/features/assistant/Assistant.tsx](/Users/govind/Projects/AIBuildersCup/apps/web/src/features/assistant/Assistant.tsx)
- [apps/web/src/features/eligibility/Eligibility.tsx](/Users/govind/Projects/AIBuildersCup/apps/web/src/features/eligibility/Eligibility.tsx)
- [apps/web/src/features/opportunities/Discover.tsx](/Users/govind/Projects/AIBuildersCup/apps/web/src/features/opportunities/Discover.tsx)
- [apps/web/src/features/profiles/Profile.tsx](/Users/govind/Projects/AIBuildersCup/apps/web/src/features/profiles/Profile.tsx)
- [apps/web/src/features/workspaces/Plan.tsx](/Users/govind/Projects/AIBuildersCup/apps/web/src/features/workspaces/Plan.tsx)
- [apps/web/src/features/workspaces/Workspaces.tsx](/Users/govind/Projects/AIBuildersCup/apps/web/src/features/workspaces/Workspaces.tsx)
- [apps/web/src/i18n/strings.ts](/Users/govind/Projects/AIBuildersCup/apps/web/src/i18n/strings.ts)
- [apps/web/src/lib/api/schema.d.ts](/Users/govind/Projects/AIBuildersCup/apps/web/src/lib/api/schema.d.ts)
- [apps/web/src/styles.css](/Users/govind/Projects/AIBuildersCup/apps/web/src/styles.css)
- [apps/web/tests/auth-errors.spec.ts](/Users/govind/Projects/AIBuildersCup/apps/web/tests/auth-errors.spec.ts)
- [apps/web/tests/eligibility.spec.ts](/Users/govind/Projects/AIBuildersCup/apps/web/tests/eligibility.spec.ts)
- [apps/web/tests/nightfall-responsive.spec.ts](/Users/govind/Projects/AIBuildersCup/apps/web/tests/nightfall-responsive.spec.ts)
- [apps/web/tests/nightfall-workspaces.spec.ts](/Users/govind/Projects/AIBuildersCup/apps/web/tests/nightfall-workspaces.spec.ts)
- [data/fixtures/depwd-captured-public-pages.json](/Users/govind/Projects/AIBuildersCup/data/fixtures/depwd-captured-public-pages.json)
- [docs/architecture-overview.md](/Users/govind/Projects/AIBuildersCup/docs/architecture-overview.md)
- [docs/coverage-and-limitations.md](/Users/govind/Projects/AIBuildersCup/docs/coverage-and-limitations.md)
- [docs/decisions/0004-firebase-initialization.md](/Users/govind/Projects/AIBuildersCup/docs/decisions/0004-firebase-initialization.md)
- [docs/decisions/0005-source-lock-namespace.md](/Users/govind/Projects/AIBuildersCup/docs/decisions/0005-source-lock-namespace.md)
- [docs/decisions/0006-explicit-extraction-providers.md](/Users/govind/Projects/AIBuildersCup/docs/decisions/0006-explicit-extraction-providers.md)
- [docs/decisions/0007-authorized-subject-planning.md](/Users/govind/Projects/AIBuildersCup/docs/decisions/0007-authorized-subject-planning.md)
- [docs/demo-script.md](/Users/govind/Projects/AIBuildersCup/docs/demo-script.md)
- [docs/live-integration-audit.md](/Users/govind/Projects/AIBuildersCup/docs/live-integration-audit.md)
- [docs/nightfall-draft-corrections.md](/Users/govind/Projects/AIBuildersCup/docs/nightfall-draft-corrections.md)
- [docs/overnight-final-report.md](/Users/govind/Projects/AIBuildersCup/docs/overnight-final-report.md)
- [docs/overnight-progress.md](/Users/govind/Projects/AIBuildersCup/docs/overnight-progress.md)
- [docs/source-policy.md](/Users/govind/Projects/AIBuildersCup/docs/source-policy.md)
- [docs/submission-readiness.md](/Users/govind/Projects/AIBuildersCup/docs/submission-readiness.md)
- [infra/README.md](/Users/govind/Projects/AIBuildersCup/infra/README.md)
- [packages/contracts/openapi.json](/Users/govind/Projects/AIBuildersCup/packages/contracts/openapi.json)
- [scripts/correct_depwd_draft.py](/Users/govind/Projects/AIBuildersCup/scripts/correct_depwd_draft.py)
- [scripts/product_smoke.py](/Users/govind/Projects/AIBuildersCup/scripts/product_smoke.py)
