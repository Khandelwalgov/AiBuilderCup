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
