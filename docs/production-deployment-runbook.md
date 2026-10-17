# Unclaimed first release — Neon + Cloud Run + Firebase Hosting

Updated 17 October 2026. **The existing application is deployed; the intelligence integration below is not yet released.** Read-only checks confirmed billing enabled, a ready Cloud Run revision, Neon head `f24a1000abcd`, zero source/opportunity records and zero administrators. No Google Cloud/Hosting/production-role/Neon mutation was performed in this integration assignment. Do not rerun first-release provisioning or initialize Neon. Sections 1–7 retain first-release reference commands; follow section 8 for the new additive release/import.

## Selected infrastructure

| Setting | Value |
|---|---|
| Google/Firebase project | `venuesignal` |
| Cloud Run region/service | `asia-south1` / `opportunity-api` |
| Firebase site/target | `unclaimed-ai-cup` / `unclaimed` |
| Public frontend | `https://unclaimed-ai-cup.web.app` |
| Existing Firebase Web app | `AiBuilderCup` in `venuesignal`; copy its public API key/app ID from Console |
| Firebase Auth domain | `venuesignal.firebaseapp.com` (project auth domain, distinct from Hosting site) |
| Database | Existing Neon Free PostgreSQL 17; no Cloud SQL instance/proxy/socket/VPC connector |
| Release schema action | `verify`: SELECT existing Alembic revisions in a read-only transaction, no initialization/stamping/upgrade |
| Cloud Run limits | Request-based CPU, 1 vCPU, 1 GiB, min 0/max 1, concurrency 4, 60-second request timeout |

Billing-enabled status now returns true. No billing linkage/change is needed for this follow-up. No Cloud SQL API, IAM client role, database, instance or attachment is required by either path.

## 1. Billing and Google prerequisites — human only

Inspect existing resources first; reuse them when already configured. Do not run create commands blindly against existing resources. Every command explicitly names `venuesignal`; no reliance on a gcloud default project.

```sh
export OPPORTUNITY_PROJECT=venuesignal
export OPPORTUNITY_REGION=asia-south1
export OPPORTUNITY_REPOSITORY=opportunity
export OPPORTUNITY_SERVICE=opportunity-api
export OPPORTUNITY_SOURCE_BUCKET=venuesignal-release-source
export OPPORTUNITY_BILLING_ACCOUNT=YOUR_BILLING_ACCOUNT_ID

# Read the actual state first. Link only after explicit budget/billing authorization.
gcloud billing projects describe "$OPPORTUNITY_PROJECT"
gcloud billing projects link "$OPPORTUNITY_PROJECT" --billing-account "$OPPORTUNITY_BILLING_ACCOUNT"
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com identitytoolkit.googleapis.com iamcredentials.googleapis.com sts.googleapis.com firebasehosting.googleapis.com --project "$OPPORTUNITY_PROJECT"

# Create only missing prerequisites; these are not invoked by deploy.py.
gcloud artifacts repositories create "$OPPORTUNITY_REPOSITORY" --repository-format=docker --location "$OPPORTUNITY_REGION" --project "$OPPORTUNITY_PROJECT"
gcloud storage buckets create "gs://$OPPORTUNITY_SOURCE_BUCKET" --location "$OPPORTUNITY_REGION" --uniform-bucket-level-access --public-access-prevention --project "$OPPORTUNITY_PROJECT"
for OPPORTUNITY_IDENTITY in opportunity-runtime opportunity-migrations opportunity-build opportunity-deploy; do
  gcloud iam service-accounts create "$OPPORTUNITY_IDENTITY" --project "$OPPORTUNITY_PROJECT"
done
for OPPORTUNITY_SECRET in opportunity-database-url opportunity-migration-database-url opportunity-document-signing-key; do
  gcloud secrets create "$OPPORTUNITY_SECRET" --replication-policy=automatic --project "$OPPORTUNITY_PROJECT"
done
```

Set a Google Cloud billing budget and 50/80/100% alerts in Console, inspect billing daily, and apply reviewed source/image/log retention policies. Alerts are not a hard spend cap. Neon remains Free; do not upgrade its plan or resize/move/reinitialize its existing database as part of this Google setup.

## 2. Store existing Neon credentials securely

The runner never fetches or prints secret payloads. In Secret Manager Console, populate numeric versions for:

- `opportunity-database-url`: runtime app role, **pooled** Neon endpoint where available, SSL required.
- `opportunity-migration-database-url`: **direct, non-pooler** Neon endpoint, separate migration role/credentials where practical. The current release uses this only to verify existing head read-only.
- `opportunity-document-signing-key`: random stable signing key (at least 32 bytes of entropy), unchanged across instances/revisions unless deliberately rotated. Uploads remain disabled.

Use SQLAlchemy/psycopg URLs: `postgresql+psycopg://ENCODED_USER:ENCODED_PASSWORD@NEON_ENDPOINT/DATABASE?sslmode=require&channel_binding=require`. Keep Neon-provided TLS options; `verify-full` is accepted when its root-certificate configuration is available. A pooled hostname contains `-pooler.`; do not use it for Alembic/schema jobs. Do not paste actual URLs into public config, terminal arguments or GitHub variables. Use Console private input or hidden stdin, never local `.env` overwrite.

Runtime production settings validate the Neon host, driver and SSL mode and reject endpoint override parameters. The runtime can also use a direct SSL endpoint if pooling is unavailable. SQLAlchemy retains a 3-connection pool with no overflow and pre-ping; psycopg server-side prepared statements are disabled for conservative transaction-pooler compatibility. Migration/schema connections use NullPool and require direct Neon. The app's advisory locks are transaction scoped; it does not rely on session-level SET/LISTEN/temp-table state for normal API work. [Neon pooling](https://neon.com/docs/connect/connection-pooling), [TLS guidance](https://neon.com/docs/connect/connect-securely).

**Role gate:** verify existing runtime and migration roles are separate and the app role has only required DML/schema usage; the migration role owns/manages schema. Distinct Secret Manager names alone do not prove different users/privileges. If only an owner URL exists, resolve role separation explicitly with the Neon administrator before release. This assignment does not create users/grants or alter Neon. Do not rerun initialization, seed fixtures, stamp revisions, or apply migrations just to populate these secrets.

Optional hidden-input secret upload (future operator command; no value appears in arguments/output):

```sh
export OPPORTUNITY_SECRET=opportunity-database-url
# Repeat for the direct migration URL and signing key, using the intended secret name.
python3 - <<'PY'
import getpass, os, subprocess
value = getpass.getpass('Secret value (hidden; never logged): ')
if not value: raise SystemExit('Empty secret rejected')
result = subprocess.run(['gcloud','secrets','versions','add',os.environ['OPPORTUNITY_SECRET'],
    '--project','venuesignal','--data-file=-','--quiet'], input=value, text=True, capture_output=True)
if result.returncode: raise SystemExit('Secret upload failed; inspect restricted logs locally')
print('Version added. Record its numeric version in the public deployment config.')
PY
```

No Gemini/OpenAI secret is needed or injected. Synthetic catalogue, live paid ingestion, assistant generation and document uploads stay explicitly false. Never supply a service-account JSON key; Firebase Admin uses Cloud Run's runtime service-account ADC.

## 3. Google IAM — no Cloud SQL permissions

Run only with an authorized IAM administrator. Existing managed Cloud Build/Cloud Run service agents should retain their documented service-agent roles. Never grant Owner/Editor to application accounts.

```sh
gcloud projects add-iam-policy-binding venuesignal --member=serviceAccount:opportunity-runtime@venuesignal.iam.gserviceaccount.com --role=roles/firebaseauth.viewer --condition=None
for OPPORTUNITY_SECRET in opportunity-database-url opportunity-document-signing-key; do
  gcloud secrets add-iam-policy-binding "$OPPORTUNITY_SECRET" --project venuesignal --member=serviceAccount:opportunity-runtime@venuesignal.iam.gserviceaccount.com --role=roles/secretmanager.secretAccessor --condition=None
done
gcloud secrets add-iam-policy-binding opportunity-migration-database-url --project venuesignal --member=serviceAccount:opportunity-migrations@venuesignal.iam.gserviceaccount.com --role=roles/secretmanager.secretAccessor --condition=None
gcloud artifacts repositories add-iam-policy-binding opportunity --location asia-south1 --project venuesignal --member=serviceAccount:opportunity-build@venuesignal.iam.gserviceaccount.com --role=roles/artifactregistry.writer
gcloud projects add-iam-policy-binding venuesignal --member=serviceAccount:opportunity-build@venuesignal.iam.gserviceaccount.com --role=roles/logging.logWriter --condition=None
gcloud storage buckets add-iam-policy-binding gs://venuesignal-release-source --project venuesignal --member=serviceAccount:opportunity-build@venuesignal.iam.gserviceaccount.com --role=roles/storage.objectViewer

# Deployment identity: initial service/job creation and Hosting release, not billing or secret payloads.
for OPPORTUNITY_ROLE in roles/cloudbuild.builds.editor roles/run.admin roles/firebasehosting.admin roles/serviceusage.serviceUsageConsumer; do
  gcloud projects add-iam-policy-binding venuesignal --member=serviceAccount:opportunity-deploy@venuesignal.iam.gserviceaccount.com --role="$OPPORTUNITY_ROLE" --condition=None
done
for OPPORTUNITY_IDENTITY in opportunity-runtime opportunity-migrations opportunity-build; do
  gcloud iam service-accounts add-iam-policy-binding "$OPPORTUNITY_IDENTITY@venuesignal.iam.gserviceaccount.com" --project venuesignal --member=serviceAccount:opportunity-deploy@venuesignal.iam.gserviceaccount.com --role=roles/iam.serviceAccountUser
done
gcloud artifacts repositories add-iam-policy-binding opportunity --location asia-south1 --project venuesignal --member=serviceAccount:opportunity-deploy@venuesignal.iam.gserviceaccount.com --role=roles/artifactregistry.reader
for OPPORTUNITY_ROLE in roles/storage.objectCreator roles/storage.objectViewer roles/storage.legacyBucketReader; do
  gcloud storage buckets add-iam-policy-binding gs://venuesignal-release-source --project venuesignal --member=serviceAccount:opportunity-deploy@venuesignal.iam.gserviceaccount.com --role="$OPPORTUNITY_ROLE"
done
```

After initial creation, narrow deployment IAM to the actual Run service/job/Hosting resources where supported. Runtime/migration identities need no Google database IAM role: Neon authenticates its own SQL roles over TLS. No VPC/NAT/proxy is provisioned. If Neon network restrictions require fixed egress, stop for a separately approved design/cost decision; this release does not add static egress infrastructure. Actual Neon region, Cloud Run-to-Neon latency, quotas and external egress costs remain operator checks.

## 4. Firebase app and exclusive Hosting target

Use the **existing AiBuilderCup Web app**, not a guessed/new app. Fill its public API key and app ID in `infra/deploy.example.json`'s copied public config. Project remains `venuesignal`; Auth domain remains `venuesignal.firebaseapp.com`. Enable Google Sign-In/support email and authorize `unclaimed-ai-cup.web.app` and `unclaimed-ai-cup.firebaseapp.com` in Firebase Authentication settings. Verify OAuth consent/test-user/organization restrictions permit the testers.

The existing `infra/.firebaserc` maps `venuesignal → hosting → unclaimed → [unclaimed-ai-cup]`; `infra/firebase.json` has `target: unclaimed`. The runner checks both files before any cloud command and uses **only `--only hosting:unclaimed`**. It never deploys the project-default site or uses `venuesignal.web.app` as the frontend. Production CORS allows the two Unclaimed site origins. The project's Auth domain is not the frontend CORS origin. [Firebase multisite targets](https://firebase.google.com/docs/hosting/multisites).

If the target mapping is already correct, do not reapply/create it. For a future clean checkout missing only that mapping, the operator can restore it from Git; the precise CLI equivalent is `firebase target:apply hosting unclaimed unclaimed-ai-cup --project venuesignal` from `infra/`. No Firebase site/app creation is required.

## 5. Protected manual GitHub WIF release

Keep `.github/workflows/deploy.yml` manual-only. It depends on CI, requires the protected repository default branch and `DEPLOY` input, targets the `production` environment and then authenticates with WIF. The human must configure required reviewers, prevent self-review/admin bypass and protected default-branch restrictions in GitHub; YAML cannot install these controls. A GitHub plan without supported approval rules blocks this protected workflow path.

One-time WIF commands (only if not configured; public placeholders):

```sh
export OPPORTUNITY_PROJECT_NUMBER=YOUR_VENUESIGNAL_PROJECT_NUMBER
export OPPORTUNITY_REPO=OWNER/REPOSITORY
export OPPORTUNITY_REPO_ID=YOUR_NUMERIC_REPOSITORY_ID
export OPPORTUNITY_OWNER_ID=YOUR_NUMERIC_OWNER_ID
export OPPORTUNITY_RELEASE_BRANCH=YOUR_PROTECTED_DEFAULT_BRANCH

gcloud iam workload-identity-pools create github-release --location global --project venuesignal --display-name='Manual Unclaimed release'
gcloud iam workload-identity-pools providers create-oidc github --location global --workload-identity-pool github-release --project venuesignal --issuer-uri=https://token.actions.githubusercontent.com --attribute-mapping='google.subject=assertion.sub,attribute.repository_id=assertion.repository_id' --attribute-condition="assertion.repository_id == '$OPPORTUNITY_REPO_ID' && assertion.repository_owner_id == '$OPPORTUNITY_OWNER_ID' && assertion.ref == 'refs/heads/$OPPORTUNITY_RELEASE_BRANCH' && assertion.sub == 'repo:$OPPORTUNITY_REPO:environment:production' && assertion.workflow_ref == '$OPPORTUNITY_REPO/.github/workflows/deploy.yml@refs/heads/$OPPORTUNITY_RELEASE_BRANCH'"
gcloud iam service-accounts add-iam-policy-binding opportunity-deploy@venuesignal.iam.gserviceaccount.com --project venuesignal --role roles/iam.workloadIdentityUser --member="principalSet://iam.googleapis.com/projects/$OPPORTUNITY_PROJECT_NUMBER/locations/global/workloadIdentityPools/github-release/attribute.repository_id/$OPPORTUNITY_REPO_ID"
```

Set production environment variables `GCP_PROJECT_ID=venuesignal`, `GCP_DEPLOY_SERVICE_ACCOUNT=opportunity-deploy@venuesignal.iam.gserviceaccount.com`, `GCP_WORKLOAD_IDENTITY_PROVIDER=projects/NUMBER/locations/global/workloadIdentityPools/github-release/providers/github`, and `DEPLOY_CONFIG_JSON` containing **only** the filled public template. Pin numeric secret versions. No database URL/password, token or JSON credential belongs in GitHub variables. Push needs separate authorization and was not performed in this adaptation.

## 6. Plan, authorize release, verify actual hosted behavior

From the repository root in a clean reviewed checkout:

```sh
cp -n infra/deploy.example.json /tmp/unclaimed-production.json
# Fill only the existing app's public Firebase key/app ID and actual numeric secret versions.
# Keep database_provider=neon and migration_mode=verify.
python3 infra/deploy.py --config /tmp/unclaimed-production.json
```

Plan-only reads local public files and prints commands, with no cloud/network/Neon operation. Execution refuses placeholder Web config and existing frontend `.env*` files, preserving local environments. Use a clean checkout; all inherited `VITE_*` values are sanitized. Docker build resources/digests/locks remain pinned, with an allowlisted context excluding credentials, corpus blobs, private files and development fixtures.

Only after billing/IAM/secrets/review protections and deployment approval are ready, either dispatch the remote workflow (after authorized publication of code):

```sh
gh workflow run deploy.yml --ref "$OPPORTUNITY_RELEASE_BRANCH" --field approved_project=venuesignal --field authorization=DEPLOY
```

or use the approved local CLI identity (gcloud login + ADC outside Git, permissions equivalent to the deployment identity), from a clean checkout:

```sh
python3 infra/deploy.py --config /tmp/unclaimed-production.json --execute --approved-project venuesignal --receipt /tmp/unclaimed-release-receipt.json
```

**Order:** existing source-bucket check → prior traffic receipt → image build → single schema-gate job using direct Neon secret (**read-only head verification**) → no-traffic tagged API → candidate public/auth/CORS smoke → frozen web build with actual API URL/existing Firebase app → exact revision traffic promotion → stable API smoke → exclusive `hosting:unclaimed` release → `https://unclaimed-ai-cup.web.app/profile` SPA verification. The receipt records Unclaimed site/target/URL, Neon provider/schema mode and safe rollback metadata; no full service/env payload. First service creation has no old revision to protect; do not advertise it before acceptance. API/Hosting promotion is not atomic.

For a later separately approved schema change only, set `migration_mode=upgrade` and invoke the runner with **both** project approval and `--approve-migrations`; the schema module also requires its explicit upgrade flag. Do not do this for the current already-applied `f24a1000abcd` release. Missing/mismatched metadata stops verification; it never initializes, stamps or seeds Neon.

Post-release commands (not run here):

```sh
python3 infra/smoke.py --api-url https://ACTUAL_SERVICE.run.app --hosting-origin https://unclaimed-ai-cup.web.app --hosting-origin https://unclaimed-ai-cup.firebaseapp.com
# Private token-file checks only after actual two-account hosted Google login:
python3 infra/smoke.py --api-url https://ACTUAL_SERVICE.run.app --hosting-origin https://unclaimed-ai-cup.web.app --hosting-origin https://unclaimed-ai-cup.firebaseapp.com --token-file /PRIVATE_TEMP/account-a.token --second-token-file /PRIVATE_TEMP/account-b.token --expected-uid ACCOUNT_A_UID
```

Complete [hosted-acceptance.md](hosted-acceptance.md). Actual Google Sign-In/Cloud Run ADC/Neon TLS connectivity/hosted search and scenarios are unverified in this assignment. Current real drafts remain unpublished; empty catalogue health/auth acceptance is legitimate but not populated recommendation acceptance. No live AI success is claimed.

## 7. Rollback and remaining gates

Before release, record the current **Unclaimed site's** live Hosting release ID in Console. Keep current/previous images and the runner's public receipt. Failed schema verification or candidate smoke stops before traffic promotion/Hosting. If failure occurs after promotion, a human can restore prior positive traffic from the receipt:

```sh
gcloud run services update-traffic opportunity-api --project venuesignal --region asia-south1 --to-revisions=PREVIOUS_REVIEWED_REVISION=100
```

Rollback Firebase Console → Hosting → **unclaimed-ai-cup** → release history, never the default venuesignal site. First release has no previous revision. Do not automatically downgrade/restore/drop/stamp Neon; current verification makes no schema changes. Future schema upgrades need backward-compatibility and recovery-window/export review under the actual Neon plan. Restrict logs/artifacts; never include DSNs, bearer tokens or profile bodies. Google egress/build/registry/log/secret charges and Neon Free quota/cold-start/availability risks are documented in [hosting-costs-and-risks.md](hosting-costs-and-risks.md).

Current gates: GitHub authentication, an explicit first-administrator decision, protected environment/WIF verification, approval for the additive schema/worker resources, substantive publication review and actual authenticated hosted acceptance. No production data/resource/policy or local environment file was changed by this task. Local development/disposable schemas were tested at the new head.

## 8. Intelligence release and actual corpus import — pending authorization

The agent should execute routine commands after the named approval boundaries; the human is not expected to edit code or paste SQL. **Current blocker:** the private Free-plan repository has zero deployment environments. Native reviewer approvals are unavailable there. Workflows deliberately fail closed before cloud authentication until real reviewer and exact default-branch protection exists. The human must select a supported native setup or explicitly approve one reviewed operator/Cloud Run Job release boundary; never make the repo public, purchase an upgrade or weaken protections automatically. [GitHub environment rules](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments). Git's existing credential helper now provides repository access. `infra/corpus.example.json` contains only public resource identifiers. Set the repository variable `CORPUS_CONFIG_JSON` to that reviewed JSON once GitHub access is available. Retain existing `DEPLOY_CONFIG_JSON` and WIF variables, required production reviewers, prevent self-review, default-branch restriction and no protection bypass. Never put credentials or Firebase bearer tokens in variables/artifacts.

**Order:** CI → approved additive application release → approved worker bucket/identity/secret setup → archive staging → protected full dry run → explicit first-admin bootstrap → protected import → human policy review/publication → local-model index job → authenticated hosted acceptance. No paid AI provider is enabled by any command here.

### Local checks and public plans (safe now)

```sh
python3 infra/deploy.py --config infra/deploy.example.json
python3 infra/deploy_frontend.py --config infra/deploy.example.json
python3 infra/corpus_job.py --config infra/corpus.example.json --all-batches
apps/api/.venv/bin/python infra/worker_secret.py --deploy-config infra/deploy.example.json --corpus-config infra/corpus.example.json
apps/api/.venv/bin/python -m opportunity_platform.corpus.production stage --project venuesignal --bucket venuesignal-public-corpus --root .corpus
```

The archive stage plan measures 125 snapshot records, 120 binary hashes and 193,031,267 bytes. One irrelevant document is excluded from database import: planned inserts are **124 source rows / 124 snapshot rows / 119 distinct document hashes**, plus three prepared drafts. Five repeated hashes retain different original URLs without repeating binary storage. These are planned counts, not production observations. The metadata checkpoint was measured at approximately 1.6 MB and contains no PDF binaries/private environment files.

### Approved one-time worker setup (not executed)

Reuse existing Run, Artifact Registry, Firebase, Neon and migration resources. The additional bucket is private despite containing public-source documents; browsers use official URLs or the public text API. The worker gets no AI-provider secrets and no migration credential.

```sh
gcloud iam service-accounts create opportunity-corpus --project venuesignal --display-name="Unclaimed public corpus worker"
gcloud storage buckets create gs://venuesignal-public-corpus --project venuesignal --location=asia-south1 --default-storage-class=STANDARD --uniform-bucket-level-access --public-access-prevention

# Explicit creation authorization: derive a direct TLS URL from the existing app secret in memory.
# This creates one separate Secret Manager resource/version, not a Neon user/password/database.
apps/api/.venv/bin/python infra/worker_secret.py --deploy-config infra/deploy.example.json --corpus-config infra/corpus.example.json --execute --approved-project venuesignal

gcloud secrets add-iam-policy-binding opportunity-corpus-database-url --project venuesignal --member=serviceAccount:opportunity-corpus@venuesignal.iam.gserviceaccount.com --role=roles/secretmanager.secretAccessor
gcloud storage buckets add-iam-policy-binding gs://venuesignal-public-corpus --member=serviceAccount:opportunity-corpus@venuesignal.iam.gserviceaccount.com --role=roles/storage.objectViewer
gcloud storage buckets add-iam-policy-binding gs://venuesignal-public-corpus --member=serviceAccount:opportunity-corpus@venuesignal.iam.gserviceaccount.com --role=roles/storage.objectCreator
gcloud storage buckets add-iam-policy-binding gs://venuesignal-public-corpus --member=serviceAccount:opportunity-corpus@venuesignal.iam.gserviceaccount.com --role=roles/storage.objectUser --condition="expression=resource.name.startsWith('projects/_/buckets/venuesignal-public-corpus/objects/public-corpus/state/'),title=corpus-state-only"

# RELEASE_DEPLOYER_SA is the existing public service-account identifier in GCP_DEPLOY_SERVICE_ACCOUNT.
gcloud iam service-accounts add-iam-policy-binding opportunity-corpus@venuesignal.iam.gserviceaccount.com --project venuesignal --member="serviceAccount:$RELEASE_DEPLOYER_SA" --role=roles/iam.serviceAccountUser
gcloud artifacts repositories add-iam-policy-binding opportunity --project venuesignal --location=asia-south1 --member="serviceAccount:$RELEASE_DEPLOYER_SA" --role=roles/artifactregistry.reader
```

If any named resource already exists, inspect/reuse it; do not recreate/overwrite it. The secret helper refuses a pooled worker URL or conflicting existing secret. Worker credentials need ordinary source/draft/vector/audit writes, not DDL; review the actual Neon role grants. A separately provisioned least-privilege worker role is preferable if available; no role change is inferred or performed by the helper. Session advisory leases require the direct endpoint; the API may retain its pooled endpoint. [Neon pooling constraints](https://neon.com/docs/connect/connection-pooling).

### Protected release, stage, dry run and import

Authenticate GitHub with the existing authorized account (`gh auth login`); do not paste a token into chat. The remote default branch was verified as `master`; dispatch the reviewed default-branch commit. Every workflow below uses the protected `production` environment and must receive its real required approval. The schema flag authorizes only the reviewed additive `f25b1000abcd` migration; no initialization, seed or destructive restore is performed.

```sh
gh workflow run deploy.yml --ref master -f approved_project=venuesignal -f authorization=DEPLOY -f approve_schema_upgrade=true

# After approved storage setup: one-time transfer from the captured local archive.
apps/api/.venv/bin/python -m opportunity_platform.corpus.production stage --project venuesignal --bucket venuesignal-public-corpus --root .corpus --execute --approved-project venuesignal

gh workflow run corpus-import.yml --ref master -f operation=dry-run -f approved_project=venuesignal -f authorization=RUN_CORPUS -f all_batches=true

# Only after the human explicitly selects/authorizes this existing signed-in account:
gh workflow run corpus-import.yml --ref master -f operation=bootstrap-admin -f approved_project=venuesignal -f authorization=BOOTSTRAP_ADMIN -f actor_uid="$REVIEWED_ADMIN_UID"

gh workflow run corpus-import.yml --ref master -f operation=import -f approved_project=venuesignal -f authorization=RUN_CORPUS -f actor_uid="$REVIEWED_ADMIN_UID" -f all_batches=true

# After substantive human review/publication, build public vectors with local CPU weights:
gh workflow run corpus-import.yml --ref master -f operation=index -f approved_project=venuesignal -f authorization=RUN_CORPUS
```

The full initial run is seven sequential jobs of at most 20 records, with one task, zero task retries, 1 CPU/1 GiB and a 900-second timeout per job. The same content-addressed API image is reused. A malformed PDF or rejected record is isolated; retries are idempotent. Inspect each execution's sanitized result and query actual Neon counts afterward. GCS staging and protected job execution have not run in this assignment. A first administrator cannot be selected by the agent; bootstrap requires an existing saved profile, an explicit UID decision and a protected security approval.

Manual collection uses `operation=collect` with the reviewed administrator UID. It fetches at most 10 documents/40 requests/50 MiB, restores and checkpoints durable state, uses validators for unchanged documents and queues changed captures without paid interpretation/publication. Scheduling remains optional and **not installed**. If enabled after approval, deploy a separate `opportunity-corpus-refresh` job using the same image/config and collect arguments, then grant a dedicated Scheduler identity `roles/run.invoker` only on that job. A separate job prevents later import/index/admin operations from being accidentally scheduled.

Example future schedule after that manual job passes:

```sh
gcloud iam service-accounts create opportunity-corpus-scheduler --project venuesignal --display-name="Unclaimed bounded source schedule"
gcloud run jobs add-iam-policy-binding opportunity-corpus-refresh --project venuesignal --region asia-south1 --member=serviceAccount:opportunity-corpus-scheduler@venuesignal.iam.gserviceaccount.com --role=roles/run.invoker
gcloud scheduler jobs create http opportunity-corpus-weekly --project venuesignal --location asia-south1 --schedule="0 7 * * 1" --time-zone="Asia/Kolkata" --uri="https://run.googleapis.com/v2/projects/venuesignal/locations/asia-south1/jobs/opportunity-corpus-refresh:run" --http-method=POST --oauth-service-account-email=opportunity-corpus-scheduler@venuesignal.iam.gserviceaccount.com --headers="Content-Type=application/json" --message-body="{}" --max-retry-attempts=0
```

Enable Scheduler API only as part of that approval if not already enabled. The operator identity needs permission to attach the Scheduler service account. Changing a schedule/source/budget requires review; budget alerts alone are not spending caps. Jobs are billed separately from request-based serving. [Cloud Run job execution](https://docs.cloud.google.com/run/docs/execute/jobs), [job logging fields](https://docs.cloud.google.com/run/docs/logging).

For a frontend-only release, use `deploy-frontend.yml` with `authorization=DEPLOY_FRONTEND`, or the plan-first `infra/deploy_frontend.py`. It never builds Docker, changes Cloud Run or touches Neon. Backend retries reuse a verified existing Artifact Registry digest. A failed classified cloud stage reports its label/exit/category without dumping credentials. Retain the prior API/Hosting receipt; additive tables permit rolling back application traffic without a database downgrade.

Final acceptance requires actual production counts, a genuine draft in the review queue, a human-published current policy, stored vector retrieval and a dedicated signed-in profile opening `/discover` with no text/mode/search action. Until those pass, report production completion as blocked, not complete.

The release runner also reuses its one-task job, after schema verification/upgrade, for a read-only application-credential privilege check. Missing grants on new vector/reservation/source tables stop before API promotion. No role grant is silently added, and actual runtime DDL privilege is reported rather than assumed absent. A one-time operator exception, if explicitly chosen by the human for the reviewed CI-passing SHA, uses the same runners from a clean checkout and records receipts/Cloud Audit; it is not described as native GitHub environment approval.
