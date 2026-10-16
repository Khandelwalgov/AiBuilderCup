# Ephemeral Scenario Studio

`POST /v1/scenarios/evaluate` accepts an actual authorized search base, typed overrides by authorized subject key, up to ten fictional people, optional excluded base subjects, and independently scoped household facts. It resolves the base again server-side, retrieves and assesses the actual graph, constructs an in-memory hypothetical graph, **reruns candidate retrieval**, assesses that new shortlist, and builds an ephemeral Unlock Graph and comparisons.

No actual ORM people, memberships, consents, facts, documents, evaluations or actions are created or updated. HTTP handlers roll back the transaction. The PostgreSQL test additionally commits after calling the service and confirms all seven relevant table counts remain unchanged. Browser fields live only in React state; no named scenarios, localStorage retention or URL-encoded private facts are implemented. Reset/discard clears fields, people and results. Switching actual workspace remounts the studio.

## Supported edits

- Person: age, personal/parental income, current and completed education, enrollment, school status, residence/domicile state/district, employment; typed nationality/disability overrides also supported by the API.
- Business: registration status/location, operating location/activity and turnover.
- Household: explicitly defined annual household income and location. Period and exact policy income definition remain required to satisfy an income rule. No automatic sums or family averaging.
- Composition: exclude authorized actual members from the hypothetical graph; add temporary spouse/child/dependent nodes with their own facts. Adding fictional people to a person base creates a temporary household context, allowing entirely new household policies to be retrieved. Family members have independent exact assessments and action identities.
- Application context: unknown, fresh or renewal. Unknown is retained when the source needs that distinction.

Temporary IDs use `scenario:` namespaces; they never become real object IDs or permission grants. Fictional relationship labels describe graph edges only: a spouse label grants no access to a real adult, and a child label alone does not supply age or legal eligibility. Arbitrary household-composition eligibility formulas are not inferred from relationship labels; unsupported/source-ambiguous definitions remain unknown. There is no marriage/adoption/life-event prediction model.

Document verification cannot be overridden. A changed subject's verified-document facts are conservatively removed from the hypothetical fact set; future circumstances cannot automatically inherit documentary verification. Unchanged subjects may retain actual evidence. Household composition changes invalidate that household's document facts. Fictional people start with no documents. The real records stay intact. Existing education consistency rules validate hypothetical person facts; contradictory new answers produce a validation error rather than an invented resolution.

## Comparison and Unlock Graph

Comparisons are keyed by opportunity plus subject, with `newly_retrieved`, `no_longer_retrieved`, `changed`, and `unchanged`, before/after statuses and exact evaluator reasons. The UI explicitly says retrieval changes are not definitive eligibility changes. A bounded shortlist can omit an opportunity even when its eligibility did not change. New fictional subjects have no actual baseline, so their entries are newly retrieved, not new official entitlements.

The hypothetical graph uses the existing `IntelligenceMap` and a full action list. The planner's scoped dependency identities group shared missing information/evidence for the **same subject**, never one person's certificate across unrelated people or different income definitions. Known unsatisfied conditions remain separately reported as blockers. Each scenario card exposes exact conditions and original citations. Hypothetical evaluation IDs are not submitted to the persisted assistant endpoint.

Studio controls and main statuses support English/Hindi and mobile layouts. Source passages and existing deterministic evaluator explanations retain their authoritative/original wording; this milestone does not claim translated legal nuance. The graph retains its existing desktop viewport; on narrow screens the full textual checklist is available. No visual identity redesign was made.

## Persistence boundary tests

`apps/api/tests/test_intelligence.py` covers no-change equivalence; age 18→17 exact boundary; trillion-rupee personal income; new fictional child and household candidates absent from the actual list; commit-after-simulation non-persistence; protected document override rejection; cross-account rejection; restricted-adult privacy and revoked guardian access; independent parent/child outcomes; income scope; fair large shortlists; national visibility; and published-pointer preservation under a newer draft.

`apps/web/tests/intelligence-real.spec.ts` uses actual Firebase emulator tokens, the API and disposable PostgreSQL, without auth overrides or live AI. It covers five search modes, explicit context in detail navigation, fictional future family, reset, graph, desktop/mobile screenshots and Hindi Studio controls.
