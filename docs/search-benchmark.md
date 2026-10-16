# Retrieval benchmark — fictional offline evaluation

Run: `cd apps/api && uv run python ../../scripts/benchmark_retrieval.py`.

450 generated **fictional** published policies in a disposable PostgreSQL schema; nine balanced categories: school, higher education, state support, household, startup, MSME, procurement, unknown conditions and documentary dependencies. Each has an explicit fictional citation at `example.invalid`. No production catalogue, external corpus or model is involved.

Three reserved training scenarios and five held-out scenarios are separately labelled in `data/fixtures/retrieval-benchmark-scenarios.json`. No model was trained and zero training scenarios were used to tune scoring. The held-out split includes boundary ages 17/18, children, older adults, business turnover and unknown household income. The policy generator is deterministic; isolated runtime IDs never influence the stable opportunity ordering. This is an initial offline harness for later representation/pair-training experiments, not an existing trained two-tower model.

## Oracle and interpretation

The exact oracle enumerates all subject-applicable published policy pairs and retains those with **no known unsatisfied condition**, including unknowns. It deliberately does not require query-token overlap: a potentially relevant policy remains relevant under an incomplete profile or wording mismatch. This is a broad coverage oracle, not human relevance judgments. Some held-out queries use `scholarships` while fictional titles use narrower category terms; ILIKE cannot recover those records. The macro comparison should not be generalized to real search quality.

K is a total **subject–opportunity pair budget**. Round-robin allocation shares it among subjects. A policy shown for two people consumes two slots. Many oracle sets exceed K, so even an ideal selection cannot reach 100% recall. We report candidate-set recall before exact-result sorting; reordering the same K pairs cannot improve it. Known failures still enter the candidate set and are identified only by the exact evaluator. The baseline executes PostgreSQL title/summary ILIKE with the same subject applicability and fair budget, UUID order, and no hybrid backfill. This is a more fair subject-aware baseline than the old generic browser alone.

## Measured results

| Candidate budget | Hybrid macro recall | ILIKE macro recall |
|---|---:|---:|
| 50 | 10.61% | 6.49% |
| 150 | 31.10% | 6.49% |

| Phase | K | p50 ms | p95 ms |
|---|---:|---:|---:|
| candidate generation | 50 | 16.04 | 34.02 |
| exact evaluation | 50 | 1.12 | 1.74 |
| ranking | 50 | 0.71 | 0.88 |
| candidate generation | 150 | 16.19 | 29.74 |
| exact evaluation | 150 | 3.24 | 16.80 |
| ranking | 150 | 2.22 | 16.25 |

| Held-out scenario | Exact oracle pairs | Hybrid R@50 | Hybrid R@150 | ILIKE R@50 | ILIKE R@150 |
|---|---:|---:|---:|---:|---:|
| held_out-10 | 200 | 19.50% | 52.00% | 25.00% | 25.00% |
| held_out-17 | 400 | 8.50% | 26.00% | 0.00% | 0.00% |
| held_out-18 | 335 | 11.04% | 35.52% | 7.46% | 7.46% |
| held_out-23 | 600 | 7.00% | 21.00% | 0.00% | 0.00% |
| held_out-67 | 600 | 7.00% | 21.00% | 0.00% | 0.00% |

One school-query scenario favors ILIKE at K=50; the hybrid does not dominate every query. Macro averages conceal that difference. Coverage and raw per-case timings are recorded in [retrieval-benchmark-results.json](retrieval-benchmark-results.json). All applicable subject contexts receive slots; stratified hybrid retrieval covers the applicable category groups. The separate integration test proves exactly 50 slots each for parent/child/business under K=150.

ILIKE candidate-query median at K=50: 1.53 ms (five observations). ILIKE candidate-query median at K=150: 1.15 ms (five observations). These baseline times exclude exact evaluation/ranking, so they are not equivalent end-to-end response times. Hybrid phase timings include published metadata/requirements/citation fetch, queue generation, exact checks, then grouping/view assembly. Three repetitions per scenario/K, 15 samples per phase/K; local warm PostgreSQL/Python, no load or cloud/network/auth timing. p95 is the empirical nearest upper sample and can be noisy. Timing is measured, not an SLA.

## Limits and next experiments

Recall@150 of roughly 31% is **not sufficient evidence for comprehensive discovery**. The broad multi-subject oracle, finite pair budget, unknown-inclusive relevance definition and uniform synthetic policies explain part of the gap; they do not justify claiming completeness. The UI discloses truncation and retains full Explore All. Candidate metadata still scans O(N); large-scale performance has not been demonstrated. Neural retrieval is unavailable. No real-world recommendation accuracy, impact, award prediction or trained embedding quality is measured.

Future work: collect reviewed real-policy judgments and consent-safe fictional profiles, freeze train/test policy-family splits before any learning, add paraphrase/multilingual judgments, measure per-subject weighted recall, run more scenarios and load tests, and only then decide whether a real local embedding/pgvector channel warrants its runtime/index costs. This sprint did not tune scoring on held-out results.
