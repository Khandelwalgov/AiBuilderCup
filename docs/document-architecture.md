# Private documents — 16 October 2026

Local fictional-file upload, retrieval, replacement, removal and requirement linking are implemented. Production uploads remain blocked in configuration; parser validation is **not malware scanning**. No private file goes to an AI provider. There is no authenticity-verification process, official acceptance claim, OCR or document-number collection.

## Storage and migration

Alembic `e14a7d63f954` adds lifecycle metadata and versioned `DocumentRequirementLink` rows while preserving old records. Legacy file references become `legacy_unavailable`; the application never guesses how to expose historical blob paths. PostgreSQL holds ownership, label, type, size/hash, optional issuer/issue/expiry dates, timestamps, approved readiness uses and immutable requirement/version links. Files live behind the small `Storage.put/get/delete` interface; replacement creates a new object/record and retains history.

Local storage uses opaque random object IDs, a 0700 private root, 0600 files, exclusive temporary writes and atomic creation without overwrite. Reads reject symlink files and are bounded. Browser responses never contain filesystem paths or bucket keys. `.private-documents/` is ignored by Git and Docker. Keep the configured root private and under operator control. A GCS adapter uses service-account access, generation-match-zero creation, bounded reads and private/no-store objects. **No GCS bucket, IAM configuration or GCS round trip was tested or provisioned**; private IAM/bucket policy, encryption, retention and scanning require production acceptance.

## Request lifecycle

1. An authenticated caller creates a metadata intent for an authorized person, household or business. Closed schemas reject arbitrary verification fields. Display names are trimmed. At least one explicit readiness-use consent is required.
2. Binary PUT preauthorizes the subject before reading; it enforces Content-Type and bounded stream length, then validates actual PDF/JPEG/PNG structure. Default limits: 5 MiB/file, 25 active/pending files per uploading account, 50 MiB total. PDF encryption/basic active-content markers and more than 100 pages are rejected; images are decoded and limited to 20 megapixels. These limits do not replace isolated malware scanning.
3. Persisted SHA-256/size are checked on retrieval. A matching repeat PUT is idempotent. A different file needs Replace. Failed writes retain the intent so retry/reselection does not create another metadata row. Interrupted refresh cannot retain browser file bytes and requires choosing the file again.
4. Preview/download requests obtain a 60-second HMAC token bound to Firebase UID, document, hash and purpose. Content requires **both** Firebase Authorization and `X-Document-Access`, with subject permission checked again. Tokens never appear in URLs. A development process generates a random signing key if unset; restarting invalidates access grants. A future multi-instance production configuration needs a managed shared signing secret.
5. Responses use no-store/nosniff/no-referrer and safe disposition/CSP headers. The UI fetches an authorized blob for preview/download and revokes object URLs on close, account/context switch and unmount. The account-scoped client rejects responses after the Firebase UID changes. No private file content is persisted in browser local storage.
6. Replacement authorizes the same subject, links compatible current requirements, commits the new file and disables the old one, then purges old bytes. Replacement works at quota capacity. Removal immediately revokes access, clears descriptive metadata/uses, retains a minimal tombstone and purges bytes. Purge failures are explicit `purge_pending` and retryable; they continue counting against quota. Removal does not delete historical policy/evaluation records. It is not full account erasure or export.

Audit events record sensitive listing, metadata access, grants, content retrieval and mutations without document content, labels, credentials or raw storage locations. Access logs omit query strings and payloads. There are no public bucket URLs/listing endpoints. A file already downloaded by an authorized user cannot be remotely recalled.

## Ownership and documentary meaning

Every operation resolves server-side subject access. A guardian's own person is distinct from a managed dependent; adults require consent, and business viewing/editing follows membership roles. UUID guessing returns a generic unavailable response. Revocation is rechecked even for an otherwise valid access token. Tests cover unrelated account/dependent, nonconsenting adult, business viewer read/write limits, removed membership and revoked guardian access.

Statuses distinguish pending upload, uploaded/unverified, expired, replaced, deleted and legacy unavailable. “Not provided” belongs to a requirement, not an invented file. Verified/rejected/awaiting-authoritative-review statuses are not exposed as user-settable choices because no such review process exists. All successful files truthfully say **Uploaded — not verified**.

A link records exact published requirement/version plus deterministic compatibility. Reuse requires matching type, income definition/period, as-of date and any captured policy scope/format/issuer constraints. Ambiguous income scope remains requirement-specific. Filename or hash similarity grants no reuse or cross-subject access. Existing links to older publications remain history; they do not satisfy new-version documentary readiness automatically. Expired files cannot be newly linked.

The profile, Family, Businesses, Opportunity Detail, evaluation, checklist, graph and Settings lead to the same authorized vault. Two compatible fictional scholarships reuse one explicitly selected file. Documentary labels update dynamically; deterministic legal results and historical fact snapshots remain unchanged. Uploading alone never creates a verified `ProfileFact` or turns an unknown document condition into satisfied.

## Local operation / production gate

Set `DOCUMENT_UPLOADS_ENABLED=true` only with `ENVIRONMENT=development`, local private storage and fictional fixtures. Restart the API after `.env` changes. Defaults/examples stay false. The existing ignored local API environment was enabled for fictional testing; credentials/provider settings were untouched. Production configuration rejects uploads=true and rejects Firebase emulator settings outright.

Before real sensitive uploads: provide isolated malware scanning/quarantine and safe parser workers; verify private GCS/IAM, managed keys, transport/CORS, rate/resource limits and retention/backups; define document verification, consent/revocation/export/account deletion; conduct security and privacy review. No deployment or automatic gate bypass is included.
