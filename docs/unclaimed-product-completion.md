# Unclaimed: source-backed discovery and readiness release

Unclaimed keeps its name, domain, logo and existing infrastructure. Initial HTML and rendered browser titles explicitly retain Unclaimed; an environment variable cannot silently rename it. This is an application-only release on local `master`; production mutation requires approval of the final exact commit. The existing research catalogue and policy publication gates remain intact.

## Implemented behavior

- Authenticated Discover loads automatically without a query, household or business. One typed response carries provisional research comparisons and strictly published reviewed-policy assessments. Empty-query matching evaluates the applicable small research catalogue before pagination; embeddings do not limit its recall.
- Discover, Overview, Unlock Plan and Scenario Studio use the selected subject. Switching to Just Me clears the previous workspace target; navigation and missing-fact links preserve the intended subject. Family research evaluates each authorized person separately, without treating the household as an individual applicant or inheriting relatives' income/category facts.
- Known canonical TEAM/ST policy identities suppress their research counterpart when the reviewed result is present. TEAM's five components share one personalized programme card with explicit component links. Other identities are not merged using fuzzy title similarity.
- Comparison results distinguish supplied facts, unknown policy interpretation, missing information, documentary gaps, known mismatches and potentially actionable future changes. They never certify eligibility. Dates, funding, recognition, category and application availability remain unknown where not established.
- Missing-fact links target the correct person or business. Research preparation tasks reuse the existing subject-scoped `ActionItem` persistence and progress endpoint. Current dependencies are recomputed before progress writes. Completed preparation never verifies documents or changes profile facts. Resolved dependencies disappear from the current plan; historical action rows are retained.
- Scenarios compare actual/hypothetical cited outcomes, including supported member overrides, hypothetical new people and exclusions. Hypothetical people grant no permissions. No scenario facts, relationships, action progress or evidence are persisted.
- English/Hindi search reuses the existing pinned 384-dimensional multilingual ONNX encoder. Public representations/vectors are cached by content, model and representation fingerprints. Private queries stay request-scoped; lexical fallback remains available without the model. No new training, hosted inference or vector database.
- Historical notices remain in the archive. There are zero verified currently actionable tenders. Original source destinations are labelled separately from unestablished application portals.

## Bounded source mappings

These are provisional source comparisons, **not approved eligibility policies**. The committed manifest binds every mapping to programme identity, snapshot ID, original binary hash, source URL, page and exact captured passage. Runtime comparison fails closed when that evidence is unavailable or differs.

| Programme | Captured evidence | Comparable supplied facts | Still unassessed |
|---|---|---|---|
| ST post-matric scholarship | ST guidelines, page 3 | Current study; completed class X/higher; bank-account presence | ST/domicile recognition, course/institution recognition, scheduled-bank/linkage specifics, income/exemptions, other awards and remaining clauses |
| PM-YASASVI pre-matric | Combined guidelines, page 3 | Nationality; current class IX/X; full-time study; government school | Certified beneficiary category, parental/guardian income, implementation and other-award restrictions |
| PM-YASASVI post-matric | Combined guidelines, page 12 | Current study only | Course classification, beneficiary category and other conditions |
| MSME TEAM (five components) | TEAM guidelines, page 12 | Explicit Udyam registration; supplied micro/small classification; manufacturing/services sector; similar-assistance exclusion | Prior SNP onboarding relative to operationalisation, transaction-data authorization, GST scope, component procedures, funds and tenure |

Four programme parents / eight existing listing records have mappings. There are 36 mapping records: 28 evaluable comparisons (12 distinct comparisons across programme parents) and eight explicit incomplete-policy markers. No new programme, benefit, deadline, government approval or live application round was invented. Income and age comparisons remain supported by the reviewed engine; these provisional mappings do not invent numeric thresholds or erase source-specific exceptions to expand coverage.

## Validation actually executed

- `make contracts`: regenerated OpenAPI and TypeScript definitions.
- `make check`: formatting/lint, **285 backend tests passed, nine optional skips**, Alembic reports no drift; frontend lint, TypeScript and production build passed. Existing pypdf/Alembic deprecation warnings and the Vite bundle-size advisory remain.
- `make test-e2e`: **38 passed**. This suite combines local public API flows with explicitly mocked private/UI contracts.
- `make test-product-e2e`: **13 passed, one optional corpus-path test skipped**. Actual Chromium + official Firebase Auth emulator SDK + FastAPI + disposable PostgreSQL schema; no auth dependency override. Includes real-source personal discovery, captured page reader, task progress, enrollment scenarios/reset, Hindi/mobile, business readiness, separate dependent comparisons and revocation. Existing integrated tests cover account isolation and the five search contexts.
- `NEURAL_TEST_MODEL_DIRECTORY=/tmp/unclaimed-embedding-model uv run pytest tests/test_neural.py tests/test_research_completion.py -q -s`: **11 passed**, using the already-downloaded pinned model. Four measured English/Hindi research queries each returned an expected category within the first five candidates. This is a small retrieval check, not a legal-accuracy benchmark.
- Representative source fixtures assert ten saved programme–subject pairs: personal three, family six (two YASASVI programmes across parent/two dependents), business one grouped TEAM programme. Three additional hypothetical-member pairs are assessed without creating a person or consent record. Additional catalogue rows remain informational, without invented rules.
- One cached local amd64 Docker build; fresh PostgreSQL container migration/runtime validation passed at `f26c1000abcd`. All **101 installed runtime Python/JSON files** match source hashes. No fictional seed, credentials or private corpus in the image. Actual local encoder dimension 384; measured container peak memory 641 MiB, below the existing 1 GiB limit.
- `python3 infra/deploy.py --config infra/deploy.example.json`: plan only. Its printed Cloud Build/job commands were **not executed**. Release will upload the already-built image rather than request another build.

Default pytest skips comprise four optional corpus datasets, three local-model tests, one live-provider test and the optional research-model test. The model tests were run explicitly above. No paid AI test, new collection or OCR was run.

## Read-only production preflight

Neon transaction explicitly used `SET TRANSACTION READ ONLY`; cloud calls only read existing metadata. Confirmed **129 captures, 124 document hashes, 96 public research listings (74 main / 22 archive), six draft policy versions, zero reviewed/published eligibility policies**, and Alembic head `f26c1000abcd`. All 800 existing listing citations and all 36 new provisional mappings match actual captured/derived pages. Original sources and drafts remain unchanged.

Rollback targets read from live services:

- Cloud Run: `opportunity-api-00009-puc` (100% traffic), project `venuesignal`, region `asia-south1`.
- Hosting: `sites/unclaimed-ai-cup/versions/846ca7df4b4def5d`, release `sites/unclaimed-ai-cup/releases/1792248741818000`.

No live Google Sign-In or hosted authenticated acceptance of this new release has been claimed. Those checks follow exact-commit authorization and deployment using the already selected account.

## Authorized release boundary to request

Upload the one existing validated image; verify schema/permissions read-only; deploy and smoke a no-traffic Cloud Run candidate, promote only after checks, and deploy only `unclaimed-ai-cup` Hosting. Perform actual authenticated acceptance and restore the recorded API/Hosting versions if it fails. Normal subject-authorized plan/action writes may occur during acceptance; app rollback does not delete those records. Saved real facts should remain unchanged by scenario acceptance.

No migration, grants, source import/update, policy publication, new IAM/resources, scheduler, model rebuild, paid AI, billing change or remote Git push is needed. Preserve existing production flags, versioned secrets, Neon connectivity, 1 vCPU / 1 GiB, min 0 / max 1 and request-based billing. Existing registry/Run/Hosting usage remains the cost driver.

Remaining limitations: detailed provisional comparisons cover four programmes, not all 96 listings; current windows/application routes and substantial remaining conditions are unverified; broader income/exception rules, district-specific research conditions, connected-adult invitation completion and comprehensive Hindi legal explanations are not claimed. Source clauses remain in their original language. Publication still needs substantive approval of specific policy versions. Live release and authenticated hosted acceptance remain gated on the one exact-commit approval.
