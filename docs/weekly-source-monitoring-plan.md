# Unclaimed weekly collection: proposed, not active

18 October 2026. **No recurring job or Scheduler was created or activated by this pass.**
This is a separate future authorization scope; it must not be bundled into an application-only
release or described as deployed. Submission and genuine Gemini evidence take priority.

Reuse `corpus.production collect`, the reviewed source registry, existing restricted corpus
worker identity, private bucket and existing durable checkpoint. Keep Gemini/OpenAI inference
disabled in this collection job. Use a reviewed allowlist of at most four source keys, one
task, parallelism one, retries zero, 900-second timeout, 1 CPU and 1 GiB. The current collector
has hard limits of 40 HTTP requests, 10 documents and 50 MiB transferred per execution.
An existing administrator actor is required for changed-source queueing; never mint an admin.

The existing collector sends conditional ETag/Last-Modified requests, hashes immutable blobs,
records previous snapshots and failed runs, and uses database/GCS checkpoint locks/generation
preconditions. A 403, CAPTCHA, timeout or missing response remains a source-check failure;
it must not remove a programme or change eligibility. New or changed documents enter the
private evidence/review flow. No research update or rule is published by collection alone.
Explicit informational publication is required for research changes. Approved eligibility
versions use the existing review/publication workflow and version-aware assessment/plan
refresh. Neural index rebuilding remains a separate authorized operation, not an AI call.

Proposed schedule: Monday 06:00 **Asia/Kolkata**, `0 6 * * 1`. After a reviewed implementation
commit and separate approval, Cloud Scheduler would issue an authenticated OAuth HTTP POST to
`https://run.googleapis.com/v2/projects/venuesignal/locations/asia-south1/jobs/REVIEWED_COLLECTION_JOB:run`.
Reuse a reviewed existing invoker identity scoped to that one job; do not grant project-wide
administration, secret access or permission to alter job arguments. If an invoker permission
or API enablement is missing, include that exact mutation in the separate approval.
The Scheduler service agent must have its documented service-agent role. Do not create an
identity, enable an API, bind IAM or run this POST under the current release authorization.

Before requesting activation: pin the exact app image digest, job definition, source keys,
actor, bucket checkpoint and versioned DB secret. Verify the job currently runs **collection**,
not import/index/bootstrap. `infra/corpus_job.py` is plan-only by default and can render this
reviewable job configuration; its execution also runs the job and therefore needs explicit
authorization. No scheduler command in this document is evidence of a running service.

Acceptance must show one approved manual bounded run, changed/unchanged/failed source counts,
last check and last success, snapshot hash/previous version, queue state, and propagation
state (`awaiting_research_approval`, `awaiting_policy_approval`, `published`,
`re_evaluation_pending` or `failed`). Existing logs and review records provide parts of this;
a consolidated recurring-run/propagation summary and alerts still require implementation
and acceptance. Never claim the full monitoring journey is complete from a cron definition.

Cost estimate: 4.35 runs/month at the full 900-second bound is about **3,915 vCPU-seconds and
3,915 GiB-seconds**, plus at most about **218 MiB/month** new wire data at the hard transfer
bound. Blob retention can grow indefinitely and needs an explicit storage policy; immutable
evidence must not be silently discarded. Scheduler offers three jobs per billing account
without charge, then approximately US$0.10/job/month; available allowance is not confirmed.
Cloud Run Jobs use instance-based billing with a one-minute minimum. Budget planning should
allow roughly **US$0–1/month incremental collection usage** for this tiny bounded schedule,
excluding existing image/DB/secret/storage/log costs and accumulated evidence; this is an
estimate, not a billing cap or guaranteed free service. Paid model cost stays zero because
collection inference remains disabled. Recheck region/SKU/allowance at authorization using
[Cloud Run pricing](https://cloud.google.com/run/pricing) and
[Scheduler pricing](https://cloud.google.com/scheduler/pricing).
