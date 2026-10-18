# Gemini attempt plan — authorization consumed

Prepared 18 October 2026. **This plan was subsequently authorized and executed once from `e713eac46beb3a32f50fe65c3509f6ec6e4a96b0`. Do not run it again.** Generation and outer-envelope validation succeeded; inner extraction failed. No candidate, reviewer, repair or import. See `evidence/gemini-team-e713eac.json`. The local ledger now holds eight reservations, its configured daily cap. The text below preserves the pre-execution authorization scope; it is not permission for another request.
Application transport implementation: `0b8237e4f2122a3c5ccd7e2b3b5383c419b37d48`.
The offline verification itself made no Google requests; the later separately authorized attempt did.

## Verified offline

- Installed `google-genai`: **2.29.0**. Real SDK serialization was exercised with a mocked HTTP transport.
- Bounded Gemini extraction sends only an object containing a required `payload_json` string, with `additionalProperties: false`. The inner schema is prompt content, not Google's response grammar. Other extraction/reviewer/provider paths retain their existing schemas.
- The string is decoded through `BoundedExtraction`, normalized through `RawPolicyExtraction` and the original typed candidate/rule contracts, then checked against original snapshot hash, page, URL and exact quotation. Missing source facts remain unknown. The bounded-excerpt human-review flag is mandatory.
- Usage is settled before output completion checks, JSON decoding, inner validation or source validation. Invalid output does not authorize another provider call.
- Implementation bytes, inner/outer schema, prompt, model and bounds affect fingerprints. The stable attempt identity includes source hash, selected pages/text, model, prompt/schema and review scope, excluding proof timestamps.
- No reviewer, repair, automatic import or publication is permitted in this proposed operation. OpenAI fallback stays off.

## Immutable source and limits

| Item | Proposed value |
|---|---|
| Source | Existing official Ministry of MSME TEAM guidelines PDF |
| Snapshot | `0394eb41-267e-4a9d-8259-65d20a7ef6c7` |
| Original URL | https://ramp.msme.gov.in/ramp/sites/default/files/2026-05/Approved-msme-team-guidelines_0.pdf |
| PDF SHA-256 | `0b9e09be6960b07d22013cf9fa52e0e0a9f6040d03df6799be100db7f76b4eaf` |
| Pages | 1 and 12 only; partial source, not complete policy coverage |
| Selected text SHA-256 | `dbf691c8771448baa8720ae79c97021358f38b0339b808cca519fa16c139119b` |
| Model | Explicit `gemini-3.5-flash-lite` |
| Key-owning project | `gen-lang-client-0305465449` |
| Outer schema SHA-256 | `180e2321ff96678fc08cdf3648b9a7f7e1e60ec342b66c5d43eff032fcc01b2a` |
| Inner schema SHA-256 | `57ab7baa65ac1f0a7b87bd2246b6164ada8d36b355393789ed1d3c355ac6eea3` |
| Maximum provider operations | One countTokens, then at most one generation; no retries |
| Token ceilings | 20,000 input, including safety margin; 4,096 output |
| SDK timeout | 60 seconds per request |
| Local schema | Existing `gemini_demo_7ab1bc86fc91405182f0e6a33faf9e98` |
| Paid budgets | Global/run US$0; paid worker and fallback disabled |
| Output | Local, incomplete extraction dossier awaiting human review |

Before a future request, re-verify project/key ownership, model support, positive model-specific free quota and billing disabled. Verification failure means **no inference**. Metadata requests are additional read-only Google operations; the two-operation bound above refers to token counting and generation.

The last saved reservation receipt contains six reservations from earlier attempts. Keep all six: do not reset the store or counters. The local daily cap is eight reservations; two remaining local slots do **not** prove two requests remain in Google's project quota. Operator diagnostics also used the key outside this ledger. Actual remaining free quota is unknown. A 429 must stop, with no wait/retry/fallback. Expected model charge is US$0 only if the account gate passes; do not activate billing.

## Exact plan-only command

Run from the repository root. This reads the preserved local public PDF and writes a new local report; it does not connect to PostgreSQL or Google. The output must not already exist.

```sh
env \
  DATABASE_URL='postgresql+psycopg://opportunity:local-development-only@localhost:5432/opportunity' \
  TEST_DATABASE_URL='postgresql+psycopg://opportunity:local-development-only@localhost:5432/opportunity' \
  ENVIRONMENT=development PAID_AI_WORKER_ENABLED=false \
  GEMINI_FREE_WORKER_ENABLED=false AI_OPENAI_FALLBACK_ENABLED=false \
  AI_GLOBAL_BUDGET_USD=0 AI_RUN_BUDGET_USD=0 \
  apps/api/.venv/bin/python -m opportunity_platform.operations.gemini_document_demo \
  --corpus-root .corpus --registry data/corpus/sources.json \
  --snapshot-id 0394eb41-267e-4a9d-8259-65d20a7ef6c7 --pages 1 12 \
  --model gemini-3.5-flash-lite \
  --output /tmp/unclaimed-team-payload-plan.json
```

A plan was actually generated at `.live-validation/submission-sprint/gemini-plan.json`. Original PDF bytes and selected plaintext were checked locally. No OCR or collection was repeated.

## Future execution — not authorized by this document

After fresh explicit approval of the exact current commit: use the existing operator-controlled wrapper pattern, assert that commit, retain and compare the six prior reservation IDs, and select the above existing local schema via PostgreSQL `options=-csearch_path=...`. Set both database URLs explicitly to localhost and reject any other host before importing application settings. Use `PROCESS_ROLE=ingestion_worker`, `GEMINI_FREE_WORKER_ENABLED=true`, the explicit project/model above, paid/fallback false, global/run budgets zero, `AI_MAX_REQUESTS_PER_RUN=8`, `GEMINI_FREE_DAILY_REQUESTS=8`, and public API ingestion/assistant flags false. Read the key only from the existing backend environment; never print it. Never execute the old commit-pinned wrappers.

Invoke the same module with `--local-schema gemini_demo_7ab1bc86fc91405182f0e6a33faf9e98`, a fresh exclusive evidence output path and `--execute-authorized-free-worker`. Do not add `--authorize-independent-review`. Verify the actual database schema before reserving. The execution wrapper must be reviewed and pinned before it runs; the plan-only command above must not simply be amended and executed against unspecified application settings.

Record separately: successful generation HTTP outcome; model/version; measured tokens and thinking tokens if returned; outer JSON validity; inner validity; original-contract validity; exact source/page/passage validity; source/schema/implementation hashes; durable reservations and sanitized failure stage/field details. A successful generation is not necessarily a valid extraction. A valid partial candidate is not an independent review or approved policy.

No import, research enrichment, policy publication, production API/database call, deployment, scheduler or paid fallback belongs to this authorization. Existing production remains unchanged.
