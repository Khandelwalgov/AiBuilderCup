# Bounded document and catalogue quality pass — 17 October 2026

This application-only change uses existing public captures and completed local OCR. It changes no original snapshots, research payloads, eligibility versions, reviews, database schema or cloud infrastructure. No source collection, OCR, model rebuild or paid inference ran.

## Reconciled production data (read-only)

| Metric | Count | Meaning |
|---|---:|---|
| Capture records | 129 | Immutable product source snapshots, including repeated content under captured identities |
| Unique document hashes | 124 | Deduplicated captured binary/HTML content; the old admin count 123 excluded the Charter-origin capture |
| Unpublished eligibility versions | 6 | Versions across four opportunity identities; not six published programmes |
| Public research listings | 96 | Programme/component/award/procurement records; many-to-many with documents |
| Published eligibility policies | 0 | Research visibility never publishes a policy |
| Completed OCR | 100 document hashes / 672 pages | Existing checkpoints; 104 capture records refer to these hashes |

Both Government Sources and admin now use the same source domain and state computation. Filters match the actual displayed states, including NULL/absent old quality flags. Text availability is separate from eligibility review. Six versions across four opportunities remain pending; historical escalation-run counts are labelled as historical runs. The old “processing backlog” means documents without eligibility drafts, **not missing OCR**.

## The frozen 96

Identity types: **46 programmes, 27 components, five awards, 18 procurement notices**. Source strength: **41 substantive-document records, 25 Charter summaries, eight official overviews, four directory-name references, 18 procurement notices**. This is explicit display curation and evidence linkage, not independent legal or eligibility certification.

The main catalogue contains **74** records, with substantive standalone programmes first, then components/awards, overviews, Charter summaries and directory references. **22** are separately accessible in the archive: all 18 procurement notices (including those whose round is unknown) and four explicitly historical non-procurement records. Moving a notice into this browsing archive does not assert that its unknown deadline has passed. No new open/current claim is made.

| Content measure across all 96 | Count | Criterion and limit |
|---|---:|---|
| Substantive benefit/assistance description | 69 | Describes a concrete assistance type or purpose in summary/benefit; excludes tender notices, directory-only names and five generic corporation-channel descriptions. Not a verified current amount or promise. |
| Listing-specific official application route | 0 | No programme-specific application URL/process has been established as operative. |
| General official portal reference | 1 | One archived notice cites the general Rajasthan procurement portal; this is not counted as a specific application route. |
| Established current eligibility conditions | 0 | No complete, current, reviewed eligibility rule set is established for a research listing. Several documents contain conditions; this number does not claim their text is absent. TEAM/ST drafts and the existing review workflow are unchanged. |
| Verified current application window | 0 | No supported current open window. Unknown dates remain unknown. |

All **800 field-level citation references** across the 96 records were checked read-only against their exact source identity, source hash, source URL, page and integrated original/OCR text. Source-strength annotations are accepted only when the stored research payload hash matches the frozen audit. Missing/new/unmatched records fail to “unassessed” rather than inheriting a stronger classification.

## Documents users can actually read

Discover cards now include direct **Read captured document** links, exact page lists and quoted excerpts. The no-published-policy view shows these documents first; the eligibility explanation remains separate below. Research details retain original official links and full cited passages.

Government Sources opens the requested captured document above its result list and expands the cited page. Existing OCR is a separate source-hash-bound runtime overlay with acquisition ID, text hash, rendered-page hash and confidence. Original extracted text remains inspectable; database snapshots are never updated. Of 672 OCR pages, **634 pass the technical readability threshold, 32 need text-quality review, six are unreadable/near-empty**. These are technical heuristics, not semantic accuracy scores. The 129 source records divide into 116 with available text and 13 with some flagged pages; four document hashes contain unreadable pages. No automatic re-OCR is triggered.

Issuer transcriptions are supported by literal source passages for **88 document hashes**. **16** catalogue document labels are improved using captured headings/context; editorial labels do not claim to be an official English legal title. Unattributed documents remain unattributed.

## Validation and release boundary

Validation passed: **62 focused backend/source/release/intelligence tests**, four optional paths skipped; **two mocked browser tests**; generated contracts; backend lint/format; frontend lint/types/production build; deployment plan-only validation. A real local browser also opened Discover and followed a cited page into the completed OCR reader. No GitHub CI run or production acceptance is claimed for this new commit. The local browser preview uses 129 real public captures and the 96 listings in an isolated, disposable PostgreSQL schema; it does not create production data or claim live acceptance. The Neon audit is read-only. Local source hashes were rechecked for 123 originals (the remaining HTML refresh is already captured in Neon), along with all 672 completed OCR text/render checkpoints.

A fresh exact-commit approval is required for an **application-only** release: one necessary backend image build using cached pinned dependencies/model artifacts, candidate validation and Cloud Run promotion, and Unclaimed-only Hosting deployment. Schema verification only: no migrations, grants, Neon import/update, policy approval, new infrastructure/IAM, scheduler or Git push. Roll back API/Hosting if acceptance fails; original documents and data remain untouched.
