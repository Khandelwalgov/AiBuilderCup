from opportunity_platform.ingestion.adapters import ADAPTERS


def test_post_matric_adapter_keeps_component_semantics_separate():
    pre = ADAPTERS["depwd-pre-matric"]
    post = ADAPTERS["depwd-post-matric"]
    assert post.key != pre.key
    assert post.url == pre.url and post.amendment_urls == pre.amendment_urls
    assert "employed/intern" in post.focus
    assert "Do not apply Pre-Matric" in post.focus
    assert "renewal exceptions" in post.focus


def test_manual_post_matric_curation_quotes_real_capture():
    import json
    from pathlib import Path

    from opportunity_platform.ingestion.curated_depwd import candidate_from
    from opportunity_platform.ingestion.schemas import validate_evidence

    path = Path(__file__).resolve().parents[3] / "data/fixtures/depwd-captured-public-pages.json"
    pages = json.loads(path.read_text())["pages"]
    c = candidate_from(pages)
    validate_evidence(c, pages)
    assert len(c.requirements) == 20
    assert len(c.document_evidence) == len(c.required_documents) == 8
    assert c.opens_on is None and c.closes_on is None and c.apply_url is None
    assert all("class IX" not in r.description for r in c.requirements)
    assert any(
        "first failure" in r.description
        for r in c.requirements
        if r.application_context == "renewal"
    )
    assert any("employed/intern" in r.description.lower() for r in c.requirements)
