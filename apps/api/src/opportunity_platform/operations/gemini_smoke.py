"""One tiny real structured-generation probe. Never retries or starts ingestion."""

import json
import logging
import time

import httpx
from google import genai
from google.genai import errors, types

from opportunity_platform.core.config import settings

OUTPUT_LIMIT = 256


def probe() -> dict:
    config = settings()
    report = {
        "stage": "generate_content",
        "model": config.gemini_model,
        "max_output_tokens": OUTPUT_LIMIT,
        "attempts": 1,
        "success": False,
        "retryable": False,
    }
    if not config.gemini_api_key:
        return {**report, "diagnostic_code": "gemini_not_configured", "attempts": 0}
    start = time.monotonic()
    try:
        with genai.Client(
            api_key=config.gemini_api_key,
            http_options=types.HttpOptions(
                timeout=20000, retry_options=types.HttpRetryOptions(attempts=1)
            ),
        ) as client:
            response = client.models.generate_content(
                model=config.gemini_model,
                contents="Return an object with ok set to true.",
                config=types.GenerateContentConfig(
                    max_output_tokens=OUTPUT_LIMIT,
                    thinking_config=types.ThinkingConfig(thinking_level="LOW"),
                    response_mime_type="application/json",
                    response_json_schema={
                        "type": "object",
                        "properties": {"ok": {"type": "boolean"}},
                        "required": ["ok"],
                        "additionalProperties": False,
                    },
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                ),
            )
        finished = bool(response.candidates) and (
            response.candidates[0].finish_reason == types.FinishReason.STOP
        )
        # Never emit arbitrary response text; even tiny model outputs are untrusted.
        payload = json.loads(response.text or "{}")
        report["success"] = (
            finished
            and isinstance(payload, dict)
            and set(payload) == {"ok"}
            and payload["ok"] is True
        )
        report["diagnostic_code"] = "ok" if report["success"] else "gemini_smoke_invalid_response"
        if response.usage_metadata:
            report["total_tokens"] = response.usage_metadata.total_token_count
    except errors.APIError as error:
        report.update(
            http_status=error.code,
            retryable=error.code in {429, 500, 502, 503, 504},
            diagnostic_code={
                400: "gemini_request_rejected",
                401: "gemini_credentials_rejected",
                403: "gemini_credentials_rejected",
                404: "gemini_model_unavailable",
                429: "gemini_rate_limited",
            }.get(error.code, "gemini_service_error"),
        )
    except (httpx.TimeoutException, TimeoutError):
        report.update(diagnostic_code="gemini_timeout", retryable=True)
    except httpx.HTTPError:
        report.update(diagnostic_code="gemini_network_error", retryable=True)
    except (ValueError, TypeError):
        report["diagnostic_code"] = "gemini_smoke_invalid_response"
    except Exception:
        report["diagnostic_code"] = "gemini_integration_error"
    report["seconds"] = round(time.monotonic() - start, 2)
    return report


def main():
    # Provider errors and model text never become CLI output.
    logging.disable(logging.CRITICAL)
    result = probe()
    print(json.dumps(result))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
