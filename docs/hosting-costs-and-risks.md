# Unclaimed hosting costs and risks — Neon architecture

Updated 17 October 2026. The current design is **Neon Free PostgreSQL 17 + Cloud Run asia-south1 + Firebase Hosting site unclaimed-ai-cup**. The previous Cloud SQL budget/instance recommendations are superseded. No Cloud SQL service/instance/client IAM/proxy is needed, and none was provisioned in this task.

| Component | Conservative first-release choice | Cost/risk drivers |
|---|---|---|
| Neon | Existing Free project/database, no reinitialization or plan change | Free-plan compute/storage/transfer/recovery quotas, suspension/cold starts, connection and availability limits. Check actual Dashboard allowance/region. |
| Cloud Run | Request-based billing, 1 vCPU, 1 GiB, min 0/max 1, concurrency 4 | Active request CPU/memory, requests, cold starts and outbound traffic to external Neon. |
| Firebase Hosting | Existing `unclaimed-ai-cup` site, static app | Stored releases and CDN transfer above allowance. |
| Builds/registry/source bucket | Pinned amd64 image, explicit build identity | Build minutes, stored images/source objects and network traffic. |
| Secret Manager/logging | Three pinned secrets, restricted logs | Active versions/access and log ingestion/retention beyond allowances. |
| AI/uploads/scheduling | Paid generation, ingestion and uploads disabled; no scheduler | No model calls from first-release flags; future enablement needs separate approval. |

Neon Free is a quota-limited plan, not a promise of unlimited compute, permanent quota levels or production SLA. Existing head `f24a1000abcd` is operator-reported; this assignment did not connect to Neon. Verify actual regional latency, role privileges, available recovery history and quota exhaustion behavior before announcement. Use direct TLS for the read-only schema gate/future approved migrations, pooled TLS for the runtime where available. Review actual region/data residency rather than assuming the database is in Mumbai because Run is. [Neon plans](https://neon.com/docs/introduction/plans), [pooling](https://neon.com/docs/connect/connection-pooling).

The runtime SQLAlchemy pool is at most 3 connections per process, no overflow, with pre-ping and a 10-second connection timeout. One steady API instance therefore has up to 3 client connections; rolling/tagged candidates, the one-task schema job and operator clients can add connections. PgBouncer client capacity is not a promise of equally many active database backends. Prepared statements are conservatively disabled for Neon. Cloud Run and Neon may both cold-start; health checks must tolerate wake-up, and actual wake latency remains unmeasured here.

Google billing must still be linked/enabled for Cloud Run, builds, registry and secrets. Cloud Run's request-based free allowances are 2 million requests, 180,000 vCPU-seconds and 360,000 GiB-seconds/month under the documented billing-account rules; jobs have different billing. External database egress, builds, registry, storage and logs are separate, so **do not promise a zero-dollar Google bill**. [Cloud Run pricing](https://cloud.google.com/run/pricing).

Firebase Hosting has documented no-cost storage/transfer allowances; excess and retained release assets can cost money on Blaze. Use the **site**, not the project name, when inspecting Hosting usage and rollback releases. Google authentication/provider quotas remain separate. [Firebase pricing](https://firebase.google.com/pricing).

The former US$20–40/month allowance was driven by always-on Cloud SQL and **does not describe this Neon release**. No recurring bill is measured or quoted for the new architecture. Have the operator choose a small initial Google budget after checking actual traffic/build/egress estimates; set 50/80/100% alerts and inspect usage daily during the Cup. Alerts and max instances are not hard spend caps. Keep min 0/max 1, avoid frequent synthetic uptime traffic that prevents scale-to-zero, and set reviewed source/image/Hosting/log retention. Preserve current/previous images and releases for rollback before deleting anything.

TLS URLs/passwords remain in Secret Manager, never logs, Git, Docker, public receipts or GitHub variables. Cloud Run ADC verifies Firebase identities; do not download service-account keys. Platform access logs can include URLs: keep private facts/tokens out of them and restrict log access. Sensitive uploads remain disabled until durable private GCS storage, malware scanning and security acceptance exist. Do not use Cloud Run ephemeral storage for real documents. Never auto-restore/downgrade Neon to undo an application release; assess its actual recovery window and data-loss implications separately.
