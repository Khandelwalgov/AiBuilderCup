"""Small, explicit Gemini wire contract for bounded public-source excerpts.

This changes transport only. Original Extraction/CandidateData, typed condition validation,
source evidence checks and human-review workflow remain authoritative after decoding.
"""

import copy
import json
from typing import Literal

from pydantic import Field

from opportunity_platform.ingestion.schemas import (
    Citation,
    DocumentEvidence,
    FieldCitation,
    validate_evidence,
)

from .contracts import Coverage, RawPolicyExtraction, Strict


class WireCondition(Strict):
    op: Literal["eq", "gte", "lte", "gt", "lt", "in", "document", "unknown"]
    fact: str
    value_json: str = Field(
        max_length=500, description="A JSON scalar/list or null. Never an expression."
    )
    income_period: str
    income_definition: str
    as_of: str


class WireRequirement(Strict):
    description: str
    kind: Literal["eligibility", "document", "procedure", "renewal", "selection", "interpretation"]
    application_context: Literal["all", "fresh", "renewal"]
    combine: Literal["all", "any"]
    conditions: list[WireCondition] = Field(min_length=1, max_length=8)
    evidence: Citation
    subject_context: Literal["person", "business", "household"]


class WireCandidate(Strict):
    title: str
    summary: str
    issuer: str
    category: str
    country: str
    state: str
    district: str
    benefits: str
    restrictions: list[str] = Field(max_length=10)
    required_documents: list[str] = Field(max_length=10)
    document_evidence: list[DocumentEvidence] = Field(max_length=10)
    opens_on: str
    closes_on: str
    apply_url: str
    field_evidence: list[FieldCitation] = Field(max_length=20)
    requirements: list[WireRequirement] = Field(max_length=6)
    review_flags: list[str] = Field(max_length=10)
    missing_fields: list[str] = Field(max_length=20)


class BoundedExtraction(Strict):
    source_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    candidate: WireCandidate
    coverage: list[Coverage] = Field(max_length=24)

    def to_raw(self, source_hash, pages, *, validation_sink=None):
        if self.source_hash != source_hash:
            raise ValueError("Model source hash does not match the preserved snapshot")
        data = self.model_dump(mode="json")
        data.pop("source_hash")
        candidate = data["candidate"]
        nullable = [
            "issuer",
            "country",
            "state",
            "district",
            "benefits",
            "opens_on",
            "closes_on",
            "apply_url",
        ]
        for name in nullable:
            if candidate[name] == "":
                candidate[name] = None
                if name not in candidate["missing_fields"]:
                    candidate["missing_fields"].append(name)
        for requirement in candidate["requirements"]:
            for condition in requirement["conditions"]:

                def invalid_constant(_):
                    raise ValueError("Non-finite JSON rule value")

                condition["value"] = json.loads(
                    condition.pop("value_json"), parse_constant=invalid_constant
                )
                for name in ["fact", "income_period", "income_definition", "as_of"]:
                    if condition[name] == "":
                        condition[name] = None
        marker = "bounded_excerpt_not_complete_policy; human review required"
        candidate["review_flags"] = list(dict.fromkeys([marker, *candidate["review_flags"]]))
        raw = RawPolicyExtraction.model_validate(data)
        if validation_sink is not None:
            validation_sink["original_contract_valid"] = True
        validate_evidence(raw.candidate.candidate(), pages)
        if validation_sink is not None:
            validation_sink["source_passages_valid"] = True
        return raw


def bounded_schema():
    """Inline a finite schema; eliminate reference and nullable/heterogeneous unions.

    additionalProperties=false remains: Google documents support for this keyword.
    Unsupported annotations are omitted only from the wire schema, not validation models.
    """
    schema = BoundedExtraction.model_json_schema()
    definitions = schema.pop("$defs", {})

    def expand(value, stack=()):
        if isinstance(value, list):
            return [expand(item, stack) for item in value]
        if not isinstance(value, dict):
            return value
        if "$ref" in value:
            ref = value["$ref"]
            if not ref.startswith("#/$defs/") or ref in stack:
                raise ValueError("Only finite local schema references are supported")
            return expand(copy.deepcopy(definitions[ref.split("/")[-1]]), (*stack, ref))
        result = {
            key: expand(item, stack)
            for key, item in value.items()
            if key not in {"default", "title", "minLength", "maxLength", "pattern"}
        }
        if result.get("type") == "object":
            result["additionalProperties"] = False
            result["required"] = list(result.get("properties", {}))
        return result

    return expand(schema)
