"""Read-only deployed CPU inference probe with public engineering text, no private data."""

import json
import platform
import resource
from time import perf_counter

from opportunity_platform.retrieval.model_artifact import MODEL, REVISION
from opportunity_platform.retrieval.neural import encoder_for


def probe(encoder):
    import numpy as np

    scholarship = encoder.encode(
        "Scholarships provide financial assistance to students for education."
    )
    unrelated = encoder.encode(
        "Government procurement tenders for construction materials suppliers."
    )
    results = []
    for label, query in [
        ("English", "Help for students to pay tuition"),
        ("Hindi", "पढ़ाई के लिए छात्रवृत्ति और आर्थिक सहायता"),
    ]:
        vector = encoder.encode(query)
        if vector.shape != (384,) or not np.isfinite(vector).all():
            raise ValueError("Invalid local inference output")
        relevant, other = float(vector @ scholarship), float(vector @ unrelated)
        if relevant <= other:
            raise ValueError("Controlled public-text inference probe failed")
        results.append({"language": label, "relevant_cosine": relevant, "unrelated_cosine": other})
    return {
        "actual_local_inference": True,
        "model": MODEL,
        "revision": REVISION,
        "dimensions": 384,
        "controlled_public_text_probe": results,
        "government_policy_quality_measured": False,
        "private_data_used": False,
        "external_api_calls": 0,
    }


def main():
    from opportunity_platform.core.config import settings

    started = perf_counter()
    encoder = encoder_for(
        settings().neural_model_directory
    )  # verifies pinned hashes before loading
    result = probe(encoder)
    result.update(
        pinned_artifacts_verified=True,
        load_and_probe_ms=round((perf_counter() - started) * 1000),
        peak_memory_mib=round(
            resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            / (1024**2 if platform.system() == "Darwin" else 1024)
        ),
    )
    print(json.dumps(result))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        raise SystemExit("Local deployed inference probe failed; no provider fallback.") from None
