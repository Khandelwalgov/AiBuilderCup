# Corpus acquisition report

Completed 16 October 2026 (Asia/Kolkata). Acquisition only: no paid Gemini/OpenAI extraction, no opportunity publication, no existing DEPwD draft changes, and no cloud provisioning. Public originals are locally archived and remain unreviewed for legal rules, applicability and currency.

## Measured outcome

| Metric | Result |
|---|---|
| Registered official source groups discovered | 23 |
| Source groups attempted by collector | 4 |
| Source groups yielding validated documents | 4 |
| Successful document HTTP fetches (includes repeated unchanged fetches) | 129 |
| Distinct successfully captured canonical document URLs | 125 |
| Unique documents after SHA-256 deduplication | 120 |
| Unique PDFs | 115 |
| Unique HTML document snapshots | 5 |
| Central source groups with documents | 1 |
| State source groups with documents | 3 |
| Original document storage (bytes) | 193031267 |
| Total local archive storage incl. ledger, manifests, probes and logs (bytes) | 200456672 |
| Collector HTTP requests (robots/listings/retries/documents) | 162 |
| Collector decoded response bytes | 255656161 |
| New / duplicate-content / unchanged / updated fetches | 120 / 5 / 4 / 0 |
| Repeated URL links skipped within a run | 1 |
| Verified unique stored blobs | 120 |
| Stored hash/size/format verification errors | 0 |

The source count is the selected, versioned registry, not every government site on the internet. Additional access probes are listed in [source inventory](corpus-sources.md) but are not counted as successful acquisition or added to the catalogue. Document count means original bytes passing validation, not index links, PDF pages, opportunities, or currently open application rounds. Successful-source geography describes publisher coverage, not eligibility geography.

## Unique content by primary registry category

| Category | Unique content |
|---|---|
| msme | 7 |
| procurement | 20 |
| scholarships | 77 |
| welfare | 16 |

Categories are registry-level labels assigned to the first successful source association; they have not been AI-extracted or verified against every document. Other associations remain in the manifest. The corpus is concentrated in Rajasthan scholarship/welfare/tender records and central MSME documents. It does not establish comprehensive agriculture, rural development, employment, women/child, disability, national-scholarship or other-state coverage.

## Per-source and per-run results

| Source | Jurisdiction | Successful fetches | Unique source-associated hashes |
|---|---|---|
| msme-ramp | India | 16 | 7 |
| rajasthan-scholarships | Rajasthan | 77 | 77 |
| rajasthan-tenders | Rajasthan | 20 | 20 |
| rajasthan-welfare | Rajasthan | 16 | 16 |

| Run UUID | Status | HTTP requests | Decoded bytes |
|---|---|---|---|
| `28bd1611-01e9-46a6-a61f-c39de96d1392` | completed | 136 | 235214747 |
| `bde9df92-3f6b-4f3c-8052-0f48fb674a99` | completed | 22 | 19451063 |
| `8b5d0809-0c49-4a76-9df3-a0e18c0e2c4d` | completed | 4 | 990351 |

The initial run used at most 160 successful documents, 500 HTTP requests, 20 MiB per file and 400 MiB decoded response bytes, with one request at a time and at least one second between host requests. The incremental MSME run used at most 15 documents, 80 requests and 100 MiB. A third discovery-only run archived all three Rajasthan indexes and corrected layout-table titles without re-downloading originals. Its budget was 30 requests and 10 MiB. No official document change was fabricated to demonstrate updates: live new/unchanged outcomes are measured above, and changed-byte history/reversions were tested offline with explicitly synthetic bytes.

## Manual access, policy exclusions and failures

- **depwd — `needs_review`:** Copyright policy requires prior permission for reproduction. Existing DEPwD drafts are untouched.
- **nsp — `needs_review`:** Public static PDF links exist, but copyright policy requires prior reproduction permission.
- **myscheme — `manual_access_required`:** Terms of Use prohibit bots/scrapers without express written authorization. Do not crawl, including with Playwright.
- **maharashtra-welfare — `needs_review`:** Website policy requires reproduction permission by email before archiving.
- **gem — `needs_review`:** Public HTML links to bid portal exist. Conflicting hyperlink restrictions and reuse terms require review; no bid API or document download verified.
- **mission-shakti — `needs_review`:** Terms permit personal non-commercial download only; platform corpus reuse requires permission.
- **startup-india — `needs_review`:** Static PDF links found. Terms-of-use review pending; login-only documents must be skipped.
- **central-social-justice — `needs_review`:** Initial robots/TLS/HTTP probe unsuccessful or challenge/empty response. Acquisition disabled until both public access and terms are reviewed.
- **tribal-scholarships — `needs_review`:** Initial robots/TLS/HTTP probe unsuccessful or challenge/empty response. Acquisition disabled until both public access and terms are reviewed.
- **central-education — `needs_review`:** Initial robots/TLS/HTTP probe unsuccessful or challenge/empty response. Acquisition disabled until both public access and terms are reviewed.
- **central-msme — `needs_review`:** Initial robots/TLS/HTTP probe unsuccessful or challenge/empty response. Acquisition disabled until both public access and terms are reviewed.
- **central-skills — `needs_review`:** Initial robots/TLS/HTTP probe unsuccessful or challenge/empty response. Acquisition disabled until both public access and terms are reviewed.
- **central-rural — `needs_review`:** Initial robots/TLS/HTTP probe unsuccessful or challenge/empty response. Acquisition disabled until both public access and terms are reviewed.
- **central-agriculture — `needs_review`:** Initial robots/TLS/HTTP probe unsuccessful or challenge/empty response. Acquisition disabled until both public access and terms are reviewed.
- **cppp — `needs_review`:** Initial robots/TLS/HTTP probe unsuccessful or challenge/empty response. Acquisition disabled until both public access and terms are reviewed.
- **kerala-welfare — `needs_review`:** Initial robots/TLS/HTTP probe unsuccessful or challenge/empty response. Acquisition disabled until both public access and terms are reviewed.
- **delhi-women — `needs_review`:** Initial robots/TLS/HTTP probe unsuccessful or challenge/empty response. Acquisition disabled until both public access and terms are reviewed.
- **delhi-welfare — `needs_review`:** Initial robots/TLS/HTTP probe unsuccessful or challenge/empty response. Acquisition disabled until both public access and terms are reviewed.
- **gujarat-welfare — `needs_review`:** Initial robots/TLS/HTTP probe unsuccessful or challenge/empty response. Acquisition disabled until both public access and terms are reviewed.

Detailed portal access methods, exact authorities and policy links are in [corpus-sources.md](corpus-sources.md). Disabled groups generate review diagnostics without collector requests. Prior permission requirements were preserved; no permission email was sent. Robots/TLS/403/timeout/challenge observations are not discontinuation or withdrawal evidence.

Document retrieval/validation failures:

| Canonical URL | Code |
|---|---|
| https://sje.rajasthan.gov.in/siteadmin/Uploads/202107061215060698.pdf | `invalid_pdf` |
| https://sje.rajasthan.gov.in/siteadmin/Uploads/202107061604065219.pdf | `invalid_pdf` |
| https://sje.rajasthan.gov.in/siteadmin/Uploads/201910311530534583.pdf | `invalid_pdf` |
| https://sje.rajasthan.gov.in/siteadmin/Uploads/202406281842173360.pdf | `invalid_pdf` |
| https://sje.rajasthan.gov.in/siteadmin/Uploads/202312051026423401.pdf | `file_too_large` |
| https://sje.rajasthan.gov.in/siteadmin/Uploads/202112011514332641.pdf | `invalid_pdf` |
| https://sje.rajasthan.gov.in/siteadmin/Uploads/202111091706342893.pdf | `invalid_pdf` |
| https://sje.rajasthan.gov.in/siteadmin/Uploads/202110061548490675.pdf | `invalid_pdf` |
| https://sje.rajasthan.gov.in/siteadmin/Uploads/202109131121396009.pdf | `invalid_pdf` |
| https://sje.rajasthan.gov.in/siteadmin/Uploads/202107291733500519.pdf | `invalid_pdf` |
| https://sje.rajasthan.gov.in/siteadmin/Uploads/202106081212423738.pdf | `invalid_pdf` |

A PDF rejection means this collector’s strict structural validation failed; it does not establish that the government document is legally invalid. Oversized responses were stopped before storage. Rejected bytes are not counted as captured documents. All failures retain their original URL and structured event; prior successful snapshots remain intact.

## Archive, versioned manifests and known limitations

Exact local corpus: `/Users/govind/Projects/AIBuildersCup/.corpus`. Original files are under `blobs/<hash-prefix>/<sha256>.pdf` or `.html`; the transactional checkpoint is `ledger.sqlite3`. The public versioned manifest is `data/corpus/acquired-manifest.jsonl`; the contract is `data/corpus/manifest.schema.json` (version 1). `data/corpus/acquisition-summary.json` contains compact measured totals. Full live events/runs/discoveries and per-source reports remain under `.corpus/` and are Git-ignored.

Each snapshot retains the canonical/final/origin URL, SHA-256, exact bytes, download time, media/HTTP/redirect/robots metadata, prior snapshot identity, validation and every discovered index/source association. Publication/effective/close dates remain null unless the adapter has explicit evidence. Index publisher authority is captured with an explicit registry provenance basis; exact document issuers/signatories, central guidelines republished by states, and district-issued tender authorities still require document-level validation. This phase does not claim those details have been extracted or verified.

The initial run retained discovery metadata but predated immutable index-response archiving. Incremental listing responses are separately archived and hashed, excluded from document counts. Some candidates outside each source’s download cap remain in the discoveries ledger for later source-policy-reviewed expansion. No supersession is inferred from title similarity or year. Tender closure is unknown unless an explicit close date is captured; historical notices are not presented as currently open bids.

One initial navigation document (Citizen Charter) remains archived and is included in source-level counts; the registry now excludes it from new discoveries. Original HTML is passive archival evidence. Do not serve it as trusted active content. Structural PDF checks and hashing are not malware certification or verification of policy currency. No public JSON/RSS/Atom endpoint or live Playwright source was verified; those reusable adapters are covered offline and optional Playwright remains uninstalled.

## Actual commands and validation

```sh
UV_CACHE_DIR=/tmp/unclaimed-uv-cache make corpus-collect CORPUS_ARGS='--dry-run'
UV_CACHE_DIR=/tmp/unclaimed-uv-cache uv run --project apps/api python -m opportunity_platform.corpus.cli collect --max-documents 160 --max-requests 500 --max-total-mib 400
UV_CACHE_DIR=/tmp/unclaimed-uv-cache make corpus-update CORPUS_ARGS='--source msme-ramp --max-documents 15 --max-requests 80 --max-total-mib 100'
UV_CACHE_DIR=/tmp/unclaimed-uv-cache make corpus-update CORPUS_ARGS='--source rajasthan-scholarships --source rajasthan-welfare --source rajasthan-tenders --discovery-only --max-requests 30 --max-total-mib 10'
UV_CACHE_DIR=/tmp/unclaimed-uv-cache make corpus-verify
UV_CACHE_DIR=/tmp/unclaimed-uv-cache make corpus-report
UV_CACHE_DIR=/tmp/unclaimed-uv-cache uv run --project apps/api ruff check apps/api/src/opportunity_platform/corpus apps/api/tests/test_corpus.py
UV_CACHE_DIR=/tmp/unclaimed-uv-cache uv run --project apps/api ruff format --check apps/api/src/opportunity_platform/corpus apps/api/tests/test_corpus.py
UV_CACHE_DIR=/tmp/unclaimed-uv-cache uv run --project apps/api pytest apps/api/tests/test_corpus.py -q
cd apps/api && UV_CACHE_DIR=/tmp/unclaimed-uv-cache uv run pytest -q
pnpm --dir apps/web lint
pnpm --dir apps/web typecheck
pnpm --dir apps/web build
```

**Collector tests: 32 passed.** Coverage includes new/unchanged/changed/reverted snapshots, identical bytes at different URLs, duplicate links, broken links, redirects and redirect loops, invalid PDFs/HTML, oversized bytes, CAPTCHA host pause, robots denial, timeout retries, rate limits, interruption recovery, explicit expired tender metadata, amendment references, missing-index observations, RSS/Atom, XML entity rejection, official-host/CDN boundaries, immutable index evidence, discovery-only runs, legacy layout-table titles and actual stored-hash corruption detection. Synthetic test bytes do not enter the live corpus.

**Repository regressions: 191 passed, 1 skipped** on the latest recorded run; frontend lint, type checking and build passed (existing bundle-size warning). The first sandboxed backend attempt was prevented from connecting to localhost PostgreSQL. The first network-enabled attempt from the repository root passed 177 tests but the migration test requires `apps/api/alembic.ini`; rerunning from `apps/api` passed, including migrations. No product data was truncated; regression fixtures use isolated random schemas. No paid model call or browser end-to-end suite was run for acquisition.

## Next steps

1. Review relevance, exact issuing authority and document-level dates, and exclude unneeded boilerplate from extraction queues without deleting archival history.
2. Map source/snapshot UUIDs to existing PostgreSQL Source/SourceSnapshot records through an explicit authorized importer. Preserve the binary hash/pointer and acquisition metadata; extract page text with immutable page references.
3. Invoke schema-validated Gemini extraction only after explicit budget/provider selection; treat all documents as untrusted content and create private candidates.
4. Have authorized admins validate clauses, related amendments, dates and completeness before publication and deterministic profile re-evaluation.
5. Obtain source-specific permissions and verify access/terms before expanding disabled sources. Add reviewed agriculture/rural/women/skills and other-state sources to improve diversity.
6. Before Cloud Run Jobs/Scheduler deployment, add durable blob/checkpoint storage, distributed locking and job termination handling; no cloud deployment was performed here.
