# Opportunity Intelligence · Phase 1

Working name: **Unclaimed**, configurable with `VITE_APP_NAME`. India-first opportunity discovery, with a deliberately truthful development catalogue. This phase runs React → FastAPI → PostgreSQL. All six seeded records are **fictional synthetic examples**, not real programmes. No official URLs, deadlines, benefits, or eligibility decisions are fabricated.

## Run locally

Prerequisites: Docker Desktop running, Python 3.12+, `uv` 0.11.28, Node.js 24+ and `pnpm` 11.25.0. Ports 5432, 8000, and 5173 must be free. Commands below run from the repository root.

```sh
cp apps/api/.env.example apps/api/.env
cp apps/web/.env.example apps/web/.env.local
make setup
make db
make migrate
make seed
make contracts
```

Start these in **two terminals**:

```sh
make api
```

```sh
make web
```

Open [the application](http://127.0.0.1:5173), [API documentation](http://127.0.0.1:8000/docs), or [database readiness](http://127.0.0.1:8000/health). Public browsing needs no Firebase or Gemini credentials. `make seed` is idempotent and preserves existing records. `docker compose stop` stops PostgreSQL without deleting its named volume.

If installation is blocked by a restricted cache location, use `UV_CACHE_DIR=/tmp/opportunity-uv-cache make setup`. pnpm can use a writable store via `pnpm --dir apps/web install --store-dir /tmp/opportunity-pnpm-store`; this affects only your local installation. Do not commit cache paths or credentials.

## What works

- Responsive React application with working navigation, English/Hindi static strings, keyboard focus, skip link, and loading/empty/error states.
- Public opportunity discovery with title/summary search, category, exact state and district filters, URL-persisted filters, cursor pagination, and detail/provenance pages. Location is a discovery filter, **not an eligibility determination**; selecting Rajasthan returns records tagged Rajasthan, not national records.
- A database-backed overview reporting actual synthetic, verified, and verified-source counts.
- FastAPI public catalogue and facets, database readiness, consistent error envelopes, redacted structured request logs and correlation IDs, bounded parameters, SQLAlchemy services, Alembic migration, and explicit development seeding.
- Firebase Google sign-in integration and backend ID-token validation, including revocation checking. `/v1/me` returns only the verified caller identity; there is no bypass and no private-domain data endpoint.
- Canonical domain schema foundations for people, households, consent, businesses, facts, evidence, versioned opportunities, requirements, evaluations and actions.
- Generated OpenAPI + TypeScript contracts with `openapi-fetch` and TanStack Query.

Profile, family, business, and My Opportunities pages intentionally explain that their workflows are not implemented. The UI does not simulate matching, applications, document uploads, monitoring, or AI answers.

## Firebase configuration

To enable sign-in, create/select your own Firebase project and register a web app. Enable **Google** in Authentication → Sign-in method, and add `localhost`, `127.0.0.1`, and your eventual Hosting domain under authorised domains.

In `apps/web/.env.local`, set the web app's:

```dotenv
VITE_FIREBASE_API_KEY=
VITE_FIREBASE_AUTH_DOMAIN=
VITE_FIREBASE_PROJECT_ID=
VITE_FIREBASE_APP_ID=
```

In `apps/api/.env`, set `FIREBASE_PROJECT_ID` to the **same project**. Backend revocation checks require Application Default Credentials with Firebase Authentication access. Locally use `gcloud auth application-default login` for an appropriately authorised account, or `GOOGLE_APPLICATION_CREDENTIALS` pointing to a credential file **outside this repository**. Cloud Run should use its attached service account and IAM. Restart both servers after configuration changes. In Settings, a signed-in account calls the protected API to verify the backend session. Firebase console configuration and real sign-in require your project; these were not tested against a live account in this milestone.

[Vetted token verification behavior](https://firebase.google.com/docs/auth/admin/verify-id-tokens) and [session revocation](https://firebase.google.com/docs/auth/admin/manage-sessions) follow Firebase's Admin SDK guidance.

`VITE_APP_NAME` controls the working product name. Leave `VITE_API_BASE_URL` blank locally to use the Vite `/v1` proxy. For Hosting, set it to the HTTPS API origin **before building**. `DATABASE_URL` configures PostgreSQL; `CORS_ORIGINS` is a JSON list of allowed frontend origins. Frontend `VITE_*` values are public build configuration; never put server credentials in them.

## Checks and contracts

With PostgreSQL running and dependencies installed:

```sh
make check
make contracts
git diff -- packages/contracts/openapi.json apps/web/src/lib/api/schema.d.ts
cd apps/web
pnpm exec playwright install chromium
pnpm exec playwright test
```

`make check` runs Ruff lint/format verification, PostgreSQL integration tests, Alembic drift detection, ESLint, TypeScript and the production Vite build. Backend tests use isolated temporary PostgreSQL schemas and remove them afterward; they do not truncate application tables. `TEST_DATABASE_URL` optionally selects a dedicated PostgreSQL test database. Schema creation permission is required for the test role. Browser tests start API/Vite automatically if they are not already running and use the seeded application database. Run `make migrate seed` first.

CI performs these checks against PostgreSQL, regenerates and checks contracts, and runs Chromium journey tests. API contract changes must be regenerated via `make contracts`; do not edit `schema.d.ts` or `openapi.json` by hand. Typed client integration follows [openapi-fetch](https://openapi-ts.dev/openapi-fetch/api).

## Repository layout

```text
apps/api/
  src/opportunity_platform/
    core/                 configuration, Firebase auth, errors
    db/                   SQLAlchemy domain models and sessions
    opportunities/        catalogue services and Pydantic responses
    main.py               HTTP routes and middleware
    seed.py               explicit synthetic fixture loader
  alembic/versions/       committed initial schema migration
  tests/                  real PostgreSQL API and constraint tests
  Dockerfile              Cloud Run-ready non-root API image
apps/web/
  src/app/                routing, shell, Firebase initialization
  src/features/opportunities/  connected listing and detail
  src/lib/api/            generated types and typed client
  src/i18n/               English/Hindi interface strings
  tests/                  desktop/mobile/error browser journeys
packages/contracts/       generated OpenAPI
infra/                    Hosting config and deployment guide
data/fixtures/            explicitly synthetic catalogue JSON
scripts/                  contract export
docs/decisions/            foundation boundaries and privacy limits
.github/workflows/        focused CI
```

## Deployment preparation and limits

See [infra/README.md](infra/README.md) for Firebase Hosting and Cloud Run instructions. No paid resources were provisioned or deployed. Local PostgreSQL is bound to loopback with a clearly development-only password. Never reuse that password remotely. Migrations run separately from application startup. Environment files, credentials, documents, build outputs, and caches are ignored.

This is a Phase 1 foundation, not the full hackathon P0. There are no real-source records, ingestion jobs, Gemini calls, eligibility engine, live requirements, family/guardian administration, secure uploads, application tracking, notifications, or deployed services. Hindi applies to static UI; fixture text and category names remain English. Account preferences are local browser settings; `/v1/me` validates identity without creating personal data. Domain tables are schema foundations, not completed workflows. Data export/deletion and consent-management UI must exist before real sensitive-data onboarding. See [decision 0001](docs/decisions/0001-foundation.md).

**Next milestone:** add one accessible official-source adapter, immutable snapshots and schema-validated Gemini extraction, a server-authorized admin candidate-review/publication workflow, and cited deterministic requirement evaluation. Preserve the last published opportunity when a newer candidate is under review or a source is unreachable, then connect progressive personal profiling with explicit permissions and unknown states.
