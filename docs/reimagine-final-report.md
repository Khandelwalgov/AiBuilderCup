# Reimagine final report

15 October 2026. Local implementation delivered. Real Firebase-authenticated and deployed acceptance remain human checks.

## Changes delivered

Canonical centralized route metadata fixes the exact Settings→logo→Overview breadcrumb/active-link bug. `/dashboard` redirects to `/`; unknown routes have a real 404. Auth resolution has a loading boundary. Authorized subject selection persists in URLs across navigation, eligibility, profile and plan. Dependent editing cannot inherit a household's subject kind. Invalid IDs do not disclose identities or silently evaluate personal facts. Fresh/renewal remains explicit; unsupported subject kinds return 422.

PATCH is allowed by actual CORS middleware. Editable profile/workspace/candidate drafts survive background refetch; navigation and sign-out guard unsaved changes. Profile is now a real basics→questions→review/save flow. Candidate corrections submit the hash from when editing began, preserving concurrent-review safety. Assistant links target stable published requirement anchors and preserve context; old answers remount on context/evaluation/language changes.

Admin candidates have dedicated routes. Missing citation locations display an error rather than page-one fallback. Ingestion opens an explicit source/provider/model/draft-count/permission/budget/cost-risk confirmation; backend live HTTP ingestion defaults disabled. Provider/model changes reject stale confirmations. Publication and rejection have explicit second dialogs. No reliable dollar estimate is invented. Budget is informational rather than an automatic cap.

The visual identity was rebuilt across Landing, Overview, Discover, Detail, Profile, Family, Businesses, Unlock Graph, Settings and Admin. Public pages have top navigation without a permanent sidebar; authenticated workspace uses midnight navigation/cobalt actions; review uses a focused queue and dark captured-evidence reader. Legacy styles.css/finale.css were deleted, replaced by maintained token/base/shell/page/intelligence/review layers. Landing preview is interactive and explicitly illustrative. Graph opportunities can be inspected; actions, citations and shared edges use actual plan data. Zoom fit measures width; height changes no longer reset zoom. Arrow keys pan the focused canvas; mobile exposes the complete checklist.

## Checks actually executed

| Check | Final outcome | Evidence |
|---|---|---|
| `make contracts` | OpenAPI and TypeScript regenerated | `/tmp/reimagine-contracts.log` |
| `make preflight` | Configuration ready; local explicit provider OpenAI/model gpt-5.6-terra, values/keys withheld | `/tmp/reimagine-preflight.log` |
| `make check` | Ruff/format,108 backend passed/1 live-provider skip, migration no drift, web ESLint/TypeScript/build passed | `/tmp/reimagine-final-check.log` |
| `make test-e2e` using dedicated local ports |28 passed | `/tmp/reimagine-final-browser2.log` |
| Final context/card fix + explicit graph inspector/keyboard-pan assertions |7 targeted passed; web lint/type/build rerun passed | `/tmp/reimagine-final-targeted.log`, `/tmp/reimagine-production-build.log` |
| `make finale-demo ARGS=--run-isolated` |8 passed, saved public-candidate copies + fictional source/fact/version scenarios in disposable schemas | `/tmp/reimagine-demo.log` |
| Fresh `docker build --no-cache -t opportunity-api:reimagine apps/api` | Built successfully; manifest sha256:d739fe7c52427b0bd75f759a14c6f9887d82c147332519107b32a598eec50f5a | `/tmp/reimagine-docker.log` |
| Fresh local container and existing local API public smoke | `/live`, `/health`, catalogue200; privileged/workspaces401 without token; disposable container stopped | `/tmp/reimagine-container-smoke.log`, `/tmp/reimagine-smoke.log` |
| Real draft read-only integrity/citation validation | Both unchanged,70 validated citations,0real publications | `/tmp/reimagine-source-audit.log`, `.live-validation/finale-source-audit.json` |
| Production bundle fixture scan / Git whitespace | No fictional session/QA switch/concept board in dist; diff check clean | Local command checks |

Earlier runs exposed failures, which were fixed and rerun. Restricted sandbox initially prevented local socket/DB tests; approved local-only executions then passed. Automatic approval review initially rejected an ingestion test because its mocks were not evident; the entire ingestion service was replaced by a fail-fast test stub before the successful rerun. No source/model operation occurred during that rejected command or this sprint. Tests emit existing deprecation warnings; Vite warns about a532.87 kB uncompressed application chunk. These are not hidden as passed performance acceptance.

## Real versus mocked

Real: local PostgreSQL/ASGI authorization, persistence, deterministic eligibility/planning, CORS middleware, migrations, generated contracts, API image/build/HTTP smoke, public catalogue/browser reads, and read-only validation of actual saved official-source evidence. The isolated demo can publish copies only inside disposable test schemas.

Fictional: browser session props and private API responses for profile/family/business/context, evaluation, action progress, assistant, review and publication. These exercise production React components without adding an auth bypass. Saved DEPwD page copies are real public evidence, but the browser reviewer/session/API is mocked. No real Firebase sign-in, paid extraction, live source retrieval, notification, application submission or deployed acceptance was run.

Preserved real records: Pre-Matric 9588fed8-1f25-423d-8b5f-890636e68695 remains draft with 36 citations and 3 reviews; Post-Matric db51eb5b-5972-4d5a-8b13-85144f2f62d5 remains draft with 34 citations and 1 review. Shared captured hash 32d14860c90b70276d91d12eb4e23d8f2eed4851c9f2798b103d060f93214446 is unchanged. No user profile/household/business record was modified by the browser contracts.

## Visual evidence

Two distinct directions and selection rationale: [design system](reimagine-design-system.md). Before120screenshots are preserved under `.live-validation/reimagine-before`; after 89under `.live-validation/reimagine-after`, including all ten required screens in both languages and four widths, plus cockpit/capture variants. [SHA256 manifest](reimagine-screenshot-manifest.json) inventories local files. Baseline uses preserved captures from the preceding Atlas implementation, with a new responsive baseline check, rather than claiming every before-file was freshly created. Actual representative images were viewed. Two critique/refinement passes are documented. [Local gallery](reimagine-visual-gallery.html) links the required comparisons; PNGs remain local ignored acceptance artifacts.

## Limitations and human approvals

[Complete interaction audit](complete-interaction-audit.md) records handlers, authorization, states, keyboard/mobile behavior, executed evidence and limits. No claim that every control has real authenticated acceptance. Adult invitation/consent UI, verified-document workflows, account export/deletion and production notifications remain unavailable; their absence is disclosed. Viewer writes remain server-denied even where the editor can be opened. System fonts vary across platforms; source-authored descriptions, legal text and some technical rule identifiers retain original language. The desktop graph intentionally shows at most six prioritized actions/opportunities; mobile uses the full checklist. Dirty forms do not survive a forced browser crash. An informational ingestion budget cannot prevent spend after a separately authorized operator invocation.

Human substantive review of both official drafts is still required. See [acceptance and exact next actions](reimagine-acceptance.md). No real information was approved or published. No cloud deployment/provisioning/billing change, paid AI or Git push occurred.

## Local commits

- `e744dc0` — explicit ingestion permission, authorized subject evaluation, PATCH CORS and generated contracts.
- `dd352d4` — Opportunity OS redesign, contextual routing/auth/draft safety and browser regressions.
- Documentation/evidence commit follows this report; use `git log -3 --oneline` for its identity.
