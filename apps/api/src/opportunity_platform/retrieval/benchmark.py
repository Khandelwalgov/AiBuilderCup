"""Small exploratory relevance check against actual captured official passages.

Not an eligibility/legal accuracy claim. LEAN is historical in this corpus. Labels are
engineering judgments, not independent human publication approvals. No hosted inference.
"""

import argparse
import json
import resource
import sys
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

import numpy as np

from opportunity_platform.ingestion.corpus_policy.archive import (
    audit_record,
    load_manifest,
    registry_from,
)
from opportunity_platform.retrieval.model_artifact import MODEL, REVISION
from opportunity_platform.retrieval.neural import LocalEncoder

SOURCES = {
    "TEAM": ("484fb5d6-115b-41e9-8827-e57ce380a874", [9, 12]),
    "LEAN": ("f2d63928-4410-4c92-9049-2073eaaba0bb", [4]),
    "PMS": ("bd36bc36-be61-415d-8274-95c1ad5ca2ad", [2, 3]),
}
CASES = [
    ("Help my small shop start selling digitally through a commerce network", "TEAM"),
    ("छोटे कारोबार को इंटरनेट पर सामान बेचने के लिए मदद", "TEAM"),
    ("Reduce waste and improve manufacturing productivity using lean tools", "LEAN"),
    ("कारखाने में बर्बादी घटाने और उत्पादकता बढ़ाने की मदद", "LEAN"),
    ("Help an enterprise cover exhibition space and travel at trade shows", "PMS"),
    ("व्यापार मेले में स्टॉल लगाने के खर्च के लिए सहायता", "PMS"),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-directory", type=Path, required=True)
    parser.add_argument("--corpus-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    args = parser.parse_args()
    registry = registry_from(args.registry)
    records = {r.snapshot_id: r for r in load_manifest(args.manifest)}
    start = perf_counter()
    encoder = LocalEncoder(args.model_directory)
    load_ms = (perf_counter() - start) * 1000
    index = []
    for label, (snapshot_id, pages) in SOURCES.items():
        audited = audit_record(records[snapshot_id], args.corpus_root, registry)
        if not audited.technically_ingestible:
            raise ValueError("Official benchmark source failed integrity checks")
        text = (
            audited.corrected_title
            + "\n"
            + "\n".join(p["text"] for p in audited.pages if p["page"] in pages)
        )
        index.append(
            {
                "label": label,
                "source_hash": audited.record.sha256,
                "source_url": audited.record.canonical_source_url,
                "snapshot_id": snapshot_id,
                "pages": pages,
                "vector": encoder.encode(text).tolist(),
            }
        )
    args.output_directory.mkdir(parents=True, exist_ok=True)
    index_path = args.output_directory / "public-vectors.json"
    index_path.write_text(
        json.dumps(
            {
                "model": MODEL,
                "revision": REVISION,
                "representation_version": "official-passage-benchmark-v1",
                "generated_at": datetime.now(UTC).isoformat(),
                "entries": index,
            }
        )
    )
    # Actually reload stored public vectors before evaluating every query.
    stored = json.loads(index_path.read_text())["entries"]
    cases = []
    for query, expected in CASES:
        start = perf_counter()
        vector = encoder.encode(query)
        scores = sorted(
            [(float(np.asarray(row["vector"]) @ vector), row["label"]) for row in stored],
            reverse=True,
        )
        cases.append(
            {
                "query": query,
                "expected": expected,
                "retrieved": scores[0][1],
                "correct_top_1": scores[0][1] == expected,
                "scores": {label: round(score, 4) for score, label in scores},
                "query_ms": round((perf_counter() - start) * 1000, 2),
            }
        )
    memory = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (
        1024**2 if sys.platform == "darwin" else 1024
    )
    report = {
        "model": MODEL,
        "revision": REVISION,
        "dimension": 384,
        "stored_vectors": len(stored),
        "model_load_ms": round(load_ms, 2),
        "peak_process_memory_mib": round(memory, 2),
        "top_1_hits": sum(row["correct_top_1"] for row in cases),
        "cases": cases,
        "paid_inference_calls": 0,
        "production_quality_claim": False,
        "caveat": "Six engineering-labeled relevance cases across three captured documents; "
        "not independent eligibility or production acceptance.",
    }
    (args.output_directory / "results.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2)
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
