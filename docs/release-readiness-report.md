# Historical release readiness validation — 17 October 2026

**Superseded architecture:** this report records the original Cloud SQL baseline. Current Neon/Unclaimed deployment instructions and validation are in [neon-deployment-adaptation.md](neon-deployment-adaptation.md) and [production-deployment-runbook.md](production-deployment-runbook.md). Do not provision Cloud SQL from this historical report.

Ready for a **human-authorized first deployment after prerequisites**, not a deployed/accepted service. No cloud provisioning, deployment, paid API call, real-policy approval/publication or remote push ran. Existing `.env` files, separate corpus implementation and Phase 4 recommender/UI were preserved.

## Local validation actually executed

| Check | Result |
|---|---|
| `make contracts` | Generated contracts unchanged. |
| `make preflight` | Local sanitized checks passed. Existing development OpenAI/upload settings were read but not overwritten or called; the runner supplies separate explicit production safety flags. |
| `make check` | Ruff/format, 198 backend passed/1 skipped at that run, clean Alembic drift, ESLint, TypeScript and Vite production build passed. |
| Final full backend pytest | **200 passed, 1 live-fetch skipped**, after mocked release-order/workflow tests were added. |
| `make test-e2e` | **29 passed**; ordinary regression tests include mocked protected paths and real public empty states. |
| `make test-product-e2e` | **10 passed**; actual local browser, fictional Firebase Auth emulator tokens, FastAPI/PostgreSQL and private local files. No Google Sign-In/provider/hosted claim. |
| Production Docker build | **amd64 build passed**, pinned Python/uv base digests, frozen no-dev/non-editable package installation, allowlisted source context. |
| `scripts/release_container_check.py` | **Passed twice**, including the final image. Created fresh disposable PostgreSQL 17, applied the full chain to `f24a1000abcd`, `alembic check` clean, GIN index/runtime semantics JSON/Phase 4 routes present, non-root, no seeded policies/private data. Removed task-owned containers/network. |
| Deployment plan | **Passed** using fictional public identifiers; only commands were printed. Unit tests fail if a plan invokes cloud commands. |
| Deployment execute tests | Explicitly **mocked** cloud/Hosting calls only: matching-project guard, private env preservation, candidate smoke before build/promotion, no promotion on failed smoke, sanitized receipt and pinned secrets. |
| Smoke tooling tests | **Mocked** public/authenticated responses: Phase 4 401 guards, Firebase UID/non-admin identity, scenario API snapshots and cross-account denial. Hosted smoke not run. Actual local product acceptance separately exercised the real endpoints. |
| DEPwD preservation | Original drafts unchanged; **36 + 34 = 70** saved-page citations revalidated, zero real published policies. |
| Cleanup | Task-owned Auth emulator stopped; disposable Docker resources removed. Existing local API/web/database preserved. |

Vite still reports the existing main-bundle size warning above 500 kB. Dependency deprecation warnings remain; they did not fail the checks. Firebase CLI `15.12.0` used by the workflow was verified to exist in the official npm registry; the remote GitHub workflow itself has not been run/pushed.

## Ready components

Image fingerprint now includes JSON/other runtime resources, migration templates, lock/package/build/ignore inputs and pinned base images. Production packaging and fresh migration chain are locally proven. Manual WIF workflow has a CI dependency, protected-default-branch condition, `production` environment reference and explicit project/DEPLOY input. Runtime, migration and build identities are separate; migration/API secret names must differ. Candidate API smoke precedes traffic promotion/Hosting; rollback receipt omits full service/env metadata. Production paid AI, ingestion, fictional catalogue and uploads are explicitly off; no AI secret is injected.

## Human actions and unresolved gates

1. Select/approve the actual project, billing-enabled Firebase/Blaze linkage, region, budget and paid PostgreSQL tier. Confirm quota/availability and accept micro zonal/no-SLA limitations or choose a larger appropriate tier.
2. Provision/inspect SQL, database/users/privileges/backups/PITR, registry/source bucket, service accounts and least-privilege IAM. Populate **three stable pinned secrets** outside Git. Cloud SQL socket connectivity and actual IAM have not been verified remotely.
3. Configure Firebase Google provider, support/OAuth settings and the two standard authorized Hosting domains; fill the matching public Web config and production CORS/project identifiers.
4. Configure GitHub protected default branch, supported production-environment required reviewers/no self-review/no admin bypass, WIF provider/conditions and environment variables. YAML cannot install these protections; lack of supported approval rules blocks the protected Actions path.
5. Authorize pushing the reviewed commits separately; no remote workflow exists from this sprint until the operator publishes the code. Then run the manual workflow or an explicitly approved local execution from a clean checkout. Current developer frontend `.env` files deliberately prevent executing from that checkout; do not overwrite them.
6. Run hosted public/authenticated smoke, actual two-account Google Sign-In, five-context and scenario/Hindi/mobile/isolation acceptance, and rollback rehearsal. **All hosted acceptance remains NOT RUN.** No live Gemini success is claimed or needed for the first disabled-AI release.
7. Populated real-catalogue matching remains **blocked pending separate substantive human review/publication**; current real drafts remain unpublished. An empty catalogue is valid health/auth acceptance, not a full opportunity demonstration.

Sensitive production uploads remain intentionally disabled pending malware scanning/durable storage/security acceptance. Neural retrieval remains the existing unavailable adapter; neither is silently enabled by deployment. Large-load performance, backup restoration and any future custom-domain CORS are unverified. No other unresolved local build/migration/test failure remains.

## Operator command order

Follow [production-deployment-runbook.md](production-deployment-runbook.md) in order: approved identifiers/budget → one-time prerequisites/IAM/SQL/secrets/Firebase → GitHub protection/WIF → fill public config → plan-only review → manual CI-backed release authorization → public smoke → private two-account authenticated smoke and [hosted acceptance](hosted-acceptance.md). The runbook contains the exact public-identifier commands and rollback procedure. Recurring-cost drivers and an explicitly non-quoted US$20–40/month micro-setup planning allowance are in [hosting-costs-and-risks.md](hosting-costs-and-risks.md).

Local implementation commit: `7c66bfa` (release runner, WIF workflow, packaging, production guards, smoke, tests). A subsequent documentation commit records these runbooks and validation. No push.
