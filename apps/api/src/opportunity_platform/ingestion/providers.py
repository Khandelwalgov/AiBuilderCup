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
        return "openai", config.openai_model, "pre-matric-openai-v1"
    return "gemini", config.gemini_model, gemini.EXTRACTOR_VERSION


def extract(pages: list[dict], focus: str) -> ExtractionResult:
    if settings().ai_extraction_provider == "openai":
        from opportunity_platform.ingestion.openai import OpenAIProvider

        provider: ExtractionProvider = OpenAIProvider()
    else:
        provider = GeminiProvider()
    return provider.extract(pages, focus)
