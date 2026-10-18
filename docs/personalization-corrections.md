# Focused personalization corrections — 18 October 2026

Local implementation only, based on `4fcc9e0c3175472a55588e32ad2a258549ec2b54`. No production requests, deployments, data imports, source collection, model calls or reservation-counter changes.

## Before and after

- **Research ranking:** Previously, having any mapped conditions sorted ahead of unmapped research, before considering a known mismatch. Now every filtered programme–subject pair is classified by deterministic condition results: some conditions met with no known mismatch; information gaps/unmapped research; known mismatches. The groups dominate semantic/lexical scores and geography. Age 22 versus the cited pension minimum of 60 is demoted, while an unknown age remains unknown. All unsatisfied mapped conditions, including potentially actionable gaps, are conservatively placed in the mismatch group; the evidence and legitimate preparation actions remain accessible.
- **Pagination:** Grouping and sorting happen server-side over the full applicable research set, then the page is sliced. Group totals and scenario totals use that full filtered set. Deterministic source-row/component selection and a final listing-ID tie-breaker preserve stable ordering. Known mismatches are collapsed on the page where they appear, and pagination remains available. Overview stays a preview linking to Discover; scenario/plan research can now be paginated too.
- **Scenario counts:** Reviewed-policy changes remain sourced from `/v1/scenarios/evaluate`. A separate `research_changes` summary from guidance counts distinct mapped source conditions per programme and authorized subject, before pagination. It reports changed/unchanged conditions, subsets now matching supplied facts or now mismatching, mapped conditions still unknown, and changed programme–subject pairs. Repeated identical mappings within a pair count once; separate family members remain separate comparisons. These are provisional research comparisons, never approved eligibility assessments.
- **Empty reviewed state:** Empty reviewed-policy changes show an explicit message rather than four misleading zero counters. Empty action/evaluation graphs are not drawn. The previous graph `100%` was a zoom value, not completion; it is now labelled “Zoom” when a graph exists. Nothing claims 100% readiness.
- **Compact cards:** Titles, short source-condition reasons, benefits, key unknowns and one prominent detail action remain visible. Full comparisons, quotations, document/page links and application information remain expandable. Known mismatches stay accessible in a collapsed group. Empty quotation blocks are hidden without supplying replacement evidence.
- **Filters and overrides:** Government Sources has full-width search, three primary filters, collapsible advanced filters and a reset action; desktop/mobile widths are tested. Scenario overrides are compact, with income period/definition inside an expandable section. Graph legends say Person, Household members or Business and provide a focusable explanatory info label/tooltip.

## Neural participation, precisely

**Historical scope of this correction commit:** the description below applies before the subsequent [profile-driven neural discovery change](profile-neural-discovery.md). That change adds request-scoped profile inference to empty-query research without weakening these relevance groups.

`research/search.py:rank` returns `{}`, `not_requested` for an empty query. Therefore the current automatic **research** recommendations do not perform neural retrieval: guidance evaluates the applicable public catalogue and its available cited mappings. Entered research queries retain lexical/neural retrieval and lexical fallback; neither score can outrank a proven mismatch.

The separate reviewed-policy retrieval path can use profile-context neural candidates even without a typed query; its small-catalogue path exhaustively assesses applicable published policies (up to 150 versions). This does not establish neural participation in the current research recommendations or imply any approved policies exist. No model/retriever behavior was changed.

## Database transfer evidence and boundary

The existing [local Neon audit](neon-egress-audit.md) identifies full `SourceSnapshot` page loading in Government Sources browse/detail, full ingestion diagnostics and listing payload retrieval, and per-condition snapshot lookups in research comparisons. Additionally, `planning/service.py:research_actions` calls full `guidance` repeatedly while paginating at 24 records, amplifying those reads within one plan/scenario request. Local packet page JSON totals 2,030,616 bytes across 125 packets; that is not measured Neon wire transfer or a proven attribution of its exhausted allowance.

This pass preserves exact hash/page/passage validation and does not change provenance loading or database query architecture. The new aggregate response adds small fixed summaries; hiding UI details does **not** reduce database reads or remove conditions from API responses. Snapshot projection/request-cache optimization remains deferred for a separately tested pass. Broader regrouping of source-specific scenario fact selectors beyond the compact overrides and expandable income context is also deferred. Production Neon remains operator-reported paused.

## Validation

- Targeted local backend: **39 passed, 1 skipped** (23.88s), covering research guidance/completion, six new ranking/count tests, scenarios/retrieval and workspace permissions. The skip is the opt-in existing local neural-weight test; no model download or inference was needed.
- Standard local browser suite: **42 passed** (19.0s), including four new mocked UI contracts for compact/mismatch cards, separate counters, empty reviewed graphs and filters at 320/1440px. The four focused UI contracts also passed separately; a final relevant subset of **12 browser tests passed** (6.4s) after the compact-card, quotation and graph lifecycle changes.
- Backend Ruff check/format; frontend ESLint, TypeScript and production build passed. OpenAPI and generated TypeScript contracts were refreshed. Existing Vite chunk-size warning remains.
- Browser screenshots of fictional fixtures were inspected locally and remain ignored/private. No current hosted acceptance was claimed.
- The separate Firebase-emulator product suite was not run: the existing localhost Auth emulator was unavailable. Its affected selectors/pagination helpers were updated, but those integrated browser paths still require rerunning once that local emulator is available.

A future release needs **both backend and frontend deployment** because ranking, typed guidance fields and unpaginated counters are server changes. No migration or catalogue import is required. No release is authorized or performed here.

## Changed files

- Backend ranking, typed grouping/count summary: `apps/api/src/opportunity_platform/research/guidance.py`.
- Backend regressions and pagination-aware corpus assertions: `apps/api/tests/test_research_ranking.py`, `apps/api/tests/test_research_completion.py`.
- Compact/grouped previews and provisional counters: `apps/web/src/features/opportunities/ResearchGuidance.tsx`.
- Reviewed scenario state and compact income overrides: `apps/web/src/features/intelligence/ScenarioStudio.tsx`.
- Responsive source filters: `apps/web/src/features/opportunities/GovernmentSources.tsx`.
- Empty quotation guards: `apps/web/src/features/opportunities/Discover.tsx`, `apps/web/src/features/opportunities/ResearchCatalogue.tsx`.
- Graph empty state, subject legend and zoom label: `apps/web/src/components/IntelligenceMap.tsx`.
- Existing design-system styling: `apps/web/src/styles/intelligence.css`.
- Browser contracts/selectors: `apps/web/tests/personalization-corrections.spec.ts`, `apps/web/tests/research-real.spec.ts`, `apps/web/tests/intelligence-real.spec.ts`.
- Generated API contracts: `packages/contracts/openapi.json`, `apps/web/src/lib/api/schema.d.ts`.
- This verification report: `docs/personalization-corrections.md`.
