# Hybrid opportunity retrieval — Phase 4

`POST /v1/search` is authenticated, permission-scoped and read-only. `GET /v1/opportunities` remains the complete paginated Explore All browser; its text filter now combines PostgreSQL full-text matching with literal substring compatibility. Recommendations do not change published policies or store evaluations.

## Working channels

1. PostgreSQL generated `tsvector` on version title, summary, issuer and category, with GIN index. `websearch_to_tsquery` treats queries as data. English stemming works; Hindi lexemes can match literally. This is not cross-language semantic translation.
2. Structured subject applicability from reviewed requirement subject contexts; explicit category/jurisdiction filters; available typed fact-key overlap for ordering. No age, income, turnover or disability cutoff excludes a candidate. Missing facts retain candidates.
3. `NeuralRetriever` accepts public `PolicyRepresentation` (opportunity/version IDs, source hash, text, typed requirements) and request-scoped `SubjectRepresentation` (typed facts with their contexts, unknown-key mask, intent). The installed adapter reports unavailable and returns no candidates. No embedding model was executed, trained or called remotely. A cached multilingual MiniLM checkpoint exists, but Torch/tokenizers/transformers/sentence-transformers are absent from the API environment. Adding that runtime was not an efficient minimal change for this sprint. This is an adapter contract, not working neural similarity.
4. Coverage queues interleave category, state and typed requirement-key signature buckets. Stable opportunity UUIDs break ties. Coverage improves diversity but cannot guarantee recall under a finite budget.

Each subject gets independent coverage/text/structured/neural queues, merged and deduplicated. Round-robin allocation across subjects stops at `RETRIEVAL_SHORTLIST_SIZE` (default 150, bounds 50–500). This budget counts **subject–opportunity pairs**, not unique opportunities. Unused subject allocation flows to remaining subjects. Small catalogues fitting the budget are assessed completely. Larger catalogues disclose counts, subject/category coverage and truncation; Explore All remains available.

Candidate metadata/rules are batched from PostgreSQL. The baseline currently scans all published metadata and builds in-memory queues; it is suitable for the measured hundreds of policies, not demonstrated million-record scale. There is no ANN index or vector database. A future measured need can justify pgvector; adding it now would provide no embeddings to index.

## Exact assessment and ranking

The existing eligibility service now exposes pure `evaluate_requirements` and `overall_status` helpers; persisted checks, recommendations and scenarios use the same logic. Rule trees, evidence citations, application context, historical dates, exact monetary definitions, document verification and unknown semantics are retained.

Ranking is deterministic: known-failure bucket last, then text relevance, explicit category interest, satisfied condition count, reusable missing-action count, upcoming published closing date, UUID tie-break. Unknowns are never converted into failures or deducted as false facts. Documentary rules contribute through their exact verified-document outcomes; the ranking does not estimate document authenticity or award probability. Shared actions use the planner's scoped identities, preserving subject, income period/definition and date. No confidence percentages or inferred benefits are shown. Cards expose conditions and evaluator reasons; detail supplies the original citations. Different authorized people retain different assessments on the same opportunity.

## Permissions and five modes

| Mode | Actual behavior |
|---|---|
| Just Me | Resolves authenticated user's person; ignores a different selected workspace ID. |
| My Family | Resolves owned household and individually authorized active members, separately. Restricted adults contribute neither identities nor facts. |
| Specific Family Member | Explicit authorized person/dependent; revoked guardian access is rejected. |
| My Business | Authorized membership, actual business facts; personal income is never substituted for turnover. |
| Explore All | Complete public paginated catalogue, marked unassessed until an actual check; switching to Just Me is the explicit personalized view. |

The selector uses authorized workspace options. Recommendation links explicitly carry subject kind/ID; the existing context provider preserves these through Detail, Eligibility, Plan and Assistant and now retains the search mode too. The personal/me selector can use the current user's profile without a household. Family and business modes require a selected actual workspace.

Search/scenario HTTP responses use `private, no-store`. Routes roll back their read transaction, including the account resolver's harmless upsert. Profile facts are never copied into public indexes or logs. Firebase ID tokens and object-level resolution remain mandatory. At most 30 actual base subjects are supported; larger families receive an explicit request to choose a member.

## Version-aware index contract

Migration `f24a1000abcd` adds the rebuildable generated vector and GIN index. Serving always follows `Opportunity.published_version_id`, with version state `published` and status `verified`; a later draft cannot displace the reviewed version. The SQL vector exists on version rows, including drafts, but serving predicates prevent their retrieval. Only reviewed versions enter neural adapter policy representations. Rebuild SQL indexes with ordinary PostgreSQL REINDEX; generated vectors update automatically with version metadata. A future embedding artifact must key by version ID + source hash + model/version + representation version and invalidate superseded published pointers.

Raw corpus files/manifests remain entirely outside this pipeline. The separate collector must feed normal candidate extraction/review/publication before a policy enters retrieval. No collector changes, corpus reads, automatic review, ingestion, publication, model calls or deployment were performed by this Phase 4 implementation.

The actual persisted planner also uses the hybrid shortlist. It reports truncation and conservatively preserves old actions when candidate omission could explain their absence; omission cannot resolve a real task. Scenario planning never invokes that persistence path.
