"""Exercise the installed real SDK serializer with a test-only HTTP transport."""

import json

import httpx
import pytest
from google import genai

from opportunity_platform.core.config import settings
from opportunity_platform.ingestion import gemini
from opportunity_platform.ingestion.gemini import ExtractionFailure

URL = "https://depwd.gov.in/synthetic-unit-test"
TEXT = "Synthetic scholarship test source with a condition needing human clarification."


def payload():
    citation = {
        "source_url": URL,
        "passage": TEXT,
        "page": 1,
        "language": "English",
        "basis": "explicit",
    }
    return {
        "title": "Synthetic scholarship",
        "summary": "Synthetic extraction test only.",
        "category": "education",
        "field_evidence": [
            {"field": field, "citation": citation} for field in ["title", "summary", "category"]
        ],
        "requirements": [
            {
                "description": "Condition needs clarification",
                "combine": "all",
                "conditions": [{"op": "unknown"}],
                "evidence": citation,
                "subject_context": "person",
            }
        ],
    }


@pytest.fixture
def sdk(monkeypatch):
    real_client = genai.Client
    monkeypatch.setattr(settings(), "gemini_api_key", "synthetic-test-key")
    requests = []
    state = {"finish": "STOP", "tokens": 1000, "payload": payload(), "error": None}

    def transport(request):
        body = json.loads(request.content)
        requests.append((request.url.path, body))
        if state["error"] == "timeout":
            raise httpx.ReadTimeout("synthetic-test-key must not escape", request=request)
        if state["error"]:
            return httpx.Response(
                state["error"],
                json={
                    "error": {
                        "code": state["error"],
                        "message": "synthetic-test-key must not escape",
                    }
                },
            )
        if request.url.path.endswith(":countTokens"):
            return httpx.Response(200, json={"totalTokens": state["tokens"]})
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "finishReason": state["finish"],
                        "content": {
                            "role": "model",
                            "parts": [{"text": json.dumps(state["payload"])}],
                        },
                    }
                ],
                "usageMetadata": {"totalTokenCount": 1500},
            },
        )

    def client(**kwargs):
        kwargs["http_options"].httpx_client = httpx.Client(transport=httpx.MockTransport(transport))
        assert kwargs["http_options"].timeout == settings().gemini_timeout_seconds * 1000
        assert kwargs["http_options"].retry_options.attempts == 1
        return real_client(**kwargs)

    monkeypatch.setattr(gemini.genai, "Client", client)
    return state, requests


def run():
    return gemini.extract([{"source_url": URL, "page": 1, "text": TEXT}], "Synthetic test only")


def test_installed_sdk_serializes_compatible_schema_and_budget(sdk):
    state, requests = sdk
    candidate = run()
    assert candidate.title == "Synthetic scholarship"
    assert candidate.requirements[0].rule.children[0].condition.op == "unknown"
    assert len(requests) == 2
    body = requests[1][1]
    generation = body["generationConfig"]
    assert generation["responseMimeType"] == "application/json"
    assert generation["responseJsonSchema"]["type"] == "object"
    assert generation["maxOutputTokens"] == settings().gemini_max_output_tokens
    assert generation["thinkingConfig"]["thinking_level"] == "LOW"
    assert not ({"temperature", "topP", "topK", "candidateCount"} & set(generation))
    assert not body.get("tools")
    assert "synthetic-test-key" not in json.dumps(body)
    # The SDK disallows system_instruction in countTokens config on the Developer API.
    assert "systemInstruction" not in requests[0][1]


@pytest.mark.parametrize(
    "status,code",
    [
        (400, "gemini_request_rejected"),
        (403, "gemini_credentials_rejected"),
        (404, "gemini_model_unavailable"),
        (429, "gemini_rate_limited"),
        (503, "gemini_service_error"),
        ("timeout", "gemini_timeout"),
    ],
)
def test_sdk_errors_are_actionable_and_sanitized(sdk, status, code):
    state, requests = sdk
    state["error"] = status
    with pytest.raises(ExtractionFailure) as caught:
        run()
    assert caught.value.code == code
    assert "synthetic-test-key" not in str(caught.value)
    assert len(requests) == 1


def test_input_limit_stops_generation(sdk):
    state, requests = sdk
    state["tokens"] = settings().gemini_max_input_tokens
    with pytest.raises(ExtractionFailure) as caught:
        run()
    assert caught.value.code == "gemini_input_budget_exceeded"
    assert len(requests) == 1


def test_truncated_json_is_not_accepted_even_when_parseable(sdk):
    state, requests = sdk
    state["finish"] = "MAX_TOKENS"
    with pytest.raises(ExtractionFailure) as caught:
        run()
    assert caught.value.code == "gemini_output_budget_exceeded"


@pytest.mark.parametrize(
    "invalid,code",
    [
        ({"is_admin": True}, "gemini_schema_invalid"),
        (None, "gemini_evidence_invalid"),
    ],
)
def test_invalid_schema_and_forged_quotes_are_distinct(sdk, invalid, code):
    state, requests = sdk
    if invalid is not None:
        state["payload"] = invalid
    else:
        state["payload"]["requirements"][0]["evidence"]["passage"] = "Unrecorded invented clause"
    with pytest.raises(ExtractionFailure) as caught:
        run()
    assert caught.value.code == code
