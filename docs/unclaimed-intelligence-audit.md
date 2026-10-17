# Unclaimed intelligence integration — observed evidence

17 October 2026. **Local integration is implemented and tested; the new release and production corpus import have not been executed.** This report distinguishes observations, local acceptance and remaining production gates.

## Reconciliation

Merged the existing `codex/corpus-policy-integration` branch locally (`a7ca190`), preserving its original archive, importer, citation checks, review pipeline and history. The earlier deploy-runner `--args=` repair already present in the workspace is preserved. Existing untracked Hosting release artifacts are not included in this change.

The critical Discover defect was a frontend default: it selected Explore All even after authentication. Empty-query backend retrieval already existed but used a subject–policy pair cap. Signed-in visits now default to Just Me, the homepage fetches recommendations, profile/evidence/workspace/publication changes invalidate them, and small catalogues are exhaustive across authorized subjects. Cards expose category groups, preliminary states, missing conditions, benefits, dates, official links and captured citations. Empty coverage is explicitly not a finding of ineligibility.

The neural path was genuinely unavailable. It now runs pinned local ONNX weights, stores version-aware public vectors and ranks hybrid candidates. Actual-source testing found exported tokenizer truncation at 128 tokens; that defect was fixed before final validation. Exact rule evaluation and publication-pointer safeguards remain unchanged.

## Corpus measurements

| Metric | Observed |
|---|---:|
| Registered source groups | 23 |
| Groups attempted / yielding captured documents in initial acquisition | 4 / 4 |
| Production scheduled/monitored groups established by this assignment | 0 |
| Immutable URL/snapshot records | 125 |
| Unique original hashes | 120 |
| Unique PDF / HTML blobs | 115 / 5 |
| Original blob bytes | 193,031,267 |
| Snapshots audited and checkpointed with extracted page/section text | 125 |
| Unique documents with technical extraction completed | 120 |
| Documents flagged for OCR or encoding triage | 94 |
| Documents with unresolved exact issuer/title attribution | 117 |
| Classifications: guideline / tender / announcement / index / unclassified / irrelevant | 34 / 20 / 48 / 5 / 12 / 1 |
| Unique documents passing conservative candidate-preparation gates | 3 |
| Actual-source candidates prepared in this Codex session | 3 |
| Separate semantic verification passes actually performed | 0 |
| New candidates requiring human/independent review | 3 |
| Original pages selectively OCR'd locally | 2, from 1 document |

The 94 flags mean at least one page needs OCR/encoding review, not that all 94 PDFs are entirely scanned. The two OCR checkpoints retain original page numbers, source/image/text hashes, tool/language identities and confidence measurements. They do not replace captured evidence or automatically clear review flags. The inspected scholarship FAQ pages contain portal troubleshooting; they are not converted into an entitlement.

Three checkpointed candidates cover TEAM, LEAN and the individual-MSE trade-fair component of PMS. TEAM's similar-assistance, prior-network-onboarding, consent, payment-recipient and activity-window qualifiers are retained. LEAN explicitly limits captured financial provisions to **31 March 2026** and is flagged as unresolved/historical pending an official extension. Garbled PMS percentage text is not asserted as an amount. Scheme-specific conditions that the typed profile model cannot express remain unknown; they are not mapped to generic business registration or guessed income facts. Application URLs/dates absent from evidence remain null.

Persistent artifacts are under ignored `.corpus/processing/packets`, `codex-v1`, `ocr-checkpoints` and `neural-benchmark`. Original binaries/manifests are untouched. The real-browser acceptance schema temporarily contained the three actual-source drafts and was cleaned up afterward. The JSON packets remain for authorized production staging; do not mistake the disposable test database for production persistence.

## Read-only production observations

Using the existing deployed runtime credential **in memory**, a read-only Neon transaction returned:

| Metric | Production observed |
|---|---:|
| Alembic head | `f24a1000abcd` |
| Sources / snapshots / opportunities / versions | 0 / 0 / 0 / 0 |
| Administrators | 0 |
| Human-approved published real opportunities | 0 |
| Active production policy embeddings from this assignment | 0; new table not deployed |

Cloud Run was ready at revision `opportunity-api-00002-mxw`, with 1 CPU/1 GiB and synthetic catalogue, live ingestion, assistant generation and uploads all disabled. Billing-enabled status was checked and returned true. The existing image's Artifact Registry digest lookup was verified read-only. A separate read-only privilege check confirmed the runtime role has existing source/draft/audit DML permissions and cannot CREATE in the application schema. Grants on the two not-yet-created tables must still pass the post-migration gate. No cloud resource, Hosting release, secret, production role or Neon data was created or changed.

Actual public smoke against `https://opportunity-api-726508228584.asia-south1.run.app` passed `/live`, `/health`, catalogue shape/real-only publication, disabled development catalogue, unauthenticated private/admin routes, missing/invalid-token search/scenario rejection, allowed Unclaimed CORS and rejected untrusted CORS. Authenticated production search and actual Google Sign-In were not run.

## Local neural evidence

Model: `Xenova/paraphrase-multilingual-MiniLM-L12-v2`, revision `b9e20f0c6dd7e5f88c72259765011e6a3a9196bc`, 384 dimensions. Weights and tokenizer are SHA-256 checked; the original model is Apache-2.0 and multilingual. [Original model card](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2).

Real local inference and PostgreSQL-stored vector retrieval passed English paraphrase, Hindi, stale-version/hash invalidation and privacy tests. An exploratory benchmark reloads three actual-source vectors from disk before scoring six engineering-labeled English/Hindi queries: **4/6 top-1**, with all three documents present at top-3. This is a tiny relevance benchmark, not independently reviewed eligibility accuracy. Earlier 2/6 results exposed truncation; corrected 4/6 results are retained. Model load was about 460 ms and queries about 2–3 ms on the developer Mac. The final fresh amd64 container run measured 1,731 ms for model load plus inference and 632 MiB peak process memory. Cloud Run cold start, concurrency and production latency remain unmeasured.

## Inference and review truth

External paid generation/embedding/OCR requests: **0**. External inference expenditure recorded for this assignment: **US$0 / ₹0**. Codex interactive usage consumes the existing account's limits and is not an unlimited/free scheduled API. Its exact session model is not programmatically attested in staged metadata. [Codex usage/pricing](https://learn.chatgpt.com/docs/pricing).

Provider transports and semantic failure/repair cases are tested with mocks. The real local model, real archive parser, local OCR, real emulator authentication, FastAPI/PostgreSQL browser journeys and read-only production smoke ran without paid inference. No independent model verification success or human publication approval is claimed.

## Remaining gates and incomplete work

- GitHub CLI initially had no login, but Git's configured credential helper provided repository access without printing/saving a token. The remote default branch is `master`. CI results are recorded separately.
- The human must identify and authorize the first existing Firebase administrator. Bootstrap is plan-only, requires an existing saved profile, records an audit event and closes after a different administrator exists.
- **Actual release blocker:** the repository is private, its plan is Free, environment listing returned zero and `GET environments/production` returned 404. Native required-reviewer protection is unavailable for private repositories on this plan. Workflows now fail closed before cloud authentication if native reviewer/branch protection is absent. The human must choose a supported native setup or explicitly authorize one reviewed operator/Cloud Run Job release. Repository visibility, billing and protection are not changed automatically. [GitHub environment availability](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments).
- Approval remains required for additive migration `f25b1000abcd`, proposed private corpus bucket/worker identity/direct application-secret resource and actual production release/import. A read-only runtime privilege gate checks application grants on new tables before API promotion; role privileges are not assumed from secret names.
- Independent semantic review remains pending. Human substantive publication approval is still required. Three prepared packets are not a comprehensive 120-document interpretation; the remaining source text/issuer/encoding, amendment and applicability work is checkpointed.
- OCR tools are currently a selective local workflow, not bundled/accepted as hosted OCR. The immutable citation path deliberately refuses to substitute OCR guesses for original pages.
- Durable GCS/job integration and optional scheduling are implemented/configured but not live executed. No production collection SLA or deployed schedule is claimed.
- Published-policy indexing and authenticated populated-production recommendations cannot be accepted until an actual policy is reviewed/published and an authorized test identity is available. Large-catalogue/family concurrency, broader semantic recall and production memory remain unproven.

Execution sequence and public-resource commands: [production deployment runbook](production-deployment-runbook.md). Hosted acceptance: [checklist](hosted-acceptance.md).

## Final local validation

- Backend: **247 passed, 1 skipped**. The skipped test is an unapproved live paid-model probe. Actual corpus and pinned local-model tests were enabled. Provider transport and semantic-repair cases use mocks.
- Real local browser: **11 passed**, using Firebase Auth emulator, real API/PostgreSQL and the actual captured-source library/draft queue. Automatic blank-query Discover passed with explicitly fictional published policies; actual government drafts were not published to satisfy this test.
- Browser regression: **29 passed**; populated contract scenarios use mocks, while public/unauthenticated states use the local API. Evidence paths now work outside the developer's home directory.
- Ruff lint/format, frontend lint/TypeScript/format, OpenAPI/client generation and production frontend build passed. The existing >500 kB bundle warning remains. There is no configured Python static type-checker; backend Pydantic/contracts/tests ran.
- Final local Docker build passed. Fresh PostgreSQL 17 applied every migration through `f25b1000abcd`, `alembic check` detected no drift, schema/runtime privilege gates ran read-only, no fictional seed existed, and the non-root image loaded 384-dimensional local weights. No cloud deployment was performed by these checks.
- Backend, Hosting-only, seven-batch corpus and direct-secret deployment plans validated without executing cloud commands.
- **Remote CI passed for `8288be8`**: [run 38986222583](https://github.com/Khandelwalgov/AiBuilderCup/actions/runs/38986222583). Initial suite: 241 passed / 7 skipped (local corpus/model/live prerequisites absent); then the separate pinned-model stage ran 2 real inference tests successfully. Browser regression: 29 passed. Docker build and fresh PostgreSQL/model/runtime audit passed: head `f25b1000abcd`, 384 dimensions, 975 ms load/inference, 584 MiB peak on the GitHub runner. No cloud release/push or inference API call ran in CI.
- **Follow-up `b72eb46` CI passed**: [run 38986455791](https://github.com/Khandelwalgov/AiBuilderCup/actions/runs/38986455791). This localizes the new source-review labels and corrects runbook wording. Relevant contracts/backend/frontend/browser/build/plan checks passed; container/model stages correctly skipped for the frontend/documentation-only diff. The latest actual-source Hindi/mobile test also passed locally (1 test).
