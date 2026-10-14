# Phase 2.5 deployment procedure

No cloud resources were created or deployments executed during validation. The runner is **plan-only by default**. Cloud execution requires the user's explicit authorization in addition to the CLI guard. Do not treat a filled config or an existing gcloud default as authorization.

## Configure and validate locally first

1. Select one Google Cloud/Firebase project. In Firebase Console, register a Web app, enable Authentication → Google (including the support email), and add `localhost` for local sign-in plus the actual Hosting domains under Authentication → Settings → Authorized domains. Copy the four **public Firebase web configuration** values from Project Settings → Your apps. Firebase's API key identifies the web application; it is not the server Gemini key. Restrict it as appropriate without breaking Firebase Authentication.
2. Copy `apps/api/.env.example` to `apps/api/.env` and `apps/web/.env.example` to `apps/web/.env.local`. These files are ignored. Backend: set `FIREBASE_PROJECT_ID`, server-only `GEMINI_API_KEY`, `GEMINI_MODEL=gemini-3.8-flash`, `DATABASE_URL` and JSON `CORS_ORIGINS`. Local CORS is `["http://localhost:5173","http://127.0.0.1:5173"]`. Keep the real catalogue default (`ENABLE_DEVELOPMENT_CATALOGUE=false`). Local Vite proxies `/v1` and `/health` to port 8000; leave `VITE_API_BASE_URL` empty locally or set the explicit API origin. Do not put Gemini keys or database passwords in any `VITE_` variable.
3. Frontend: set `VITE_FIREBASE_PROJECT_ID`, `VITE_FIREBASE_API_KEY`, `VITE_FIREBASE_AUTH_DOMAIN`, `VITE_FIREBASE_APP_ID` from that same project. Restart Vite after changes. Backend/bootstrap/web project IDs must all match.
4. Configure local ADC outside this repository: `gcloud auth application-default login`. A credential refresh proves authentication, not permission to your selected Firebase project. The API's revocation checks and bootstrap need Firebase Authentication read access (`roles/firebaseauth.viewer`). The user chooses the intended project and UID; never use the gcloud default implicitly. On Cloud Run use service-account ADC, not a downloaded service-account key.
5. Run `make db migrate preflight`, then `make api` and `make web` in separate terminals. Preflight prints presence/matching checks, never values, and exits nonzero for missing configuration. It does not claim live access. Ensure your Gemini key/project can access the configured model; no automatic model substitution occurs.
6. Sign in through the actual application. Obtain that user's UID from Firebase Console → Authentication. Bootstrap only the explicitly chosen user:

```sh
cd apps/api
uv run python -m opportunity_platform.admin.bootstrap --project-id YOUR_PROJECT_ID --uid YOUR_FIREBASE_UID
```

Add `--revoke` to remove the DB admin role. This verifies the Firebase user and records an audit event. It does not mint a login token. See the [real acceptance checklist](../docs/phase-2.5-validation.md).

## Provision prerequisites — requires explicit approval, creates costs

Select region, budget and database size before proceeding. Cloud SQL has ongoing baseline charges even when Cloud Run scales to zero. Configure a Cloud Billing budget and alerts in the console; alerts and instance limits are not a hard spend cap. The following commands are an executable **future operator procedure**, not commands executed by this milestone. Substitute public project/region identifiers; never put passwords or API keys in command arguments.

```sh
export OPPORTUNITY_PROJECT=YOUR_PROJECT_ID
export OPPORTUNITY_REGION=asia-south1
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com sqladmin.googleapis.com secretmanager.googleapis.com identitytoolkit.googleapis.com --project "$OPPORTUNITY_PROJECT"
gcloud artifacts repositories create opportunity --repository-format=docker --location "$OPPORTUNITY_REGION" --project "$OPPORTUNITY_PROJECT"
gcloud iam service-accounts create opportunity-runtime --project "$OPPORTUNITY_PROJECT"
gcloud iam service-accounts create opportunity-migrations --project "$OPPORTUNITY_PROJECT"
gcloud sql instances create opportunity-db --project "$OPPORTUNITY_PROJECT" --region "$OPPORTUNITY_REGION" --database-version=POSTGRES_17 --edition=ENTERPRISE --tier=db-f1-micro --availability-type=ZONAL --storage-type=SSD --storage-size=10 --storage-auto-increase-limit=20 --backup-start-time=03:00 --deletion-protection
gcloud sql databases create opportunity --instance opportunity-db --project "$OPPORTUNITY_PROJECT"
gcloud secrets create opportunity-database-url --replication-policy=automatic --project "$OPPORTUNITY_PROJECT"
gcloud secrets create opportunity-gemini-key --replication-policy=automatic --project "$OPPORTUNITY_PROJECT"
```

Use Cloud SQL Console to create a dedicated database user with a generated password (not the postgres superuser). Through Cloud SQL Studio, make this user owner of the application database and its `public` schema, or grant the exact schema/table privileges needed by Alembic. Test `alembic upgrade head` with that user before release; creating a login alone is insufficient. This prototype shares the database login between API and migration jobs; separate database roles with DDL restricted to migrations remain a hardening step. Store it in a password manager. Use the hidden-input snippet below locally to add the database secret version. It creates no database user and never prints the URL/password. The socket connection requires Cloud SQL Client IAM; do not expose the database with `0.0.0.0/0` authorized networks.

```sh
python3 - <<'PY'
import getpass, os, subprocess
from urllib.parse import quote
project = os.environ['OPPORTUNITY_PROJECT']
region = os.environ['OPPORTUNITY_REGION']
username = input('Dedicated database username: ').strip()
password = getpass.getpass('Database password (hidden): ')
connection = f'{project}:{region}:opportunity-db'
url = f'postgresql+psycopg://{quote(username,safe="")}:{quote(password,safe="")}@/opportunity?host=/cloudsql/{connection}'
result = subprocess.run(['gcloud','secrets','versions','add','opportunity-database-url','--project',project,'--data-file=-','--quiet'], input=url, text=True, capture_output=True)
if result.returncode: raise SystemExit('Secret creation failed; inspect provider logs locally.')
print('Database secret version stored. Confirm its numeric version in Secret Manager.')
PY
python3 - <<'PY'
import getpass, os, subprocess
key = getpass.getpass('Server Gemini API key (hidden): ')
if not key: raise SystemExit('A key is required.')
result = subprocess.run(['gcloud','secrets','versions','add','opportunity-gemini-key','--project',os.environ['OPPORTUNITY_PROJECT'],'--data-file=-','--quiet'], input=key, text=True, capture_output=True)
if result.returncode: raise SystemExit('Secret creation failed; inspect provider logs locally.')
print('Gemini secret version stored. Confirm its numeric version in Secret Manager.')
PY
```

Grant the two service accounts Cloud SQL connectivity, and the runtime account Firebase Authentication read access:

```sh
for OPPORTUNITY_ACCOUNT in opportunity-runtime opportunity-migrations; do
  gcloud projects add-iam-policy-binding "$OPPORTUNITY_PROJECT" --member="serviceAccount:$OPPORTUNITY_ACCOUNT@$OPPORTUNITY_PROJECT.iam.gserviceaccount.com" --role=roles/cloudsql.client --condition=None
done
gcloud projects add-iam-policy-binding "$OPPORTUNITY_PROJECT" --member="serviceAccount:opportunity-runtime@$OPPORTUNITY_PROJECT.iam.gserviceaccount.com" --role=roles/firebaseauth.viewer --condition=None
for OPPORTUNITY_ACCOUNT in opportunity-runtime opportunity-migrations; do
  gcloud secrets add-iam-policy-binding opportunity-database-url --project "$OPPORTUNITY_PROJECT" --member="serviceAccount:$OPPORTUNITY_ACCOUNT@$OPPORTUNITY_PROJECT.iam.gserviceaccount.com" --role=roles/secretmanager.secretAccessor --condition=None
done
gcloud secrets add-iam-policy-binding opportunity-gemini-key --project "$OPPORTUNITY_PROJECT" --member="serviceAccount:opportunity-runtime@$OPPORTUNITY_PROJECT.iam.gserviceaccount.com" --role=roles/secretmanager.secretAccessor --condition=None
```

The deploy operator needs permission to submit Cloud Builds, deploy Cloud Run services/jobs, act as these specific service accounts, publish Hosting, and grant public Cloud Run invocation. Configure the project's selected Cloud Build execution account with Artifact Registry write access to this repository and required logging/source permissions. Organization policy may restrict public invocation; resolve that explicitly rather than bypassing it. No Owner/Editor grant is required by the application. For first-admin bootstrap against Cloud SQL, use an authorized Cloud SQL Auth Proxy session and local ADC; override local `DATABASE_URL` securely to that connection. Do not bootstrap a local database and assume the role exists in production.

## Review plan, then release

From the repository root:

```sh
cp infra/deploy.example.json infra/deploy.local.json
# Edit only public config and Secret Manager names + pinned numeric versions.
python3 infra/deploy.py --config infra/deploy.local.json
# Only after explicit project/cost/deployment authorization:
python3 infra/deploy.py --config infra/deploy.local.json --execute --approved-project YOUR_PROJECT_ID
```

The runner uses an explicit project on every cloud command. It builds a content-tagged amd64 Cloud Build image, deploys/executes a single-task Alembic migration job, then deploys the API, checks readiness/auth guards/CORS, builds web with the returned API URL and matching Firebase config, deploys Hosting and checks SPA routing. The plan intentionally prints a placeholder env-file path; the runner generates the real temporary public configuration only during execution. Secret **values** never belong in JSON; pinned Secret Manager references are injected by Cloud Run. No synthetic seed runs in deployment.

Production guards reject local/default databases, development catalogue mode and missing/non-HTTPS CORS configuration. The API uses the supplied `PORT`, non-root user, DB-independent `/live`, database-dependent `/health`, 120-second per-model-call timeout, 900-second request timeout and concurrency 4. Service maximum 2/minimum 0 limits runtime scale; DB pool size 3 with no overflow gives six service DB connections at steady maximum, plus the migration job. Rolling revisions/jobs/operator tools can add connections. Synchronous ingestion holds one connection/transaction; another ingestion for that source returns `source_busy` immediately. Fetch retries are bounded; Gemini has one attempt per count/generation request. Do not use these prototype limits as a production capacity guarantee.

Cloud Run allows public HTTP invocation for the catalogue, while every private/admin route still validates Firebase and database permissions. CORS permits only the two Hosting origins. Custom domains need an explicit CORS/config update. Firebase Hosting serves the SPA fallback and security headers from `infra/firebase.json`. Public smoke success does **not** prove Google sign-in, admin publication or eligibility. Complete the real browser checklist before announcing deployment acceptance. Record actual URLs only after a successful deployment.

If release fails, stop and inspect logs locally; runner error output is sanitized. Database migrations run before API traffic and must remain backwards-compatible; restore/rollback requires a deliberate operator decision. Retention, deletion/export, GCS uploads and scheduled ingestion are not implemented by this milestone.

References: [Cloud SQL create flags](https://cloud.google.com/sdk/gcloud/reference/sql/instances/create), [Cloud Build account selection](https://cloud.google.com/build/docs/cloud-build-service-account-updates), [Cloud Run secrets](https://cloud.google.com/run/docs/configuring/services/secrets), [Cloud SQL with Cloud Run](https://cloud.google.com/sql/docs/postgres/connect-run), [health checks](https://cloud.google.com/run/docs/configuring/healthchecks), [Hosting configuration](https://firebase.google.com/docs/hosting/full-config), [Google sign-in](https://firebase.google.com/docs/auth/web/google-signin).


## Explicit development provider selection

The backend now defaults to `AI_EXTRACTION_PROVIDER=gemini`; OpenAI is an explicit development option via backend-only `OPENAI_API_KEY` and `OPENAI_MODEL`. There is no automatic fallback. The existing deployment runner still prepares the primary Gemini path; it does not deploy OpenAI keys or infer provider choice from errors. Any later authorized OpenAI deployment must explicitly inject its own Secret Manager reference and provider setting. Apply the additive provenance migration `a70d81ea2f20` before running updated code. No deployment occurred during this provider integration.
