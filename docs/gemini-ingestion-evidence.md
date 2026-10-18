# Unclaimed: Google GenAI ingestion evidence

18 October 2026. This worker change is **local only**. The deployed application remains
commit `038594fb823136e6468cfaef79cd80e503800a0c`, Cloud Run
`opportunity-api-00013-zoj`, Hosting `375a1c14fd8ab1fe` on
[Unclaimed](https://unclaimed-ai-cup.web.app).

## Product acceptance actually completed

The live public API was rechecked: **96 research listings (74 main / 22 archive),
85 evidence-bound comparison records across 11 programme parents**. These are provisional
source-backed comparisons, not 11 administrator-approved eligibility policies. Six policy
versions remain unpublished; zero eligibility policies have been published.

Actual signed-in hosted acceptance performed during the release showed automatic personal
Discover, an original ST source/page link, a scenario changing six enrollment conditions
from unknown to satisfied, scenario reset, and a shared Unlock Plan task covering six
scholarship parents. Remaining income/category requirements stayed unknown. The two saved
profile facts had identical before/after hashes. A task completion was tested and restored
to pending. Normal preparation/action/audit writes occurred. Populated family/business and
cross-account hosted acceptance were not performed; their earlier local emulator tests must
not be represented as hosted tests. The final native search/category browser recheck was
interrupted when Chrome switched to an unrelated conversation; no private browser context
was used to obtain authentication tokens.

## Genuine Google requests, including failures

The configured key successfully authenticated Google model metadata. Its owner was verified
through the API Keys lookup endpoint as project `gen-lang-client-0305465449`.
Cloud Billing reported `billingEnabled=false` and no linked billing account. Model-specific
free-tier quota metadata exposed:

| Model | Requests/minute | Requests/day | Input tokens/minute |
|---|---:|---:|---:|
| `gemini-3.8-flash` | 5 | 20 | 250,000 |
| `gemini-3.5-flash-lite` | 15 | 500 | 250,000 |

These are configured limits, **not measurements of remaining quota or capacity guarantees**.
[Google pricing](https://ai.google.dev/gemini-api/docs/pricing) documents free-tier input and
output. [Structured output documentation](https://ai.google.dev/gemini-api/docs/structured-output)
describes a schema subset and warns that complex schemas may be rejected. Billing is checked
again immediately before each reserved free request; external concurrent billing changes
cannot be made impossible by a local process. Metadata/proof failures deny inference.

Actual requests made:

1. Earlier tiny `gemini-3.8-flash` JSON smoke: **HTTP 504**, one attempt, no output usage available.
2. `gemini-3.5-flash-lite`: existing **MSME TEAM Operating Guide**, original PDF pages **1 and 12**.
   Token counting succeeded (3,392 tokens before the 1,024-token safety allowance);
   generation returned **HTTP 400**, no candidate.
3. One separately authorized corrected transport-schema attempt against the same pages:
   token counting succeeded; generation again returned **HTTP 400**,
   `Request contains an invalid argument.` No further attempt ran.

Source SHA-256: `0b9e09be6960b07d22013cf9fa52e0e0a9f6040d03df6799be100db7f76b4eaf`.
Acquisition snapshot: `0394eb41-267e-4a9d-8259-65d20a7ef6c7`.
Original URL and preserved passage text are recorded in the local evidence dossier.
The original content-addressed PDF and packet were not modified. Plain PDF text is checked
against the selected packet pages; no OCR, crawling or new source acquisition is performed.

**Result: genuine Gemini document extraction has NOT succeeded. No independent Gemini review,
repair, new research import, candidate publication or new user-visible GenAI result may be
claimed.** Both failed generation reservations remain retained at USD 0; output token usage
was not supplied. No OpenAI or other paid inference request ran. A transport rejection is
not a justification for paid fallback. The precise remaining blocker is Google's generic
HTTP 400 for this structured generation request; its underlying field is not identified.

Local ignored evidence: `.live-validation/gemini-first/provider-discovery.json`,
`quota-metadata.json`, `genuine-document-attempt.json`,
`genuine-document-schema-adapted.json`, `genuine-reservations*.json`.
These are not credentials and must still be sanitized/reviewed before submission sharing.
Do not put a key, access token or local account identifier into a PPT screenshot.

## Implemented worker safeguards

- Default provider remains Gemini; normal public/API provider selection still has no fallback.
- `GEMINI_FREE_WORKER_ENABLED` defaults false and is rejected in API processes. Explicit
  project/model/key ownership, available model, positive free quotas and disabled billing
  must all be established using read-only Google metadata. No billing activation occurs.
- Existing durable `InferenceReservation` rows account for zero-dollar requests. Existing
  paid accounting is retained. Defaults allow at most eight free external requests/day,
  100,000 reserved input/output tokens/day, four external requests/minute or the tighter
  provider quota, at most 20,000 input / 4,096 output tokens per request, and one concurrent
  free worker sequence. Failed calls keep reservations; token overruns block further calls.
- Single-attempt Google SDK HTTP calls, explicit JSON schema, no tools or function calls.
  Transport-only schema adaptation retains original `Extraction`/`CandidateData` validation.
  Usage is settled before JSON/schema validation, including rejected model outputs.
- Existing separate extractor/reviewer workflow still permits **one** repair and fresh
  independent review. CLI default is now explicitly one repair, rather than silently zero.
  CLI execution also checks capacity for the full bounded sequence (eight external requests
  for Gemini extraction/review/repair/review); configure `AI_MAX_REQUESTS_PER_RUN=8` for that
  sequence or explicitly choose zero repair.
  The single-generation demonstration deliberately uses pending human review, with its
  zero-repair/one-call limit stated in the report, unless independent review is authorized.
- Source/model/prompt/schema/focus participate in idempotency. Actual generation provider
  and model are retained on runs/drafts; review/repair usage is separately attributed.
  Prepared interactive candidates retain their existing provenance identity.
- OpenAI backup defaults off. It requires an explicit model/key, paid worker authorization,
  positive global/run and separate provider/run ceilings, and durable reservations. Only
  Gemini 429, 500/502/503/504 or timeout can trigger it, once per document scope. Schema,
  citation, source, credential, unknown-model, account-proof and budget failures do not.
  The backup cannot loop. This path has only mocked acceptance; no paid call is authorized.
- No automatic policy publication or research informational-publication bypass exists.

## Reproduction and product mapping

Use `operations.gemini_document_demo` with an isolated **local** PostgreSQL schema, existing
backend key, `PROCESS_ROLE=ingestion_worker`, paid worker false, both USD budgets zero,
explicit `GEMINI_FREE_PROJECT_ID`, `GEMINI_FREE_MODEL`, and free-worker flag true. The module
is plan-only unless `--execute-authorized-free-worker` is supplied. An output file is created
exclusively; existing attempts are never overwritten. One model generation is the default.

```sh
cd apps/api
.venv/bin/python -m opportunity_platform.operations.gemini_document_demo \
  --corpus-root ../../.corpus --registry ../../data/corpus/sources.json \
  --snapshot-id 0394eb41-267e-4a9d-8259-65d20a7ef6c7 --pages 1 12 \
  --model gemini-3.5-flash-lite --output /tmp/unclaimed-gemini-plan.json
```

This is a reproducible **plan command**, not evidence of a successful extraction. Do not
append the execution flag for another actual attempt without a new bounded authorization.

TEAM already has a canonical research identity/components and evidence-bound comparisons
in `research/conditions.json`. A successful future dossier must reconcile to those identities,
validate every passage against the full original snapshot, retain unknown current windows,
and pass informational import and human review gates. Do not duplicate TEAM or turn these
partial pages into a comprehensive eligibility assessment. Only after that validation can
new extracted intelligence be demonstrated through Discover, Unlock Plan or scenarios.

No database migration or production import manifest is proposed by this worker-only pass.
Deploying this code or importing any resulting dossier requires a new exact-commit/scope
approval. Rolling back an image cannot undo future approved data imports or user actions.

## Local verification for this worker pass

Full backend: **319 passed, 9 optional skips** (37.27 seconds), including existing authentication,
subject permissions, source integrity, repair/escalation, idempotency and migration tests.
New free-tier/fallback tests use mocked provider/account metadata; they are not live AI proof.
Standard local browser suite: **38 passed** (18.9 seconds). Frontend lint, TypeScript and
production build passed; the existing large-chunk advisory remains. Backend Ruff lint/format,
`git diff --check`, and OpenAPI/TypeScript regeneration passed with no contract changes.
The final immutable-source demonstration **plan-only** command passed. No Docker/model build,
production deployment/import, source acquisition, OCR or scheduler activation was performed.

## Subsequent offline transport investigation

See [the current offline SDK audit and proposed request](gemini-offline-transport-audit.md).
It corrects the earlier implication that reference/union keywords were unsupported: Google's
GenerateContent JSON-schema API explicitly supports them. The exact 400 field is still unknown.
A smaller explicit excerpt envelope and truthful stage diagnostics are locally tested; no
additional real request has run under this follow-up. A new exact one-request approval is required.
