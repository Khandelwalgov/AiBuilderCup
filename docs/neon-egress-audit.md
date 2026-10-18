# Neon transfer audit — local inspection only

18 October 2026. The operator reports 5.42 GB monthly transfer, the monthly limit reached and Neon project `unclaimed` paused; storage approximately 0.08 GB and compute 2.12 CU-hours. These are operator-supplied console readings, not independently queried billing metrics.

**Production availability is uncertain.** Earlier hosted acceptance does not establish current database availability. This pass made no production API or Neon requests, imports, migrations, index rebuilds or credential changes. No service upgrade or quota workaround was attempted.

## Findings

| Priority | Evidence in current source | Minimal recommendation |
|---|---|---|
| High | `ingestion/corpus_policy/library.py:169`, `catalogue_entries`, executes `base_query()` for every snapshot before filtering/pagination. ORM selection includes full `SourceSnapshot.pages` and metadata. | Separate card metadata from page bodies; push applicable filtering/pagination into SQL without changing catalogue metrics or source evidence. Profile locally before changing semantics. |
| High | `library.py:288`, `detail`, fetches the requested snapshot, then calls the same all-snapshot `catalogue_entries` to find one card. One reader request therefore loads unrelated source page blobs. | Add a snapshot-scoped metadata path for detail, limiting statuses/relations to that snapshot; preserve page/hash/citation behavior. Add a local query/materialization regression with a large unrelated snapshot. |
| Medium | `catalogue_entries` loads full `IngestionRun` rows including diagnostics to obtain snapshot/status, plus every public `ResearchListing.payload` to compute source relations. | Project only snapshot/status fields; constrain related-listing reads or use a minimal source-link projection. Avoid new tables/migrations for this first fix. |
| Medium | `research/conditions.py:64`, `compare`, calls `session.get(SourceSnapshot, ...)` inside each mapped condition. | Measure SQL counts locally and reuse one request-scoped snapshot/page map across comparisons. Do not assume ORM identity caching retains every object, and do not remove exact evidence validation. |
| Medium | Research guidance/facets select full public listing payloads. Discover/plan/scenario endpoints can each repeat evidence evaluation. | Measure and project only necessary columns or reuse request-scoped results. Continue evaluating all applicable programmes for an empty query; do not trade recall for lower transfer. |
| Lower / unproven | React Query default retries once and has 30-second stale time (`apps/web/src/main.tsx`). Guidance, Plan and subject context override stale time to zero; focus/mount can refetch. No `refetchInterval` was found in frontend source. | Measure mount/focus requests locally; consider conservative freshness and focus settings only if redundant requests are demonstrated. No evidence of a continuous polling loop was found. |
| Operational | Previous acceptance traversed many document details and citations. Each request through the all-snapshot reader can amplify traffic. | Keep future checks sampled and bounded; reuse one captured response per immutable document where suitable. Do not rerun production acceptance while paused. |

## Local size measurement

Serialized only `packet.pages` from **125 existing local archive-text packets** using UTF-8 JSON (`ensure_ascii=False`): **2,030,616 bytes total**; largest document **267,039 bytes**. One thousand reads of that entire local pages set represent approximately **1.89 GiB** before metadata and protocol overhead.

This is an illustrative code-path size estimate, **not measured Neon wire transfer**, and the 125 local packets are not all 129 production captures. JSONB/TOAST, compression, result encoding, relation/diagnostic sizes, API usage and observation periods differ. The findings establish avoidable over-fetching, not the precise attribution of 5.42 GB. A large API response and database egress are also different quantities.

No model rebuild/download, source discovery or OCR was performed. No application code was changed during this audit. Prioritize the single-document reader fix after authorization for that focused engineering/release scope; it will reduce future traffic but cannot restore a project already paused for an exhausted allowance.

## Next operator decision

Use Neon's official console/support information to establish when the allowance resets and what recovery options are available for this project. No paid change is authorized. Until recovery is confirmed, record any demonstration from an explicitly local environment using fictional profiles and preserved official sources; label it accurately. Do not present past acceptance as current hosted health.
