"""One bounded smoke request for the explicitly selected provider; no fallback."""

import json
import logging

from opportunity_platform.core.config import settings
from opportunity_platform.ingestion.gemini import ExtractionFailure
from opportunity_platform.ingestion.openai import request, response_text
from opportunity_platform.operations.gemini_smoke import probe as gemini_probe


def probe():
    config = settings()
    if config.ai_extraction_provider == "gemini":
        return {"provider": "gemini", **gemini_probe()}
    report = {"provider": "openai", "model": config.openai_model, "success": False}
    try:
        result = request(
            {
                "model": config.openai_model,
                "input": "Return an object with ok set to true.",
                "reasoning": {"effort": "none"},
                "store": False,
                "max_output_tokens": 128,
                "text": {
                    "format": {
                        "type": "json_schema",
                        "name": "smoke",
                        "strict": True,
                        "schema": {
                            "type": "object",
                            "properties": {"ok": {"type": "boolean"}},
                            "required": ["ok"],
                            "additionalProperties": False,
                        },
                    }
                },
            }
        )
        text, usage = response_text(result)
        payload = json.loads(text)
        report.update(
            success=isinstance(payload, dict) and set(payload) == {"ok"} and payload["ok"] is True,
            usage=usage,
        )
    except ExtractionFailure as error:
        report.update(diagnostic_code=error.code, stage=error.stage, http_status=error.http_status)
    except (ValueError, TypeError):
        report["diagnostic_code"] = "openai_smoke_invalid_response"
    return report


def main():
    logging.disable(logging.CRITICAL)
    report = probe()
    print(json.dumps(report))
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
