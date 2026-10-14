# Current update — Explicit providers and first genuine draft

**14 October 2026, Asia/Kolkata.** This update supersedes the historical audits below. **One real official-source extraction draft is now stored in the administrator review queue**, with validated original-page citations and provider provenance. It remains unpublished; substantive review belongs to the user.

Open [Admin review](http://127.0.0.1:5173/admin) in your already signed-in administrator browser and select **Pre-Matric Scholarship for Students with Disabilities**. Candidate ID: `9588fed8-1f25-423d-8b5f-890636e68695`. No additional ingestion is necessary to inspect this draft.

## What changed

- Added the explicit `ExtractionProvider` protocol/result and Gemini/OpenAI implementations. `AI_EXTRACTION_PROVIDER=gemini` remains the code/template default; there is **no error-triggered fallback**. Local development explicitly selects `openai`, as authorized.
- Added backend-only `OPENAI_API_KEY`, `OPENAI_MODEL` and bounded input/output/timeout settings. The confirmed replacement OpenAI key was moved in memory from its mistaken Gemini env slot into `OPENAI_API_KEY` in the ignored local env file; its value was preserved and never printed. `GEMINI_MODEL` was restored to `gemini-3.8-flash`; OpenAI retains the user's selected `gpt-5.6-terra` model. The actual Google API key currently needs restoration to `GEMINI_API_KEY` before Gemini can run again.
- OpenAI uses Structured Outputs through Responses, adapting the wire schema's required/default/additional-properties rules. **The original `Extraction`, `CandidateData`, typed conditions and exact citation validator remain unchanged.** Additional rule-type instructions address constraints that JSON Schema alone cannot express. No government rule was hardcoded or synthesized as source data.
- Migration `a70d81ea2f20` adds run/version provider/model/version/usage provenance and sanitized diagnostics. It preserves existing data and nullable legacy unknowns. Admin API contracts and TypeScript were regenerated. The existing review screen now shows provider/model/extractor/token usage; no UI redesign was made.
- Same-source/provider/model/extractor runs are idempotent. Provider changes can create another draft without replacing a published version. This behavior and source reversion are tested. See [decision](decisions/0006-explicit-extraction-providers.md).

## Google free-tier inspection

Google currently documents free text input/output for Gemini 3.8 Flash, 3.6 Flash and 3.5 Flash-Lite. The specific [3.5 Flash-Lite model page](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite) lists structured output support and sufficient context for the bundle; [pricing](https://ai.google.dev/gemini-api/docs/pricing) lists its free tier. This establishes documented capability, not account-specific quota or live availability.

**Zero new Gemini generation calls were made.** The local Gemini credential had been replaced with an OpenAI-format key; sending it to Google would be incorrect. After moving it to the correct setting, there is no Google key available for the permitted one-shot alternative-model test. ADC/Firebase permissions are not substituted for a Gemini free-tier key, and no billing/Vertex AI path was enabled. Gemini remains the default primary implementation and passes SDK/behavior tests; live free-tier recovery remains unverified.

## Actual OpenAI calls and budget

The interrupted tiny test result was recovered, not repeated. All AI inputs were public/non-sensitive: a tiny diagnostic prompt or the two actual allowlisted DEPwD documents. No private profiles, credentials or identity documents were sent. There were no tools, automatic retries or publication actions.

| Live request | Outcome | Input / output tokens | Duration |
|---|---|---:|---:|
| Tiny OpenAI Responses smoke, 128-token output cap | HTTP 200, completed, exact expected `OK` response | 11 / 5 (16 total) | 2.54s |
| Full official-source extraction, attempt 1 | Response returned; Pydantic application validation rejected it (`openai_schema_invalid`). Failed run and snapshot retained. | 41,474 / 4,539 (46,013 total) | 44.24s including source retrieval |
| Controlled full retry after explicit typed-rule instructions and improved failure capture | **Validated candidate created**, exact quote checks passed | 41,654 / 3,725 (45,379 total) | 34.73s including retrieval |

Two full attempts occurred, not one successful first attempt. The first failed response's detailed validation payload was not captured by the initial code, so its specific invalid condition is **not retrospectively invented**. Failure capture was improved, and typed-rule instructions were made explicit; the second candidate passed without relaxing validation or inserting manual scheme data. No further model request was made after success.

At the documented [Terra rates](https://developers.openai.com/api/docs/models/gpt-5.6-terra) of $2/M input and $12/M output tokens, the three measured requests total approximately **US$0.2655**, excluding taxes and billing adjustments. This is an estimate from actual returned usage, not an invoice. The second request's conservative preflight ceiling plus measured earlier usage stayed below the authorized US$1 test budget. No account credits/billing settings were modified.

The first full request was `c050497f-0bba-4b36-a62a-5945fb489452`; successful run: `1a533cfe-7707-4758-9e32-98ea5612a40a`. Both record `openai`, `gpt-5.6-terra`, extractor `pre-matric-openai-v1` and the same captured source hash. Public snapshots were deduplicated, not replaced. Failed parsed public-source outputs in future attempts may be retained only as unvalidated privileged diagnostics; they are not approvable candidates. All remote error strings remain withheld.

## Persisted draft and review findings

| Evidence / state | Actual result |
|---|---|
| Registered adapter | `depwd-pre-matric` |
| Official source bundle | 2024 guidelines + 2025 amendment, **68 pages** |
| Source SHA-256 | `32d14860c90b70276d91d12eb4e23d8f2eed4851c9f2798b103d060f93214446` |
| Provider/model/extractor | `openai` / `gpt-5.6-terra` / `pre-matric-openai-v1` |
| Measured successful usage | 41,654 input + 3,725 output = 45,379 total tokens |
| Exact citations revalidated from persisted data | **18** metadata/requirement citations |
| Requirements and flags | **8 requirement groups**, **13 review flags** |
| Application dates and apply URL | Null; no currently open application round asserted |
| Database counts | **1 real source, 1 snapshot, 2 runs, 1 draft, 0 real publications** |
| Review payload | Read successfully through the existing PostgreSQL-backed admin domain service after resolving the unique enabled Google-linked existing admin via Firebase Admin SDK; no role was granted |

The complete actual generated requirement set was inspected. It includes nationality, disability percentage, amended identity requirements, school/class/full-time context, parental-income ceiling context, sibling/twin restriction, competing scholarship exclusion and amended cross-state verification. Unsupported conditions remain unknown; no income period or household sum is guessed. The actual profile/evaluator contracts are unchanged.

**Do not approve solely because the schema and quotations pass.** Human review must address:

- The repeated-class exclusion and renewal/progress/conduct conditions appear in restrictions/flags but are not separate executable/unknown requirement groups. They need explicit rule treatment or a clearly justified review correction before a completeness acknowledgement.
- Class IX/X, regular/full-time and recognized-school requirements are represented by one unknown group. This is conservative but cannot distinguish a known school/class disqualifier yet. Review how to preserve each distinct condition without inventing new fact semantics.
- The income threshold is described but remains unknown because the exact definition/assessment period is not established. Do not silently invent a financial year or sum household members.
- Reconcile the amended UDID/Aadhaar provision with the older application-document list and verify the applicable certificate requirement. Do not assume that self-reported document possession is verified evidence.
- Review selection/slot limits, fresh-versus-renewal routing, all applicability differences and source completeness against later official notices. The supplied documents do not establish the current application window.
- Check category/country normalization (`Education scholarship`, `India`) against the intended catalogue vocabulary before publication. No automatic metadata correction or substantive approval was performed.

Exact quote matching establishes that the cited text occurs on the captured URL/page, **not** that every claim has correct semantic coverage. The source-review checklist from earlier audits remains applicable. No published rules, eligibility results or user profile data were changed.

## Live versus automated validation

**Live verified:** OpenAI smoke and both full public-source calls; actual PostgreSQL admin-authorized ingestion/persistence; source fetch/hash/page capture; persisted candidate/schema/citation revalidation; additive migration; real-only public catalogue remains empty because nothing is published.

**Automated/mocked only:** provider dispatch/failure handling, strict-schema adaptation, cross-provider idempotency, protected routes, review UI and publication, personal-profile evaluation and Gemini SDK generation configuration. Existing browser auth/publication/evaluation contract mocks remain clearly labeled. The new provider was not inserted as a fake browser or API identity.

The available controlled in-app browser is still distinct from the user's signed-in browser; agent-observed real browser authentication/queue rendering and real personal eligibility remain unverified. This does not prevent the real persisted draft appearing to the already authorized user at `/admin`. Publication is deliberately pending the user's substantive review, not an implementation bypass.

Executed checks (uv used `UV_CACHE_DIR=/tmp/opportunity-uv-cache`; browser used `PLAYWRIGHT_BROWSERS_PATH=/tmp/opportunity-browsers`):

| Command | Result |
|---|---|
| `cd apps/api && uv run alembic upgrade head` | Applied additive `a70d81ea2f20`, existing records preserved |
| `make contracts preflight` | Contracts regenerated; explicit local OpenAI configuration passed preflight |
| `make check` | Passed Ruff lint/format, backend tests, Alembic drift, ESLint, TypeScript and production frontend build; last full run: 83 passed / 1 optional network test skipped |
| `cd apps/api && uv run pytest -q && uv run alembic check` after final Gemini usage test | **84 passed, 1 skipped**; no drift |
| `make test-e2e` | **7 passed**, including existing explicitly mocked contract journeys |
| Persisted draft `CandidateData.model_validate` + `validate_evidence` | Passed; all 18 citations verified again against stored pages |
| Actual API privacy checks | `/health` 200, real catalogue total 0, actual stable opportunity detail 404 while draft, candidate admin endpoint 401 without authentication |
| `git diff --check` | Passed |

No cloud deployment, billable resource creation, new package dependency or Phase 3 feature was introduced. The task-owned API was restored with the real ignored local configuration after fixture browser tests. The earlier failed fresh Docker image builds are historical; no new Docker build is claimed here.

## What to do now

Open [Admin](http://127.0.0.1:5173/admin) in your signed-in browser and inspect **Pre-Matric Scholarship for Students with Disabilities**. Review the eight groups, source pages, 13 flags and the omissions above before correcting/approving anything. **Do not rerun ingestion merely to find this draft.**

For later provider tests: `make extraction-smoke` uses only the explicit selected provider; it does not start ingestion. `make gemini-smoke` targets Google only. To restore the primary path, put a real Google key in ignored `apps/api/.env` as `GEMINI_API_KEY` and explicitly select `AI_EXTRACTION_PROVIDER=gemini`. A one-shot `gemini-3.5-flash-lite` test is documented as an option; none was executed without Google credentials. Do not paste keys in chat or use frontend `VITE_` secrets.

---

## Historical Phase 2.7 — First real ingestion validation

**Current update, 14 October 2026 (Asia/Kolkata).** This section supersedes the Phase 2.6 status below; the older audit is retained as history. Completed Google configuration and bootstrap were recognized and not repeated. No model substitution, authentication bypass, publication, deployment or paid infrastructure provisioning occurred.

**Outcome:** the one requested minimal real Gemini generation returned HTTP **503** in **0.74 seconds**, at `generate_content`, with retryability classified true. Consequently **no full extraction was invoked**, as required by the smoke-test gate. No genuine draft exists yet. Successful source-to-review acceptance remains blocked by provider generation availability, not by missing Google configuration or bootstrap.

## Current subsystem status

| Subsystem | Configured? | Tested live? | Working? | Remaining blocker / precise status |
|---|---|---|---|---|
| Firebase web configuration | Yes, `venuesignal` / `AiBuilderCup` | Preflight and existing browser initialization | Yes | **PASS — LIVE VERIFIED** for configuration previously compared with Firebase; preflight passes again. |
| Google Sign-In | Enabled | Provider list GET 200, Google enabled; user reports successful interactive login | Enabled; user-confirmed login | **CONFIGURED — NOT VERIFIED** by this agent for the valid-token browser journey. The controlled in-app browser is a separate signed-out session. |
| Backend Firebase verification | Yes | Selected-project ADC reads and live unauthorized-route rejection | Guards work; valid-token acceptance not observed here | **CONFIGURED — NOT VERIFIED** for actual authenticated `/v1/me` acceptance. No token was fabricated/exported. |
| ADC/IAM | Yes | Real Firebase account reads and provider configuration | Yes for audited read operations | **PASS — LIVE VERIFIED**. No IAM mutation was needed. |
| Administrator account | Existing DB roles | Each admin UID resolved via Admin SDK to an existing enabled Firebase account | Confirmed | **PASS — LIVE VERIFIED** for existing roles/identities: two admins, both enabled; exactly one Google-linked. No UID, email or credential printed; no role was changed. |
| PostgreSQL | Yes | Docker healthy, connectivity, Alembic head/drift | Yes | **PASS — LIVE VERIFIED**; migration `fcc8ecdfdfad` remains head. |
| Gemini small generation | Configured `gemini-3.8-flash` | One genuine tiny structured-generation request | No | **FAIL — NEEDS FIX**: upstream HTTP 503 at generation. Retryable does not guarantee recovery; no automatic retries. |
| Gemini full structured extraction | Configured | Not invoked after failed smoke | Not reached | **BLOCKED — USER ACTION REQUIRED** to resume testing after service recovery. No full-request token usage this run. |
| Official-source ingestion | One registered code adapter | Real fetch/parse/DB evidence tested in isolated schemas | Fetch path passes; application ingestion not invoked | **BLOCKED — USER ACTION REQUIRED** after model recovery. Source records in application DB remain zero. |
| Admin review queue | Implemented | Automated tests; authenticated browser unavailable to agent | No candidate to inspect | **PASS — AUTOMATED TEST ONLY**; actual queue has zero draft candidates. |
| Opportunity publication | Human-controlled | Automated tests only | Zero real publications | **BLOCKED — USER ACTION REQUIRED**: extraction and substantive review/approval first. Nothing was published automatically. |
| Personal profile | Implemented | PostgreSQL persistence/permissions tests | No actual profile created in this run | **PASS — AUTOMATED TEST ONLY**. No private existing profile was overwritten. |
| Real eligibility | Deterministic implementation | Backend tests; browser contract tests include mocks | Actual journey pending | **BLOCKED — USER ACTION REQUIRED**: authenticated session available for testing and an explicitly approved real opportunity. |
| Deployment | Existing preparation | No cloud execution | Not deployed | **CONFIGURED — NOT VERIFIED**. Outside Phase 2.7 scope. Phase 2.6 fresh-image download failures remain historical/unresolved, not claimed fixed here. |

## Executed real checks and boundaries

- `make preflight` passed. Backend and frontend configuration still match the selected project. Existing ignored env files/secrets were preserved.
- Docker PostgreSQL reports healthy; `alembic current` reports `fcc8ecdfdfad (head)`. No migration was needed. API `/health` and Vite-proxied `/health` returned 200. Unauthenticated `/v1/admin/sources` returned 401.
- The two existing DB admin UIDs were resolved **in memory** with `firebase_admin.auth.get_user` against `venuesignal`, without printing identities. Both Firebase accounts are enabled; one is Google-linked. This is a trusted local resolution method available for future authorized ingestion, so there is no reason to request another bootstrap or guess a UID.
- Google provider configuration now reads enabled. The user reports completing Google login. The browser connector available to this agent controls a separate in-app browser, where `/admin` shows sign-in required and no ingestion button. No browser storage, cookies or tokens were copied to bridge that separation. Real authenticated endpoint acceptance cannot be inferred from ADC account reads alone.
- The user was asked only to open `/settings` and `/admin` **in their existing signed-in browser** and confirm the server-backed status/source card. No response was received during this run. This is an access/observation limitation, not a request to redo provider setup or bootstrap. Do not treat it as evidence that the user's existing login is broken.

## Minimal Gemini attempt

Exactly **one** real `generate_content` request used the configured server-only key and unchanged `gemini-3.8-flash` model. Prompt: a tiny non-sensitive request for an object with `ok=true`. Configuration: JSON MIME/schema, LOW thinking, **256 maximum output tokens**, **20-second timeout**, **one SDK attempt**, no tools or automatic function calls, no deprecated sampling overrides.

Sanitized result saved in ignored `.live-validation/phase27-smoke.json`:

```json
{
  "stage": "generate_content",
  "model": "gemini-3.8-flash",
  "max_output_tokens": 256,
  "attempts": 1,
  "success": false,
  "http_status": 503,
  "retryable": true,
  "diagnostic_code": "gemini_service_error",
  "seconds": 0.74
}
```

No model response, measured token usage or billing result was returned. No full extraction, segmentation or reconciliation call followed. The approximately 46,000-token bundle figure belongs to the earlier audit, not a new full-generation attempt. This turn stayed within the authorized tiny-probe scope; the US$1 budget is not permission to loop a failing model. Google documents 503 as retryable, but the user's stricter one-attempt/no-loop boundary was retained. [Gemini troubleshooting](https://ai.google.dev/gemini-api/docs/troubleshooting)

Because even the tiny request failed, there is no evidence implicating the 68-page context size or extraction schema complexity. Source-aware segmentation or a model swap would be speculative and was not implemented. Complete scholarship requirements, exact generated citations and amendment interpretation cannot be reviewed without an actual candidate; no rule or open application window was invented.

The ordinary ingestion service was **not** called after the smoke failure; thus no actual `IngestionRun` was created. The isolated live-source test deliberately disables Gemini and proves official fetch/parsing/snapshot preservation only. It does not produce a candidate in the main database or bypass administrator authorization.

## Small operational changes

1. Added `make gemini-smoke` / `python -m opportunity_platform.operations.gemini_smoke` as a reusable one-attempt diagnostic. It has the same tiny prompt/schema/limits as the real probe, emits only sanitized fields, returns nonzero for failure, and never starts ingestion or writes DB data. It accepts only a STOP response with an actual boolean `true`, not a truncated response or numeric lookalike. **The new command itself was unit-tested with mock HTTP transport; it was not executed against the live provider again**, preserving the single-live-attempt budget.
2. Fixed the ingestion advisory-lock namespace. Parallel backend and live-source tests revealed that independent PostgreSQL schemas used the same source lock, causing 11 initial `source_busy` failures (58 passed, 1 skipped). The lock now includes `current_schema()` plus adapter identity. Duplicate ingestion in one schema is still rejected immediately; independent schemas no longer block each other or the application. A real two-session PostgreSQL regression test verifies both behaviors, using a non-application namespace for the independent lock. This changes no tables or role permissions. [Decision](decisions/0005-source-lock-namespace.md)

Existing Phase 2.6 changes in the working tree were preserved. No dependency, model, API schema, government rule, profile or opportunity version was replaced. No Phase 3 feature was added.

## Regression commands and final results

`UV_CACHE_DIR=/tmp/opportunity-uv-cache` and `PLAYWRIGHT_BROWSERS_PATH=/tmp/opportunity-browsers` were used where relevant. Test-only schemas are removed after execution; no application data was truncated.

| Executed command/check | Result |
|---|---|
| `make preflight` | Passed, all checks true. |
| `make contracts` | OpenAPI and TypeScript regenerated; no contract changes. |
| `make check` | **70 passed, 1 optional live test skipped**; Ruff lint/format, Alembic drift, ESLint, TypeScript and production frontend build passed. |
| `cd apps/api && RUN_LIVE_SOURCE_TESTS=1 uv run pytest tests/test_pipeline.py::test_live_official_source_capture -q` | **1 passed**, repeated after lock fix; actual 68-page official fetch and isolated DB capture; no model call. |
| `make test-e2e` | **7 passed**. Existing synthetic public discovery uses real DB API; profile/evaluation and publication journeys remain explicitly mocked. One check is a unit-level sign-in message test. No authenticated acceptance claim. |
| `cd apps/api && uv run pytest tests/test_pipeline.py::test_source_lock_rejects_same_schema_but_does_not_block_independent_schema -q` | **1 passed**, including the final non-application independent-namespace adjustment. |
| `cd apps/api && uv run alembic current` | `fcc8ecdfdfad (head)`; drift check also passed in `make check`. |
| Actual Google account/provider reads | Enabled existing admins and Google provider confirmed; no role grants. |
| Actual minimal generation | One attempt, HTTP 503; no full extraction. |
| `git diff --check` | Passed. |

The first full suite overlapped with the isolated live-source test and failed on shared advisory locks; that failure was investigated and fixed rather than hidden. Final suite and live-source test both passed after namespace correction. Known nonblocking warnings are the same Starlette HTTPX TestClient/Alembic path-separator notices. The task-owned API was restored to its real ignored env configuration and real-only catalogue after the brief browser regression server run. Vite remains running.

## Application database and review state

Final aggregate application counts: **2 existing admins**, **0 personal profiles**, **0 real Source rows**, **0 source snapshots**, **0 ingestion runs**, **0 draft candidates**, **0 published real opportunities**. The code registry still contains `depwd-pre-matric`; DB registration happens during ingestion and is not missing adapter code. Existing six synthetic opportunity/version fixtures remain preserved and isolated from normal public coverage.

No actual review candidate, evidence editor, diff or citation list could be inspected this run. The queue must remain empty until genuine extraction succeeds. A known source URL or a passing mocked review test is not a substitute candidate. No publication or live eligibility evaluation occurred. The full source-to-eligibility milestone remains incomplete at the Gemini generation gate.

## What I need to do now

1. Once the provider has recovered, run **one** bounded probe from the repository root:

```sh
cd /Users/govind/Projects/AIBuildersCup
make gemini-smoke
```

If it still reports 503, stop; check [Google AI Studio status](https://aistudio.google.com/status) and your project's AI Studio usage/rate-limit dashboard. Do not retry full extraction or change models based only on this failure.

2. In your **already signed-in browser**, open [Settings](http://127.0.0.1:5173/settings) and [Admin](http://127.0.0.1:5173/admin). Confirm server-backed “Signed in securely” status and the DEPwD source card. No bootstrap or provider reconfiguration is needed. Do not send ID tokens. To allow direct agent UI verification, sign in within the separate Codex in-app browser session if you choose; credentials need not be exported between browsers.

3. Only after the small probe succeeds, click **Ingest source once** in `/admin`. The existing service checks your DB admin role, captures real sources and creates a draft only after genuine schema/citation validation. Stop and retain diagnostics if it fails.

4. When a genuine draft appears, inspect all requirements and original passages, especially common/pre-matric applicability, annual parental income, amended identity documentation, competing scholarships, renewal/selection restrictions and unknown dates. Correct/acknowledge only after real review; **you decide whether to publish**. Then the real profile/eligibility path can be tested. There is currently nothing ready for approval.

---

## Historical Phase 2.6 — Live integration audit

Audit date: **14 October 2026 (Asia/Kolkata)**. Selected project: **venuesignal**, registered Firebase web app: **AiBuilderCup**. The monorepo, source adapters, database records, migrations and review boundary are preserved. No cloud resources, IAM grants, administrator grants, credential changes or government-opportunity publications were made. Secrets were inspected only in memory; none are reproduced here.

**Furthest achieved:** real official PDFs fetched and parsed → real Gemini model access and token counting verified → actual generation attempted twice, with service failure (second attempt HTTP 503). No candidate was generated. Google sign-in is blocked because the selected project's configured provider list is empty. No application admin exists. Therefore persistence into the admin queue, human publication and authenticated eligibility remain unverified, not successful.

## Subsystem status

“Configured” means values exist and match where checked; it does not imply live functional acceptance.

| Subsystem | Configured? | Tested live? | Working? | Remaining blocker / precise status |
|---|---|---|---|---|
| Firebase web configuration | Yes | Yes: Management API app/config comparison and browser initialization | Yes | **PASS — LIVE VERIFIED**: registered app name, app ID, API-key match, auth domain and project match; no values exposed. |
| Google Sign-In | Web SDK yes; Google provider absent | Yes: provider config/list and actual browser sign-in attempt | No | **BLOCKED — USER ACTION REQUIRED**: provider GET 404; provider list GET 200 with empty list. Enable Google and complete interactive login. |
| Backend Firebase verification | Yes | Initialization and missing/invalid-token rejection; no valid user token | Partial | **CONFIGURED — NOT VERIFIED** for valid-token/revocation journey. Missing/invalid-token guards are live verified; do not count them as successful authentication. |
| ADC/IAM permissions | Yes | ADC refresh, Firebase config/users and web-app reads | Yes for inspected operations | **PASS — LIVE VERIFIED** for selected-project read permissions. This does not prove IAM mutation, bootstrap or deployment permissions. |
| Admin bootstrap | CLI ready; no chosen signed-in identity | No role grant | No application admin | **BLOCKED — USER ACTION REQUIRED**: two existing Firebase users, zero Google-linked users at audit; identity ownership cannot be inferred. Obtain your UID after Google login and run the explicit bootstrap below. |
| PostgreSQL | Yes | Docker health, connectivity, migration head/drift and aggregate records | Yes | **PASS — LIVE VERIFIED**: PostgreSQL 17 healthy, migration `fcc8ecdfdfad` at head; six existing fixture opportunities/versions preserved. |
| Gemini API/model | Yes, server-only key distinct from Firebase web key | Model GET and countTokens | Yes for metadata/counting | **PASS — LIVE VERIFIED** for `gemini-3.8-flash` access and token counting, not generation. No replacement model was selected. |
| Official-source ingestion | Adapter/fetch yes; no authorized application admin | Real fetch/parse; isolated DB capture test | Fetch works; full ingestion blocked | **PASS — LIVE VERIFIED** for 61+7 pages; **BLOCKED — USER ACTION REQUIRED** for authorized persisted application ingestion. |
| Gemini structured extraction | Yes | Two real source-bundle attempts | No candidate | **FAIL — NEEDS FIX**: upstream generation unavailable, second attempt HTTP 503; full live schema/output/evidence acceptance is unverified. No mocked replacement. |
| Admin review | Implemented | Automated tests only | Not live verified | **PASS — AUTOMATED TEST ONLY**: actual queue remains empty; sign-in/bootstrap/extraction required. |
| Opportunity publication | Human-controlled implementation | Automated tests only | Zero real publications | **BLOCKED — USER ACTION REQUIRED**: candidate generation plus your substantive review/approval; no automatic publication. |
| Personal profile | Implemented, protected | Persistence tests only; no real login | Not live verified | **PASS — AUTOMATED TEST ONLY**; actual fictional-profile creation pending Google login. |
| Real eligibility evaluation | Deterministic implementation | Automated backend tests and mocked browser contract only | Not live verified | **BLOCKED — USER ACTION REQUIRED**: login and an explicitly reviewed/published real version. |
| Deployment readiness | Plan/script/config template; actual hosted DB/secrets absent | Local smoke and automated plan guards only; fresh build failed | Not deployed | **CONFIGURED — NOT VERIFIED** for cloud execution. Explicit authorization, cloud prerequisites and hosted acceptance required. No public deployment URLs. |

## Findings, fixes and retests

### Firebase initialization cancelled active queries

Configuring Firebase revealed a real runtime regression. The initial signed-out `onAuthStateChanged` callback called `queryClient.clear()` after public/admin queries began. Observers could remain pending indefinitely. First browser run: **five failures, two passes**; discovery, empty catalogue and admin review stayed loading. This had been hidden when Firebase was unconfigured.

Fixed the listener to clear cache only when the UID changes. The existing main workspace subtree remains keyed by the current UID/guest state, so an actual account change remounts profile/editor state and does not retain previous-account form values. This preserves server authorization and does not add an auth bypass. Existing browser journeys now pass with real Firebase initialization configured. Actual in-app browser discovery also reached the empty state with no recorded console errors. The pre-existing main-element UID key already provided workspace remounting and was retained; no redundant route key was added. Real signed-in account switching remains pending interactive acceptance.

Sign-in errors now select static, localized English/Hindi messages for disabled provider, unauthorized domain, blocked/closed popup and network failure. Arbitrary provider error text is never rendered. A dedicated automated test checks known mappings, localization and rejection of sensitive-looking error messages.

### Live Gemini service failure lacked stage context

Both real source extraction attempts failed with `gemini_service_error`. The second attempt confirmed **stage `generate_content`, HTTP 503**; token counting succeeded. Added safe failure stage/status/token metadata to `ExtractionFailure`, stage/status logs for provider failures, and a pre-generation input-budget log. Only allowlisted stage names, diagnostic codes, numbers and configured model identifiers are recorded; no provider error text, prompts, keys or private facts.

A real-SDK serializer test with a mocked HTTP transport now reproduces count success followed by generation 503, asserting one generation attempt, correct stage/status/token metadata and no secret-bearing provider text in logs. This is a regression test, not a simulated successful extraction. No request-configuration error was established by HTTP 503, so the model/schema/SDK were not speculatively replaced.

### Container package download failure

The first fresh Docker build failed after 321.7 seconds while resolving a Hatchling build dependency from PyPI (`trove-classifiers`): TLS peer closed the connection. The bounded retry also failed after 82.50 seconds downloading/extracting the protobuf wheel, with a network timeout. No TLS bypass or untrusted package mirror was used. Added BuildKit uv cache mounting and one HTTP retry with a 30-second read timeout, retaining frozen dependencies and TLS verification. This bounds retry amplification per request; it is not an overall build-duration cap. Fresh-build reproducibility is blocked by package-network access; current code was smoke-tested against the prior image with the same frozen dependencies, as detailed below. See [uv Docker guidance](https://docs.astral.sh/uv/guides/integration/docker/) and [uv network settings](https://docs.astral.sh/uv/reference/environment/).

## Live source and model evidence

The existing allowlisted `depwd-pre-matric` adapter fetched the real 2024 guidelines and 2025 amendment, both successfully parsed. **68 PDF pages, 127,248 text characters**; bundle SHA-256 `32d14860c90b70276d91d12eb4e23d8f2eed4851c9f2798b103d060f93214446`, matching Phase 2.5. Per-document hashes/robots/retrieval metadata were captured locally; no blocks/CAPTCHAs were bypassed. See [official guidelines](https://cdnbbsr.s3waas.gov.in/s3e58aea67b01fa747687f038dfde066f6/uploads/2024/09/202409261656732428.pdf) and [amendment](https://cdnbbsr.s3waas.gov.in/s3e58aea67b01fa747687f038dfde066f6/uploads/2025/09/202509111852335844.pdf).

The actual configured key can retrieve `gemini-3.8-flash` metadata: input limit 1,048,576; output 65,536; generation/counting listed as supported. Bundle count including instruction/schema text is **45,989 tokens**, plus the application's 1,024-token framing reserve, under the configured 200,000 input cap. Output cap 16,384, LOW thinking, 120-second timeout per request, one attempt per SDK call remain unchanged.

Attempt 1: official fetch 6.60s; extraction 2.19s; `gemini_service_error`. Original code did not expose stage/HTTP status, so neither is retrospectively invented. Attempt 2 reused those captured pages: 1.53s; `gemini_service_error`, generation stage, HTTP 503. Additional metadata and token-count probes performed no generation. **No more generation attempts were made after the second failure.**

At published standard rates of $0.75/M input and $3.75/M output through 31 December 2026, the configured caps give a conservative two-attempt token-price estimate of **$0.4229**, excluding taxes/rounding/framing uncertainty; this is not a measured invoice or hard account spend cap. Measured bundle size would be lower. No tools, grounding, paid provisioning or automatic SDK retries were enabled. [Google pricing](https://ai.google.dev/gemini-api/docs/pricing)

The live probes directly invoked the existing adapter/extractor under the operator's authorized audit request. They **did not bypass the admin-only ingestion service** or fabricate an actor. Public source pages and sanitized reports are under ignored `.live-validation/phase26-*`; no candidate file was produced. No application `IngestionRun`, snapshot or candidate was inserted because no authorized application admin exists. The separate live-source test verifies DB evidence preservation in an isolated test schema, removed afterward. Neither is a successful persisted ingestion.

There is no generated requirement set to inspect or correct. Live completeness, schema acceptance and quote accuracy remain **unmeasured**. The [Phase 2.5 source-review checklist](phase-2.5-validation.md) remains the review baseline: common versus pre-matric provisions, precise annual parental-income context, amended UDID/Aadhaar requirements, classes IX/X, recognized full-time education, other-scholarship/repeated-class/sibling exceptions, renewal and cross-state verification, competitive selection and unknown dates. Do not assume a current application round is open. Unsupported rule-language conditions must remain explicit unknowns; no policy fact is manufactured to reach acceptance.

## Authentication and backend integration evidence

Selected-project ADC refresh succeeded. Identity Platform project config returned 200; both `localhost` and `127.0.0.1` are authorized. Google provider GET returned 404; provider list returned 200 with no configured providers. Firebase Admin `list_users` succeeded: two users, no Google-linked users, no further page. Only counts were printed; identities and credentials were withheld.

Firebase Management API confirmed the configured app is registered as `AiBuilderCup`; app ID, API key, auth domain and project match the ignored frontend file. Server Gemini key and web API key are distinct. Browser initialization succeeded. The actual Google sign-in attempt failed; no real Firebase ID token was obtained, exported or substituted.

API `/health` and Vite-proxied `/health` returned 200. Private `/v1/me` and `/v1/admin/sources` without credentials returned 401/`authentication_required`. An intentionally invalid token was rejected with 401/`invalid_token` on the configured API. These checks do not prove verification of a valid user's token or live revocation behavior. Actual normal-user 403 checks await login; automated PostgreSQL/permission tests pass.

Real CORS preflight with Authorization/Content-Type and PUT succeeded for both local origins; an untrusted HTTPS origin returned 400 without an allow-origin header. No CORS broadening was needed. Final DB aggregates: six opportunities and six versions (existing synthetic fixtures), zero application users/admins/ingestion runs/audit events. Zero real drafts/publications. Records were not deleted, reseeded or modified by the audit. Existing env files were not overwritten; `git check-ignore` confirms env files and local audit captures are ignored.

## Executed checks

`UV_CACHE_DIR=/tmp/opportunity-uv-cache` was used with uv. Browser binaries: `PLAYWRIGHT_BROWSERS_PATH=/tmp/opportunity-browsers`. All test schemas are isolated and removed. Tests do not populate the real catalogue or grant application roles.

| Executed command/check | Final result |
|---|---|
| `make preflight` | Passed before and after changes; all configuration-presence checks true. This remains config-only, not live acceptance. |
| `cd apps/api && uv run alembic current` / `uv run alembic heads` | Both `fcc8ecdfdfad (head)`; no migration was needed. |
| `make contracts` | OpenAPI/TypeScript regenerated; no contract differences. |
| `make check` | **64 passed, 1 optional network test skipped**; Ruff lint/format, Alembic drift, ESLint, TypeScript and production frontend build passed. |
| `RUN_LIVE_SOURCE_TESTS=1 uv run pytest tests/test_pipeline.py::test_live_official_source_capture -q` from `apps/api` | **1 passed**; actual PDF fetch and failure-preserving DB capture, Gemini intentionally unconfigured inside this isolated test. |
| `cd apps/api && uv run alembic check` | No new upgrade operations detected. |
| `make test-e2e` with the browser path above | **7 passed after fix**. Six existing browser journeys plus one unit-level error-message mapping test. Auth/evaluation/publication journeys retain explicit mocks; not live acceptance. |
| Actual in-app browser | Firebase initializes; catalogue finishes loading, shows zero real records, recorded console-error count zero. Google sign-in failed; no authenticated journey claimed. |
| `docker build -t opportunity-api:phase26 apps/api` | **Failed twice** on external PyPI TLS/download timeout (321.7s, then 82.50s). No fresh image was produced; cloud build remains unverified. |
| Local container smoke | **Passed with explicit limitation:** cached `opportunity-api:phase25` production-dependency image, current `apps/api/src` mounted read-only. `/live` 200, `/health` 200/connected, catalogue total 0, profile/admin 401, UID 1000; current failure-stage code loaded. Container removed. This is not a successful fresh image build. |
| `git diff --check` | Passed. |

Initial expanded regression run had five browser failures caused by the Firebase cache-reset race; the corrected run passed all seven. Earlier SDK unit run passed 11 tests before adding the observed generation-failure case; final full suite includes it. Known nonblocking warnings: Starlette HTTPX TestClient deprecation, Alembic `path_separator`, and browser worker color settings. No schema migration or dependency/model replacement was introduced.

## Prioritized actions for the user

1. Open [Firebase Authentication providers for venuesignal](https://console.firebase.google.com/project/venuesignal/authentication/providers). Choose **Google → Enable**, select your project support email and save. This changes authentication configuration; it was not performed automatically. Both local domains already exist in **Authentication → Settings → Authorized domains**.
2. At [local account settings](http://127.0.0.1:5173/settings), complete Google sign-in interactively. Do not send passwords, tokens or keys in chat. Confirm the app shows your signed-in state. If a popup is blocked, allow this application's Google sign-in popup and retry.
3. Open **Firebase Console → venuesignal → Authentication → Users**, select **your signed-in account** and copy its UID locally. Two pre-existing non-Google users cannot be assumed to be your intended admin identity. From a trusted local terminal:

```sh
cd /Users/govind/Projects/AIBuildersCup/apps/api
uv run python -m opportunity_platform.admin.bootstrap --project-id venuesignal --uid YOUR_CONFIRMED_FIREBASE_UID
```

Replace only the UID argument with your own Console UID. No arbitrary account was granted admin during this audit. Refresh the app afterward. Successful bootstrap verifies the account and writes its audited DB role.

4. Once Gemini generation is available, run **one** source ingestion at [local admin review](http://127.0.0.1:5173/admin), or:

```sh
cd /Users/govind/Projects/AIBuildersCup/apps/api
uv run python -m opportunity_platform.ingestion.service --source depwd-pre-matric --actor-uid YOUR_CONFIRMED_FIREBASE_UID
```

Do not loop paid attempts. If another 503 occurs, retain diagnostics and check [Google AI Studio status](https://aistudio.google.com/status) and your project's **AI Studio → Usage / Rate limits** before retrying. Current evidence supports keeping the configured model; switching is not justified solely by this service failure.

5. When a draft exists, inspect its complete evidence/requirements/diff in `/admin`, correct omissions/unsupported interpretations, add a review note, and acknowledge flags/completeness only after genuine review. **You must authorize substantive publication.** No draft is currently ready for review and nothing was published automatically.
6. After publication, create a fictional profile through `/profile`, evaluate the real record, inspect citations/unknowns, edit a relevant fact and re-evaluate. Test a substantive blocker against an unrelated fact. Sign in as a genuine non-admin in another browser context to confirm admin 403. Do not use mocked tokens or synthetic opportunity substitutes for acceptance.
7. Retry `docker build -t opportunity-api:phase26 apps/api` once Docker can reliably reach PyPI and files.pythonhosted.org; do not disable TLS verification. A clean image build still needs to pass. Before any deployment, explicitly authorize the project/budget/region and provide the hosted database, IAM and pinned secrets described in [deployment procedure](../infra/README.md). No Google Cloud deploy or paid resource provisioning was attempted.

Final formatting/type check: `cd apps/web && pnpm exec prettier --check src/app/App.tsx src/app/auth-errors.ts src/i18n/strings.ts tests/auth-errors.spec.ts && pnpm typecheck` passed. Ignored secret files were preserved and no credentials entered source control.

**Phase 3 readiness:** not yet. The audit fixed a real configured-Firebase runtime bug and verified infrastructure access, but successful model extraction, human-reviewed publication and real authenticated eligibility are still required before the Unlock Graph milestone.
