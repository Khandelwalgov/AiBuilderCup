# Phase 4 implementation report — 16 October 2026

Five search contexts, explainable exact recommendations and an ephemeral Scenario Studio are implemented locally. A fictional future family triggers a fresh retrieval pass and retrieves household opportunities absent from the actual personal shortlist. Production deployment was not requested or performed.

## Delivered behavior

- Working PostgreSQL FTS/GIN, structured applicability and stratified coverage channels; deduplication, fair per-subject pair budget, deterministic ranking and visible shortlist limits. Small catalogues fitting the budget are assessed in full.
- Neural adapter contract and public version-aware representations, private request-scoped subject facts and unknown masks. **No real embedding model was used; neural retrieval is unavailable.** No fabricated vectors or neural-success claim.
- Just Me, My Family, Specific Family Member, My Business and full Explore All. Family recommendations identify each authorized person separately. Household income is never an average or sum. Restricted adults are not exposed; revoked dependent access and other-account subject IDs are denied.
- Exact existing evaluator reused through a pure helper; source citations, unknown states, dated facts, education semantics, scoped income and document verification retained. Known blockers remain distinct from missing information.
- Studio supports scoped person/parental/household/business income, education, enrollment, geography, employment, registration, operating context, fictional spouse/children/dependents, and per-member overrides or scenario-only exclusions. Fresh/renewal can be explicit or unknown.
- Actual versus hypothetical retrieval/condition comparisons, cited cards, hypothetical Unlock Graph, shared scoped actions, known blockers, reset/discard and English/Hindi controls. Selected subject is carried into real detail/evaluation/plan/assistant navigation; hypothetical IDs are not sent to the persisted assistant.
- Generated OpenAPI/TypeScript contracts, additive local migration `f24a1000abcd`, environment example, deterministic fictional benchmark and integration tests.

## What persists

The local SQL generated vector/index and normal application code/configuration persist. Search/scenario transactions roll back, and service-level commit-after-simulation tests prove no new profile facts, people, households/memberships, documents, evaluations or actions. Studio state is ephemeral browser memory; there is no saved-scenario retention. Existing actual profile/save/check/plan workflows retain their original explicit persistence behavior. Hypothetical relationships grant no actual consent; changed circumstances never manufacture verified documents.

## Measured benchmark

450 fictional policies, nine categories, three reserved training scenarios, five held-out scenarios and three timing repetitions per K. No training occurred. The oracle is exhaustive subject-applicable exact assessments without known failures, including unknowns and query wording mismatches.

| Metric | Hybrid | Historical ILIKE |
|---|---:|---:|
| Macro Recall@50 | 10.61% | 6.49% |
| Macro Recall@150 | 31.10% | 6.49% |

At K=150, candidate-generation p50/p95 = **16.19/29.74 ms**, exact evaluation = **3.24/16.80 ms**, ranking/view assembly = **2.22/16.25 ms**. These are local phase measurements, not end-to-end network latency or production SLAs. One school-query scenario favors ILIKE at K=50. Broad oracle sets exceed K, so the shortlist is deliberately disclosed as incomplete. This benchmark does not establish real-world recommendation accuracy. Full methodology, per-case subject/category coverage and raw metrics are in [search-benchmark.md](search-benchmark.md) and [retrieval-benchmark-results.json](retrieval-benchmark-results.json).

## Executed validation

| Command/check | Actual outcome and boundary |
|---|---|
| `make contracts` | OpenAPI and frontend types generated from Pydantic. |
| `make preflight` | All sanitized configuration checks true; this verifies configuration presence, not provider availability. |
| `make check` | Final full command: 192 backend passed, 1 live-fetch skipped, clean Alembic drift, Ruff, frontend ESLint/TypeScript and production build passed. |
| Final `.venv/bin/pytest -q` | **193 passed, 1 skipped** after adding the monetary-boundary regression. Includes 32 independently authored concurrent corpus tests; Phase 4 did not modify that collector. |
| Targeted PostgreSQL integration | Six Phase 4 tests: exact age/income boundaries and trillion-rupee overrides, unknown scope, fair 150-pair allocations, national visibility, determinism, actual/future retrieval differences, unchanged equivalence, commit-after-simulation non-persistence, restricted adult/revoked/cross-account denial, reviewed-pointer preservation under a newer draft. Other existing planner/privacy/version tests passed too. |
| `make test-e2e` | **29 passed**, ordinary regression suite with mocked protected workflows and real public/empty pages; task ports 15211/18211, cached Chromium. |
| `make test-product-e2e` | **10 passed**, actual browser + Firebase Auth emulator + local FastAPI/PostgreSQL/private-file store. All five search contexts, context-specific detail navigation, scenarios/reset, responsive captures and Hindi controls exercised; no authentication bypass. Task ports 15210/18210; disposable schema/files cleaned on shutdown. |
| Retrieval benchmark | Real PostgreSQL in random disposable schema; 450 fictional records; actual SQL FTS and ILIKE, pure exact evaluator; no provider calls. Schema dropped afterward. |
| Production frontend build | Passed; existing Vite warning remains for the main bundle above 500 kB. |
| Local API smoke | `/live`, `/health`, `/v1/opportunities`: 200. New `/v1/search` and `/v1/scenarios/evaluate` without tokens: 401. Existing smoke also asserts privileged/workspace authentication. |
| DEPwD source audit | Both original drafts, captured page content/hash, candidate JSON and citations unchanged. 36 + 34 = **70 citations** revalidated against saved pages. Zero real published opportunities; no review/publication action. |

The first product-browser invocation failed before any test ran because the default Chromium cache path was missing. Re-running with `PLAYWRIGHT_BROWSERS_PATH=/tmp/opportunity-browsers` succeeded. It was an environment-path correction, not a skipped product failure. The task-owned Auth emulator was shut down after validation; the user's existing API/web servers were preserved.

**Live versus mocked:** Real local database, migration, evaluator, planner, Firebase emulator authentication, UI and file storage ran. Some older browser tests and provider unit tests use explicit mocks. No live Google authentication/service call, Gemini/OpenAI generation, paid embedding, official-source fetch/ingestion, review, publication, deployment, provisioning or push was performed in this Phase 4 work. Existing Gemini default and explicit development OpenAI configuration remain available unchanged.

## Screenshots inspected

All captures contain fictional test accounts/policies and emulator banner. Desktop and mobile overflow checks are part of the capture helper.

- [Personal recommendations](screenshots/phase4/phase4-ranked-me.png)
- [Family results with distinct parent/dependent outcomes](screenshots/phase4/phase4-family-context.png)
- [Actual/future comparison and Unlock Graph](screenshots/phase4/phase4-scenario-family.png)
- [Mobile scenario](screenshots/phase4/phase4-scenario-mobile.png)
- [Hindi mobile Studio](screenshots/phase4/phase4-studio-hi-mobile.png)

## Remaining limits

Neural retrieval is unavailable; no pgvector/ANN index or training pipeline is claimed. Candidate metadata is scanned in memory and large-catalogue/load performance is unproven. Recall is incomplete and needs real reviewed-policy judgments. Fictional relationship labels do not invent source-specific household-composition formulas. Legal passages and existing exact-evaluator explanations retain original wording; English/Hindi control coverage is not validated legal translation. Scenarios are ephemeral, not privately saved. On narrow screens the existing graph uses the full text checklist instead of a dense node diagram. Production uploads remain gated by the earlier malware-scanning limitation. No additional official policies were published for this milestone.

## Local commits

- `95294b6` — authorized hybrid retrieval, pure exact assessment, scenario backend, migration/contracts.
- `d91fe17` — five-mode Discover, Scenario Studio, scoped planner, permissions/version tests, real browser journey.
- `2912a84` — screenshot-driven layout correction and exact parental-income boundary/trillion-rupee regression.
- Final documentation commit — fictional benchmark fixtures/script/raw results, architecture/scenario/report documents and five inspected screenshots. The separate corpus commits are not Phase 4 implementation work.

Architecture: [hybrid-retrieval-architecture.md](hybrid-retrieval-architecture.md). Scenario behavior: [scenario-engine.md](scenario-engine.md). No remote push.
