import json

import httpx
import pytest

from opportunity_platform.core.config import settings
from opportunity_platform.ingestion import openai, providers
from opportunity_platform.ingestion.gemini import ExtractionFailure
from opportunity_platform.ingestion.schemas import Extraction

URL = "https://depwd.gov.in/synthetic-unit-test"
TEXT = "Synthetic source for a condition that requires review."


def output():
    citation = {
        "source_url": URL,
        "passage": TEXT,
        "page": 1,
        "language": "en",
        "basis": "explicit",
    }
    return {
        "title": "Synthetic policy",
        "summary": "Synthetic policy for unit tests only",
        "category": "education",
        "field_evidence": [
            {"field": f, "citation": citation} for f in ["title", "summary", "category"]
        ],
        "requirements": [
            {
                "description": "Unknown condition",
                "combine": "all",
                "conditions": [{"op": "unknown"}],
                "evidence": citation,
                "subject_context": "person",
            }
        ],
    }


def test_strict_transport_schema_preserves_application_contract():
    before = Extraction.model_json_schema()
    schema = openai.structured_schema()

    def walk(node):
        if isinstance(node, dict):
            assert "default" not in node
            if node.get("type") == "object":
                assert node["additionalProperties"] is False
                assert set(node["required"]) == set(node["properties"])
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(schema)
    assert schema["properties"]["issuer"]["anyOf"][-1]["type"] == "null"
    assert Extraction.model_json_schema() == before


@pytest.mark.parametrize("mode", ["valid", "forged", "schema", "incomplete", "service"])
def test_openai_validates_real_response_shape_and_never_falls_back(monkeypatch, mode):
    monkeypatch.setattr(settings(), "ai_extraction_provider", "openai")
    monkeypatch.setattr(settings(), "openai_api_key", "synthetic-private-key")
    monkeypatch.setattr(providers.GeminiProvider, "extract", lambda *a: pytest.fail("No fallback"))
    real_client = httpx.Client
    requests = []

    def transport(request):
        body = json.loads(request.content)
        requests.append(body)
        assert body["store"] is False and not body.get("tools")
        assert body["text"]["format"]["strict"] is True
        assert "synthetic-private-key" not in json.dumps(body)
        if mode == "service":
            return httpx.Response(503, json={"error": {"message": "synthetic-private-key"}})
        data = output()
        if mode == "forged":
            data["requirements"][0]["evidence"]["passage"] = "Invented passage"
        if mode == "schema":
            data["is_admin"] = True
        return httpx.Response(
            200,
            json={
                "status": "incomplete" if mode == "incomplete" else "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": json.dumps(data)}],
                    }
                ],
                "usage": {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
            },
        )

    monkeypatch.setattr(
        openai.httpx,
        "Client",
        lambda **kw: real_client(transport=httpx.MockTransport(transport), **kw),
    )
    pages = [{"source_url": URL, "page": 1, "text": TEXT}]
    if mode == "valid":
        result = providers.extract(pages, "Synthetic unit test")
        assert result.candidate.title == "Synthetic policy"
        assert result.usage["total_tokens"] == 30
    else:
        with pytest.raises(ExtractionFailure) as caught:
            providers.extract(pages, "Synthetic unit test")
        expected = {
            "forged": "openai_evidence_invalid",
            "schema": "openai_schema_invalid",
            "incomplete": "openai_response_incomplete",
            "service": "openai_service_error",
        }
        assert caught.value.code == expected[mode]
        if mode == "schema":
            assert caught.value.issues and caught.value.output["is_admin"] is True
        assert "synthetic-private-key" not in str(caught.value)
    assert len(requests) == 1


def test_missing_key_and_input_budget_do_not_call_openai(monkeypatch):
    monkeypatch.setattr(settings(), "openai_api_key", "")
    monkeypatch.setattr(openai.httpx, "Client", lambda **k: pytest.fail("No network"))
    with pytest.raises(ExtractionFailure) as caught:
        openai.request({})
    assert caught.value.code == "openai_not_configured"
    monkeypatch.setattr(settings(), "openai_max_input_tokens", 1024)
    with pytest.raises(ExtractionFailure) as caught:
        openai.OpenAIProvider().extract([], "test")
    assert caught.value.code == "openai_input_budget_exceeded"


def test_smoke_uses_only_explicit_provider_and_emits_sanitized_failure(monkeypatch):
    from opportunity_platform.operations import extraction_smoke

    monkeypatch.setattr(settings(), "ai_extraction_provider", "openai")
    monkeypatch.setattr(extraction_smoke, "gemini_probe", lambda: pytest.fail("No fallback"))

    def fail(payload):
        assert payload["max_output_tokens"] == 128
        raise openai.ProviderFailure(
            "openai_service_error", stage="generate_content", http_status=503
        )

    monkeypatch.setattr(extraction_smoke, "request", fail)
    report = extraction_smoke.probe()
    assert report["provider"] == "openai" and report["success"] is False
    assert report["http_status"] == 503


def test_default_provider_remains_gemini():
    from opportunity_platform.core.config import Settings

    assert Settings(_env_file=None).ai_extraction_provider == "gemini"


def test_non_google_key_is_never_sent_to_gemini(monkeypatch):
    from opportunity_platform.ingestion import gemini

    monkeypatch.setattr(settings(), "gemini_api_key", "sk-synthetic-openai-key")
    monkeypatch.setattr(gemini.genai, "Client", lambda **kw: pytest.fail("No Google request"))
    with pytest.raises(ExtractionFailure) as caught:
        gemini.extract([], "test")
    assert caught.value.code == "gemini_provider_key_mismatch"


def test_google_key_is_not_sent_to_openai(monkeypatch):
    monkeypatch.setattr(settings(), "openai_api_key", "AIza-synthetic-google-key")
    monkeypatch.setattr(openai.httpx, "Client", lambda **kw: pytest.fail("No provider request"))
    with pytest.raises(ExtractionFailure) as caught:
        openai.request({})
    assert caught.value.code == "openai_provider_key_mismatch"
