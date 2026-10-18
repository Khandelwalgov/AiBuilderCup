# Profile-driven neural research discovery — 18 October 2026

Implemented locally on master from `e0c3574589b6eb2ad4c8f486834651ee88736998`.
No production queries, deployments, external AI calls, data imports into application
schemas, new dependencies or source/condition changes. Local tests created and
removed isolated PostgreSQL test schemas. Gemini reservations were untouched.

## Before / after

Before: empty-query research returned `not_requested`; personal facts affected
only deterministic condition and geographic ordering. Neural inference served
optional typed research searches and reviewed-policy retrieval.

After: each authorized person's or business's current relevant facts form a
bounded deterministic text query for the existing local multilingual ONNX encoder.
Authorized family members receive separate queries. Household-wide facts are not
substituted for member facts. Unknown/expired/future/conflicting facts, ambiguous
legacy education, names and identifiers are omitted. No interests or goals are
invented: current profiles do not store them. An explicit category filter can
supply intent. Private context and vectors are not cached, logged or persisted.

All research rows receive a semantic rank, including low-similarity records.
Only within-group ordering changes: **promising → information gaps → known
mismatches** remains dominant, followed by satisfied-condition count. Semantic
rank then improves ordering before geography/source-strength/stable tie-breakers.
Programme/component grouping, subject separation, existing filters, total counts,
full server-side pagination and exact citations remain. Typed-query scoring and
missing-model deterministic fallback are preserved. Similarity is never an
eligibility verdict. No publication state changes.

## Actual local model evidence

Existing pinned artifacts only; no download, training, model rebuild or provider:

- `Xenova/paraphrase-multilingual-MiniLM-L12-v2`
- Revision `b9e20f0c6dd7e5f88c72259765011e6a3a9196bc`
- Quantized ONNX, CPU, 384 dimensions; existing one-thread/session model cache.
- Local weights `/private/tmp/unclaimed-embedding-model`; production image already
  contains these pinned artifacts, but **this code has not been deployed**.

Real-model suite: **10 passed, 6.76 seconds**. Includes five new profile tests,
four existing neural tests and the existing English/Hindi research-search test.
The three model-dependent new cases genuinely invoke the encoder; offline-only
cases validate context filtering and unavailable-model fallback.

Measured on this local Mac (not a Cloud Run benchmark or service guarantee):

| Measurement | Result / scope |
|---|---|
| Model load including artifact verification | 0.487 s |
| Test-process peak RSS after load | 673,972,224 bytes, about 643 MiB; total process, not incremental model RAM |
| Three-document profile query + initially uncached public vectors | 29 ms |
| Repeat private query with public vectors cached | 3 ms; private query encoded again |
| Full public-source fixture, all pages | 1.641 s, 52 applicable person–programme pairs; first public-vector population |
| Warm seven-item page | 93 ms including API / source comparisons |

Controlled fictional text corpus: a saved undergraduate/student context ranks
education first, a retired 75-year-old context ranks pension first, and a small
manufacturing-business context ranks enterprise support first. The real encoder
changes ordering; these are controlled semantics checks, not a measured legal or
catalogue-wide quality score.

Full existing public-source fixture: the populated age-22 profile's within-group
ordering differs from missing-model ordering, while all 52 applicable pairs remain
reachable. Every listing and condition/citation payload remains identical. The
old-age pension remains in known mismatches below promising/information-gap groups.
No profile facts, policy versions or public/private embeddings are inserted by
serving. Real-model guidance tests also cover distinct authorized family members,
denied-member exclusion, business context and repeated stable one-item pagination.

First requests pay model load plus public-document encoding costs; warm requests
still encode each subject privately and score all rows. Concurrent requests share
the existing serialized encoder/cache. Large-family or larger-catalogue hosted
latency is not established. No paid inference charge exists, but backend CPU and
memory retain ordinary Cloud Run usage costs after deployment.

## Fresh release image check

One local amd64 image was built after the source tests, reusing cached pinned
model/dependency layers: `release-db8dfe70c0f2de96836dd07c`. No Cloud Build or
registry upload. Image manifest list digest:
`sha256:e47840bcb344c50294e2bbda6b3e4925ef50c9e0ab936b0a8538dbbd291d9887`.

A new container ran actual profile-driven ONNX ranking with `--network none`,
read-only filesystem, one CPU,1GiB memory and no DB credentials. It preserved all
three controlled candidates and ranked student assistance first. Cold load plus
first ranking:3.876s; warm ranking:24ms; process peak RSS560.1MiB. This is local
amd64 emulation on this Mac, **not measured Cloud Run latency**. The full96-record
fixture performance above was measured separately in native local Python.
The container made no network/DB call and persisted no private vector.

## Other checks

- Focused research/ranking/guidance/intelligence: **28 passed, one skipped**,24.11s.
- Full offline backend: **355 passed,12 skipped**,58.54s. Skips include opt-in real
  model, real archive and live-source tests; separately run model cases passed above.
- Standard local browser suite: **42 passed**,20.4s, local API plus mocked UI cases;
  not authenticated hosted acceptance.
- Backend Ruff check and format passed for source/changed tests.
- Frontend lint, TypeScript and production build passed. Existing bundle-size
  advisory remains. No frontend/API schema changed.

Do not sum overlapping test runs into a distinct-test count. Reproduction:

```sh
# Explicit localhost URLs prevent accidental production test access.
export DATABASE_URL='postgresql+psycopg://opportunity:local-development-only@localhost:5432/opportunity'
export TEST_DATABASE_URL="$DATABASE_URL"
export ENVIRONMENT=development
cd apps/api
NEURAL_TEST_MODEL_DIRECTORY=/private/tmp/unclaimed-embedding-model .venv/bin/pytest -q -s \
  tests/test_profile_neural.py tests/test_neural.py \
  tests/test_research_completion.py::test_local_multilingual_research_retrieval_with_existing_pinned_model
NEURAL_RETRIEVAL_ENABLED=false .venv/bin/pytest -q
```

CI's existing opt-in real-model step now includes `test_profile_neural.py`.
No new CI deployment trigger is added.

## Release boundary

Backend-only code change: no migrations, catalogue imports, index job, new model,
frontend Hosting update, production feature-flag change or policy publication is
required. A new backend image/revision is needed. Production rollout remains
pending exact-commit approval, candidate health/auth smoke checks and a captured
rollback target. The prior application release approval does not cover this commit.
