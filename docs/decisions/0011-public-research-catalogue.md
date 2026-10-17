# Separate source-backed research catalogue

The 17 October 2026 content-first recovery instruction explicitly adds a public informational tier. This supersedes the previous product restriction that all Discover cards must be fully approved eligibility-policy versions. It does not change publication or evidence requirements for deterministic eligibility.

`research_listings` stores sanitized, hash-bound programme/component descriptions and cited original/OCR passages. Existing public `SourceSnapshot` identities remain immutable. Offline OCR is labelled as a derivative and carries text/render fingerprints; it is not independent verification. Unknown availability is explicit. Capture dates, index update dates and successful HTTP responses do not establish an open application round.

The public research API queries only this new table. It never queries private profiles or generates evaluations, readiness actions or benefit promises. Eligibility continues to query only genuine human-published `OpportunityVersion` records. TEAM/ST drafts stay unpublished; LEAN/PMS/SC disputes do not block unrelated research listings. A research listing cannot be passed to the eligibility endpoint as an approved opportunity.

Imports default to plan-only. A persisted administrator, exact approved bundle digest and explicit public visibility are required for the operator execution. Stable programme/component keys deduplicate source aliases and amendments. Same-bundle repeats are no-ops; changed content under an existing identity fails closed pending explicit revision review. Existing policy/source/history rows are not overwritten.

One additive migration and narrowly scoped application-role DML grants on the new table are needed. No new service, crawler, model, scheduler or authentication architecture is introduced. A fresh exact-commit production authorization is required before applying these changes or exposing the prepared listings.
