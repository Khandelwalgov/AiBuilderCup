# Hybrid opportunity retrieval — Phase 4

`POST /v1/search` is authenticated, permission-scoped and read-only. `GET /v1/opportunities` remains the complete paginated Explore All browser; its text filter now combines PostgreSQL full-text matching with literal substring compatibility. Recommendations do not change published policies or store evaluations.

## Working channels

1. PostgreSQL generated `tsvector` on version title, summary, issuer and category, with GIN index. `websearch_to_tsquery` treats queries as data. English stemming works; Hindi lexemes can match literally. This is not cross-language semantic translation.
2. Structured subject applicability from reviewed requirement subject contexts; explicit category/jurisdiction filters; available typed fact-key overlap for ordering. No age, income, turnover or disability cutoff excludes a candidate. Missing facts retain candidates.
3. `NeuralRetriever` accepts public version/hash-keyed policy representations and transient permission-scoped subject representations. The production image now bundles checksum-pinned multilingual MiniLM ONNX weights and runs CPU inference. Public vectors are persisted in `policy_embeddings` by the explicit index job; missing vectors can be computed into a bounded public-only memory cache. Private query/profile vectors are not persisted. Exact cosine ranking is combined with FTS relevance; embeddings never decide eligibility. Missing local weights are reported as unavailable, with no hosted provider fallback. See [measured evidence and limitations](unclaimed-intelligence-audit.md).
4. Coverage queues interleave category, state and typed requirement-key signature buckets. Stable opportunity UUIDs break ties. Coverage improves diversity but cannot guarantee recall under a finite budget.

Each subject gets independent coverage/text/structured/neural queues, merged and deduplicated. For at most 150 filtered published versions, **all applicable pairs** across authorized subjects are assessed, even when their count exceeds the pair budget. Larger catalogues use the round-robin `RETRIEVAL_SHORTLIST_SIZE` pair cap (default 150, bounds 50–500), and disclose counts/coverage/truncation. Explore All remains available. Empty text is a normal personalized request, not a reason to return no candidates.

Candidate metadata/rules are batched from PostgreSQL. The implementation scans published metadata and uses bounded exact vector scoring; million-record scale and large-family production memory are unproven. No ANN/vector service or pgvector dependency is required for this catalogue.

## Exact assessment and ranking

The existing eligibility service now exposes pure `evaluate_requirements` and `overall_status` helpers; persisted checks, recommendations and scenarios use the same logic. Rule trees, evidence citations, application context, historical dates, exact monetary definitions, document verification and unknown semantics are retained.

Ranking is deterministic: passed application windows last, then known failures, combined FTS/reciprocal neural relevance, explicit category interest, satisfied condition count, reusable missing-action count, upcoming published closing date, UUID tie-break. Unknowns are never converted into failures or deducted as false facts. Documentary rules contribute through their exact verified-document outcomes; the ranking does not estimate document authenticity or award probability. Shared actions use the planner's scoped identities, preserving subject, income period/definition and date. No confidence percentages or inferred benefits are shown. Cards expose conditions and evaluator reasons; detail supplies the original citations. Different authorized people retain different assessments on the same opportunity.

## Permissions and five modes

| Mode | Actual behavior |
|---|---|
| Just Me | Resolves authenticated user's person; ignores a different selected workspace ID. |
| My Family | Resolves owned household and individually authorized active members, separately. Restricted adults contribute neither identities nor facts. |
| Specific Family Member | Explicit authorized person/dependent; revoked guardian access is rejected. |
| My Business | Authorized membership, actual business facts; personal income is never substituted for turnover. |
| Explore All | Explicit complete public paginated catalogue, unassessed until a check. Anonymous Discover defaults here; authenticated Discover defaults to Just Me. |

The selector uses authorized workspace options. Recommendation links explicitly carry subject kind/ID; the existing context provider preserves these through Detail, Eligibility, Plan and Assistant and now retains the search mode too. The personal/me selector can use the current user's profile without a household. Family and business modes require a selected actual workspace.

Search/scenario HTTP responses use `private, no-store`. Routes roll back their read transaction, including the account resolver's harmless upsert. Profile facts are never copied into public indexes or logs. Firebase ID tokens and object-level resolution remain mandatory. At most 30 actual base subjects are supported; larger families receive an explicit request to choose a member.

## Version-aware index contract

Migration `f24a1000abcd` adds the generated FTS vector/GIN index; additive `f25b1000abcd` adds version-aware public JSON embeddings and durable inference reservations. Serving always follows `Opportunity.published_version_id`, with version state `published` and status `verified`; a later draft cannot displace the reviewed version. The SQL vector exists on version rows, including drafts, but serving predicates prevent their retrieval. Only reviewed versions enter neural adapter policy representations. Rebuild SQL indexes with ordinary PostgreSQL REINDEX; generated vectors update automatically with version metadata. Current embedding records key by version ID + source hash + model/revision + representation/text hash, record generation time and invalidate changed published representations.

The corpus importer now stages actual public documents and prepared candidates into the existing source/snapshot/review model. Captured or machine-analyzed documents remain outside active opportunity retrieval until human publication. The earlier Phase 4 milestone made no corpus/model/deployment changes; the 17 October follow-up's actual work and production blockers are recorded separately in the intelligence audit.

The actual persisted planner also uses the hybrid shortlist. It reports truncation and conservatively preserves old actions when candidate omission could explain their absence; omission cannot resolve a real task. Scenario planning never invokes that persistence path.
