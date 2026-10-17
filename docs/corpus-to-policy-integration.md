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

The following is for a separately and explicitly authorized operator test. It selects one exact archived MSME TEAM snapshot, one focus, explicit Gemini extractor/reviewer models, at most two repairs, 20,000 input tokens and 8,192 output tokens per generation. It appends only private corpus records/drafts and cannot publish. An existing database administrator UID and configured Gemini key are required; keep keys in the existing secret configuration.

```sh
cd /Users/govind/.codex/worktrees/corpus-policy/AIBuildersCup/apps/api
AI_INGESTION_LIVE_ENABLED=true PYTHONPATH="$PWD/src" \
  /Users/govind/Projects/AIBuildersCup/apps/api/.venv/bin/python \
  -m opportunity_platform.ingestion.corpus_policy.cli live-test \
  --corpus-root /Users/govind/Projects/AIBuildersCup/.corpus \
  --snapshot-id 484fb5d6-115b-41e9-8827-e57ce380a874 --limit 1 \
  --provider gemini --model "$CORPUS_EXTRACTOR_MODEL" \
  --review-model "$CORPUS_REVIEW_MODEL" \
  --actor-uid "$CORPUS_ADMIN_UID" \
  --focus "MSME TEAM Initiative only: extract cited requirements and procedures; keep unsupported conditions unknown" \
  --max-repairs 2 --max-input-tokens 20000 --max-output-tokens 8192 \
  --execute --authorize-paid
```

Do not execute this as part of ordinary validation. Without `--execute` it is a read-only plan. Preflight rejects a disabled or unconfigured model before any database append. Execution additionally requires `--authorize-paid`, an explicit provider/model pair, one exact selected snapshot and the live-ingestion configuration flag. Multi-version document selections must resolve to one exact snapshot. SDK requests have a 60-second timeout, one attempt, no tools, no automatic function calls and no fallback. Input-token limits are checked before generation; oversized context escalates without truncation. At most four generation and four token-count requests are structurally possible, further restricted by durable run/day/month/spending reservations. These are token/request bounds, not a dollar-price guarantee; no live model behavior or cost was measured.

## Remaining work

- Review the 94 flagged PDF documents and choose OCR or font-aware remediation on a small, labeled sample. Improve detector evaluation before treating all flags as scan diagnoses.
- Resolve exact issuers and the 12 unclassified documents; manually assess announcements, dependencies, legal effective dates and referenced baselines.
- Add explicit, reviewed baseline/amendment bundle modeling before deriving operative consolidated policy rules. Current unresolved amendments intentionally escalate.
- Run one separately authorized live test and evaluate extraction/review quality on labeled source clauses. Shared-model agreement must not be reported as accuracy.
- Keep human publication decisions and existing privacy/permissions intact. No cloud, frontend, retrieval or Scenario Studio integration is included in this change.
