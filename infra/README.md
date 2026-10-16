# Unclaimed manual release infrastructure

Current architecture: **venuesignal / asia-south1 Cloud Run + existing Neon Free PostgreSQL 17 + Firebase Hosting unclaimed-ai-cup**. [Exact operator runbook](../docs/production-deployment-runbook.md), [costs and risks](../docs/hosting-costs-and-risks.md), [hosted acceptance](../docs/hosted-acceptance.md).

```sh
python3 infra/deploy.py --config infra/deploy.example.json
```

This is **plan-only**: no build/cloud/Neon command runs. The public template names the selected project/site, separate pinned Secret Manager references and the existing app's public Web config placeholders. Actual secret values never belong there. Execution needs `--execute --approved-project venuesignal`, a clean checkout without frontend `.env*` files, filled public app values, billing/IAM/secrets and human authorization.

Default `migration_mode=verify` deploys a one-task job that reads existing Alembic metadata in a read-only transaction through a direct SSL Neon connection; it does not repeat initialization, stamp or upgrade. `f24a1000abcd` is already applied per operator report. A future schema upgrade requires both config `upgrade` and explicit `--approve-migrations`. Runtime can use the pooled SSL Neon endpoint; migration jobs require direct. No Cloud SQL attachment flags, instance/proxy/VPC provisioning or Cloud SQL IAM permissions are present in this path.

The runner validates existing `infra/.firebaserc` and `infra/firebase.json` mapping before any cloud command and deploys **only `hosting:unclaimed`**. CORS, smoke, receipt and final SPA verification use `https://unclaimed-ai-cup.web.app`, not `venuesignal.web.app`. Firebase Admin uses runtime service-account ADC; the frontend's project Auth domain remains `venuesignal.firebaseapp.com`.

Cloud Run uses request-based CPU, 1 vCPU/1 GiB, min 0/max 1. Synthetic catalogue, paid ingestion, assistant generation and sensitive uploads stay off. Pinned Docker resources/locks, allowlisted context, candidate smoke before promotion, safe rollback receipts and manual production-environment/WIF approval remain intact. The human must configure GitHub reviewers/branch protections/WIF; no cloud/GitHub/billing resource was changed here.

Validation must **explicitly override local database settings**, because developer `.env` may now point at Neon:

```sh
DATABASE_URL='postgresql+psycopg://opportunity:local-development-only@127.0.0.1:5432/opportunity' TEST_DATABASE_URL='postgresql+psycopg://opportunity:local-development-only@127.0.0.1:5432/opportunity' DATABASE_PROVIDER=postgresql ENVIRONMENT=development make contracts check
docker build --platform linux/amd64 -t opportunity-release-local:readiness apps/api
python3 scripts/release_container_check.py
```

The container checker creates fresh **local disposable** PostgreSQL 17, applies migrations there, verifies the read-only gate and runtime package, then removes task resources. It never reads a Neon URL or uses the application database. Do not run `make migrate`, `make seed` or generic `alembic upgrade head` against Neon for this adaptation. Existing `.env` files must remain untouched.
