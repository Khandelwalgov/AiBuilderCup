# Manual release infrastructure

The current procedure is [production-deployment-runbook.md](../docs/production-deployment-runbook.md). Cost assumptions and trial/SLA limits are in [hosting-costs-and-risks.md](../docs/hosting-costs-and-risks.md); real Google Sign-In and hosted acceptance are in [hosted-acceptance.md](../docs/hosted-acceptance.md).

`python3 infra/deploy.py --config PUBLIC_CONFIG.json` is **plan-only**. No gcloud, Firebase, build, migration or network command runs in that mode. Execution needs both `--execute` and `--approved-project` matching the reviewed config, and explicit human release authorization. A config file or existing login does not itself provide that authorization.

`deploy.example.json` contains only public Firebase configuration, project/region/resource identifiers and pinned numeric Secret Manager versions. API and migration database secrets must be separate. Gemini is the primary provider, but first-release paid ingestion and assistant generation are explicitly off and no AI key is injected. Production uploads and fictional catalogue are off. The runtime document signing key is stable and versioned.

The runner hashes all runtime source resources (including JSON), migration files/templates, backend package metadata/lock, Docker/build configuration and ignore manifests. The build context is allowlisted. It builds with an explicit low-privilege Cloud Build identity, migrates once with a separate DDL identity, requests a no-traffic tagged API revision, checks its public/authorization/CORS boundaries, builds the web with matching public settings, promotes the API and publishes Hosting. It records rollback metadata when `--receipt` is supplied. No synthetic seed runs.

`.github/workflows/deploy.yml` is manual-only, restricted to the repository default branch, depends on CI, targets the `production` environment and uses Workload Identity Federation. **The human must configure environment required reviewers, no self-review/bypass and protected-branch restrictions in GitHub**; YAML alone does not configure those protections. Push/PR CI has no deployment or cloud identity.

Local validation:

```sh
make contracts preflight check
PLAYWRIGHT_BROWSERS_PATH=/tmp/opportunity-browsers E2E_WEB_PORT=15211 E2E_API_PORT=18211 make test-e2e
docker build --platform linux/amd64 -t opportunity-release-local:readiness apps/api
python3 scripts/release_container_check.py
```

The container checker creates only random local Docker containers/network, applies all migrations to fresh PostgreSQL 17, verifies the runtime JSON/routes/flags/non-root user and removes its resources. Never substitute a production database URL. Real local browser tests require the explicitly fictional Auth emulator described in `docs/real-user-acceptance.md`.

No cloud provisioning, release, paid model call, real-policy review/publication or remote push occurred during this release-readiness sprint.
