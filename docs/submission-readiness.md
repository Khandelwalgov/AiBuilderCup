# Submission readiness — 18 October 2026 target

The local product has a working subject/planner/UI implementation and reproducible checks. It is **not submission-ready as a deployed, live-Gemini-validated product**. Two real opportunity drafts require human review; public coverage is zero. Do not claim approved benefits, measured impact, comprehensive source coverage or successful Gemini calls.

Before recording: review/correct/approve real candidates; verify genuine Firebase sign-in and all subject permissions with fictional accounts; verify shared actions against actually reviewed rules; restore a valid Gemini key and authorize a bounded live acceptance call; authorize deployment configuration and costs.

Local release gates: `make preflight`, `make contracts`, `make check`, `make test-e2e`, Docker build/smoke, exact citation revalidation and zero draft leakage. Configuration preflight does not prove external permissions. Public smoke: `cd apps/api && uv run python ../../scripts/product_smoke.py --api-url http://127.0.0.1:8000`. The optional `--create-fictional-workspaces` flag requires a real Firebase token in `FIREBASE_ID_TOKEN` and refuses to overwrite any existing profile; use a dedicated fictional test account. It makes no AI call and does not publish.

Deployment approval checklist:

- Confirm project (`venuesignal` is the configured development identifier), production environment and region; `asia-south1` is the prepared example, not an approved purchase.
- Approve budget, Cloud SQL size/backup/storage/deletion protection and ongoing baseline charges. Budget alerts are not a spending cap.
- Provide pre-provisioned Cloud SQL connection/database login, Artifact Registry repository, runtime/migration service accounts and least-privilege IAM.
- Create numeric pinned Secret Manager versions through hidden-input procedures in `infra/README.md`; never paste keys into source or browser configuration.
- Confirm Firebase Google provider, authorized production domains, matching web/backend project, HTTPS API origin/CORS, admin operator bootstrap and real-only catalogue.
- Review `infra/deploy.local.json` locally; run `python infra/deploy.py --config infra/deploy.local.json` to inspect the plan. **No `--execute` without separate approval.**

A plan-only illustrative check was executed using `.live-validation/nightfall-deploy-plan-config.json`; public placeholders are not validated cloud resources. Plan output is `.live-validation/nightfall-deploy-plan.txt`. No cloud command executed. The clean local Docker build succeeds with locked dependencies and TLS intact.

Use `docs/demo-script.md` for three minutes and `docs/architecture-overview.md` for the architecture. See `docs/overnight-final-report.md` for exact executed validation and remaining gaps.

Finale checkpoint: Intelligence Atlas UI and canonical shared documentary actions are implemented; unchanged assessments now reuse records, concurrent requests serialize, current-version action links and meaningful differences are tested. See `docs/finale-final-report.md`. Neither real candidate was modified or published. Browser tests own separate5174/8001ports; regular5173/8000services remain intact. The clean local release image is `opportunity-api:finale`; cloud authorization and genuine interactive acceptance remain outstanding.
