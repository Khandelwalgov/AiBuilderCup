# Hosting costs and risks — reviewed 17 October 2026

This is a planning document, not a cloud quote or proof of deployed service. Select **asia-south1 (Mumbai)** for Cloud Run, Artifact Registry, build source storage and Cloud SQL to keep database/application traffic regional. Firebase Hosting is a global CDN. Confirm current regional prices in the calculator before approving billing.

| Component | First release choice | Recurring-cost driver |
|---|---|---|
| Firebase Hosting | Static Vite app, retained rollback releases | Stored releases and CDN transfer beyond allowance. |
| Cloud Run | 1 vCPU, 1 GiB, request-based CPU, min 0/max 2, concurrency 4, 60-second requests | Active CPU/memory/requests, cold starts, excess/abusive traffic and network egress. |
| PostgreSQL | Paid Enterprise **zonal db-f1-micro**, PostgreSQL 17, 10 GiB SSD, backups/deletion protection | Always-on compute, provisioned disk, backup/PITR retention and egress. Never scales to zero with Run. |
| Build and registry | Explicit Cloud Build identity, amd64 Docker, Artifact Registry | Build minutes, stored images, build-source objects and logs. |
| Secret Manager/logging | Three pinned first-release secrets; bounded logging retention | Active secret versions/access and log ingestion/retention above allowance. |
| Firebase Authentication | Google provider only, existing Firebase project | Applicable Firebase/Identity Platform quotas, enabled features and any later SMS/provider usage. |
| AI/documents/schedulers | Paid generation and ingestion off; uploads off; no Scheduler/GCS vault provisioned | Zero AI calls from this release configuration; future enablement needs a separate cost/privacy review. |

## Free allowances are not a free stack

Cloud Run's **request-based** monthly free allowance is 2 million requests, 180,000 vCPU-seconds and 360,000 GiB-seconds, aggregated according to billing-account rules. Jobs use a different billing basis; do not apply the request allowance to migration jobs. Egress, builds, registry and the database are separate. [Cloud Run pricing](https://cloud.google.com/run/pricing), [Google Free Tier](https://docs.cloud.google.com/free/docs/free-cloud-features).

Firebase Hosting documents 10 GB no-cost stored content. Spark transfer allowance is 10 GB/month; Blaze's no-cost transfer is calculated at 360 MB/day, with paid excess. Retained releases consume storage; keep a small number of rollback releases. Linked Cloud Run/Cloud SQL require a billing-enabled project even if Hosting usage is within allowance. [Firebase pricing](https://firebase.google.com/pricing), [Hosting quotas](https://firebase.google.com/docs/hosting/usage-quotas-pricing).

**Cloud SQL has no ongoing always-free PostgreSQL instance in this design.** The Cloud SQL trial lasts up to 30 days and is separate from the new-customer Google Cloud US$300/90-day trial. A trial instance can stop when the trial ends; upgrade/expiration/backup behavior must be reviewed explicitly. Never present a trial as an always-free production database or assume paid production guarantees. [Cloud SQL trial terms](https://docs.cloud.google.com/sql/docs/postgres/free-trial-instance), [Google trial](https://docs.cloud.google.com/free/docs/free-cloud-features).

Shared-core `db-f1-micro`/`db-g1-small` instances are **excluded from the Cloud SQL SLA**. The micro option is a low-traffic hackathon tradeoff (small memory, limited burst capacity), not a highly available production recommendation. Choose paid `db-g1-small` for more memory or a dedicated-core/HA option when justified, and recalculate cost. A zonal instance has outage/maintenance risk; backups support recovery, not seamless availability. [Cloud SQL pricing and SLA exclusions](https://cloud.google.com/sql/pricing).

## Planning allowance and safeguards

For the micro zonal setup, reserve roughly **US$20–40/month as an initial planning allowance**, dominated by always-on PostgreSQL, disk and backups. This is an engineering budget allowance, **not a quoted Mumbai SKU total**; replace it with the selected region/edition/tier/storage/retention calculator estimate before approval. A larger database, HA, high traffic, abusive requests, extensive logs or many builds can exceed it. No total bill was measured in this sprint. Taxes/currency conversion and other projects sharing the billing account are additional factors.

Set budget notifications at 50/80/100% of the approved monthly budget and inspect billing daily during the Cup. Alerts are **not a hard spending cap**. Run max instances does not cap DB/storage/build/egress bills and can be temporarily exceeded during platform operations. Apply source-bucket lifecycle deletion (e.g. 7 days), Artifact Registry cleanup retaining current/previous release images, Hosting release retention and appropriate Cloud Logging retention. Review these policies against rollback needs before applying them. No scheduled paid jobs or automatic ingestion are part of first release.

Pool sizing is 3 connections, no overflow, per API process. Two steady instances imply up to 6 API connections; candidate/rolling revisions, jobs, Cloud SQL internals and operator tools add more. Confirm `SHOW max_connections` and monitor reserved/active connections; leave headroom instead of allocating the full limit. Use one migration task, zero retries, no simultaneous releases. Cold starts and a small database can increase latency; capacity/load acceptance remains unverified.

Private documents stay disabled because production malware scanning/security acceptance and durable private storage are not complete. Do not enable local file uploads on Cloud Run's ephemeral filesystem. No raw household facts or tokens belong in logs, public artifacts or embedding indexes. Keep platform log access restricted; API access logs may include URLs, so private values must stay out of URLs. The app's structured request logs omit bodies, tokens and query values. Sanitized deploy errors omit provider stderr; operators may inspect restricted provider logs when required.
