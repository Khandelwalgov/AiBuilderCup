# Phase 2.5 — Live integration validation

Validated locally on 13 October 2026 with PostgreSQL 17, Python 3.12, locked google-genai 2.29.0, Vite and Chromium. **The real source-to-eligibility acceptance journey is blocked by external configuration.** No real Gemini response, Firebase login, admin publication or deployed application is claimed. Existing Phase 2 features/migrations and synthetic fixtures were preserved.

| Requested outcome | Actual result |
|---|---|
| Live Gemini extraction | Not executed: no server Gemini API key configured. No substitute model or fake candidate used. |
| Published real opportunities | **0** in the application PostgreSQL database and real-only catalogue API. |
| Firebase authentication | Backend project and four web values absent; actual browser displays the setup blocker. Local ADC credential refresh **succeeded**, correcting the Phase 2 assumption that ADC was unavailable. Permission to an explicitly selected Firebase project is unverified. |
| Admin review/publication | No selected Firebase UID, bootstrapped application admin or real candidate. No live review executed. |
| End-to-end eligibility | Blocked before extraction/publication/authentication. Backend and mocked UI tests do not meet live acceptance. |
| Deployment | Prepared, not executed. No public URLs, resource creation, billing changes or real-secret deployment. |
| Phase 3 readiness | **Not ready for the Unlock Graph milestone** until a real candidate is reviewed and a real authenticated profile evaluation succeeds. |

## Executed commands and validation levels

Commands ran from repository root unless specified. `UV_CACHE_DIR=/tmp/opportunity-uv-cache` was set for uv. Network/localhost checks used sandbox escalation. Backend tests use isolated PostgreSQL schemas removed afterward; they do not publish into the application database.

| Command/check | Result |
|---|---|
| `make contracts` | OpenAPI exported; generated TypeScript refreshed, including `/live`. |
| `make check` | Ruff lint/format including deployment runner; **63 backend tests passed, 1 optional network test skipped**; Alembic: no new upgrade operations; ESLint, TypeScript and Vite production build passed. |
| `cd apps/api && RUN_LIVE_SOURCE_TESTS=1 uv run pytest tests/test_pipeline.py::test_live_official_source_capture -q` | **1 passed**. Real official fetch/parse/DB capture; expected `extraction_blocked / gemini_not_configured`. Fictional test admin in isolated schema is not acceptance authentication. |
| `PLAYWRIGHT_BROWSERS_PATH=/tmp/opportunity-browsers make test-e2e` | **6 passed**. Public synthetic discovery/navigation and unauthenticated catalogue/profile use the actual API. Profile/evaluation and admin publication use explicitly mocked auth/API contracts. Network failure test aborts a route. |
| `cd apps/web && PLAYWRIGHT_BROWSERS_PATH=/tmp/opportunity-browsers node --input-type=module` with actual-page assertions | Without route mocks, `/settings` displays missing sign-in configuration and `/discover` an empty catalogue. This proves blocker UI, **not Google login**. |
| `docker build -t opportunity-api:phase25 apps/api` | Native local image built with frozen production dependencies. Cloud Build amd64 image remains unbuilt/unpushed. |
| `docker run --detach --rm --name opportunity-phase25-smoke -p 127.0.0.1:18080:8080 -e DATABASE_URL=postgresql+psycopg://opportunity:local-development-only@host.docker.internal:5432/opportunity opportunity-api:phase25` | Local container: `/live` 200/not_checked, `/health` 200/connected, catalogue 200/total 0, private profile 401, UID 1000. Container stopped/removed. Uses local development DB configuration, not hosted Cloud SQL. |
| `make preflight` | Expected nonzero: Firebase backend project, web config/project match and Gemini key missing. Model selected; ADC file present; no frontend server-secret values. No credential values printed. |
| `google.auth.default()` then `credentials.refresh(Request())` | Real ADC refresh succeeded; no access token printed. Existing quota/default project is not authorization to select it. |
| `firebase projects:list --json --non-interactive` | Sanitized wrapper could not parse CLI output as JSON. No selected project/access inferred. |
| `gcloud run deploy --help`, `gcloud run jobs deploy --help`, `gcloud sql instances create --help` | Planned flags supported by installed CLI; no resource mutations. |
| Deployment runner tests (`test_operations.py`) | Synthetic public config prints plan without executing commands; migration before service, numeric secret versions, approval guard, rejection of extra secret-value field. |
| `git diff --check` | No whitespace errors. |

The first expanded SDK test found an assertion mismatch: the locked SDK emits `thinking_level`, not the asserted `thinkingLevel`. Corrected to check actual serialization. An attempt to pass `system_instruction` to Developer API countTokens was incompatible and replaced with instruction/schema text in counted contents. Ruff formatting initially failed on the runner, then passed. These corrections are covered by the final suite, not proof of live model acceptance.

Nonblocking warnings: Starlette HTTPX TestClient deprecation and Alembic missing `path_separator`. Phase 2.5 adds no DB columns; the existing Phase 2 migration remains authoritative. The development API was restored with default real-only catalogue after browser regression tests.

## Actual public source capture

Adapter `depwd-pre-matric`: both HTTP 200; robots.txt 404/policy not present; no CAPTCHA/login/block bypass. **68 pages, 127,248 characters**. Bundle SHA-256: `32d14860c90b70276d91d12eb4e23d8f2eed4851c9f2798b103d060f93214446`.

| Official source | Pages | Bytes | SHA-256 |
|---|---:|---:|---|
| [2024 guidelines](https://cdnbbsr.s3waas.gov.in/s3e58aea67b01fa747687f038dfde066f6/uploads/2024/09/202409261656732428.pdf) | 61 | 1,457,647 | `2f4a1e8a7d453cf049092960d0f5df950cccbc382f224db0a1503cf714ca6171` |
| [2025 amendment](https://cdnbbsr.s3waas.gov.in/s3e58aea67b01fa747687f038dfde066f6/uploads/2025/09/202509111852335844.pdf) | 7 | 2,985,253 | `a26f688260d03eb31b46261447dbab9d85e859f2dcf900bb5b6b148614d5157d` |

Direct adapter inspection saved public text under ignored `.live-validation/source-pages.json`; no private documents/tokens. The live test proves snapshot persistence through missing-key failure in an isolated schema. The main admin queue remains unpopulated. Fetch timestamps are not review timestamps.

## Reviewer checklist from actual text

PDF indexes below differ from printed page labels. These are **reviewer checks, not a generated candidate**. No actual generated requirement set exists; extraction accuracy/omissions cannot yet be measured.

2024 PDF: general conditions p5; annual parental-income ceiling/slot restrictions p6; income-certificate notes and regular full-time class IX/X recognized-school conditions p7. Review application/evidence p10, merit/renewal p11, ongoing/payment conditions p12 and common provisions pp31–32. Preserve the sibling/twin exception, repeated-class restriction and other-scholarship exclusion. Do not import post-matric employed-student income rules. Limited slots do not guarantee an award. Annual income needs its exact definition and a clarified period, not an invented financial year or household sum. [Guidelines](https://cdnbbsr.s3waas.gov.in/s3e58aea67b01fa747687f038dfde066f6/uploads/2024/09/202409261656732428.pdf)

2025 PDF: p1 states immediate effect; p2 revises general identity requirements to UDID and Aadhaar card. Reconcile earlier certificate/biometric/enrolment wording rather than retaining it automatically. Pages 3–4 change cross-state fresh-application verification to the state of study, distinguish renewal, and revise selection. Changes to other components must not become pre-matric requirements or benefits. Cite the amended-column text, preserving human review of applicability/effective dates. [Amendment](https://cdnbbsr.s3waas.gov.in/s3e58aea67b01fa747687f038dfde066f6/uploads/2025/09/202509111852335844.pdf)

No current application-round opening/closing dates were established. Do not turn publication/effective/payment dates into application dates. Keep null dates and review flags without separately captured authoritative round evidence. The source index is not comprehensive current coverage.

Current fact/rule vocabulary cannot faithfully encode sibling/twin history, renewal branches, school recognition, state verification, Aadhaar possession, competitive merit/slots or discretion. Preserve these as explicit unknown conditions with descriptive citations/flags. Never hide omissions in summary text while implying complete matching. Required documents remain unknown readiness conditions; document verification is not implemented. Correct/reject unsupported model semantics through the existing review UI.

## Hardened integration and remaining limits

Removed deprecated `temperature=0`; retained configured model and official SDK schema interface. See [Google migration guidance](https://ai.google.dev/gemini-api/docs/latest-model), [model capabilities](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash), and [official SDK JSON-schema examples](https://github.com/googleapis/python-genai). Installed-SDK serialization uses a **mock HTTP transport**; actual model/schema acceptance remains unverified.

Input guard counts document/instruction/schema text plus a 1,024-token framing reserve, not an exact billing estimate. Defaults: input cap 200,000, output 16,384, LOW thinking, 120-second timeout per count/generation call, one attempt each. The actual bundle token count and generation duration are **unknown without a key**. Character count is not token measurement. STOP, Pydantic and exact-page quote validation are mandatory; truncated/blocked output is rejected.

Sanitized diagnostics distinguish configuration, credentials/model/request rejection, rate limit/service/network/timeout, input/output limits, incomplete/empty response, schema and evidence failures. No SDK exception message, key or prompt is persisted. Candidate savepoints retain snapshots/runs after extraction failure; a process crash/DB outage can still roll back the outer synchronous transaction. Nonblocking source locks and bounded DB pools reduce contention, not a durable job guarantee. Published pointers remain independent of failed source freshness.

Production configuration fails closed for default/local DB, development catalogue and invalid CORS. Existing Firebase Admin app must match backend project; bootstrap now requires matching `--project-id`. Deployment is plan-first, explicit-project, pinned-secret, migration-before-service. See [decision](decisions/0003-live-integration.md).

## Exact external blockers and next actions

1. Select the Firebase/GCP project and existing Firebase user UID. Neither was supplied. Do not assume the CLI default is this application's project.
2. Configure backend `FIREBASE_PROJECT_ID`, four web Firebase values, Google provider and authorized domains. Use ignored local env files, never chat. ADC refresh works, but selected-project Firebase Authentication read permission remains unverified.
3. Set server-only `GEMINI_API_KEY`; confirm access/quota for `gemini-3.8-flash`; rerun `make preflight`. Local PostgreSQL works; hosted DB config is absent.
4. Complete actual browser sign-in/bootstrap, actual extraction and full human candidate review before publication.
5. Deployment additionally needs explicit authorization and project/region/budget, Hosting, Cloud SQL/database user/IAM and pinned Secret Manager versions. [Executable procedure](../infra/README.md), [runner](../infra/deploy.py) and [public config template](../infra/deploy.example.json) are prepared. No cloud prerequisite was created/deployment-tested.

## Real acceptance checklist — pending, no mocks

1. Start real-only API/web with configured local env. Google-sign-in in the actual app; verify authenticated `/v1/me`. Bootstrap the chosen Console UID with `--project-id`; refresh. Do not use dependency overrides, custom test tokens or intercepted routes.
2. Admin: ingest `depwd-pre-matric`; record run/model/extractor IDs, snapshot hash/page count, token usage and timings without credentials/prompts. Preserve failure diagnostics without publishing. Compare the **entire** output against source text/checklist; record omissions/interpretations/corrections. Correct JSON with exact source passages and a meaningful review note. Flags alone do not establish completeness.
3. Confirm draft absent from public catalogue. Approve only after actual comparison and completeness/flag acknowledgement. Confirm reviewer/time/audit and one cited public record without invented open status/deadline.
4. Separate browser: Google-sign-in as a non-admin. Confirm actual admin requests return 403. Do not export tokens/storage state or copy authorization headers into commands/chat.
5. Create clearly fictional personal profile through real UI. Enter source-relevant facts supported by the published rules; evaluate through actual backend. Inspect satisfied/unsatisfied/unknown outcomes, citations and persisted version/fact snapshot. Missing/unrepresentable conditions stay unknown; no official approval claim.
6. Edit a relevant fact, save/re-evaluate, verify actual result changes. Establish a substantive blocker; add an unrelated fact and confirm the blocker remains. Document upload/verification is not available: self-reported possession must not count as verified evidence.
7. On a subsequent real fetch/model failure, confirm last reviewed publication remains visible with freshness warning and failed run. Offline failure injection already tests this; record a live occurrence separately if encountered. Do not fabricate an amendment or bypass source access controls to stage a demo.
8. After authorized deployment, repeat real Google login, normal-user denial, review and evaluation on hosted origins. Health/CORS/SPA smoke does not meet authenticated acceptance. Record actual URLs and only then begin the graph milestone.
