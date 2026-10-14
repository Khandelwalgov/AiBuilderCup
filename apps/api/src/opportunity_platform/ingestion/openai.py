"""OpenAI Responses Structured Outputs for public source text only; no fallback."""

import copy
import json

import httpx
from pydantic import ValidationError

from opportunity_platform.core.config import settings
from opportunity_platform.ingestion.gemini import SYSTEM, ExtractionFailure
from opportunity_platform.ingestion.providers import ExtractionResult
from opportunity_platform.ingestion.schemas import Extraction, validate_evidence


class ProviderFailure(ExtractionFailure):
    def __init__(self, code, *, stage=None, http_status=None, usage=None, output=None, issues=None):
        super().__init__(code, stage=stage, http_status=http_status)
        self.usage = usage or {}
        self.output = output
        self.issues = issues or []


def structured_schema() -> dict:
    schema = copy.deepcopy(Extraction.model_json_schema())

    def visit(node):
        if isinstance(node, dict):
            # Transport schema only. The original Pydantic model still validates everything.
            node.pop("default", None)
            if node.get("type") == "object":
                node["additionalProperties"] = False
                node["required"] = list(node.get("properties", {}))
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)

    visit(schema)
    return schema


def request(payload: dict) -> dict:
    config = settings()
    if config.openai_api_key.startswith("AIza"):
        raise ProviderFailure("openai_provider_key_mismatch", stage="configuration")
    if not config.openai_api_key:
        raise ProviderFailure("openai_not_configured", stage="configuration")
    try:
        with httpx.Client(timeout=config.openai_timeout_seconds, follow_redirects=False) as client:
            response = client.post(
                "https://api.openai.com/v1/responses",
                headers={"Authorization": "Bearer " + config.openai_api_key},
                json=payload,
            )
        if response.status_code != 200:
            codes = {
                400: "openai_request_rejected",
                401: "openai_credentials_rejected",
                403: "openai_credentials_rejected",
                404: "openai_model_unavailable",
                429: "openai_rate_limited",
            }
            raise ProviderFailure(
                codes.get(response.status_code, "openai_service_error"),
                stage="generate_content",
                http_status=response.status_code,
            )
        return response.json()
    except ProviderFailure:
        raise
    except httpx.TimeoutException:
        raise ProviderFailure("openai_timeout", stage="generate_content") from None
    except httpx.HTTPError:
        raise ProviderFailure("openai_network_error", stage="generate_content") from None
    except ValueError:
        raise ProviderFailure("openai_response_invalid", stage="validate_response") from None


def response_text(response: dict) -> tuple[str, dict]:
    raw_usage = response.get("usage") or {}
    usage = {
        k: v
        for k, v in raw_usage.items()
        if k in {"input_tokens", "output_tokens", "total_tokens"} and type(v) is int
    }
    if response.get("status") != "completed":
        raise ProviderFailure("openai_response_incomplete", stage="validate_response", usage=usage)
    parts = [
        part
        for item in response.get("output", [])
        if item.get("type") == "message"
        for part in item.get("content", [])
    ]
    if any(part.get("type") == "refusal" for part in parts):
        raise ProviderFailure("openai_response_refused", stage="validate_response", usage=usage)
    text = "".join(part.get("text", "") for part in parts if part.get("type") == "output_text")
    if not text:
        raise ProviderFailure("openai_empty_response", stage="validate_response", usage=usage)
    return text, usage


class OpenAIProvider:
    def extract(self, pages: list[dict], focus: str) -> ExtractionResult:
        config = settings()
        contents = json.dumps({"task": focus, "untrusted_source_pages": pages}, ensure_ascii=False)
        schema = structured_schema()
        # Conservative UTF-8 byte bound: avoids a second paid/tokenizer dependency.
        # Reserve framing overhead. Actual token usage comes from the provider response.
        instructions = (
            SYSTEM
            + """
Rule language value types: age, annual_personal_income, annual_parental_income,
disability_percentage, business_turnover are nonnegative numbers (age a whole number).
student_status, has_* facts, auto_debit_consent, business_registered are booleans.
Other facts are short text. Only numeric facts support gte/lte; eq needs one scalar;
in needs a nonempty list of appropriate scalars. document uses only supported has_* fields.
Every income comparison needs an exact source-supported definition and period. If either
is not established, use op=unknown, not a guessed period. For unknown conditions, set
fact/value/income_period/income_definition/as_of to null. Describe the original condition
and cite it even if it cannot be encoded. Do not map recognized school/full-time/regular
attendance or sibling exceptions to mere student_status=true. Flag unsupported semantics.
"""
        )
        input_upper_bound = len((instructions + contents + json.dumps(schema)).encode()) + 1024
        if input_upper_bound > config.openai_max_input_tokens:
            raise ProviderFailure("openai_input_budget_exceeded", stage="input_budget")
        response = request(
            {
                "model": config.openai_model,
                "instructions": instructions,
                "input": contents,
                "reasoning": {"effort": "none"},
                "store": False,
                "max_output_tokens": config.openai_max_output_tokens,
                "text": {
                    "format": {
                        "type": "json_schema",
                        "name": "opportunity_extraction",
                        "strict": True,
                        "schema": schema,
                    }
                },
            }
        )
        text, usage = response_text(response)
        try:
            candidate = Extraction.model_validate_json(text).candidate()
        except ValidationError as error:
            try:
                rejected = json.loads(text)
            except ValueError:
                rejected = None
            issues = [
                {"path": list(item["loc"]), "type": item["type"]}
                for item in error.errors(
                    include_input=False, include_context=False, include_url=False
                )
            ]
            raise ProviderFailure(
                "openai_schema_invalid",
                stage="validate_response",
                usage=usage,
                output=rejected,
                issues=issues,
            ) from None
        try:
            validate_evidence(candidate, pages)
        except ValueError:
            raise ProviderFailure(
                "openai_evidence_invalid",
                stage="validate_evidence",
                usage=usage,
                output=json.loads(text),
            ) from None
        return ExtractionResult(candidate, usage)
