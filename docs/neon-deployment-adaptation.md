# Neon / Unclaimed deployment adaptation — 17 October 2026

Ready tooling for `venuesignal` / `asia-south1`, existing Firebase Web app `AiBuilderCup`, Hosting target `unclaimed` → `unclaimed-ai-cup`, frontend `https://unclaimed-ai-cup.web.app`, and external Neon Free PostgreSQL 17. **Not deployed or remotely accepted.** Billing linkage is unverified since the operator's last unlinked check.

## Implemented

- Deployment config explicitly selects Neon; no Cloud SQL connection field or attachment flags. Unexpected existing service Cloud SQL attachments cause a stop rather than silently persisting them. No SQL instance/proxy/VPC/client IAM provisioning is required.
- Runtime and schema-gate credentials use separate Secret Manager references with pinned numeric versions. Neon URLs require psycopg/TLS and the provider hostname; migration connections must be direct, runtime may be pooled. Runtime disables server-side prepared statements and retains pre-ping/3 connections/no overflow. Migration connections use NullPool.
- Default release schema mode is **verify**, reading Alembic metadata in a read-only transaction. Missing/mismatched metadata fails closed, with no initialization, stamp, seed or upgrade. Future upgrade needs separate runner/module authorization. Existing Neon head `f24a1000abcd` is **operator-reported**, not rechecked against Neon in this task.
- Cloud Run uses request-based CPU, 1 vCPU, 1 GiB, min 0/max **1**. Production fictional catalogue, paid ingestion, assistant generation and uploads remain disabled; no model key is injected. Firebase Admin uses runtime ADC, not a JSON key.
- Preserved and tracked the operator's existing Firebase target files. Local mapping validation occurs before cloud access; only `hosting:unclaimed` is deployed. CORS, candidate/stable smoke, final SPA URL and receipts use Unclaimed site origins; the project's Firebase Auth domain remains `venuesignal.firebaseapp.com`.
- Hardened Docker/lock/resource fingerprints, no-secret allowlist, no-traffic candidate smoke, exact revision promotion, safe rollback metadata and the protected manual WIF workflow are preserved. CI plan validation now uses the public selected-project template without cloud calls.

## Executed locally

| Check | Result |
|---|---|
| Deployment plan | Passed with public example config; no Cloud SQL attachment flag, `--max 1`, schema `verify`, exclusive `hosting:unclaimed`, branded frontend URL. Only printed commands. |
| Mocked deployment tests | Passed: project/upgrade authorization, target mismatch rejection, secret pins, candidate-before-promotion ordering, final branded URL and receipt, no promotion after failed smoke. No real gcloud/Firebase subprocess executed. |
| Neon connection-policy tests | Passed with fictional URLs only: SSL/hostname/driver validation, direct-vs-pooler rules, endpoint override rejection and prepare-threshold configuration. No live TLS/Neon connection. |
| Read-only schema-gate tests | Passed in isolated local PostgreSQL schemas: head match, mismatch, transaction read-only and absent metadata stays absent. |
| `make contracts check` / final `make check` | Explicit local DATABASE_URL + TEST_DATABASE_URL + provider overrides; **205 passed, 1 skipped** in final backend run; Ruff/format, clean Alembic drift, ESLint, TypeScript and production Vite build passed. Contracts unchanged. |
| amd64 production Docker build | Passed with existing pinned base digests/frozen dependencies and new connection/schema modules. No push. |
| Fresh container checks | Passed on disposable local PostgreSQL 17: full chain to `f24a1000abcd`, clean drift, read-only verification, runtime semantics JSON/Phase 4 routes, non-root, no fixtures/private data. Local containers/network cleaned. |
| Firebase CLI mapping resolution | Installed CLI read local files only; explicit nested config resolves `infra/.firebaserc` to exactly `[unclaimed-ai-cup]`. No auth/deploy/network command. |

Browser suites were not rerun in this adaptation; frontend product UI is unchanged. Previous browser results remain historical, not new hosted evidence. The production bundle still has the existing Vite >500 kB warning; backend dependency deprecation warnings are unchanged.

**No Neon query/initialization/migration/data mutation, Google provisioning/billing linkage/deployment, paid model call, policy publication, environment overwrite or remote push occurred.** Validation deliberately overrides any `.env` Neon URL. The separate corpus implementation and recommender/UI were not modified.

## Remaining human-operated steps

The exact commands are in [production-deployment-runbook.md](production-deployment-runbook.md), in this order:

1. Approve/check/link the existing billing account to `venuesignal`; enable only needed Google APIs. Create/reuse registry, private build-source bucket and four service accounts. **No Cloud SQL.**
2. Populate three pinned Secret Manager versions using existing Neon runtime/direct migration credentials and a stable signing key. Verify role separation/privileges with the Neon administrator; this task makes no role/grant changes.
3. Apply least-privilege Google IAM; no database IAM client role. Confirm existing AiBuilderCup public key/app ID, Google provider, authorized Unclaimed domains and production public config.
4. Configure GitHub required reviewers/branch protections, WIF trust and update `DEPLOY_CONFIG_JSON` to the Neon template. The former Cloud SQL config is rejected. Publishing code requires separate push authorization.
5. Review plan-only output, then explicitly authorize the manual workflow or clean-checkout CLI release with **migration_mode=verify**. No `--approve-migrations` is needed or appropriate for this already-applied head.
6. Run actual branded public/authenticated smoke and [two-account hosted acceptance](hosted-acceptance.md); record Cloud Run ADC/Neon connectivity/Google Sign-In/latency and rollback observations separately. These are still **NOT RUN** remotely.

Potential release blockers are billing linkage, missing prerequisite/IAM/secret versions, owner-only/shared Neon credentials, unavailable GitHub approval protections, missing app public values/authorized domains, or failed actual hosted connectivity/acceptance. Populated real-policy acceptance still requires separate substantive human review/publication. Neon Free quotas, cold starts, cross-cloud egress/latency and recovery limits need operator monitoring; no zero-cost or production SLA promise. [Costs and risks](hosting-costs-and-risks.md).

Implementation local commit: `bbb56d1`. A subsequent documentation commit records the updated Neon operator runbook and this validation. No push.
