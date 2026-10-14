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
