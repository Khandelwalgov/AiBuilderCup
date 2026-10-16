# Phase 4 progress — 16 October 2026

Implementation uses the existing evaluator/permissions and does not modify the separate corpus collector or its workspace. A collector commit appeared concurrently; changes are staged by explicit Phase 4 paths only. No ingestion, review, publication, paid models, deployment, provisioning or push.

Working: SQL FTS/structured/coverage channels, fair configurable shortlist, five Discover contexts, pure exact assessments, ephemeral scenario graphs, reretrieval, scoped actions/comparisons, Studio/member editing/reset, version-aware index migration and generated contracts. Neural retrieval is an explicitly unavailable adapter.

First local commit `95294b6` contains the backend/index/contracts slice. Full checks initially passed 188 tests/1 skip, then 191/1 skip as family permission tests and concurrent external collector tests were added. Browser regression 29 passed; real local acceptance 10 passed. Additional final verification and docs/report record final counts and benchmark metrics.

Final: 193 backend passed/1 live-fetch skip; 29 ordinary browser regressions and 10 real local emulator/API/PostgreSQL journeys passed; full production build passed. Source audit preserves both drafts and 70 citations. Benchmark macro R@150 31.10% vs ILIKE 6.49%; neural unavailable. All task-owned disposable schemas cleaned and Auth emulator stopped. Local commits 95294b6, d91fe17, 2912a84 plus documentation/benchmark commit.
