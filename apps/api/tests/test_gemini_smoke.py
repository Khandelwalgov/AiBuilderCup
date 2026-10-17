import json

import httpx
import pytest
from google import genai

from opportunity_platform.core.config import settings
from opportunity_platform.operations import gemini_smoke


@pytest.mark.parametrize(
    "status,finish,response_text,success",
    [
        (200, "STOP", '{"ok": true}', True),
        (200, "STOP", '{"ok": 1}', False),
        (200, "MAX_TOKENS", '{"ok": true}', False),
        (503, None, None, False),
    ],
)
def test_smoke_bounds_one_generation_and_sanitizes_provider_failures(
    monkeypatch, status, finish, response_text, success
):
    # Only the mocked transport is exercised in this serialization test.
    monkeypatch.setattr(gemini_smoke.budget, "reserve", lambda *args: None)
    monkeypatch.setattr(gemini_smoke.budget, "settle", lambda *args: None)
    monkeypatch.setattr(settings(), "gemini_api_key", "synthetic-private-key")
    real_client = genai.Client
    calls = []

    def transport(request):
        body = json.loads(request.content)
        calls.append(body)
        if status == 503:
            return httpx.Response(
                503,
                json={"error": {"code": 503, "message": "synthetic-private-key provider details"}},
            )
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "finishReason": finish,
                        "content": {"role": "model", "parts": [{"text": response_text}]},
                    }
                ]
            },
        )

    def client(**kwargs):
        assert kwargs["http_options"].timeout == 20000
        assert kwargs["http_options"].retry_options.attempts == 1
        kwargs["http_options"].httpx_client = httpx.Client(transport=httpx.MockTransport(transport))
        return real_client(**kwargs)

    monkeypatch.setattr(gemini_smoke.genai, "Client", client)
    result = gemini_smoke.probe()
    assert len(calls) == 1
    assert calls[0]["generationConfig"]["maxOutputTokens"] == 256
    assert not calls[0].get("tools")
    assert "synthetic-private-key" not in json.dumps(result)
    assert result["success"] is success
    if status == 503:
        assert result["http_status"] == 503 and result["retryable"]
        assert result["stage"] == "generate_content"


def test_missing_key_does_not_create_a_client(monkeypatch):
    monkeypatch.setattr(settings(), "gemini_api_key", "")
    monkeypatch.setattr(gemini_smoke.genai, "Client", lambda **kwargs: pytest.fail("No API call"))
    result = gemini_smoke.probe()
    assert result["attempts"] == 0
    assert result["diagnostic_code"] == "gemini_not_configured"
