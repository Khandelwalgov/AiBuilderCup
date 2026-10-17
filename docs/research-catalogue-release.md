# Frozen research catalogue release

Prepared 17 October 2026. Scope is frozen at 98 programme/component/award/procurement identities; no further acquisition or OCR is part of this release.

The public tier is **Source-backed research — eligibility not verified**. It contains 27 education, 27 welfare, 23 business, 18 procurement and one healthcare listing. Availability is unknown for 69, continuation unestablished for seven, and historical for 20. No listing claims an open application round. Three notices have cited expired closing dates. Programme existence does not establish current funding, an application window or personal eligibility.

The automated pass checks closed Pydantic contracts, unique stable identities and titles/jurisdictions, official source domains, original snapshot identity/hash, page text hashes, exact quoted passages, OCR derivative/render fingerprints and cited deadline syntax. There are 800 field-level references across 45 captured source snapshots. This is evidence linkage and conservative curation, **not independent semantic verification**. Unresolved eligibility, rates, dates and later amendments remain explicitly unknown in the listing limitations. Five repeated-content acquisition aliases and a refreshed scholarship-directory version were already grouped upstream; none is an additional programme. Within the frozen 98: zero duplicate identities excluded, 96 valid listings, and two quarantined records (MSE-GIFT and MSE-SPICE) whose prepared OCR text differed from stored checkpoints. No additional OCR was attempted. The 124-document exclusion ledger explains which captured documents contribute, group into another programme or are irrelevant/insufficient; it is not 124 additional listings.

The read-only Neon preflight matched 44 existing snapshots; one previously captured Citizen Charter snapshot will be appended, preserving its original pages separately from OCR. Six existing eligibility versions, zero published policies and zero substantive review decisions were observed unchanged. TEAM/ST remain unpublished drafts. Research visibility does not publish a policy or create eligibility evaluations/neural embeddings.

Bundle: `data/research/catalogue-v1.json`

SHA-256: `3bcd07713a4f84fd4bc149fe2f3493f6c2ed3fa6b47636c5b0068baf6702066b`

## Approval scope

A fresh exact-commit production approval is required. Apply additive migration `f26c1000abcd`; grant only SELECT/INSERT/UPDATE on `research_listings` to the existing runtime role. Upload the single locally validated amd64 image, deploy/smoke a Cloud Run candidate, promote and deploy only `unclaimed-ai-cup` Hosting. Import the exact bundle as public research under the existing authorized administrator, repeat idempotently and read back payload hashes/counts. Append only the one existing public capture; preserve all eligibility drafts and review history. Verify public Discover with no query, categories, search, evidence detail and original official links. Roll back API/Hosting if acceptance fails; do not delete policy data or downgrade the additive schema.

No new infrastructure/IAM, scheduler, paid AI, opportunity approval/publication, remote Git push or additional build is included. Use existing zero-minimum, one-maximum Cloud Run settings and pinned secrets. Existing API/Hosting rollback targets must be checked immediately before execution. Production results are recorded separately after authorization; local tests are not live acceptance.

## Validation completed

31 focused backend/release tests passed; two mocked browser tests passed; backend lint/format, frontend lint/types/build, generated contracts, deployment plan, fresh PostgreSQL migrations and Alembic drift checks passed. One amd64 image was built and audited locally (non-root, no corpus/fixtures/secrets, runtime JSON present, local neural inference 384 dimensions). No new cloud mutation or paid inference was performed. The final 96-record Neon preflight matched 44 existing snapshots and 800 field references.

## Reproduce bounded checks

```sh
cd apps/api
uv run pytest tests/test_research_catalogue.py tests/test_release.py -q
uv run python -m opportunity_platform.research.importer ../../data/research/catalogue-v1.json --make-public
cd ../..
make contracts
pnpm --dir apps/web lint
pnpm --dir apps/web build
pnpm --dir apps/web exec playwright test tests/research-catalogue.spec.ts
python3 infra/deploy.py --config infra/deploy.example.json
# Disposable local PostgreSQL and the already-built image only:
python3 scripts/release_container_check.py
```

Browser tests mock the research HTTP responses using the real frozen bundle; backend import tests replay its records against isolated local PostgreSQL. Neon preflight is read-only. No live Firebase authentication, live publication or hosted research acceptance is claimed before release.
