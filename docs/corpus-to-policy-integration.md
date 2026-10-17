# Corpus-to-policy integration

## Bulk processing checkpoint — 17 October 2026

**The bulk interpretation task is not complete.** This checkpoint completes local text/OCR processing and portable source handoff for the initial corpus; it does not claim complete policy extraction, independent semantic verification, current opportunity availability or publication. All remaining work is explicitly queued. The original acquisition manifest, original bytes, existing snapshots, DEPwD drafts and review history remain unchanged.

Work is isolated on `codex/corpus-completion` at `/Users/govind/.codex/worktrees/corpus-completion/AIBuildersCup`. Agent 2 owns production release, GCS staging and database mutations. No deployment, retrieval, Scenario Studio or frontend files were edited here. No paid external inference request was made.

### Measured initial-corpus results

| Measure | Initial corpus |
|---|---:|
| Unique documents / immutable URL-snapshot records | 120 / 125 |
| Original bytes | 193,031,267 |
| Hash-validated documents with page/section artifacts | 120 |
| Fully processed through complete policy interpretation | **0** |
| Documents with every required OCR page checkpointed | 95 |
| Documents still missing required OCR checkpoints | 0 |
| Documents with low-confidence or empty OCR pages | 13 |
| OCR checkpoint files / unique content-hash-page pairs | 665 / 643 |
| Structured component drafts / original-citation-valid drafts | 7 / 7 |
| Deterministic-valid drafts / blocked drafts | 3 / 4 |
| Focused same-session semantic critiques | 7 |
| Completed full independent semantic reviews | **0** |
| Drafts with material review concerns / requiring human review | 7 / 7 |
| Confirmed currently actionable opportunities | **0** |
| Exact issuer/title uncertainty from original audit | 117 |
| Current availability unverified | 120 |
| Technically transportable source artifacts | 125 records / 120 content hashes |
| Existing importer eligible, after Citizen Charter exclusion | 124 records / 119 content hashes |

“Fully processed” includes complete interpretation and amendment/currentness reconciliation, not merely nonempty text, a classifier label, or a model agreeing with itself. Zero here is deliberate: the existing three MSME drafts and new scholarship drafts are partial, conservative interpretations. “OCR completed” means local OCR ran and its checkpoints passed integrity checks, not that all recognition is correct. The 13 quality cases include empty pages; they are not 13 proven unreadable policies.

The original detector flagged 94 documents and 640 pages. Codex inspection found an additional false negative: the three-page “Woman Welfare” PDF contained garbled Latin glyph fragments in place of Hindi. An explicit source-hash-bound quality override now requests OCR for those pages. Its recovered text identifies an institutional Expression of Interest for operating working-women residences, rather than a direct cash benefit for every working woman. Its OCR date is unreliable and has not become a current deadline.

There were 147 bounded initial OCR chunks. One stopped on an existing English-only checkpoint identity rather than overwriting it with Hindi/English output. A second bounded pass processed only the four missing pages. All 643 required unique source-content/page pairs are now checkpointed. Existing equivalent-content URL aliases retain their own source attribution; 665 physical checkpoint files include these aliases and previously selective passes.

### Classification and outstanding interpretations

Current deterministic triage, which remains subject to source interpretation:

| Class | Unique documents |
|---|---:|
| Policy or guideline | 19 |
| Application schedule or amendment | 32 |
| Procedure or FAQ | 12 |
| Institution compliance, hold/debar/blacklist or show-cause material | 18 |
| Tender notice | 20 |
| Document index | 5 |
| Administrative reference | 1 |
| Announcement or unclassified | 13 |

These are document counts, not opportunity counts. The five HTML documents are indexes; linked titles do not establish eligibility. The Citizen Charter stays archived and excluded by the existing importer. Institution lists are dependencies to reconcile, not new scholarships. Tender cancellation/correction relationships and deadline scopes remain pending; the task has not fabricated an expired-tender count. LEAN explicitly limits captured financial provisions to 31 March 2026. MSE-GIFT's older fresh-loan sanction cutoff does not prove the whole scheme discontinued. The IC bundle includes an amendment and an older financial-cycle baseline; filenames and capture dates cannot extend it.

### Candidate preparation and verification

The initial selection contains the existing TEAM, LEAN and PMS individual-trade-fair drafts. Four new PM-YASASVI component drafts cover pre-matric, post-matric, Top Class School and Top Class College education. They contain 46 cited applicant-facing conditions and exceptions, plus explicit unknown fields and clause dispositions. They do not conflate parental/guardian income, household income and family income, or the two-boy limit with the college two-sibling limit.

The school component says income **less than** the threshold. The existing typed engine supports inclusive comparisons, so that condition remains unknown. A new operator was not invented. The college source's institutional verification date is not a student application deadline. Tuition paid to institutions is distinguished from student living/books/computer support.

All four new drafts pass closed-schema and exact-original-page citation checks. Their first deterministic pass rejected overbroad whole-page-to-clause coverage mappings; one targeted repair changed those mappings to explicit completeness-review dispositions. The strict source readability check still rejects the bundle because page 66 has no substantive extracted text. The importer gate was not weakened to improve draft counts. These four drafts are quarantined outside the import selection, with both attempts and remaining findings retained.

Seven focused source-grounded critiques are stored in `processing/completion-v1/semantic-critique.*.json`. They record actual examined claims and evidence, including income definitions, strict comparisons, exceptions, recipient scope and dates. **They used this Codex session and are not independent-model or independent-context verification.** They do not claim full-document semantic completeness. The existing independent-review stage remains pending and publication still requires an authorized human.

Visual inspection of original PMS physical page 2 resolved the garbled space-rent table to 80% for general-category units and 100% for the specified categories on minimum stall size. That observation, image hash and suggested correction are retained separately. The original extracted quote was not silently rewritten and those rates were not promoted to executable rules.

### Targeted coverage supplement

All 23 registered groups were investigated using the existing registry, access notes, archived indexes and acquisition results. Four remain public acquisition groups; nineteen remain restricted, blocked or awaiting terms review. MyScheme, login/challenge sources and permission-restricted sources were not scraped.

Three substantive PDFs linked by the already archived Rajasthan scholarship/residential-school index were acquired using the existing robots-aware collector, capped at three documents, five requests, 40 MiB and one-second host delay. They are a **separate** immutable root at `/Users/govind/Projects/AIBuildersCup/.corpus/coverage-supplement-v1`:

- SC post-matric guidelines linked as March 2021.
- ST post-matric regulations applicable from 1 April 2022.
- Residential-school summary PDF.

This adds 3 unique PDFs and 4,366,911 original bytes, without modifying the initial 125-record manifest. Two supplemental documents required OCR; all required pages were checkpointed, with one document retaining low-confidence/empty content. One additional ST draft contains 19 cited conditions and exceptions and passes deterministic/original-citation validation. Its income definition combines parents' gross income, excludes other earning family members, exempts guardian-supported orphans and uses the previous financial year for salaried employees. Suggestive timetable dates remain distinct from actual State deadlines. It is unapproved, contains unknown typed conditions and awaits independent review and current amendment reconciliation.

The supplement selects a compatible one-segment candidate filename, preserving the original repair file unchanged. `handoff build --import-manifest` explicitly maps the compatible immutable selection to the importer-required `processing/import-manifest-v1.json` inside the bundle. Both source manifests and acquisition ledgers remain separate; no hidden merge or scope expansion occurs.

### Portable, immutable handoff

The new `corpus_policy.handoff` CLI builds deterministic exclusive-create archives. Each has `handoff.json`, a manifest, registry, read-only SQLite backup, public acquisition ledgers, exactly the manifest-referenced original blobs, page packets, OCR PNG/TXT/TSV/JSON, classifications, candidate versions, findings and an explicit import manifest. It excludes environment files, arbitrary local documents, neural-retrieval artifacts and unlisted directories. No 193 MB PDF set is committed to Git.

Verification rejects duplicate/noncanonical/traversal paths, symlinks, unsupported members, excessive member counts/sizes, inconsistent manifest/blob inventories and checksum mismatches. Restore validates every member before creating a **new** destination; it refuses merging or overwriting a collector directory, then rechecks source access, original byte hashes and sizes. Agent 2's importer independently revalidates candidates against fresh original extraction before writes. Byte-identical candidate aliases are deduplicated; conflicting same-focus candidates escalate.

| Bundle | Exact bytes | SHA-256 |
|---|---:|---|
| `.corpus/handoffs/initial-20261017-v1.tar.gz` | 814,747,164 | `94ca625c1d793284e2aabdfe65c5892ce682f2b82241fb88b5ad69e02099c423` |
| `.corpus/handoffs/rajasthan-supplement-20261017-v1.tar.gz` | 37,841,352 | `ecd001143e08c604e0b09e2ef6ac51e1c307a2b05ffcf07149f1cfd989ef9e7f` |

Absolute paths begin `/Users/govind/Projects/AIBuildersCup/`. Large size is primarily original PDFs and OCR page imagery, not a requirement to place those images inside the live metadata state. Agent 2 confirmed separate initial/supplemental state names and explicit reviewed record counts, using shared content-addressed private blob storage after release authorization.

Initial manifest SHA: `a8f235f1f3ade35bce34ef5324cafdf12f037c63186f55405708d64f9d23f02c`; registry SHA: `ac9f2c89030c2db03f6b9e54d8ec33a059190e05412eb09c3971ec426863f8a3`.

Supplement manifest SHA: `497bb7abefcbda640e4413035566d3c213caa2b6d4123bf1c54ecea4d3a79b14`; registry SHA: `f45d3da356f6a56a29cda8319a6ce44a80dd4fdc4c36d399d1e185dbdb77a07d`.

Prepared import entries use the coordinated `prepared-import-v1` contract: snapshot/source hash, exact allowlisted candidate path and file hash, stable focus, deterministic validation state and `digest({snapshot_id, source_hash, candidate_sha256, focus})`. The initial manifest selects **3**, the separate supplement selects **1**. This selection cannot assert human approval or publish anything. Other candidates remain in the bundle as quarantined diagnostics.

Read-only verification and portable restore (no model calls, no database writes):

```sh
cd /Users/govind/.codex/worktrees/corpus-completion/AIBuildersCup
export PYTHONPATH="$PWD/apps/api/src"
PYTHON=/Users/govind/Projects/AIBuildersCup/apps/api/.venv/bin/python
"$PYTHON" -m opportunity_platform.ingestion.corpus_policy.handoff verify \
  --bundle /Users/govind/Projects/AIBuildersCup/.corpus/handoffs/initial-20261017-v1.tar.gz
"$PYTHON" -m opportunity_platform.ingestion.corpus_policy.handoff restore \
  --bundle /Users/govind/Projects/AIBuildersCup/.corpus/handoffs/initial-20261017-v1.tar.gz \
  --destination /private/tmp/unclaimed-initial-new-restore
```

Use another new destination and the separate supplemental bundle for that scope. Checksum reports and fresh restore tests are available locally; Git contains only code, tests and sanitized counts. No GCS upload, production import or release was performed by Agent 1.

### Resuming processing without repeating completed OCR

Implementation additions:

- `ocr_batch.py`: plan-only default, 1–1,000 pages, 1–4 local workers, one targeted retry, source/page identity checks and durable per-page checkpoints.
- `ocr.py`: explicit local macOS font configuration fixes bundled Poppler build-host paths; existing checkpoints remain immutable.
- `completion.py`: per-record hash checks, original page boundaries, explicitly separate OCR derivatives, content-bound idempotency, source mentions/qualifiers and isolated failed-document reports. Damaged OCR affects its own source, not every document. Authority mentions are not automatically promoted to exact issuers.
- `import_inventory.py`: closed-schema/exact-citation/deterministic checks, component deduplication, quarantined findings and immutable import selection.
- `handoff.py`: portable bounded packaging, checksum/inventory validation and exclusive restore.

The all-corpus processing inventories use content-addressed filenames under `processing/completion-v1`; new derivatives create new checkpoints instead of replacing prior pages. The inventory identifies which source still needs interpretation. The original `SourceSnapshot.pages` and `archive-text-v1` parser contract remain unchanged.

```sh
"$PYTHON" -m opportunity_platform.ingestion.corpus_policy.ocr_batch \
  --corpus-root /Users/govind/Projects/AIBuildersCup/.corpus \
  --manifest data/corpus/acquired-manifest.jsonl --registry data/corpus/sources.json \
  --max-pages 64
```

This prints a plan. Executing local OCR additionally needs `--execute --tessdata-directory /private/tmp/unclaimed-ocr-data`. It never falls back to a hosted OCR or model service. The initial backlog plan now selects zero missing originally flagged pages; manually diagnosed false negatives are retained in the explicit quality override.

### Remaining work, not silently assigned to the user

The next interpretation queue is the 19 potential guideline documents, 32 schedule/amendment documents and relevant procedure/dependency material, rather than treating 120 documents as 120 application opportunities. The unresolved queue is for continuing source interpretation and targeted consequential decisions; it is not a request for the user to transcribe 120 documents. Important remaining cases include MSE-SPICE/GIFT/IC/ODR complete component logic, welfare operating-grant recipients, Mirasi/Bhishti scholarship conditions, institution restrictions and State-specific scholarship amendment chronology. OCR tables and unreliable dates must be reconciled with original imagery before becoming rules.

The strict readable-source gate, typed-rule limits, unknown states, independent-review requirements and human publication safeguards remain intact. No new human `CandidateReview`, published requirement, catalogue update, notification or profile evaluation was created by this checkpoint.

### Verification executed for this checkpoint

The final full backend run passed **259 tests, 3 skipped**, with six existing dependency/deprecation warnings. The focused corpus suite passed **78 tests** with the real archive enabled; **14** tests cover the new completion/handoff behavior. Backend Ruff lint and format checks passed (122 files). Tests cover hash/citation/schema validation, candidate aliases and conflicts, corrupted OCR isolation, immutable resume, traversal/noncanonical paths, checksum tampering, exclusive restore and one-retry escalation. Earlier full-run results below are historical.

Both real bundles were restored into fresh `/private/tmp` directories and candidate validation replayed there. Replay reproduced **7 citation-valid initial candidates, 3 deterministic-valid and 4 escalated**, plus **1 citation-valid and deterministic-valid supplemental candidate**. The compatible alias deduplicated without inventing a second opportunity. No original archive access is required after portable restore. Initial/supplemental roots and SQLite acquisition ledgers remain separate.

Local DEPwD rows were fingerprinted before and after the final tests in read-only PostgreSQL transactions: **2 sources, 2 drafts, 70 citations, 4 review records, 16 fingerprinted rows**, unchanged. SHA-256: `61d5ad62def2711559893a1f9b493bdc9565e58023fa498d03608c16107318ab`. No production database connection or mutation was made.

Commands actually executed included `corpus_policy.ocr`, `corpus_policy.ocr_batch`, `corpus_policy.completion`, `corpus_policy.import_inventory`, `corpus_policy.handoff build/restore`, the full `pytest -q` suite from `apps/api`, and backend `ruff check .` / `ruff format --check .`. All used the existing local virtual environment with the isolated worktree on `PYTHONPATH`. The future paid extraction command in the historical operator section was **not run**; its repair cap and worker/budget preflight settings have been corrected to the current interface.

## Historical Phase 2 baseline

The following sections record the earlier bounded integration and its original 94-document OCR triage. The checkpoint above supersedes its progress counts; earlier measurements are retained as history.

> 17 October follow-up: paid worker execution now additionally requires an explicit worker role, paid-worker permission, positive global/per-run budgets and reviewed provider/model price ceilings. Defaults remain zero. Interactive Codex packets can be staged without API calls; missing separate semantic review is escalated, never fabricated. Current evidence: [intelligence audit](unclaimed-intelligence-audit.md).

# Corpus-to-policy integration — phase 2

Verified 17 October 2026 (Asia/Kolkata). Work is isolated on `codex/corpus-policy-integration` in `/Users/govind/.codex/worktrees/corpus-policy/AIBuildersCup`. The shared checkout, deployment infrastructure, retrieval, Scenario Studio and frontend are unchanged. No paid model call, public-source fetch, publication, cloud operation or product-database import was performed. Database writes in verification used disposable PostgreSQL schemas only.

## Outcome and scope

The corpus can now enter an offline source/snapshot import, bounded text extraction, deterministic candidate validation, independent AI review, at most one feedback-driven repair, and a private draft or human escalation. Every outcome requires a human decision. The implementation reuses existing records and publication controls without modifying the existing ingestion/provider behavior or DEPwD drafts.

The quality audit read all archived records to establish counts. Candidate workflow tests use a small representative set and mocked models. There was no attempt to extract or publish all 120 documents. Only three unique documents currently pass the conservative automatic extraction gate; the other files remain preserved for triage, OCR/encoding remediation or scope/metadata review.

## Measured corpus quality

| Measure | Unique documents |
|---|---|
| Original content | 120 |
| Technically ingestible | 120 |
| Flagged for OCR or legacy-font/encoding review | 94 |
| Questionable or unresolved metadata | 117 |
| Suitable for bounded candidate extraction now | 3 |
| Title cleanup in the derived overlay | 103 |

The immutable acquisition manifest contains 125 URL/snapshot records over 120 distinct hashes (115 PDFs, five HTML snapshots). Counts above deduplicate by SHA-256. “Technically ingestible” means hash, size and official-source attribution checks passed and bounded page/section extraction completed; it does **not** mean readable legal text. The OCR/encoding flag is raised if any PDF page has insufficient text, replacement-character corruption or detected legacy-font encoding. Blank covers can trigger this conservative flag; font-aware conversion may suffice for some files. These are triage measurements, not manually certified OCR diagnoses or measured detector accuracy. No OCR was run.

117 unique documents lack an exact issuer recognized by the limited header detector. The source/index owner is retained separately and is never substituted for a document signatory or issuing department. These metadata flags overlap OCR and classification flags. Title cleanup is an auditable normalization, not a claim that a legal title has been verified. Raw titles and original acquisition history remain available.

### Provisional source-type classification

| Type | Unique documents |
|---|---|
| `policy_guideline` | 34 |
| `amendment` | 0 |
| `tender_notice` | 20 |
| `general_announcement` | 48 |
| `document_index` | 5 |
| `unclassified` | 12 |
| `irrelevant` | 1 |

These classifications are deterministic triage labels based on source/index titles and HTML content structure. Zero detected standalone amendments is not proof that the corpus contains no amendment effects. General announcements can contain binding changes and must not be treated as irrelevant or as complete policies. The irrelevant record is the Citizen Charter/navigation PDF; it remains archived and is skipped by the operator importer. All five archived HTML files are document/notice indexes, not substantive standalone eligibility policies. A manual spot-check caught an index with allowance/eligibility link titles; the gate now prevents those labels from becoming rules.

### Source diversity

| Source group | Unique content | Needs OCR/encoding review | Suitable now |
|---|---|---|---|
| `msme-ramp` | 7 | 4 | 3 |
| `rajasthan-scholarships` | 77 | 63 | 0 |
| `rajasthan-tenders` | 20 | 17 | 0 |
| `rajasthan-welfare` | 16 | 10 | 0 |

The three currently suitable documents are MSME TEAM operating guidelines, MSME Competitive (LEAN) guidelines and Procurement and Marketing Support guidelines. Source dates, issuer details and applicability still need human review. No open-round or current-benefit claim is inferred from their filenames, capture dates or years. Scholarship, welfare and tender acquisition files are supported by import and triage tests; their unreadable/incomplete cases escalate without a model call.

## Files and architecture

Implementation: `apps/api/src/opportunity_platform/ingestion/corpus_policy/`.

- `archive.py`: manifest/schema validation, official host/path and source-policy checks, byte/hash/size validation, PDF/HTML text extraction, source-type/title/issuer triage and material-clause inventory.
- `contracts.py`: strict candidate/coverage, review issue, independent review, stage trace and outcome contracts. AI output has no approval or publication field.
- `validation.py`: source checks described below; it uses the existing `CandidateData`, typed `Rule`/`Condition` and exact-evidence validator.
- `workflow.py`: fresh independent review and 0–1 feedback repair cycles, with explicit human outcomes and no provider fallback.
- `service.py`: administrator-only, append-only corpus namespace mapping into `Source`, `SourceSnapshot`, `IngestionRun` and private draft `OpportunityVersion` records.
- `live.py`: explicit future Gemini role clients with bounded tokens/timeout/retry behavior; never invoked by audit/import or these tests.
- `cli.py`: read-only audit/import plans by default; database writes require `--execute` and an existing administrator UID; live tests require additional explicit authorization.

No database schema, API contract, dependency, deployment or frontend change is needed. Existing JSON provenance/diagnostic columns hold the new typed workflow traces. No Alembic migration or generated frontend contract change was introduced.

## Original bytes, corrections and provenance

Original corpus: `/Users/govind/Projects/AIBuildersCup/.corpus`. The acquisition manifest `data/corpus/acquired-manifest.jsonl`, its schema and source registry are not edited. The importer resolves each blob strictly inside the archive’s `blobs/` directory, validates its exact byte length and SHA-256, and verifies canonical/final/discovery URLs against the enabled official registry. Non-public source entries, path escapes, mismatched domains and missing attribution fail closed. No document URL is fetched.

Derived corrections and per-document quality flags are versioned in `data/corpus/policy-quality-audit.json`. Generic “Scheme Guidelines PDF File” labels are replaced with recognizable source-page headings where available; legacy table row numbers, view/download labels and view-count/date trailers are removed. Missing titles and unresolved encodings remain flagged. The index publisher and exact document issuer are distinct fields. No authority, publication/effective date, deadline, amendment relationship or supersession is invented.

PDF citations retain physical one-based page numbers and the canonical original document URL. HTML citations use deterministic section ordinals in the existing integer page field, with the original heading, explicit `html_section_ordinal_not_pdf_page` provenance and section name in snapshot pages. HTML candidate drafts receive an explicit ordinal warning. Scripts, style, frames and form controls are removed from extracted text; whole ASP.NET forms are retained because they can wrap legitimate page content. Original HTML bytes remain unchanged and are not rendered/executed by this pipeline.

Extraction limits: 20 MiB/file, 500 PDF pages or HTML sections, two million text characters/document and 2,000 inventoried material source blocks. Over-limit text is refused, not silently truncated into an apparently complete policy. Source blocks have stable IDs based on URL, page/section, position and original text. The inventory uses normative-language heuristics and is not a proof that every legal condition was recognized. Entire extracted pages are also supplied to the independent reviewer.

## Import identities, duplicates and versions

The corpus uses a new fixed UUID namespace (`c1f1748a-246c-4e09-8cd1-180ba2816c67`), disjoint from existing DEPwD adapter IDs. Source identity follows the canonical document identity rather than a title. A source snapshot is identified by document identity + original byte hash. Identical bytes at different official URLs keep separate source/citation identities and a duplicate-content reference. Original acquisition snapshot and previous-snapshot IDs, HTTP metadata, archive blob pointer, origin domain, capture time, discoveries and quality flags are retained.

Import-run identity follows the acquisition snapshot occurrence + text-extractor version. Repeating an import reuses its records. Changed bytes create a new source snapshot. A→B→A reversion reuses A’s original immutable text snapshot but retains a distinct acquisition occurrence/run with the link to B. Existing snapshots, sources and runs are not overwritten. A conflicting text derivative for the same bytes is refused for human reconciliation. There is no inferred policy supersession.

Source check timestamps reflect the archived capture, not the import time. Offline import does not claim a fresh government check. PostgreSQL transaction-scoped advisory locks serialize imports for a document; callers own the transaction, and the service does not commit unrelated work. The CLI creates a fresh session and commits only its explicit bounded operation.

## Deterministic candidate validation

1. Validate the closed Pydantic schema and existing bounded rule language; unsupported operators/fields fail. Unknown conditions remain explicit `unknown` and require human review. Ambiguous legacy education keys are rejected.
2. Match every cited passage exactly after whitespace normalization to the supplied URL and page/section. Nonempty metadata fields and every required document need source evidence.
3. Check numerical rule values and numerical metadata claims against their own cited clauses, normalizing commas and explicit lakh/crore/thousand/million units. This does not establish that a number has been assigned to the correct legal concept.
4. Require explicit income definition, assessment period and subject context. Parental income is not inferred from generic family income; household income is not inferred from a parental-only clause. Unsupported periods/definitions escalate rather than being guessed.
5. Validate deadline date values, associated opening/closing language and date order. Publication/notice dates do not become application deadlines.
6. Account for every inventoried material block with a supported requirement/metadata citation or an explicit excluded/unrepresentable/review disposition. Invented clause IDs, nonexistent requirements and unsupported represented mappings fail. Exclusion is a human-review flag, not automatic completeness.
7. Standalone amendments need reviewed baseline/effect context and are escalated. Similar titles, newer years and acquisition hashes never authorize clause replacement.
8. Interpretive clauses, unknown rules, comparison inclusivity/direction and other consequential criteria carry human flags. No deterministic check is advertised as legal entailment or complete policy understanding.

These checks deliberately prefer false-positive triage to an unsupported consequential rule. Numeral presence alone cannot prove interpretation; dates, subject scope, logical all/any structure, exclusions and reference dependencies remain independent-AI and human review responsibilities.

## Independent review, repair and human escalation

Extraction produces a typed candidate plus clause-disposition mapping. Review is a fresh request using a separate role instance and system prompt, original source pages, clause inventory, candidate and exact hashes. It receives no extractor rationale, previous review history or approval authority. Independence here means separate context/request; shared-model errors remain possible.

Each review returns `assessment`, source/candidate hashes, all examined clause IDs and issues with code, severity (`info`/`warning`/`error`/`critical`), field, exact source evidence, suggested correction and a human-required flag. Hash mismatch, incomplete coverage, inconsistent assessment, fabricated evidence, missing consequential issue evidence or malformed review output forces escalation.

The workflow makes one initial extraction and permits at most one feedback repair. A valid candidate is independently re-reviewed after each repair. At most two extraction/repair role calls and two review role calls occur. Provider failures, invalid independent reviews, critical issues, unreadable sources and unresolved amendment context stop for a human. Remaining invalid candidates after the single repair are retained only as privileged unvalidated diagnostics.

Success means `draft_for_human_review`, not approval. Every outcome has `human_required=true`. Every saved draft has a mandatory completeness/consequential-criteria flag, `publication_state=draft`, `status=needs_review`, no published pointer and no executable published requirements. Administrative safety flags are added after the reviewed candidate; both the reviewed-stage hash and final stored-candidate hash are retained.

The AI stage never calls the existing approval service, creates a human `CandidateReview`, inserts published `Requirement` rows, re-evaluates user matches or changes the public catalogue. Existing administrator checks, exact citations, completeness confirmation and flag acknowledgment remain the publication boundary. A human escalation is visible through privileged ingestion-run diagnostics, including each attempted candidate, deterministic/AI issues and repair history.

## Verification and preservation

24 scoped tests passed with the real archive enabled. The complete backend suite passed **217 passed, 1 skipped**. Backend lint and format checks passed. Existing deprecation warnings remain. An additional Ruff invocation from the repository root reported eight pre-existing findings in infra/scripts under the root lint context; those out-of-scope files were left unchanged. The API-configured lint and format checks passed. There was no frontend test or deployment change.

Tests cover exact citations; unsupported schemas/rules; lakh conversion; invented amounts; income definitions/periods; publication-vs-deadline confusion; material-block coverage; reversed comparison caught by independent review; feedback-driven repairs; the one-cycle cap; critical/reviewer failure escalation; unknown-income preservation; source policy/path/hash/size failures; scanned PDFs; PDF pages and HTML sections; link-index rejection; substantive HTML support; disabled model client protection; administrator permissions; duplicate/version/reversion identities; immutable text conflict; persistence/idempotency; unchanged published catalogue queries; and representative real scholarship, welfare, MSME and tender files.

Real-archive tests use mocked responses, with unsupported source conditions deliberately represented as unknown. They verify technical integration and escalation, not AI extraction accuracy. The current scholarship/welfare/tender specimens escalate rather than forcing models to interpret unreadable text or link labels. MSME specimens exercise the private candidate workflow; synthetic source cases exercise semantic repair and rejection boundaries. Tests create/drop isolated random PostgreSQL schemas and do not truncate application tables.

Local DEPwD preservation was checked with PostgreSQL read-only transactions: **2 source records, 2 drafts, 70 extraction citations, 4 human review records**, plus associated snapshots/runs. All 16 fingerprinted records were identical before and after verification. Fingerprint: `61d5ad62def2711559893a1f9b493bdc9565e58023fa498d03608c16107318ab`. No DEPwD correction, review, publication or extraction was run.

### Commands actually executed

```sh
cd /Users/govind/.codex/worktrees/corpus-policy/AIBuildersCup
PYTHONPATH="$PWD/apps/api/src" /Users/govind/Projects/AIBuildersCup/apps/api/.venv/bin/python -m opportunity_platform.ingestion.corpus_policy.cli audit --corpus-root /Users/govind/Projects/AIBuildersCup/.corpus --output /tmp/corpus-policy-audit-release.json
PYTHONPATH="$PWD/apps/api/src" /Users/govind/Projects/AIBuildersCup/apps/api/.venv/bin/python -m opportunity_platform.ingestion.corpus_policy.cli import --corpus-root /Users/govind/Projects/AIBuildersCup/.corpus --limit 4
PYTHONPATH="$PWD/apps/api/src" CORPUS_ARCHIVE_ROOT=/Users/govind/Projects/AIBuildersCup/.corpus /Users/govind/Projects/AIBuildersCup/apps/api/.venv/bin/python -m pytest apps/api/tests/test_corpus_policy.py -q
cd apps/api
/Users/govind/Projects/AIBuildersCup/apps/api/.venv/bin/ruff check .
/Users/govind/Projects/AIBuildersCup/apps/api/.venv/bin/ruff format --check .
PYTHONPATH="$PWD/src" CORPUS_ARCHIVE_ROOT=/Users/govind/Projects/AIBuildersCup/.corpus /Users/govind/Projects/AIBuildersCup/apps/api/.venv/bin/python -m pytest -q
```

The existing runtime was reused with the worktree source first on `PYTHONPATH`; no dependency install was required. Audit/import plans are read-only by default. `--output` creates a new file exclusively and refuses overwriting an existing report. Without `CORPUS_ARCHIVE_ROOT`, four real-archive tests skip explicitly; the reported run enabled them.

## Bounded future live extraction command — provided, not executed

The following is for a separately and explicitly authorized operator test. It selects one exact archived MSME TEAM snapshot, one focus, explicit Gemini extractor/reviewer models, at most one repair, 20,000 input tokens and 8,192 output tokens per generation. It appends only private corpus records/drafts and cannot publish. An existing database administrator UID and configured Gemini key are required; keep keys in the existing secret configuration.

```sh
cd /Users/govind/.codex/worktrees/corpus-policy/AIBuildersCup/apps/api
PROCESS_ROLE=ingestion_worker PAID_AI_WORKER_ENABLED=true \
  AI_GLOBAL_BUDGET_USD="$CORPUS_GLOBAL_BUDGET_USD" \
  AI_RUN_BUDGET_USD="$CORPUS_RUN_BUDGET_USD" \
  AI_INGESTION_LIVE_ENABLED=true PYTHONPATH="$PWD/src" \
  /Users/govind/Projects/AIBuildersCup/apps/api/.venv/bin/python \
  -m opportunity_platform.ingestion.corpus_policy.cli live-test \
  --corpus-root /Users/govind/Projects/AIBuildersCup/.corpus \
  --snapshot-id 484fb5d6-115b-41e9-8827-e57ce380a874 --limit 1 \
  --provider gemini --model "$CORPUS_EXTRACTOR_MODEL" \
  --review-model "$CORPUS_REVIEW_MODEL" \
  --actor-uid "$CORPUS_ADMIN_UID" \
  --focus "MSME TEAM Initiative only: extract cited requirements and procedures; keep unsupported conditions unknown" \
  --max-repairs 1 --max-input-tokens 20000 --max-output-tokens 8192 \
  --execute --authorize-paid
```

Do not execute this as part of ordinary validation. Without `--execute` it is a read-only plan. Preflight rejects a disabled or unconfigured model before any database append. Execution additionally requires `--authorize-paid`, an explicit provider/model pair, one exact selected snapshot and the live-ingestion configuration flag. Multi-version document selections must resolve to one exact snapshot. SDK requests have a 60-second timeout, one attempt, no tools, no automatic function calls and no fallback. Input-token limits are checked before generation; oversized context escalates without truncation. At most four generation and four token-count requests are structurally possible, further restricted by durable run/day/month/spending reservations. These are token/request bounds, not a dollar-price guarantee; no live model behavior or cost was measured.

## Remaining work

- Review the 94 flagged PDF documents and choose OCR or font-aware remediation on a small, labeled sample. Improve detector evaluation before treating all flags as scan diagnoses.
- Resolve exact issuers and the 12 unclassified documents; manually assess announcements, dependencies, legal effective dates and referenced baselines.
- Add explicit, reviewed baseline/amendment bundle modeling before deriving operative consolidated policy rules. Current unresolved amendments intentionally escalate.
- Run one separately authorized live test and evaluate extraction/review quality on labeled source clauses. Shared-model agreement must not be reported as accuracy.
- Keep human publication decisions and existing privacy/permissions intact. No cloud, frontend, retrieval or Scenario Studio integration is included in this change.
