"""Optional neural adapter. No model, synthetic vectors, training or remote calls."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class PolicyRepresentation:
    opportunity_id: str
    version_id: str
    source_hash: str
    text: str
    typed_requirements: list[dict]


@dataclass(frozen=True)
class SubjectRepresentation:
    kind: str
    facts: list[dict]  # Private, request-scoped only. Income contexts stay separate.
    unknown_keys: list[str]
    intent: str


class NeuralRetriever(Protocol):
    status: str

    def retrieve(
        self, policies: list[PolicyRepresentation], subject: SubjectRepresentation, limit: int
    ) -> list[str]: ...


class UnavailableNeuralRetriever:
    status = "unavailable: no local pretrained embedding model integrated"

    def retrieve(self, policies, subject, limit):
        return []
