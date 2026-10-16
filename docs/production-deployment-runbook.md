# First production release runbook — 17 October 2026

**Status: locally validated release tooling; no cloud resources created/changed and no hosted acceptance claimed.** Every provisioning/release command below is a future human-operator procedure requiring project, cost and deployment approval. The runner defaults to plan-only. Do not paste secret values into this file, JSON configs, shell command arguments or GitHub variables.

## 1. Choose and approve the public identifiers

Use one Firebase-enabled Google Cloud project. Pick Mumbai (`asia-south1`) for API/database/registry/build storage. Approve the database tradeoff and budget in [hosting-costs-and-risks.md](hosting-costs-and-risks.md). Billing/Blaze linkage, quotas, organization policy and database capacity require human confirmation. A trial is not the recommended release database.

```sh
export OPPORTUNITY_PROJECT=YOUR_PROJECT_ID
export OPPORTUNITY_REGION=asia-south1
export OPPORTUNITY_SQL_INSTANCE=opportunity-db
export OPPORTUNITY_REPOSITORY=opportunity
export OPPORTUNITY_SERVICE=opportunity-api
export OPPORTUNITY_SOURCE_BUCKET="$OPPORTUNITY_PROJECT-release-source"
export OPPORTUNITY_REPO=OWNER/REPOSITORY
export OPPORTUNITY_RELEASE_BRANCH=master
```

Use the repository's actual protected default branch (currently the local branch is `master`), not an assumed `main`. These variables contain only public identifiers. Confirm the selected project in Console; never rely on the gcloud default project.

## 2. One-time infrastructure prerequisites — human only

Enable billing and create/register the Firebase project/Web app in Console. Configure **Authentication → Google**, support email and Authorized domains: `PROJECT.web.app`, `PROJECT.firebaseapp.com`; the first-release CORS allows only these two standard Hosting origins. Custom domains require a separately reviewed CORS/config change, not just an Authorized domains entry. Use the Web app's matching public project ID, API key, auth domain and app ID. Google OAuth consent/supported users and organization restrictions must permit the intended test accounts. Do not create service-account JSON keys.

After approval, provision the following once. Existing resources should be inspected/reused, not recreated blindly. These commands were **not run** during this assignment.

```sh
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com sqladmin.googleapis.com secretmanager.googleapis.com identitytoolkit.googleapis.com iamcredentials.googleapis.com sts.googleapis.com firebasehosting.googleapis.com --project "$OPPORTUNITY_PROJECT"
gcloud artifacts repositories create "$OPPORTUNITY_REPOSITORY" --repository-format=docker --location "$OPPORTUNITY_REGION" --project "$OPPORTUNITY_PROJECT"
gcloud storage buckets create "gs://$OPPORTUNITY_SOURCE_BUCKET" --location "$OPPORTUNITY_REGION" --uniform-bucket-level-access --public-access-prevention --project "$OPPORTUNITY_PROJECT"
gcloud sql instances create "$OPPORTUNITY_SQL_INSTANCE" --project "$OPPORTUNITY_PROJECT" --region "$OPPORTUNITY_REGION" --database-version=POSTGRES_17 --edition=ENTERPRISE --tier=db-f1-micro --availability-type=ZONAL --storage-type=SSD --storage-size=10 --storage-auto-increase-limit=20 --backup-start-time=03:00 --enable-point-in-time-recovery --deletion-protection
gcloud sql databases create opportunity --instance "$OPPORTUNITY_SQL_INSTANCE" --project "$OPPORTUNITY_PROJECT"
for OPPORTUNITY_IDENTITY in opportunity-runtime opportunity-migrations opportunity-build opportunity-deploy; do
  gcloud iam service-accounts create "$OPPORTUNITY_IDENTITY" --project "$OPPORTUNITY_PROJECT"
done
for OPPORTUNITY_SECRET in opportunity-database-url opportunity-migration-database-url opportunity-document-signing-key; do
  gcloud secrets create "$OPPORTUNITY_SECRET" --replication-policy=automatic --project "$OPPORTUNITY_PROJECT"
done
```

Use the standard Cloud SQL Auth Proxy/Cloud Run connector over the instance's public IP **without authorized external networks**; never add `0.0.0.0/0`. IAM connector access and SQL login are separate. Private-IP-only networking would require a separately reviewed VPC configuration/cost; this runner does not add one. [Cloud Run–Cloud SQL connection guidance](https://docs.cloud.google.com/sql/docs/postgres/connect-run).

## 3. SQL roles and secret values — Console/private input only

Create two dedicated SQL users using Cloud SQL Console's password controls: `opportunity_migrator` and `opportunity_app`. Keep generated passwords in an approved password manager. Make the migrator owner of the `opportunity` database/schema and run these SQL privilege statements with an authorized SQL administrator. Do not put passwords in SQL scripts or terminal history.

```sql
-- Connect to the opportunity database; names are public, passwords are not present here.
ALTER DATABASE opportunity OWNER TO opportunity_migrator;
ALTER SCHEMA public OWNER TO opportunity_migrator;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT CONNECT ON DATABASE opportunity TO opportunity_app;
GRANT USAGE ON SCHEMA public TO opportunity_app;
ALTER DEFAULT PRIVILEGES FOR ROLE opportunity_migrator IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO opportunity_app;
ALTER DEFAULT PRIVILEGES FOR ROLE opportunity_migrator IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO opportunity_app;
-- If tables already exist, grant their DML privileges too; do not grant DDL/ownership to the API.
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO opportunity_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO opportunity_app;
```

In Secret Manager Console, add numeric versions of these values using private input. The DSN must URL-encode the username/password and use the Cloud SQL socket; never include a real DSN in the public JSON:

- `opportunity-database-url`: `postgresql+psycopg://ENCODED_APP_USER:ENCODED_PASSWORD@/opportunity?host=/cloudsql/PROJECT:REGION:INSTANCE`
- `opportunity-migration-database-url`: same socket/database, **migrator** credentials.
- `opportunity-document-signing-key`: cryptographically random, at least 32 bytes of entropy, kept stable across instances/revisions; record its numeric version. Rotate deliberately because old short-lived download tokens will stop validating.

No Gemini/OpenAI secret is needed for this first release: generation/paid ingestion are off. Production uploads remain off even though a stable signing key is supplied. Future private document storage must use durable scoped GCS, malware scanning and security acceptance; do not enable local uploads on Cloud Run.

## 4. Least-privilege cloud IAM

All commands require an authorized IAM administrator. Runtime gets only database connectivity, Firebase user lookup/revocation checks and its specific secrets; migrations get only connectivity and their separate DDL credential. No account needs Owner/Editor.

```sh
for OPPORTUNITY_IDENTITY in opportunity-runtime opportunity-migrations; do
  gcloud projects add-iam-policy-binding "$OPPORTUNITY_PROJECT" --member="serviceAccount:$OPPORTUNITY_IDENTITY@$OPPORTUNITY_PROJECT.iam.gserviceaccount.com" --role=roles/cloudsql.client --condition=None
done
gcloud projects add-iam-policy-binding "$OPPORTUNITY_PROJECT" --member="serviceAccount:opportunity-runtime@$OPPORTUNITY_PROJECT.iam.gserviceaccount.com" --role=roles/firebaseauth.viewer --condition=None
gcloud secrets add-iam-policy-binding opportunity-database-url --project "$OPPORTUNITY_PROJECT" --member="serviceAccount:opportunity-runtime@$OPPORTUNITY_PROJECT.iam.gserviceaccount.com" --role=roles/secretmanager.secretAccessor --condition=None
gcloud secrets add-iam-policy-binding opportunity-document-signing-key --project "$OPPORTUNITY_PROJECT" --member="serviceAccount:opportunity-runtime@$OPPORTUNITY_PROJECT.iam.gserviceaccount.com" --role=roles/secretmanager.secretAccessor --condition=None
gcloud secrets add-iam-policy-binding opportunity-migration-database-url --project "$OPPORTUNITY_PROJECT" --member="serviceAccount:opportunity-migrations@$OPPORTUNITY_PROJECT.iam.gserviceaccount.com" --role=roles/secretmanager.secretAccessor --condition=None
gcloud artifacts repositories add-iam-policy-binding "$OPPORTUNITY_REPOSITORY" --location "$OPPORTUNITY_REGION" --project "$OPPORTUNITY_PROJECT" --member="serviceAccount:opportunity-build@$OPPORTUNITY_PROJECT.iam.gserviceaccount.com" --role=roles/artifactregistry.writer
gcloud projects add-iam-policy-binding "$OPPORTUNITY_PROJECT" --member="serviceAccount:opportunity-build@$OPPORTUNITY_PROJECT.iam.gserviceaccount.com" --role=roles/logging.logWriter --condition=None
gcloud storage buckets add-iam-policy-binding "gs://$OPPORTUNITY_SOURCE_BUCKET" --member="serviceAccount:opportunity-build@$OPPORTUNITY_PROJECT.iam.gserviceaccount.com" --role=roles/storage.objectViewer --project "$OPPORTUNITY_PROJECT"
```

The deployment service account (or explicitly authorized human CLI identity) needs `roles/cloudbuild.builds.editor`, `roles/run.admin`, `roles/firebasehosting.admin`, and `roles/serviceusage.serviceUsageConsumer` in this project; Artifact Registry reader on this repository; object creator/viewer plus bucket metadata read on the source bucket; and `roles/iam.serviceAccountUser` **on each of the three exact build/runtime/migration accounts**, not project-wide. It does **not** need secret payload access. `roles/run.admin` is needed for initial service/job creation and public invoker IAM; after first release, narrow its resource scope where possible. This project-level initial-release authority is not a promise of custom minimal permissions.

```sh
for OPPORTUNITY_ROLE in roles/cloudbuild.builds.editor roles/run.admin roles/firebasehosting.admin roles/serviceusage.serviceUsageConsumer; do
  gcloud projects add-iam-policy-binding "$OPPORTUNITY_PROJECT" --member="serviceAccount:opportunity-deploy@$OPPORTUNITY_PROJECT.iam.gserviceaccount.com" --role="$OPPORTUNITY_ROLE" --condition=None
done
for OPPORTUNITY_IDENTITY in opportunity-runtime opportunity-migrations opportunity-build; do
  gcloud iam service-accounts add-iam-policy-binding "$OPPORTUNITY_IDENTITY@$OPPORTUNITY_PROJECT.iam.gserviceaccount.com" --project "$OPPORTUNITY_PROJECT" --member="serviceAccount:opportunity-deploy@$OPPORTUNITY_PROJECT.iam.gserviceaccount.com" --role=roles/iam.serviceAccountUser
done
gcloud artifacts repositories add-iam-policy-binding "$OPPORTUNITY_REPOSITORY" --location "$OPPORTUNITY_REGION" --project "$OPPORTUNITY_PROJECT" --member="serviceAccount:opportunity-deploy@$OPPORTUNITY_PROJECT.iam.gserviceaccount.com" --role=roles/artifactregistry.reader
for OPPORTUNITY_ROLE in roles/storage.objectCreator roles/storage.objectViewer roles/storage.legacyBucketReader; do
  gcloud storage buckets add-iam-policy-binding "gs://$OPPORTUNITY_SOURCE_BUCKET" --project "$OPPORTUNITY_PROJECT" --member="serviceAccount:opportunity-deploy@$OPPORTUNITY_PROJECT.iam.gserviceaccount.com" --role="$OPPORTUNITY_ROLE"
done
```

Confirm the managed Cloud Build/Run service agents exist and retain their documented service-agent roles after API enablement. The same-project Cloud Run service agent must be able to pull the Artifact Registry image; do not grant public registry access. Organization restrictions on public Run invocation must be resolved explicitly: the catalogue needs public HTTP while Firebase guards private routes. No organization-policy bypass is implemented.

## 5. GitHub manual release/WIF setup — operator action required

Configure repository default-branch protection/rulesets requiring successful `intelligence` CI. Configure a **production** GitHub environment with required human reviewers, prevent self-review, disable admin bypass and restrict deployment branches to the protected default branch. Verify your GitHub plan/repository visibility supports these protection rules; if it does not, the protected Actions release is blocked until the operator chooses a supported arrangement. Merely naming an environment in YAML does not create approval rules. [GitHub environment protections](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments).

Use repository/owner **numeric IDs** and exact workflow/branch/environment conditions to scope WIF. Obtain these public IDs from GitHub and the project number from Google Console. Substitute only public identifiers below.

```sh
export OPPORTUNITY_PROJECT_NUMBER=YOUR_NUMERIC_PROJECT_NUMBER
export OPPORTUNITY_REPO_ID=YOUR_NUMERIC_REPOSITORY_ID
export OPPORTUNITY_OWNER_ID=YOUR_NUMERIC_OWNER_ID
gcloud iam workload-identity-pools create github-release --location=global --project "$OPPORTUNITY_PROJECT" --display-name='Manual GitHub release'
gcloud iam workload-identity-pools providers create-oidc github --location=global --workload-identity-pool=github-release --project "$OPPORTUNITY_PROJECT" --issuer-uri=https://token.actions.githubusercontent.com --attribute-mapping='google.subject=assertion.sub,attribute.repository_id=assertion.repository_id' --attribute-condition="assertion.repository_id == '$OPPORTUNITY_REPO_ID' && assertion.repository_owner_id == '$OPPORTUNITY_OWNER_ID' && assertion.ref == 'refs/heads/$OPPORTUNITY_RELEASE_BRANCH' && assertion.sub == 'repo:$OPPORTUNITY_REPO:environment:production' && assertion.workflow_ref == '$OPPORTUNITY_REPO/.github/workflows/deploy.yml@refs/heads/$OPPORTUNITY_RELEASE_BRANCH'"
gcloud iam service-accounts add-iam-policy-binding "opportunity-deploy@$OPPORTUNITY_PROJECT.iam.gserviceaccount.com" --project "$OPPORTUNITY_PROJECT" --role=roles/iam.workloadIdentityUser --member="principalSet://iam.googleapis.com/projects/$OPPORTUNITY_PROJECT_NUMBER/locations/global/workloadIdentityPools/github-release/attribute.repository_id/$OPPORTUNITY_REPO_ID"
```

The manual workflow uses short-lived GitHub OIDC through service-account impersonation, never a long-lived service-account JSON or Firebase login token. Firebase CLI uses the generated ADC file, removed by the auth action afterward and ignored in Git. Only the deployment job has `id-token: write`; push/PR CI and the reusable validation job have no cloud auth/deploy steps. [Google WIF guidance](https://docs.cloud.google.com/iam/docs/workload-identity-federation-with-deployment-pipelines), [official auth action](https://github.com/google-github-actions/auth), [Firebase ADC support](https://firebase.google.com/docs/cli).

## 6. Fill public config, inspect plan, then explicitly release

Start from a **clean checkout** of the reviewed commit. The runner refuses frontend `.env`, `.env.local`, `.env.production` or `.env.production.local` files; it never overwrites them. All inherited `VITE_*` variables are discarded except the explicit public production values it supplies. API secrets are Cloud Run references, not local `.env` files.

```sh
cp -n infra/deploy.example.json /tmp/opportunity-production.json
# Edit project/region/resource IDs, numeric secret versions and public Firebase Web values.
# Leave real credentials out of this file.
python3 infra/deploy.py --config /tmp/opportunity-production.json
```

The JSON contains a separate build account/source bucket and separate API/migration database secrets. Pin numeric secret versions; `latest` is rejected. Placeholder Firebase web values are allowed in a plan, but rejected for execution. The example's Gemini model is retained as configuration only; it is not called or injected with a key in this first release.

For Actions, configure these **production environment variables**, not JSON credentials:

- `GCP_PROJECT_ID`
- `GCP_WORKLOAD_IDENTITY_PROVIDER`: `projects/NUMBER/locations/global/workloadIdentityPools/github-release/providers/github`
- `GCP_DEPLOY_SERVICE_ACCOUNT`: `opportunity-deploy@PROJECT.iam.gserviceaccount.com`
- `DEPLOY_CONFIG_JSON`: the filled public configuration document.

After local checks pass, the workflow is on the remote protected default branch (pushing needs separate user authorization), and infrastructure/approval protections are confirmed:

```sh
gh workflow run deploy.yml --ref "$OPPORTUNITY_RELEASE_BRANCH" --field approved_project="$OPPORTUNITY_PROJECT" --field authorization=DEPLOY
```

The reusable CI job runs tests/builds first; the deployment job then waits for the configured production environment reviewer before WIF auth/cloud access. For an explicitly approved local alternative, first use `gcloud auth login` and `gcloud auth application-default login` **outside the repository**, with an identity granted the operator permissions above; Firebase CLI uses ADC. Then, from the clean checkout only:

```sh
python3 infra/deploy.py --config /tmp/opportunity-production.json --execute --approved-project "$OPPORTUNITY_PROJECT" --receipt /tmp/opportunity-release-receipt.json
```

**Runner order:** check existing build-source bucket → record prior API traffic → allowlisted amd64 Cloud Build → deploy/execute single-task migration job (zero retries) → deploy tagged API with `--no-traffic` requested → candidate public/auth/CORS smoke → frozen web install/build → promote exact ready revision → stable API smoke → Firebase Hosting release → SPA-route smoke. It does not provision SQL, secrets, IAM, budgets or WIF. First-ever service creation has no previous revision to preserve; do not advertise its URL before acceptance. API and Hosting promotion are not atomic.

All secrets use pinned versions. Build input fingerprint includes every regular runtime source/config file (not just Python), migration/template, `uv.lock`, Python package metadata, pinned Dockerfile, Cloud Build and ignore manifests. The web is independently rebuilt using its frozen `pnpm-lock.yaml`; frontend packages are not included in the API image. Cloud Build explicitly enables BuildKit for the Dockerfile cache mount. No private documents, root corpus downloads, credentials, local env, tests or development fixtures are uploaded. The application package includes collector **code**, but its separate registry/blob workspace is not packaged or modified and no collection command runs.

## 7. Hosted acceptance — required after public smoke

Record the actual API/Hosting URLs and revision/digest only after successful release. Run the public check (an empty real catalogue is legitimate):

```sh
python3 infra/smoke.py --api-url https://YOUR_SERVICE.run.app --hosting-origin "https://$OPPORTUNITY_PROJECT.web.app" --hosting-origin "https://$OPPORTUNITY_PROJECT.firebaseapp.com"
```

Complete [hosted-acceptance.md](hosted-acceptance.md), including two actual Google accounts, all five contexts, non-persistence and Hindi/mobile. The optional authenticated API smoke reads **private local token files**, not CLI tokens or GitHub secrets. Never claim Google Sign-In, hosted search/scenario acceptance or Gemini worked because local emulator/public smoke passed. Empty published data cannot demonstrate opportunity match quality; substantive opportunity review/publication remains a separate human task and is not part of deployment.

## 8. Rollback, secrets and logs

Before release, record the previous **Firebase Hosting live release ID** from Console and retain its assets; download the public API traffic receipt from Actions (14-day artifact retention). It contains only revision names, traffic percentages, tags, URLs and image tag, never full service/env metadata. Candidate smoke failure stops before API promotion/Hosting. Migration failure stops before candidate deployment. If failure happens after API promotion, use the receipt's prior positive-traffic revision(s), explicitly approved:

```sh
gcloud run services update-traffic "$OPPORTUNITY_SERVICE" --project "$OPPORTUNITY_PROJECT" --region "$OPPORTUNITY_REGION" --to-revisions=PREVIOUS_REVIEWED_REVISION=100
```

Use Firebase Console → Hosting → release history → rollback to the recorded release; there is no invented CLI command or automatic rollback. First release has no previous revision: keep the site unannounced, investigate, and make a deliberate operator decision. Keep the current/previous images and remove unused tagged candidates only after investigation. Never delete the database to undo a release.

Migrations run before API traffic and must be backward compatible. `f24a1000abcd` is additive; local fresh upgrade and existing-data upgrade/downgrade tests pass. Adding its stored generated column/index can rewrite/lock a populated table: reserve a maintenance window and test representative data before later upgrades; additive does not mean lock-free. **Do not automatically downgrade production schemas.** Test the previous image with the expanded schema or approve a backup/PITR restoration with its data-loss/outage implications. Backups/PITR recovery must be rehearsed before relying on them.

Logs and rollback artifacts are access-controlled. Deploy errors suppress raw CLI stderr; inspect restricted Cloud Build/Run/SQL logs as needed, never paste credentials or profile bodies into tickets. Bound log/source/image retention and monitor database connections, HTTP error rates, cold starts and billing daily. Secrets rotation should be an explicit config/version update and new release. No `.env` overwrite, real-policy publication, paid AI enablement or remote push is included in this runbook's current execution status.
