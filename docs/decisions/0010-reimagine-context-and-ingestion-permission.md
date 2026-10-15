# Explicit subject navigation and operator ingestion permission

15 October 2026. Preserve React/FastAPI/PostgreSQL and the existing contracts.

A single route metadata table controls canonical routes, navigation, titles and route access. `/` is adaptive home; `/dashboard` redirects. React Router Data Router supplies the dirty-navigation blocker. Backend Firebase/object authorization remains authoritative; browser readiness and access screens are presentation gates.

Subject selection uses authorized `/v1/workspaces` options and explicit `kind/id` URL state. Personal is the default; dependent editing explicitly selects that person even when entered from a household. Invalid/revoked context does not fall back to personal for evaluation. Context and account changes remount private forms/results; account UID changes clear queries. Unsupported subject/opportunity combinations return 422. Plans omit those combinations. Other-scope conditions within a supported opportunity remain unknown rather than importing facts from another subject.

Editable forms retain local drafts while dirty. Candidate submissions bind to the hash captured when editing began, preserving optimistic concurrency even if a background fetch observes a newer candidate.

HTTP ingestion now defaults to disabled with `AI_INGESTION_LIVE_ENABLED=false`. Admin-only settings expose provider/model/budget/permission without credentials. Each explicit confirmation binds provider/model and acknowledges potential paid use. `AI_INGESTION_TEST_BUDGET_USD` is informational; it is not a billing cap. No automatic fallback, billing activation or provider switch was added. CLI operator flows retain their existing explicit invocation semantics. No live model operation was executed during this sprint.
