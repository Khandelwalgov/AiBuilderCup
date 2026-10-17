"""Real pinned-model checks, explicitly enabled with local weights. No hosted AI."""

import os
from pathlib import Path

import pytest
from sqlalchemy import func, select

from opportunity_platform.db.models import PolicyEmbedding
from opportunity_platform.retrieval.index import build
from opportunity_platform.retrieval.neural import (
    LocalEncoder,
    LocalNeuralRetriever,
    PolicyRepresentation,
    SubjectRepresentation,
)


@pytest.fixture(scope="module")
def encoder():
    directory = os.environ.get("NEURAL_TEST_MODEL_DIRECTORY")
    if not directory:
        pytest.skip("Real local weights not configured; no download or inference API fallback")
    return LocalEncoder(Path(directory))


def test_real_multilingual_stored_vectors_and_invalidation(db, encoder):
    from test_intelligence import fictional_catalogue

    fictional_catalogue(db, 3)
    from opportunity_platform.db.models import OpportunityVersion

    versions = list(
        db.scalars(
            select(OpportunityVersion)
            .where(OpportunityVersion.title.like("FICTIONAL % policy %"))
            .order_by(OpportunityVersion.id)
        )
    )
    # Controlled semantics test: fixture data, not a real-world quality claim.
    texts = [
        "Scholarships provide financial assistance to students for education.",
        "Government procurement tenders for suppliers of construction materials.",
        "Small enterprises receive marketing assistance to sell goods online.",
    ]
    policies = [
        PolicyRepresentation(str(v.opportunity_id), str(v.id), "a" * 64, text, [], {})
        for v, text in zip(versions, texts, strict=True)
    ]
    assert build(db, encoder, policies) == 3
    db.commit()
    assert build(db, encoder, policies) == 0
    retriever = LocalNeuralRetriever(encoder, db)
    for query in ["Help for students to pay tuition", "पढ़ाई के लिए छात्रवृत्ति और आर्थिक सहायता"]:
        result = retriever.retrieve(policies, SubjectRepresentation("person", [], [], query), 3)
        assert result[0] == policies[0].opportunity_id
    assert retriever.stored_vectors_used == 6
    assert db.scalar(select(func.count()).select_from(PolicyEmbedding)) == 3
    assert all(len(row.vector) == 384 for row in db.scalars(select(PolicyEmbedding)))
    private_text = "PRIVATE PROFILE NEVER INDEXED 123456789"
    retriever.retrieve(
        policies,
        SubjectRepresentation("person", [{"key": "private", "value": private_text}], [], ""),
        3,
    )
    assert private_text not in str(encoder.public_vectors)
    for row in db.scalars(select(PolicyEmbedding)):
        assert private_text not in str(row.vector)
    policies[0] = PolicyRepresentation(
        policies[0].opportunity_id, policies[0].version_id, "b" * 64, texts[0], [], {}
    )
    before = retriever.stored_vectors_used
    retriever.retrieve(policies, SubjectRepresentation("person", [], [], "education help"), 3)
    assert retriever.stored_vectors_used - before == 2  # stale hash excluded
    assert build(db, encoder, policies) == 1


def test_real_encoder_shape_and_trailing_policy_sections(encoder):
    import numpy as np

    vector = encoder.encode("Scholarship and tuition assistance")
    assert vector.shape == (384,)
    assert np.isfinite(vector).all()
    assert abs(float(np.linalg.norm(vector)) - 1) < 1e-5
    assert len(encoder.tokenizer.encode("Business registration requirements. " * 130).ids) > 128
    long = encoder.encode(
        ("Business registration requirements. " * 130) + " Student tuition assistance."
    )
    assert not np.allclose(vector, long)


def test_deployed_public_text_probe_uses_real_cpu_model(encoder):
    from opportunity_platform.operations.neural_probe import probe

    result = probe(encoder)
    assert result["actual_local_inference"] and result["dimensions"] == 384
    assert result["external_api_calls"] == 0 and not result["private_data_used"]
    assert not result["government_policy_quality_measured"]
    assert len(result["controlled_public_text_probe"]) == 2


def test_concurrent_cold_requests_load_only_one_model(monkeypatch):
    import threading
    import time
    from concurrent.futures import ThreadPoolExecutor

    from opportunity_platform.retrieval import neural

    calls = []
    barrier = threading.Barrier(4)

    def factory(path):
        calls.append(path)
        time.sleep(0.02)
        return object()

    neural._load_encoder.cache_clear()
    monkeypatch.setattr(neural, "LocalEncoder", factory)

    def request(_):
        barrier.wait()
        return neural.encoder_for("fictional-model-path")

    try:
        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(request, range(4)))
        assert len(calls) == 1 and len({id(value) for value in results}) == 1
    finally:
        neural._load_encoder.cache_clear()
