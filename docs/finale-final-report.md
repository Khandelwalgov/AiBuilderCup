# Finale release candidate — 15 October 2026

The local product now has a substantially different Intelligence Atlas composition: editorial landing, evidence-centered detail and review workbenches, distinct context mastheads and a deterministic interactive graph. The core engineering gaps are corrected: eight genuinely equivalent DEPwD document dependencies merge across the two saved candidate copies, and unchanged consecutive assessments reuse persistent records. Source/version/fact changes retain history. The complete hosted P0 acceptance remains gated by human publication, genuine Firebase testing, Google model availability and authorized deployment.

No genuine draft was edited, regenerated, approved or published. No administrator was created, private profile transmitted, live model called, cloud resource provisioned, deployment executed or Git push made.

## Completion and verification

“PostgreSQL” means actual local storage in disposable schemas with fictional identities. “Contract” means explicit browser API mocks, not a signed-in Firebase session. Live below means the actual local public API/container or read-only saved-source audit.

| Capability | Implemented and tested | Actual live state / remaining gate |
|---|---|---|
| Authentication | Existing Firebase token/revocation backend preserved; object permissions and localized errors tested | Real interactive sign-in/private journey remains human acceptance |
| Landing | New Atlas composition, illustrative connection specimen, real navigation, responsive EN/HI | Public UI rendered; illustration never claims a match |
| Home/dashboard | Actual summary and top plan action; minimal-profile entry; account/context utilities | Populated component tested with fictional API; real authenticated rendering pending |
| Discover | Search/filter/detail, visible coverage, national inclusion opt-in; no domicile inference | Actual normal catalogue remains empty; development fixture navigation tested |
| Opportunity detail | Editorial issuer/summary, sectional evidence, application context and condition ledger | Populated contract tested; real publication required |
| Personal profile | Progressive optional topics, provenance, missing-field deep links, save/return-to-plan | PostgreSQL and contracts; no automatic save from links |
| Households | Create/edit/primary and identity workbench; fixed erroneous create-on-edit call | PostgreSQL and contract PUT regression; real auth pending |
| Managed dependents | Explicit guardian grant, separate facts/plans, revocation | Adversarial cross-account and post-revocation tests pass |
| Businesses | Unregistered workspace, roles, independent facts/plan | Owner/editor/viewer boundaries tested; no real business opportunity coverage |
| Context-aware eligibility | One typed deterministic engine; personal/household/business and fresh/renewal | PostgreSQL results; unsupported household/policy semantics stay unknown |
| Document provenance | Exact saved-page quotations, individual document bindings, provider/hash/version | 70 genuine saved citations revalidated; no current remote re-fetch |
| Shared actions | Eight shared DEPwD documents, explicit aliases, scoped source basis and subject | Copies approved solely in disposable test schemas; genuine drafts untouched |
| Unlock Graph | Deterministic directed layout, selected/hover paths, pan/zoom/measured fit, evidence details | Fictional desktop/tablet/mobile contracts; mobile uses complete checklist |
| Simulation | Actual vs hypothetical comparison; age preview without persistence | PostgreSQL and browser contract; no evidence verification manufactured |
| Source versioning | Human review transition/pointer and obsolete-link replacement | Real logic with explicitly fictional test amendment; no real government amendment fabricated |
| Re-evaluation | Relevant-fact refresh, stable fingerprint, distinct history and outcome diff | Repeated/concurrent/context/version/hypothetical tests pass |
| EN/HI explanations | Cited local messages distinguish evidence/context/selection; stale snapshots rejected | Deterministic tests/contracts; Gemini generic intent mocked, not live accepted |
| Admin review | One-condition editor beside searchable capture, document evidence, amendment pages, field-change history | Actual 68-page public-copy browser navigation tested with mocks; real admin acceptance pending |
| Publication controls | Admin role/hash/locks/exact citations/completeness/document evidence retained | Real publications zero; substantive review belongs to user |
| Build | Lint/types/contracts/migrations/web and clean API image | Local build and non-root container smoke passed |
| Deployment readiness | Plan-first existing Firebase/Cloud Run/Cloud SQL workflow | Illustrative plan only; actual resources/IAM/secrets/cost authorization unverified |

## Material technical changes

Migration `d03e9c62e843` adds nullable `Requirement.document_dependency` and indexed `MatchEvaluation.fingerprint`, preserving old rows. Engine version is 3. Explicit plain-name aliases normalize UDID, Aadhaar, photograph, age proof, disability certificate, parental-income certificate, tuition receipt and academic qualification. Authoritative URL/page, subject scope and income basis remain in identity. Conditional/open-ended labels retain separate clarification identities. Typed UDID and its document-list entry share an action. Every link retains its own requirement/version/citation. Progress never verifies a document.

Fingerprints cover relevant values, origin/verification, validity, income period/definition, subject, published version, application context, date and engine. Fact UUIDs and audit timestamps do not cause duplicates. Subject-scoped transaction locks serialize concurrent callers. Consecutive unchanged assessments reuse ID/time; meaningful transitions (including returning to a previous context) preserve new history. Daily date changes allow date-sensitive evaluation. Simulations write nothing. Prior distinct snapshots supply meaningful differences even after unchanged reloads.

Planner reads batch catalogue rows, facts, requirements and citations. Responses remain bounded to 100 current opportunities; map display is six priority actions/six opportunities with full checklist. Browser requests have bounded cancellation timeouts. Stale explanation requests reject newer fact assessments/superseded versions. Account change cache clearing and guardian/business authorization remain intact. Household save now uses PUT for existing records; profile/action/admin changes invalidate related plans and summaries. Discovery can include national records without modifying facts.

No dependencies added. System fonts and existing Lucide/React tooling used. Base CSS primitives remain alongside the new composition stylesheet; consolidating legacy selectors is future maintenance. Detailed decision: `docs/decisions/0008-document-and-evaluation-identity.md`.

## Visual comparison and critique

Before directory: `/Users/govind/Projects/AIBuildersCup/.live-validation/finale-before/` (fresh baseline). After directory: `/Users/govind/Projects/AIBuildersCup/.live-validation/finale-after/`. Final public/empty captures also remain in `.live-validation/ui/`. All populated images are fictional contracts unless explicitly labeled public-capture-copy; none proves real Firebase authentication.

| Screen | Before filename | After filename | Composition change |
|---|---|---|---|
| Landing/home desktop | [Before](/Users/govind/Projects/AIBuildersCup/.live-validation/finale-before/dashboard-en-1440.png) | [After](/Users/govind/Projects/AIBuildersCup/.live-validation/ui/dashboard-en-1440.png) | Generic overview replaced by editorial Atlas, connected illustrative specimen and numbered method |
| Discover | [Before](/Users/govind/Projects/AIBuildersCup/.live-validation/finale-before/discover-en-1440.png) | [After](/Users/govind/Projects/AIBuildersCup/.live-validation/ui/discover-en-1440.png) | Search-led research masthead, sectional coverage, readable filters/results |
| Opportunity detail | [Before](/Users/govind/Projects/AIBuildersCup/.live-validation/finale-before/eligibility-populated-contract-1440.png) | [After](/Users/govind/Projects/AIBuildersCup/.live-validation/finale-after/detail-fictional-en-1440.png) | Editorial headline, outcome ledger and evidence folios |
| Profile | [Before](/Users/govind/Projects/AIBuildersCup/.live-validation/finale-before/profile-populated-contract-1440.png) | [After](/Users/govind/Projects/AIBuildersCup/.live-validation/finale-after/profile-fictional-en-1440.png) | Readiness journey, optional topics and follow-up navigation |
| Household | [Before](/Users/govind/Projects/AIBuildersCup/.live-validation/finale-before/family-populated-contract-1440.png) | [After](/Users/govind/Projects/AIBuildersCup/.live-validation/finale-after/family-fictional-en-1440.png) | Context masthead, member identities and separate personal plans |
| Business | [Before](/Users/govind/Projects/AIBuildersCup/.live-validation/finale-before/business-populated-contract-1440.png) | [After](/Users/govind/Projects/AIBuildersCup/.live-validation/finale-after/business-fictional-en-1440.png) | Independent business identity and scope/role workbench |
| Graph desktop | [Before](/Users/govind/Projects/AIBuildersCup/.live-validation/finale-before/graph-populated-contract-1440.png) | [After](/Users/govind/Projects/AIBuildersCup/.live-validation/finale-after/graph-fictional-en-1440.png) | Directed canvas with selected dependency paths, pan/zoom/fit |
| Graph mobile | [Before](/Users/govind/Projects/AIBuildersCup/.live-validation/finale-before/graph-populated-contract-hi-320.png) | [After](/Users/govind/Projects/AIBuildersCup/.live-validation/finale-after/graph-fictional-hi-320.png) | Full readable checklist/evidence and actual/hypothetical comparison |
| Admin | [Before](/Users/govind/Projects/AIBuildersCup/.live-validation/finale-before/admin-populated-contract-1440.png) | [After](/Users/govind/Projects/AIBuildersCup/.live-validation/finale-after/admin-fictional-en-1440.png) | Focused condition editor beside searchable captured source |

Additional: `cockpit-fictional-en-1440.png` is a test-only component fixture, not real auth. `admin-public-capture-copy-1440.png` displays the actual saved public source copy with no writes. The latter verifies all 68 page options and amendment/UDID search/navigation.

Two deliberate screenshot review passes used actual image viewing. Composition fixes: overly broad SVG selector, excess graph whitespace, measured fit, context hierarchy and readable type. Product-polish fixes: captured text contrast, Hindi heading spacing/font, narrow filters, 320px English metric wrapping and source screenshot scroll position. Final desktop and narrow EN/HI graph, household, business, detail, profile and review images were viewed. This is visual QA, not WCAG certification or a claim that every frame was manually inspected.

## Executed validation

| Command/check | Actual result |
|---|---|
| Fresh baseline `make check` | 99 backend passed/1 optional live-source skipped; lint/format/drift/web passed |
| Fresh baseline selected Playwright suites | 10 passed; before captures preserved |
| `cd apps/api && uv run alembic upgrade head` | Additive local migration applied |
| `UV_CACHE_DIR=/tmp/opportunity-uv-cache make contracts` | Authoritative OpenAPI/TS regenerated |
| Final `UV_CACHE_DIR=/tmp/opportunity-uv-cache make check` | 105 backend passed/1 skipped, Ruff/format/Alembic drift/ESLint/types/build passed |
| `make finale-demo ARGS=--run-isolated` | Eight actual PostgreSQL disposable-schema scenarios passed |
| Full `PLAYWRIGHT_BROWSERS_PATH=/tmp/opportunity-browsers pnpm exec playwright test` in web | **18 passed** on dedicated ports; focused source-reader/cockpit checks also passed. |
| Frontend `pnpm lint && pnpm typecheck && pnpm build` | Passed after final UI changes |
| `uv run ruff check ../../scripts/finale_demo.py` and format check | Passed |
| `docker build --no-cache --pull=false -t opportunity-api:finale apps/api` | Passed with locked dependencies and normal TLS |
| `scripts/product_smoke.py --api-url http://127.0.0.1:18080` | Live health/catalogue 200; anonymous admin/workspace 401 |
| Image inspection | UID 1000, no `/app/.env`, no model keys; default Gemini, assistant live false |
| Read-only source comparison and citation validation | Two unchanged drafts/pages/hashes;70 valid citations;zero real publications |
| Frontend model-secret scan | No configured model secret in built assets |
| `python infra/deploy.py --config .live-validation/nightfall-deploy-plan-config.json` | Plan only, no cloud commands; illustrative configuration |
| `git diff --check` | Passed at milestones |

Intermediate failures were fixed, not suppressed: import formatting; fingerprints accidentally included recorded_at; typed/listed UDID initially split; old engine-version/previous-self snapshot assertions updated for new semantics; removed graph/reader selectors replaced with functional assertions; URL-driven checkbox feedback delay; 320px metric min-content overflow. Existing six deprecation warnings remain. One live-source test is intentionally optional/skipped; it was not a live model test. No final failing check is being hidden.

Image: `opportunity-api:finale`, ID `sha256:257aa329458ba24a7e161c53a5ada223a5820460b2cb0f842abea2503bc6a527`. Ignored evidence: `.live-validation/finale-source-audit.json`, `finale-release-manifest.json`, `finale-deploy-plan.txt`, screenshot folders. The temporary smoke container was stopped/removed; PostgreSQL data preserved.

## Data/model transparency

Two genuine private drafts, zero genuine published opportunities. Six pre-existing synthetic development catalogue fixtures remain gated and preserved. One captured DEPwD bundle:61 guideline pages + 7 amendment pages, two component adapters; not comprehensive India coverage. Both source hashes remain `32d14860c90b70276d91d12eb4e23d8f2eed4851c9f2798b103d060f93214446`.

Pre-Matric `9588fed8-1f25-423d-8b5f-890636e68695`:17 groups / 9 document citations / 36 total citations, provider OpenAI / model gpt-5.6-terra, historical 41,654 input + 3,725 output = 45,379 tokens, three prior correction entries unchanged. Post-Matric `db51eb5b-5972-4d5a-8b13-85144f2f62d5`:20 conditions / 8 document citations / 34 total, manual-curation, no model/usage, one prior correction unchanged. Copied fixtures contain public documents/candidate text only, no private account data.

Finale actual model calls **zero**; source fetches **zero**; new measured tokens/spend **zero**. Historical usage above is not new execution. Gemini remains default; local explicit OpenAI development settings retained. Live assistant remains disabled and optional Gemini is intent classification only. No Google AI success or unrestricted conversational legal reasoning is claimed.

## Tomorrow and remaining gates

Follow [the executable acceptance checklist](finale-acceptance.md). Local web `http://127.0.0.1:5173/`, admin `/admin`, API `http://127.0.0.1:8000/health`. Review real drafts first, authenticate fictional accounts, exercise separate contexts and revocation, publish only if justified, inspect shared graph/citations/EN/HI/simulation, then approve exact cloud prerequisites and rehearse the honest three-minute demo.

- **Human review:** policy meaning, completeness, amendments, benefits, income/household exceptions, current rounds and publication; real Firebase interactive acceptance.
- **Google credential/availability:** valid key/model and explicitly authorized bounded live testing. No repeated 503 or automatic fallback.
- **Cloud authorization:** project/region/budget/resources/IAM/pinned secrets/domains/migration and deployment approval. Plan output is not deployed infrastructure.
- **Genuinely limited implementation:** assistant intent only; unsupported legal/household semantics unknown; no complete registration/school geography evaluator beyond supported facts; graph bounded display; manual source/version refresh rather than scheduled monitoring. These limits are visible/documented, not external credentials issues.
- **Deferred P1/P2:** adult invitations, private document upload/verification, automated notifications, export/deletion lifecycle, real business/tender sources, broad portal discovery and submission integrations. No impact/approval/accuracy metric invented.


The populated cockpit was separately rendered through the real component in a test-only Vite HTML fixture with clearly fictional API responses. No Firebase state was forged and no production route was added. Screenshot review reduced the supporting summary strip so the API's actual next action is dominant. Test-only HTML/TSX are excluded from the production dist.


## Final local checkpoint

Final dedicated-port suite: **18 passed** (ten public/development-fixture/guest checks, seven explicitly mocked protected/component contracts and one error-message unit check). Final backend: **105 passed, one optional live-source test skipped**. Native normal API restored on 8000 and public smoke passed; it returns real catalogue total 0 and development catalogue 404. Test listeners 5174/8001 stop automatically; main Vite 5173 remains available.

The final build uses 453.56 kB main JS (135.46kB gzip), 155.47 kB Firebase JS (31.89kB gzip), 71.51 kB CSS (16.58kB gzip). No new dependencies. Before images: 63; final screenshot matrix has 56 public/empty captures, 48 populated workflow captures, 8 cockpit component captures plus source-copy and additional artifacts. Exact file paths are linked above. Production output excludes the cockpit HTML/TSX fixture; final asset manifest and configured model-secret scan are recorded locally.

Local milestones: d7999b8 (document/fingerprint correctness),7e29b5d (batching/privacy/diffs),837bf01 (Atlas design/workspaces); subsequent test and documentation commits are available with `git log --oneline 42e1017..HEAD`. All commits are local. No deployment/push occurred.
