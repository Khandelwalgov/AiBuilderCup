# Operation Nightfall progress

Started 14 October 2026. Solo workflow; existing working tree and real draft preserved.

| Milestone | Status | Evidence / next work |
|---|---|---|
| A — draft fidelity | PARTIAL | Confirmed document-publication citation bug; implementing explicit evidence and policy categories. No approval authorized. |
| B — design | DEFERRED | Requested design skills absent from installed skill catalog/files. Use existing React stack. |
| C/D — households/businesses | DEFERRED | Existing tables inspected; workflows not yet implemented. |
| E/G — planner/matching | DEFERRED | Existing deterministic evaluator retained. |
| F — second draft | DEFERRED | No additional paid model requests authorized. |
| H — assistant | DEFERRED | Live Gemini unavailable; no paid calls authorized. |
| I/J — release/quality | DEFERRED | No deployment authorized. |

No new live model calls, publication, cloud provisioning or deployment. Pre-existing uncommitted integration/provider changes are retained; milestone commits will include them explicitly where necessary.

A: draft correction stored successfully: 18 requirement groups, nine document-specific citations; original before/after audited, unchanged provenance, still draft. Additive migration `b81f7a40c621`. Baseline regression 84 passed / 1 skipped before new document-specific test. Pre-existing integration/provider/auth work included in first preservation commit.

B/C/D/E/G: working UI and backend added for household creation, explicit guardian-dependent access/revocation, dependent editing, business role-based editing, subject evaluation, persisted reusable actions, current-version dependency links, graph/list selection and age-correction simulation. Three isolated PostgreSQL workspace/planner tests passed. Four rendered public/protected-empty-state checks passed (56 screenshots, all four widths, EN/HI, no overflow/page errors). Desktop dashboard and Hindi 320px discovery visually inspected. Frontend lint/type/build passed. Real authenticated populated acceptance remains PARTIAL; no auth bypass is shipped. Household facts remain separate and unknown; no inferred family income. No real publication, AI call or cloud deployment.

Quality checkpoint: `make contracts`, `make preflight`, `make check` passed. 88 backend tests passed, one optional live source test skipped; migration drift clean; frontend lint/types/production build passed. No new dependencies. Added progressive question topics and optional advanced admin JSON; controlled source-backed correction cards remain primary.

F/H/G follow-up: second real Post-Matric draft `db51eb5b-5972-4d5a-8b13-85144f2f62d5` created using offline manual curation of the existing official capture; 20 conditions/eight document citations. Recorded provider `manual-curation`, no AI model/usage, no new fetch. A distinct adapter is registered; its associated snapshot retains the original capture hash and reuse provenance. Both real candidates remain draft. Pre-Matric now has 17 distinct groups after removing a redundant cross-state procedure, with typed class/full-time/recognized-school checks and unknown income/household interpretations.

Local bilingual cited assistant works from authorized current evaluations. Optional Gemini only interprets redacted generic concepts with no raw questions/facts/documents; operator switch defaults false. Live Google-model acceptance BLOCKED. Automatic fact-dependent re-evaluation preserves history and skips unrelated changes. Per-opportunity fresh/renewal context is explicit, never a universal personal fact.

Docker build `opportunity-api:nightfall` succeeded with locked dependencies and normal TLS. No TLS bypass, new dependency, cloud provisioning or deployment. Populated household/business and graph browser contracts passed (2 tests, fictional mocked API); graph desktop/Hindi narrow mobile and family screenshots visually inspected. Screenshot capture refined to scroll to top for fixed navigation.

Additional safety: fresh/renewal context now resolves per opportunity; mismatched contexts are not_applicable and unspecified contexts stay unknown. Conservative school facts are typed. Latest backend checkpoint: 95 passed/1 skipped; frontend capability-schema typing issue found and fixed by adding an explicit response model, after which lint/types/build passed. Final checks still pending after last hardening changes.

## Final checkpoint — 15 October 2026

| Milestone | Final status | Evidence / remaining boundary |
|---|---|---|
| A | COMPLETE for corrective implementation | 17 Pre-Matric groups/nine document citations; audited corrections, original preserved; human review/publication pending |
| B | PARTIAL | Cohesive redesign, progressive questions, structured admin, 63 local screenshots and keyboard checks; genuine authenticated populated acceptance pending |
| C | PARTIAL | Household/primary/dependent editing and guardian revocation implemented/tested; scheme-specific household logic stays unknown, adult invitations unavailable |
| D | PARTIAL | Business management/roles/context implemented; real reviewed business coverage and actual Firebase acceptance absent |
| E | COMPLETE for minimal local slice | Shared actions, current-version links, progress, graph/checklist and non-saving age simulation tested; real multi-opportunity acceptance needs publication |
| F | COMPLETE for draft preparation | Separate Post-Matric adapter/manual-curation draft; no new fetch/model call, no publication |
| G | PARTIAL | Typed subject-aware engine, school facts, per-opportunity fresh/renewal, affected fact refresh; unsupported interpretations remain unknown |
| H | PARTIAL / live AI BLOCKED | Local EN/HI cited explanations and Gemini intent integration tested with mocks; no successful live Gemini acceptance or unrestricted generative assistant |
| I | PARTIAL / deployment BLOCKED | Locked image builds, native/container smoke and plan-first procedure pass; no deployment/cost authorization |
| J | PARTIAL | 99 backend tests pass/one optional live test skipped; 14 browser checks pass plus five focused post-refinement checks; real authenticated/hosted acceptance pending |

Final extractor audit fixed loss of category/application context during shallow conversion and added a regression. Future schema versions are `policy-candidate-v3` / `policy-candidate-openai-v2`; historical metadata unchanged. No draft regenerated and zero new live AI calls. The final image is refreshed after this fix. API/Vite restored for local inspection; smoke containers removed. Full report: `docs/overnight-final-report.md`.
