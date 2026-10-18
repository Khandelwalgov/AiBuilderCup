"""Explicit provider selection. Failures never select another provider."""

from dataclasses import dataclass, field
from typing import Protocol

from opportunity_platform.core.config import settings
from opportunity_platform.ingestion import gemini
from opportunity_platform.ingestion.schemas import CandidateData


@dataclass
class ExtractionResult:
    candidate: CandidateData
    usage: dict = field(default_factory=dict)


class ExtractionProvider(Protocol):
    def extract(self, pages: list[dict], focus: str) -> ExtractionResult: ...


class GeminiProvider:
    def extract(self, pages: list[dict], focus: str) -> ExtractionResult:
        usage = {}
        candidate = gemini.extract(pages, focus, usage_sink=usage)
        return ExtractionResult(candidate, usage)


def identity() -> tuple[str, str, str]:
    config = settings()
    if config.ai_extraction_provider == "openai":
        return "openai", config.openai_model, "policy-candidate-openai-v3"
    return "gemini", config.gemini_model, gemini.EXTRACTOR_VERSION


def extract(pages: list[dict], focus: str) -> ExtractionResult:
    if settings().ai_extraction_provider == "openai":
        from opportunity_platform.ingestion.openai import OpenAIProvider

        provider: ExtractionProvider = OpenAIProvider()
    else:
        provider = GeminiProvider()
    return provider.extract(pages, focus)


def controlled_worker_fallback(role, schema, system, payload, error):
    """One explicitly budgeted backup for transport outages, never output-quality errors.

    This is used only by operator corpus roles, not the public API provider selector.
    """
    import httpx
    from google.genai.errors import APIError

    from opportunity_platform.ingestion import budget

    config = settings()
    transient = (
        isinstance(error, APIError) and error.code in {429, 500, 502, 503, 504}
    ) or isinstance(error, (httpx.TimeoutException, TimeoutError))
    if not (
        transient
        and config.ai_openai_fallback_enabled
        and config.process_role == "ingestion_worker"
        and config.paid_ai_worker_enabled
        and config.openai_api_key
        and config.ai_openai_fallback_model
        and config.ai_global_budget_usd > 0
        and config.ai_run_budget_usd > 0
        and config.ai_openai_fallback_budget_usd > 0
        and config.ai_openai_fallback_run_budget_usd > 0
        and budget.run_key.get()
        and not budget.fallback_used.get()
    ):
        raise error
    from opportunity_platform.ingestion.corpus_policy.live import OpenAIRole

    budget.fallback_used.set(True)
    backup = OpenAIRole(
        role.role,
        config.ai_openai_fallback_model,
        max_input_tokens=role.max_input_tokens,
        max_output_tokens=role.max_output_tokens,
    )
    primary_usage = dict(role.last_usage)
    try:
        result, usage = backup.generate(schema, system, payload)
    except Exception:
        role.last_usage = {
            **getattr(backup, "last_usage", {}),
            "fallback": True,
            "primary_attempt": primary_usage,
        }
        raise
    consumed = {
        **usage,
        "fallback": True,
        "primary_attempt": primary_usage,
        "external_api_calls": usage.get("external_api_calls", 0)
        + primary_usage.get("external_api_calls", 0),
    }
    role.last_usage = consumed
    return result, consumed
