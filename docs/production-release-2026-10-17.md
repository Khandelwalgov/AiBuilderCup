# Production release — 17 October 2026

The human explicitly approved commit `984e6670968654c3f689e1b044cfa4ad37092ae2`, the itemized one-time operations and a US$2 initial infrastructure planning allowance. The explicitly selected existing Google account was resolved privately and bootstrapped; no account, token or secret is included in this document. No policy publication, paid AI, scheduler, Cloud SQL or billing-plan change was authorized or performed.

## Actual production result

- [Live document library](https://unclaimed-ai-cup.web.app/government-sources): **128 captured snapshots** visibly rendered in the signed-in browser, with real official links and captured-page text.
- API revision **`opportunity-api-00003-jur`**, 100% traffic. [Exact deployed commit CI](https://github.com/Khandelwalgov/AiBuilderCup/actions/runs/39010100957) passed backend, frontend, contracts/build/browser stages.
- Image digest `sha256:81e665e6d867ec40a6042d631af9745d0ebaa4953819fc0ee3de983f3afc529d`. One successful Cloud Build: `eaffffc9-a32d-4296-938d-ba2eb6393c87`, approximately 81 seconds.
- Unclaimed Hosting version **`sites/unclaimed-ai-cup/versions/c34e61e654737c46`**; fresh homepage and three JavaScript/CSS assets matched local build hashes. Only `hosting:unclaimed` was released.
- Neon schema **`f25b1000abcd`**. Migration was additive; minimal SELECT/INSERT/UPDATE grants on the two new tables were applied and runtime privileges verified. No initialization/seed/downgrade occurred.

| Measured database result | Count |
|---|---:|
| Source rows, including four collector registry rows | 131 |
| Captured snapshots | 128 |
| Distinct captured hashes in Neon | 123 |
| Draft opportunities / draft versions | 4 / 4 |
| Human review decisions / published versions | 0 / 0 |
| Active policy embeddings | 0 |
| Administrators | 1 |
| Paid-inference reservations | 0 |
| Persisted match evaluations / actions after scenario acceptance | 0 / 0 |

The approved immutable handoffs imported **127 snapshots / 122 hashes / four drafts**. One irrelevant Citizen Charter was preserved in the private archive but excluded from database import. The separately approved bounded refresh added **one changed snapshot/hash**, not ten new opportunities. Source rows increased by four registry records. Counts above are actual SQL observations, not dry-run predictions.

## Durable corpus and bounded jobs

Private `venuesignal-public-corpus` contains **124 original objects**, totaling **197,502,042 bytes**, and two distinct metadata checkpoints (`current` and `rajasthan-supplement-20261017`). No manifests or SQLite ledgers were merged. The worker uses its own service identity and versioned direct application-role secret; originals have no public access, and replacement privileges are limited to the checkpoint prefix. No migration credential/provider key/service-account JSON was supplied to the worker.

Both production dry runs validated exact original-page citations and schemas: 128 transport records, 127 insertable snapshots, one exclusion, four selected candidates, zero failures and zero database writes. Bootstrap then imported all approved records. **Twenty one-task corpus executions succeeded; none failed.** Tasks had zero retries. A delayed Cloud Logging summary was recovered without rerunning its import.

The single collector execution `opportunity-corpus-s4qf6` returned `0`, checkpointed state and imported one changed snapshot with zero failures. It fetched ten documents and stopped at its configured budget (`budget_exhausted`), preserving existing snapshots. Limits were 40 requests / 10 documents / 50 MiB. No recurring schedule was created or enabled, and no second collection was attempted.

## Actual neural and browser acceptance

The deployed CPU probe verified pinned weights and real English/Hindi inference: **384 dimensions, 3,795 ms load/probe and 504 MiB process peak RSS**, with zero external API calls. Controlled scholarship-vs-unrelated-tender similarities passed. This proves deployed inference health; it does not establish government-policy retrieval quality. The published-only index job correctly indexed zero versions because every policy remains a draft.

The human completed fresh Google Sign-In. The agent observed the existing saved profile and automatic **blank-query Just Me Discover**, with zero-publication coverage explicitly distinguished from ineligibility. Family/member/business contexts required authorized subject selection; no private subjects were created for testing. Explore All was checked. Real source browsing/search worked; MSME TEAM's actual 15-page snapshot and title page opened. The administrator queue displayed all four drafts, actual extraction provenance and incomplete independent verification; **Approve & publish was disabled**. Authenticated admin endpoints returned HTTP 200.

A real hosted hypothetical enrollment scenario ran, displayed **“No scenario data was saved”**, and was reset/discarded. Aggregate checks still showed two personal fact rows and zero persisted evaluations/actions. Private fact values were not read for the database audit, so this is not a value-by-value database comparison. Public Hindi Discover rendered at 390px without horizontal DOM overflow; browser language/viewport were restored. Actual missing/invalid-token search/scenario 401, private/admin 401, CORS, health and real-only catalogue checks passed.

The first account's ordinary-user admin page denied access before bootstrap. A direct authenticated non-admin HTTP 403 and cross-account isolation were **not run**: no second approved identity was provided. Google credential-entry steps were performed by the human, not observed by the agent. Populated-policy eligibility and realistic production semantic quality remain **blocked by publication/verification**, not passed using fabricated examples. Paid-provider failure tests were not run.

## Costs and release repairs

External paid AI inference expenditure: **₹0**. Prepared interactive-session extraction usage is not separately attributable per document; no paid Gemini/OpenAI/OCR/embedding API was called during this release. Bounded job/build compute is expected to be comfortably below the approved US$2 planning allowance before ongoing usage/storage/network/log charges, but this is an estimate, not a billing invoice or hard project cap. Idle min-zero Run services/jobs avoid idle compute charges; existing Neon Free has its own limits and no assumed production guarantee. See [costs and risks](hosting-costs-and-risks.md).

Effective Cloud Run service maximum is one, minimum defaults to zero, with CPU 1 / memory 1 GiB / concurrency 4 and request-based billing. The inherited revision annotation still says maximum 20, but the observed service-level cap of one governs the service. Synthetic catalogue, paid ingestion, assistant generation and production uploads are disabled; paid budget is zero.

Three provider/CLI issues were corrected operationally without changing the approved application image: duplicate `gcloud --args` values, Cloud Run's combined tag/service length limit, and Firebase's prohibition on public directories outside its project directory. Local runner regression fixes now serialize `--flag=value`, use a shorter routing tag independently of the image fingerprint, and copy the freshly built web output into `infra/deploy-dist`. Frontend retry did not rebuild Docker. These local tooling fixes are **not a new application deployment**.

Local verification after these fixes: **258 backend tests passed, one unapproved paid-live test skipped**; 23 focused release tests passed; repository-configured lint/format and deployment/collector plan validation passed. The first post-fix full-suite invocation used the repository root and failed to find Alembic configuration; the documented `apps/api` invocation passed. Fresh PostgreSQL 17/container checks and frontend/browser/contracts/build checks had already passed for the exact deployed commit; no unnecessary second cloud image build was performed.

## Remaining gates and rollback

All four drafts require substantive independent/human review. LEAN financial currentness, PMS rates and missing amendments must be reconciled; deterministic citation validation is not independent semantic verification. Bulk corpus interpretation/OCR reconciliation remains Agent 1's separate work. A generic Explore All empty caption still suggests keywords despite the accurate zero-publication banner; default personalized Discover correctly explains the coverage gap. These are not claims of a completed verified catalogue.

Rollback targets remain API **`opportunity-api-00002-mxw`** and Hosting **`sites/unclaimed-ai-cup/versions/cd9f1efd5fcb22d6`**. They were preserved; no rollback was needed for health/privacy checks. Rollback would not downgrade the additive schema or delete imported evidence/profile data. Sanitized stage receipts are retained locally under ignored `.live-validation/production-release`; identity/credential data must not be uploaded as artifacts.
