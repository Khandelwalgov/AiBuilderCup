# Gemini HTTP 400: offline investigation and proposed bounded request

18 October 2026. Local-only follow-up to `a5eaacb9f4e350044af533aa53234e8b69a67021`.
**No genuine model, countTokens or account-verification request ran in this pass.**
Public documentation and production metadata were read; production/data were not modified.

## Findings: what is proved, and what remains unknown

Installed `google-genai` is **2.29.0**, matching the existing locked environment. A real SDK
client was exercised with an injected `httpx.MockTransport`, a dummy key and `vertexai=False`.
The mock cannot send a network request. Only the JSON body is retained; headers/keys are not.

The earlier request serializes as:

- `contents` with user text; `systemInstruction` with text;
- `generationConfig.maxOutputTokens=4096`;
- `generationConfig.responseMimeType=application/json`;
- `generationConfig.responseJsonSchema`, not `responseSchema`;
- no tools/tool declarations, URL context or server function-calling configuration.
  `automatic_function_calling.disable` is a client-side SDK option and does not appear on wire.

The former compact schema is **6,145 bytes**, with seven named definitions, nine `$ref` uses
and fourteen `anyOf` nodes, including the heterogeneous scalar/list/null rule-value union.
The current [GenerateContent API reference](https://ai.google.dev/api/generate-content)
explicitly supports `$defs`, `$ref`, `anyOf` and `additionalProperties` for JSON schema.
No forbidden `$ref` sibling or cyclic reference was found. Therefore **it is incorrect to
call these keywords inherently unsupported or identify them as the proven cause of the 400**.
The [structured-output guide](https://ai.google.dev/gemini-api/docs/structured-output) warns
that complex schemas may be rejected; complexity remains a hypothesis. The
[3.5 Flash-Lite model page](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite)
lists structured-output support. Prior account/model metadata success does not prove that a
specific generation request will work.

The API reference now also documents `responseFormat` and marks older format fields deprecated.
Installed SDK 2.29.0 does not expose `GenerateContentConfig.response_format`. This is a
compatibility observation, **not proof that documented legacy fields are rejected**. No SDK
upgrade or alternate paid/model endpoint was introduced speculatively.

Both previous real document requests returned HTTP 400; the only retained provider message
was `Request contains an invalid argument.` Earlier field-level response details were not
preserved and cannot be reconstructed offline. Thus the exact server-side root cause is
**not conclusively established**. A successful server generation is not claimed by this fix.

## Bounded transport, unchanged authoritative contracts

`ingestion/corpus_policy/transport.py` defines an explicitly selected excerpt envelope:

- at most three captured pages, 24 coverage clauses, six requirements and eight conditions
  per requirement; excess input fails instead of being silently truncated;
- all candidate metadata/evidence fields explicit, including empty strings for unknown
  optional values; exact source hash, original URL, page and passage remain required;
- typed operation/combine/subject fields; rule values travel as bounded `value_json` text,
  decoded with `json.loads`, never evaluation or execution;
- finite inlined schema: **3,954 compact bytes, zero `$defs`, `$ref`, `anyOf` or `oneOf`**;
  `additionalProperties=false` retained; transport annotations do not replace validators.

After generation, the existing `RawPolicyExtraction`, `Extraction`, `CandidateData`, typed
Condition validation, original normalization and exact source-evidence checks still run.
Invalid fact keys, numeric value types, missing evidence, wrong hash/page/URL, fabricated
passages and unsupported numeric thresholds fail. Unknowns stay unknown, dates are never
inferred, and the existing coverage/independent-review/human publication gates remain intact.
The ordinary full-document/OpenAI paths are preserved; the demonstration explicitly selects
`bounded_transport=True`. A partial excerpt is never promoted to a complete policy.

Separate truth flags record successful generation, transport schema, original contracts,
passage validation, incomplete draft and independent review. HTTP 200 alone does not imply a
valid or cited candidate. Reviewer execution requires separate authorization.

Diagnostics now retain the request stage (`cost_gate`, `count_tokens`, `generate_content`,
`validate_response`, `normalize_and_validate_source`) and safe Google BadRequest field
paths/descriptions when supplied. Configured keys and URLs are redacted; arbitrary response
bodies, headers, prompts and profile facts are not logged.

Also fixed: the previous demonstration keyed idempotency on the whole report, including its
account-proof timestamp. Proof refresh could create a different attempt identity. The new key
uses stable source/excerpt/model/focus/prompt-schema/version/limits and review scope only.
Local execution now requires an explicit isolated `gemini_demo_<32 hex>` schema matching
`current_schema()`. Paid permission, positive USD budgets or enabled fallback reject this
free-only operation before any model call.

## Reproducible offline evidence

```sh
cd apps/api
.venv/bin/python -m opportunity_platform.operations.gemini_transport_audit \
  --output /tmp/unclaimed-sdk-wire-audit.json
.venv/bin/pytest tests/test_gemini_transport.py -q
```

The audit file must be new. It serializes both old and bounded envelopes for 3.5 Flash-Lite
and 3.8 Flash through the installed SDK, entirely into an in-memory HTTP mock. A mock response
is explicitly simulated and is not Google generation evidence.

Local ignored evidence is under `.live-validation/gemini-offline/`: SDK request audit,
frozen public-source plan, backend/browser logs, production baseline, public submission
checks and history-secret audit. No original corpus, private identity or user document was
changed or added to these transport requests.

## Next authorization: one generation, not deployment or review

Proposed model: **`gemini-3.5-flash-lite`**, explicitly pinned; reverify key ownership,
billing-disabled project `gen-lang-client-0305465449`, model access and positive free quota
before execution. Deny if proof cannot be refreshed. Keep paid worker/fallback false and both
USD budgets zero. Expected provider cost is **US$0 only if those checks pass**; no billing
activation or paid fallback is authorized. No claim of unlimited/free capacity is made.

Source: existing [MSME TEAM Operating Guide](https://ramp.msme.gov.in/ramp/sites/default/files/2026-05/Approved-msme-team-guidelines_0.pdf),
physical pages **1 and 12**, acquisition snapshot `0394eb41-267e-4a9d-8259-65d20a7ef6c7`.
Original PDF SHA-256:
`0b9e09be6960b07d22013cf9fa52e0e0a9f6040d03df6799be100db7f76b4eaf`.
Selected text SHA-256:
`dbf691c8771448baa8720ae79c97021358f38b0339b808cca519fa16c139119b`.
Schema SHA-256:
`57ab7baa65ac1f0a7b87bd2246b6164ada8d36b355393789ed1d3c355ac6eea3`.

Scope: reuse the existing isolated local PostgreSQL reservation store, retaining all previous
reservations. One countTokens request and **one** structured generation request, each with
one HTTP attempt and 60-second SDK timeout; maximum 20,000 input and 4,096 output tokens.
Read-only account-proof requests have bounded timeouts and no billing mutation. Existing
request/day/token/concurrency limits can still deny the operation. No automatic retry,
repair, reviewer request, OpenAI fallback, candidate import or policy publication. Write an
exclusive local dossier only, with stage-by-stage results and sanitized usage/errors.

If valid source-backed output is produced it remains an **incomplete draft awaiting human
review**, not an approved policy and not a newly imported Discover record. Independent AI
review, any further generation, and production mutations each need their own explicit scope.

## Final local validation and changed files

- Full backend: **339 passed / 9 optional skips**, 45.35 seconds, six existing deprecation warnings.
- Latest transport subset: **20 passed**. These include real SDK serialization with mocked HTTP,
  valid normalization, truthful response stages, human escalation and fabricated-evidence rejection.
- Standard local browser regressions: **38 passed**, 19.2 seconds. No hosted authenticated UI
  test was repeated and no synthetic production subject was created.
- Frontend lint, TypeScript and production build passed; existing >500 kB chunk advisory remains.
- Backend Ruff lint/format, whitespace checks and OpenAPI/type regeneration passed; API contracts
  are unchanged. No Docker/model build, paid API, production import/deploy or remote CI/push ran.
- Read-only baseline: Cloud Run `opportunity-api-00013-zoj` at 100%, Unclaimed Hosting
  `375a1c14fd8ab1fe`, 96 listings / six drafts / zero published eligibility policies.

Changed implementation files: `ingestion/corpus_policy/live.py`, new
`ingestion/corpus_policy/transport.py`, `operations/gemini_document_demo.py`, new
`operations/gemini_transport_audit.py`, and new `tests/test_gemini_transport.py`.
Documentation: this report, `docs/gemini-ingestion-evidence.md`, and
`docs/submission-readiness.md`. `ingestion/gemini.py`, `free_tier.py`, original contracts,
research mappings, catalogue records, source snapshots and production resources remain unchanged.

Weekly collection implementation/activation is deferred under the user's priority ordering
until qualifying Gemini evidence and submission-critical tasks. The existing separately scoped
[weekly plan](weekly-source-monitoring-plan.md) is still a plan, not a running scheduler.
