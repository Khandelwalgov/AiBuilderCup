# Public government document corpus — phase 1

This is an acquisition archive, separate from published opportunities, user documents,
AI extraction, and the existing DEPwD drafts. The job imports none of the application
services or model providers and never connects to the product PostgreSQL database.
No cloud resources are provisioned.

## Repeatable commands

From the repository root, using the existing API environment:

```sh
make corpus-collect CORPUS_ARGS='--dry-run'
make corpus-collect CORPUS_ARGS='--max-documents 160 --max-requests 500 --max-total-mib 400'
make corpus-update CORPUS_ARGS='--source msme-ramp'
make corpus-collect CORPUS_ARGS='--resume RUN_UUID'
make corpus-verify
make corpus-report
```

`UV_CACHE_DIR=/tmp/unclaimed-uv-cache` was necessary in the Codex filesystem sandbox.
`--root /absolute/path` changes the archive location. `--source` can be repeated.
Dry-run prints the configuration without network, file or ledger writes. Collect and
update both discover current candidates and fetch bounded documents; update is an
explicit operational name, not a separate versioning algorithm. They both preserve
prior runs. Resume uses the interrupted run's **original** source configuration and
remaining cumulative budgets, resets its interrupted working task, and skips completed
tasks. A budget-exhausted run cannot gain budget by resuming; start a new bounded update.

## Components and boundaries

- `schemas.py`: Pydantic registry, candidate and manifest contracts; generated public
  JSON Schema in `data/corpus/manifest.schema.json`.
- `network.py`: HTTPS allowlist and issuing-authority CDN path scopes, manual redirect
  validation, robots decisions, streaming byte limits, host pacing, bounded retries.
- `discovery.py`: static HTML/PDF indexes, direct public PDFs, JSON/RSS/Atom feed parsing,
  optional Playwright discovery and actual-byte validation. Remote content is never
  executed as Python, interpreted as instructions, or sent to a paid model.
- `store.py`: SQLite acquisition ledger, immutable content-addressed binary archive,
  transactional task checkpoints, immutable URL snapshot history and JSONL exports.
- `cli.py`: source selection, single-writer process lock, bounded discovery followed by
  round-robin document acquisition, integrity verification, run reports and CLI.

SQLite is a **local job checkpoint and export ledger**, not a replacement product database.
It avoids requiring credentials or changing live data for this acquisition phase.
The versioned manifest is the downstream integration boundary. SQLite table creation is
local only; no product schema or API changes are introduced, so no Alembic migration or
frontend API regeneration is required for this change.

## Access controls and budgets

Only source-controlled registry URLs/hosts are accepted. Paths on shared government
CDNs need explicit issuing-authority prefixes. Redirect targets are checked before
fetching and get their own robots check. No credentials, cookies, proxy evasion, TLS
relaxation, CAPTCHA solving or login automation are used. A 404 robots response is
recorded as `not_present`; HTML masquerading as robots, robots redirects, blocked robots,
TLS errors and ambiguous access fail closed. This conservative robots-redirect policy
can exclude otherwise public sources; manual registry review is the intended resolution.

The registered access policy is a human/code-reviewed precondition. `needs_review` and
`manual_access_required` sources generate diagnostic records with **zero collector
requests**. Review policies again before enabling a source or scheduling this job.
Some government sites require reproduction permission even when robots permits crawling.
The report distinguishes source access probes from actual collector requests.

Execution is sequential (concurrency one). Defaults: 200 successful document fetches,
1,200 HTTP requests, 20 MiB per response, 600 MiB decoded response bytes, one second
between host requests, depth at most 3, at most 30 listing pages and 100 candidate
URLs per source. Registered sources have smaller budgets. Robots crawl delays and
request-rate intervals can increase host pacing. Timeouts are 15s connect / 30s read.
Transient 500/502/503/504 and timeouts get at most three attempts with backoff; an explicit
Retry-After defers that host. 429 stops the host for the remainder of the run and stores
Retry-After without sleeping past it or trying another access path. Request and decoded
byte budgets include robots, listing pages, retries and downloads, and survive resumption.
A single read chunk can cross the byte limit by at most 64 KiB before stopping.

Playwright is optional and **not installed or enabled in the live registry**. When enabled
for a reviewed JavaScript-only source, every GET goes through the same HTTP fetcher and
robots/budget checks. Non-GET requests, service workers, websockets and media are blocked.
This intentionally cannot handle every portal. A challenge remains a manual-access result.
No public feed endpoint was assumed or reverse-engineered from private APIs.

## Archive and provenance

Default: `/Users/govind/Projects/AIBuildersCup/.corpus` (Git-ignored).

```text
.corpus/
  ledger.sqlite3              # authoritative transactional job state
  collector.lock              # prevents two local writers
  blobs/ab/<sha256>.pdf        # original server bytes, content addressed
  blobs/ab/<sha256>.html       # original HTML, when a configured document candidate
  manifest.jsonl              # immutable snapshots, JSON Schema v1
  events.jsonl                # each listing/document outcome with run/source identity
  sources.jsonl               # source registry records and stable IDs
  discoveries.jsonl           # all discovered associations, including over-budget candidates
  runs.jsonl                  # run configurations, cumulative requests/bytes and status
  reports/<run-uuid>.json     # per-source metrics and failures
```

A snapshot includes canonical/origin/final URL, UUID document/snapshot/previous-snapshot
identity, format, bytes, SHA-256, original blob pointer, capture time, HTTP status,
ETag/Last-Modified/Date/Content-Type/redirects/robots metadata and validation outcome.
`discoveries` retain title, index URL, source UUID/key, issuing-authority registry value,
category, jurisdiction, null-or-explicit publication/effective/close dates, and related
references. Authority provenance explicitly identifies the reviewed index owner; document
signatories and subordinate district issuers require later document review. No legal
eligibility, currency or publication approval is implied by capture or structural validation.

Raw binaries, live checkpoints, probe HTML, logs and run reports stay out of Git. A public
manifest and compact acquisition summary are versioned in `data/corpus` after verification.
Source configs, schemas, tests, code and reports are versioned.

## Identity and change semantics

Canonicalization removes URL fragments and normalizes scheme/host; query parameters are
preserved because they can identify documents. Stable UUID5 source keys and URL document
identities keep discovery separate from content deduplication. Identical bytes across URLs
share one blob while retaining each URL's provenance. Files are installed atomically without
overwriting; SQLite records a snapshot and advances its URL's current pointer transactionally.
A crash can leave an unreferenced valid blob; historical artifacts are never silently deleted.

- `new`: a URL's first snapshot with previously unseen bytes.
- `duplicate`: a new URL sharing previously captured bytes.
- `unchanged`: current URL bytes match its current snapshot; no new snapshot.
- `updated`: same URL changed; new snapshot points to the preceding snapshot. Reversion to
  older bytes is another version, sharing the old blob.
- `duplicate_link`: URL already captured during this run, including another source's index;
  association retained without downloading twice.
- `amendment` / `possible_replacement`: candidate metadata from explicit feed fields or
  amendment wording in an index title. References from one index row are labeled unverified;
  similarity or a newer year never establishes replacement or supersession.
- `listing_unavailable`: HTTP 404/410 observation, not an official withdrawal decision.
- Other structured retrieval errors retain all prior snapshots. No absence or crawl failure
  deletes records or changes an opportunity's status.

Tender close dates are accepted only when explicitly supplied by a source adapter/feed.
Unknown dates remain null; an old filename or publication year is not an expiry date.
No application-open claims are made. Historical tenders are archival evidence, not live bids.

## Verification and PostgreSQL handoff

PDFs need PDF magic bytes and a successful pypdf structural parse of every page (unencrypted,
1–500 pages); claimed PDF URLs returning HTML are rejected. HTML needs meaningful text and
challenge screening. Validation does not prove legal authority, extraction accuracy, malware
safety or opportunity currency. The explicit verify command re-reads every referenced unique
blob, checks its exact size and SHA-256, and repeats format validation.

The downstream importer should map registry source identity to existing `Source`, a reviewed
manifest snapshot to `SourceSnapshot` (preserving binary pointer, hash, capture metadata and
separately extracted cited pages), and acquisition diagnostics to a separately authorized
`IngestionRun`. Existing actor IDs and review permissions must be supplied; UUIDs must be
mapped, not assumed to already exist in PostgreSQL. Then invoke the existing schema-validated
AI candidate extraction and human review pipeline explicitly. Do not publish automatically.

A future Cloud Run Job can use the existing Python image and this CLI, but must persist
checkpoint/export state and blobs to durable storage, implement distributed locking, handle
SIGTERM cleanly, and review each source's terms/pacing before Cloud Scheduler is enabled.
The current local flock and SQLite archive alone are **not** durable cloud deployment support.

Incremental listing responses are also saved immutably under `indexes/<sha256>.raw`
and referenced with HTTP metadata/hash/size by listing events. These are discovery
evidence and are excluded from document counts. The initial acquisition predates this
additional index-archive check; its candidate associations and listing outcomes remain
in the ledger. A document absent from a later successfully parsed index generates
`not_seen_in_listing_needs_review`, never automatic withdrawal or deletion. Explicit
close dates produce `deadline_state_at_capture`; unknown closes remain `unknown`.
RSS/Atom XML rejects DTD/entity declarations and uses bounded standard XML parsing.
CAPTCHA/challenge responses pause the host for the rest of that run.

`make corpus-update CORPUS_ARGS='--discovery-only --source rajasthan-welfare'`
archives reviewed indexes and reconciles candidate metadata without fetching document
bytes. Legacy layout tables are excluded from document-row titles and amendment
associations. Manifest associations retain discovery run/timestamp and are ordered
newest first, so corrected index metadata does not erase historical discoveries.
