"""All provider responses and HTTP transports here are simulated, never genuine Gemini."""

import copy
import json
from datetime import date
from types import SimpleNamespace

import httpx
import pytest
from google.genai.errors import ClientError
from pydantic import ValidationError
from test_corpus_policy import audited

from opportunity_platform.eligibility.engine import FactRecord, evaluate
from opportunity_platform.ingestion.corpus_policy.live import GeminiRole, safe_field_errors
from opportunity_platform.ingestion.corpus_policy.transport import (
    BoundedExtraction,
    PayloadEnvelope,
    payload_schema,
)
from opportunity_platform.operations.gemini_document_demo import attempt_key
from opportunity_platform.operations.gemini_transport_audit import serialize


def sample():
    source = audited("Public scholarship guidelines. Applicants must be at least 18 years old.")
    citation = {
        "source_url": source.record.canonical_source_url,
        "page": 1,
        "passage": source.pages[0]["text"],
        "language": "original",
        "basis": "explicit",
    }
    candidate = {
        "title": "Public scholarship guidelines",
        "summary": source.pages[0]["text"],
        "category": "education",
        **{
            k: ""
            for k in [
                "issuer",
                "country",
                "state",
                "district",
                "benefits",
                "opens_on",
                "closes_on",
                "apply_url",
            ]
        },
        "restrictions": [],
        "required_documents": [],
        "document_evidence": [],
        "field_evidence": [
            {"field": k, "citation": citation} for k in ["title", "summary", "category"]
        ],
        "requirements": [
            {
                "description": "Applicants must be at least 18 years old.",
                "kind": "eligibility",
                "application_context": "all",
                "combine": "all",
                "conditions": [
                    {
                        "op": "gte",
                        "fact": "age",
                        "value_json": "18",
                        "income_period": "",
                        "income_definition": "",
                        "as_of": "",
                    }
                ],
                "evidence": citation,
                "subject_context": "person",
            }
        ],
        "review_flags": [],
        "missing_fields": [],
    }
    return source, {
        "source_hash": source.record.sha256,
        "candidate": candidate,
        "coverage": [
            {
                "clause_id": c.id,
                "disposition": "represented",
                "requirement_indexes": [0],
                "field_names": [],
                "reason": "The cited age condition represents this clause.",
            }
            for c in source.clauses
        ],
    }


@pytest.mark.parametrize("model", ["gemini-3.5-flash-lite", "gemini-3.8-flash"])
def test_real_sdk_wire_serialization_is_offline_finite_and_tool_free(model):
    body = serialize(model, BoundedExtraction)
    assert set(body) == {"contents", "systemInstruction", "generationConfig"}
    config = body["generationConfig"]
    assert set(config) == {"maxOutputTokens", "responseMimeType", "responseJsonSchema"}
    assert config["maxOutputTokens"] == 4096 and config["responseMimeType"] == "application/json"
    assert config["responseJsonSchema"] == payload_schema()
    assert set(config["responseJsonSchema"]["properties"]) == {"payload_json"}

    def validate(node):
        if isinstance(node, dict):
            assert not set(node) & {"anyOf", "oneOf", "$defs", "$ref", "default"}
            if node.get("type") == "object":
                assert node["additionalProperties"] is False
                # Every material field is explicit, including empty/unknown markers.
                assert set(node["required"]) == set(node["properties"])
            for value in node.values():
                validate(value)
        elif isinstance(node, list):
            for value in node:
                validate(value)

    validate(config["responseJsonSchema"])


def test_normalization_preserves_original_contract_unknowns_and_human_gate():
    source, wire = sample()
    raw = BoundedExtraction.model_validate(wire).to_raw(source.record.sha256, source.pages)
    normalized = raw.normalized().candidate
    assert normalized.closes_on is None and normalized.apply_url is None
    assert "closes_on" in normalized.missing_fields
    assert "human review" in normalized.review_flags[0]
    rule = normalized.requirements[0].rule
    assert evaluate(rule, [], date.today()).outcome == "unknown"
    assert (
        evaluate(rule, [FactRecord(id="fictional-age", key="age", value=17)], date.today()).outcome
        == "unsatisfied"
    )


@pytest.mark.parametrize(
    "defect",
    [
        "missing_field",
        "missing_evidence",
        "fabricated",
        "wrong_page",
        "wrong_url",
        "wrong_hash",
        "invalid_fact",
        "wrong_value_type",
        "invalid_json",
        "nonfinite",
    ],
)
def test_generated_transport_cannot_bypass_original_schema_or_source_evidence(defect):
    source, data = sample()
    data = copy.deepcopy(data)
    candidate = data["candidate"]
    condition = candidate["requirements"][0]["conditions"][0]
    if defect == "missing_field":
        del candidate["field_evidence"]
    elif defect == "missing_evidence":
        candidate["field_evidence"] = []
    elif defect == "fabricated":
        candidate["requirements"][0]["evidence"]["passage"] = "An invented government benefit."
    elif defect == "wrong_page":
        candidate["requirements"][0]["evidence"]["page"] = 99
    elif defect == "wrong_url":
        candidate["requirements"][0]["evidence"]["source_url"] = "https://wrong.gov.in/no.pdf"
    elif defect == "wrong_hash":
        data["source_hash"] = "0" * 64
    elif defect == "invalid_fact":
        condition["fact"] = "invented_sensitive_profile_fact"
    elif defect == "wrong_value_type":
        condition["value_json"] = '"18"'
    elif defect == "invalid_json":
        condition["value_json"] = '__import__("os").system("false")'
    elif defect == "nonfinite":
        condition["value_json"] = "NaN"
    with pytest.raises((ValueError, ValidationError)):
        BoundedExtraction.model_validate(data).to_raw(source.record.sha256, source.pages)


def test_attempt_identity_excludes_proof_timestamp_but_includes_evidence_model_and_prompt():
    report = {
        "source": {"sha256": "a" * 64},
        "selected_text_sha256": "b" * 64,
        "selected_pages": [1, 12],
        "model": "explicit-model",
        "independent_review_authorized": False,
        "maximum_role_requests": 1,
        "account_proof": {"verified_at_unix": 1},
    }
    first = attempt_key(report, "schema-v1", "scope")
    report["account_proof"]["verified_at_unix"] = 999
    assert attempt_key(report, "schema-v1", "scope") == first
    assert attempt_key(report, "schema-v2", "scope") != first
    report["selected_text_sha256"] = "c" * 64
    assert attempt_key(report, "schema-v1", "scope") != first


def test_sanitized_field_diagnostics_retain_paths_without_credentials():
    error = ClientError(
        400,
        {
            "error": {
                "details": [
                    {
                        "@type": "type.googleapis.com/google.rpc.BadRequest",
                        "fieldViolations": [
                            {
                                "field": "generation_config.response_json_schema",
                                "description": "bad schema secret-key https://private.example/key",
                            },
                            {"field": "https://private.example", "description": "discard"},
                        ],
                    }
                ]
            }
        },
    )
    details = safe_field_errors(error, "secret-key")
    assert details == [
        {
            "field": "generation_config.response_json_schema",
            "description": "bad schema [REDACTED] [URL]",
        }
    ]
    assert safe_field_errors(SimpleNamespace(details={"error": {"details": None}}), "") == []


def test_provider_stage_is_captured_for_count_and_generation_errors(monkeypatch):
    from contextlib import nullcontext

    from opportunity_platform.core.config import settings
    from opportunity_platform.ingestion import budget
    from opportunity_platform.ingestion.corpus_policy import live

    monkeypatch.setattr(settings(), "process_role", "ingestion_worker")
    monkeypatch.setattr(settings(), "gemini_free_worker_enabled", True)
    monkeypatch.setattr(settings(), "gemini_api_key", "offline-secret")
    monkeypatch.setattr(budget, "worker_slot", nullcontext)
    monkeypatch.setattr(budget, "reserve", lambda *args: "mock-reservation")
    monkeypatch.setattr(budget, "settle", lambda *args: None)

    def handler(request):
        if request.url.path.endswith(":countTokens"):
            return httpx.Response(200, json={"totalTokens": 100})
        return httpx.Response(400, json={"error": {"code": 400, "message": "invalid argument"}})

    # The official SDK is real; only its network transport is replaced.
    real_client = live.genai.Client
    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        monkeypatch.setattr(
            live.genai,
            "Client",
            lambda **kwargs: real_client(
                api_key="dummy",
                vertexai=False,
                http_options=live.types.HttpOptions(
                    httpx_client=http, retry_options=live.types.HttpRetryOptions(attempts=1)
                ),
            ),
        )
        role = GeminiRole("extractor", "explicit-model", bounded_transport=True)
        with pytest.raises(ClientError):
            role.generate(BoundedExtraction, "public source only", {"untrusted_source_pages": []})
    assert role.last_usage["request_stage"] == "generate_content"
    assert role.last_usage["field_errors"] == []
    assert "offline-secret" not in json.dumps(role.last_usage)


def test_exact_quote_does_not_validate_a_fabricated_numeric_threshold():
    from opportunity_platform.ingestion.corpus_policy.validation import validate

    source, wire = sample()
    wire["candidate"]["requirements"][0]["conditions"][0]["value_json"] = "99"
    raw = BoundedExtraction.model_validate(wire).to_raw(source.record.sha256, source.pages)
    _, issues = validate(raw.normalized().model_dump(mode="json"), source)
    assert "numerical_value_not_in_clause" in {issue.code for issue in issues}
    assert any(issue.severity in {"error", "critical"} for issue in issues)


def test_bounded_role_uses_existing_review_workflow_and_never_publishes(monkeypatch):
    from opportunity_platform.ingestion.corpus_policy.contracts import RawPolicyExtraction
    from opportunity_platform.ingestion.corpus_policy.prepared import PendingIndependentReview
    from opportunity_platform.ingestion.corpus_policy.workflow import run_pipeline

    source, wire = sample()
    role = GeminiRole("extractor", "explicit-model", bounded_transport=True)

    def response(schema, system, payload):
        assert schema is BoundedExtraction
        assert payload["source_hash"] == source.record.sha256
        assert "allowed_fact_keys" in payload
        assert set(payload) <= {
            "focus",
            "untrusted_source_pages",
            "clauses",
            "feedback",
            "previous_untrusted_candidate",
            "source_hash",
            "wire_instructions",
            "allowed_fact_keys",
        }
        role.last_usage = {
            "provider": "gemini",
            "model": role.model,
            "generation_succeeded": True,
            "transport_schema_valid": True,
            "external_api_calls": 0,
            "simulated": True,
        }
        return BoundedExtraction.model_validate(wire), role.last_usage

    monkeypatch.setattr(role, "generate", response)
    outcome = run_pipeline(
        source, "Fictional offline fixture", role, PendingIndependentReview(), max_repairs=0
    )
    assert outcome.status == "human_escalation"
    assert outcome.candidate is not None
    assert outcome.human_required
    assert outcome.stages[0].independent_review is None
    assert isinstance(
        BoundedExtraction.model_validate(wire).to_raw(source.record.sha256, source.pages),
        RawPolicyExtraction,
    )


@pytest.mark.parametrize("defect", ["none", "fabricated", "incomplete"])
def test_full_bounded_sdk_response_stages_are_truthful_with_mocked_http(monkeypatch, defect):
    from contextlib import nullcontext

    from opportunity_platform.core.config import settings
    from opportunity_platform.ingestion import budget
    from opportunity_platform.ingestion.corpus_policy import live

    source, wire = sample()
    if defect == "fabricated":
        wire["candidate"]["requirements"][0]["evidence"]["passage"] = "Unsupported claim."
    if defect == "incomplete":
        del wire["candidate"]["field_evidence"]
        wire["candidate"]["untrusted-secret-extra-field"] = "never-record-this-value"
    monkeypatch.setattr(settings(), "process_role", "ingestion_worker")
    monkeypatch.setattr(settings(), "gemini_free_worker_enabled", True)
    monkeypatch.setattr(settings(), "gemini_api_key", "dummy-not-real")
    monkeypatch.setattr(budget, "worker_slot", nullcontext)
    reservations = []

    def reserve(*args):
        reservations.append(args)
        return "mock-reservation"

    monkeypatch.setattr(budget, "reserve", reserve)
    settlements = []
    monkeypatch.setattr(budget, "settle", lambda *args: settlements.append(args))
    captured = []

    def handler(request):
        captured.append(str(request.url.path))
        if request.url.path.endswith(":countTokens"):
            counted_request = json.loads(request.content)
            assert "Inner schema:" in json.dumps(counted_request)
            assert "value_json" in json.dumps(counted_request)
            return httpx.Response(200, json={"totalTokens": 100})
        body = json.loads(request.content)
        assert body["generationConfig"]["responseJsonSchema"] == payload_schema()
        system = body["systemInstruction"]["parts"][0]["text"]
        content = body["contents"][0]["parts"][0]["text"]
        assert reservations[0][2] >= len((system + content).encode())
        assert not set(body) & {"tools", "toolConfig"}
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {
                            "parts": [{"text": json.dumps({"payload_json": json.dumps(wire)})}]
                        },
                        "finishReason": "STOP",
                    }
                ],
                "usageMetadata": {"promptTokenCount": 100, "candidatesTokenCount": 200},
                "modelVersion": "simulated-version",
            },
        )

    real_client = live.genai.Client
    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        monkeypatch.setattr(
            live.genai,
            "Client",
            lambda **kwargs: real_client(
                api_key="dummy",
                vertexai=False,
                http_options=live.types.HttpOptions(
                    httpx_client=http, retry_options=live.types.HttpRetryOptions(attempts=1)
                ),
            ),
        )
        role = GeminiRole("extractor", "explicit-model", bounded_transport=True)
        if defect == "incomplete":
            with pytest.raises(ValidationError):
                role.extract(source, "Fictional offline fixture")
        elif defect == "fabricated":
            with pytest.raises(ValueError, match="Citation"):
                role.extract(source, "Fictional offline fixture")
        else:
            candidate, usage = role.extract(source, "Fictional offline fixture")
            assert candidate.candidate.closes_on is None
            assert usage["source_passages_valid"]
    assert role.last_usage["generation_succeeded"]
    assert role.last_usage["transport_schema_valid"]
    if defect == "incomplete":
        assert not role.last_usage.get("bounded_payload_valid", False)
        assert {
            (item["type"], tuple(item["location"])) for item in role.last_usage["validation_errors"]
        } == {
            ("missing", ("candidate", "field_evidence")),
            ("extra_forbidden", ("candidate", "[unrecognized_field]")),
        }
        assert "untrusted-secret" not in json.dumps(role.last_usage)
        assert "never-record-this-value" not in json.dumps(role.last_usage)
    else:
        assert role.last_usage["bounded_payload_valid"]
        assert role.last_usage["original_contract_valid"]
    assert role.last_usage.get("source_passages_valid", False) is (defect == "none")
    assert len(settlements) == 2
    assert settlements[-1][1]["input_tokens"] == 100
    assert settlements[-1][1]["output_tokens"] == 200
    assert role.last_usage["model_version"] == "simulated-version"
    assert len(captured) == 2


@pytest.mark.parametrize(
    "response",
    [
        "{}",
        '{"payload_json": {}}',
        '{"payload_json": "{}", "unexpected": true}',
        '{"payload_json": "not JSON"}',
        '{"payload_json": "{}"}',
    ],
)
def test_payload_envelope_rejects_malformed_or_incomplete_inner_output(response):
    with pytest.raises(ValidationError):
        envelope = PayloadEnvelope.model_validate_json(response)
        BoundedExtraction.model_validate_json(envelope.payload_json)


def test_payload_envelope_keeps_source_validation_and_unknowns():
    source, wire = sample()
    envelope = PayloadEnvelope.model_validate_json(json.dumps({"payload_json": json.dumps(wire)}))
    bounded = BoundedExtraction.model_validate_json(envelope.payload_json)
    candidate = bounded.to_raw(source.record.sha256, source.pages).normalized().candidate
    assert candidate.closes_on is None
    assert "human review" in candidate.review_flags[0]
    wire["candidate"]["requirements"][0]["evidence"]["page"] = 99
    envelope = PayloadEnvelope.model_validate_json(json.dumps({"payload_json": json.dumps(wire)}))
    with pytest.raises(ValueError, match="Citation"):
        BoundedExtraction.model_validate_json(envelope.payload_json).to_raw(
            source.record.sha256, source.pages
        )


def test_envelope_is_exclusive_to_bounded_gemini_and_fingerprinted():
    from opportunity_platform.ingestion.corpus_policy.contracts import AIReview, RawPolicyExtraction
    from opportunity_platform.ingestion.corpus_policy.live import generation_config

    for schema in [AIReview, RawPolicyExtraction]:
        assert generation_config(schema, 1024).response_json_schema != payload_schema()
    bounded = GeminiRole("extractor", "explicit-model", bounded_transport=True)
    ordinary = GeminiRole("extractor", "explicit-model")
    assert bounded.input_hash != ordinary.input_hash
