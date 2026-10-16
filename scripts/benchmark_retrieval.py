"""Offline fictional benchmark: isolated PostgreSQL schema, exact oracle, no AI/network."""

import json
import os
import sys
import uuid
from pathlib import Path
from statistics import mean, median
from time import perf_counter

from sqlalchemy import create_engine, or_
from sqlalchemy.orm import Session

from opportunity_platform.core.config import settings
from opportunity_platform.db.models import Base, Opportunity, OpportunityVersion
from opportunity_platform.eligibility.engine import FactRecord
from opportunity_platform.eligibility.service import evaluate_requirements, overall_status
from opportunity_platform.retrieval.service import (
    SearchRequest,
    SearchSubject,
    load_catalogue,
    published_query,
    search,
)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api/tests"))


def run():
    from test_intelligence import fictional_catalogue

    settings().enable_development_catalogue = True
    url = os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql+psycopg://opportunity:local-development-only@localhost:5432/opportunity",
    )
    admin = create_engine(url)
    schema = "benchmark_" + uuid.uuid4().hex
    with admin.begin() as c:
        c.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    output = []
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            fictional_catalogue(db, 450)
            fixture = json.loads(
                (ROOT / "data/fixtures/retrieval-benchmark-scenarios.json").read_text()
            )
            for case in fixture["held_out"]:
                subjects = [
                    SearchSubject(
                        s["key"],
                        s["kind"],
                        s["key"],
                        None,
                        [FactRecord(id="fictional", **f) for f in s["facts"]],
                    )
                    for s in case["subjects"]
                ]
                request = SearchRequest(mode="me", q=case["query"], development=True)
                rows, reqs, evidence, _ = load_catalogue(db, request)
                # Oracle: all subject-applicable records without exact known failures.
                relevant = set()
                for s in subjects:
                    for o, v, _ in rows:
                        if any(r.subject_context == s.kind for r in reqs[v.id]):
                            results = evaluate_requirements(reqs[v.id], s.facts, s.kind, evidence)
                            if overall_status(results) != "not_eligible_on_known_facts":
                                relevant.add((str(o.id), s.key))
                measurements = []
                recalls = {}
                coverage = {}
                for k in [50, 150]:
                    request.shortlist = k
                    for repetition in range(3):
                        result = search(db, "benchmark-no-account", request, subjects)
                        measurements.append({"k": k, **result.timings_ms})
                    retrieved = {
                        (str(i.opportunity.id), a.subject_key)
                        for i in result.items
                        for a in i.assessments
                    }
                    recalls[f"hybrid_recall_at_{k}"] = (
                        len(relevant & retrieved) / len(relevant) if relevant else 1
                    )
                    coverage[str(k)] = {
                        "subjects": result.subject_coverage,
                        "categories": result.category_coverage,
                    }
                    # Historical title/summary substring baseline, UUID order.
                    # Same fair round-robin budget; no exact rank in baseline.
                    start = perf_counter()
                    escaped = (
                        case["query"].replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
                    )
                    baseline_rows = db.execute(
                        published_query(request)
                        .where(
                            or_(
                                OpportunityVersion.title.ilike(f"%{escaped}%", escape="\\"),
                                OpportunityVersion.summary.ilike(f"%{escaped}%", escape="\\"),
                            )
                        )
                        .order_by(Opportunity.id)
                    ).all()
                    streams = []
                    for s in subjects:
                        streams.append(
                            [
                                (str(o.id), s.key)
                                for o, v, _ in baseline_rows
                                if any(r.subject_context == s.kind for r in reqs[v.id])
                            ]
                        )
                    baseline = []
                    while any(streams) and len(baseline) < k:
                        for stream in streams:
                            if stream and len(baseline) < k:
                                baseline.append(stream.pop(0))
                    recalls[f"ilike_recall_at_{k}"] = (
                        len(relevant & set(baseline)) / len(relevant) if relevant else 1
                    )
                    recalls[f"ilike_candidate_ms_at_{k}"] = (perf_counter() - start) * 1000
                output.append(
                    {
                        "case": case["id"],
                        "oracle_pairs": len(relevant),
                        **recalls,
                        "measurements_ms": measurements,
                        "coverage": coverage,
                    }
                )
        summary = {}
        for name in [
            "hybrid_recall_at_50",
            "hybrid_recall_at_150",
            "ilike_recall_at_50",
            "ilike_recall_at_150",
        ]:
            summary[name] = mean(r[name] for r in output)
        for k in [50, 150]:
            for name in ["candidate_generation", "exact_evaluation", "ranking"]:
                values = sorted(
                    m[name] for r in output for m in r["measurements_ms"] if m["k"] == k
                )
                summary[f"{name}_{k}_p50_ms"] = median(values)
                summary[f"{name}_{k}_p95_ms"] = values[
                    min(len(values) - 1, int(0.95 * len(values)))
                ]
        report = {
            "policies": 450,
            "training_scenarios_used": 0,
            "held_out_scenarios": len(output),
            "neural_model_used": False,
            "summary": summary,
            "cases": output,
        }
        target = ROOT / "docs/retrieval-benchmark-results.json"
        target.write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(summary, indent=2))
    finally:
        engine.dispose()
        with admin.begin() as c:
            c.exec_driver_sql(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
        admin.dispose()


if __name__ == "__main__":
    run()
