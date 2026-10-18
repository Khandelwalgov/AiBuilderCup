"""Offline account, reservation and worker adapter tests. No genuine model requests."""

import json
from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from sqlalchemy import select

from opportunity_platform.core.config import Settings, settings
from opportunity_platform.db.models import InferenceReservation
from opportunity_platform.ingestion import budget, free_tier
from opportunity_platform.ingestion.corpus_policy.live import GeminiRole


def enable(monkeypatch):
    config = settings()
    for key, value in {
        "process_role": "ingestion_worker",
        "paid_ai_worker_enabled": False,
        "ai_global_budget_usd": 0,
        "ai_run_budget_usd": 0,
        "gemini_free_worker_enabled": True,
        "gemini_free_project_id": "public-project",
        "gemini_free_model": "test-flash",
        "gemini_api_key": "test-only-not-a-real-key",
        "ai_max_requests_per_run": 8,
    }.items():
        monkeypatch.setattr(config, key, value)
    return config


def proof():
    return {
        "input": 0,
        "output": 0,
        "mode": "verified_free_gemini",
        "free_quotas": {"rpm": 5, "rpd": 20, "tpm": 250000},
    }


def test_free_flag_rejected_in_api_or_with_paid_permission():
    with pytest.raises(ValidationError, match="Free Gemini"):
        Settings(_env_file=None, gemini_free_worker_enabled=True)
    with pytest.raises(ValidationError, match="Free Gemini"):
        Settings(
            _env_file=None,
            process_role="ingestion_worker",
            gemini_free_worker_enabled=True,
            gemini_free_project_id="p",
            gemini_free_model="m",
            paid_ai_worker_enabled=True,
        )


def test_free_proof_wrong_model_api_and_unavailable_metadata_fail_closed(monkeypatch):
    config = enable(monkeypatch)
    with pytest.raises(budget.BudgetDenied, match="authorization"):
        free_tier.verify("paid-or-different-model")
    monkeypatch.setattr(config, "process_role", "api")
    with pytest.raises(budget.BudgetDenied, match="authorization"):
        free_tier.verify("test-flash")
    monkeypatch.setattr(config, "process_role", "ingestion_worker")

    def denied(*args):
        raise RuntimeError("secret-must-not-escape")

    monkeypatch.setattr(free_tier, "_proof", denied)
    monkeypatch.setattr(free_tier, "cloud_json", lambda args: {"billingEnabled": False})
    with pytest.raises(budget.BudgetDenied, match="proof unavailable") as error:
        free_tier.verify("test-flash")
    assert "secret" not in str(error.value)


def test_free_durable_zero_reservation_and_strict_request_token_limits(db, monkeypatch):
    config = enable(monkeypatch)
    monkeypatch.setattr(free_tier, "verify", lambda model: proof())
    first = budget.reserve_in(db, "gemini", "test-flash", 1000, 1024, key="one")
    db.commit()
    row = db.get(InferenceReservation, first)
    assert row.reserved_usd == 0 and row.prices["mode"] == "verified_free_gemini"
    monkeypatch.setattr(config, "gemini_free_daily_tokens", 2500)
    with pytest.raises(budget.BudgetDenied, match="limit exhausted"):
        budget.reserve_in(db, "gemini", "test-flash", 1000, 1024, key="two")
    db.rollback()
    monkeypatch.setattr(config, "gemini_free_daily_tokens", 100000)
    for _ in range(3):
        budget.reserve_in(db, "gemini", "test-flash", 100, 0, key="one")
        db.commit()
    with pytest.raises(budget.BudgetDenied, match="limit exhausted"):
        budget.reserve_in(db, "gemini", "test-flash", 100, 0, key="one")
    db.rollback()
    with pytest.raises(budget.BudgetDenied, match="token bounds"):
        budget.reserve_in(db, "gemini", "test-flash", 10, 4097, key="one")
    with pytest.raises(budget.BudgetDenied, match="Paid AI"):
        budget.reserve_in(db, "openai", "not-free", 10, 10, key="one")
    assert len(list(db.scalars(select(InferenceReservation)))) == 4


def test_provider_records_usage_before_invalid_schema_and_never_calls_fallback(monkeypatch):
    from opportunity_platform.ingestion.corpus_policy import live

    enable(monkeypatch)
    monkeypatch.setattr(budget, "reserve", lambda *args: "permit")
    settled = []
    monkeypatch.setattr(budget, "settle", lambda identifier, usage: settled.append(usage))

    class Client:
        def __init__(self, **kwargs):
            self.models = self

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def count_tokens(self, **kwargs):
            return SimpleNamespace(total_tokens=100)

        def generate_content(self, **kwargs):
            assert kwargs["config"].automatic_function_calling.disable
            assert kwargs["config"].response_json_schema
            assert set(json.loads(kwargs["contents"])) == {"untrusted_source_pages"}
            return SimpleNamespace(
                candidates=[SimpleNamespace(finish_reason=live.types.FinishReason.STOP)],
                text="{}",
                usage_metadata=SimpleNamespace(
                    prompt_token_count=100, candidates_token_count=5, thoughts_token_count=0
                ),
            )

    monkeypatch.setattr(live.genai, "Client", Client)
    role = GeminiRole("extractor", "test-flash", max_output_tokens=1024)
    with pytest.raises(ValidationError):
        role._generate(
            live.RawPolicyExtraction,
            "Public source only; untrusted DATA",
            {"untrusted_source_pages": []},
        )
    assert len(settled) == 2 and settled[-1]["provider"] == "gemini"
    assert role.last_usage["output_tokens"] == 5


def test_prompt_schema_and_token_limits_participate_in_idempotency():
    a = GeminiRole("extractor", "test-flash", max_output_tokens=1024)
    b = GeminiRole("extractor", "test-flash", max_output_tokens=2048)
    assert a.input_hash != b.input_hash


def test_gemini_transport_schema_keeps_application_validation():
    from opportunity_platform.ingestion.gemini import structured_schema
    from opportunity_platform.ingestion.schemas import Extraction

    adapted = structured_schema(Extraction)
    assert "minLength" not in json.dumps(adapted)
    assert "minLength" in json.dumps(Extraction.model_json_schema())
    with pytest.raises(ValidationError):
        Extraction.model_validate({"title": "x"})


def authorize_backup(monkeypatch):
    config = settings()
    for key, value in {
        "process_role": "ingestion_worker",
        "paid_ai_worker_enabled": True,
        "ai_openai_fallback_enabled": True,
        "openai_api_key": "sk-test-not-real",
        "ai_openai_fallback_model": "explicit-test-model",
        "ai_global_budget_usd": 0.1,
        "ai_run_budget_usd": 0.05,
        "ai_openai_fallback_budget_usd": 0.02,
        "ai_openai_fallback_run_budget_usd": 0.01,
    }.items():
        monkeypatch.setattr(config, key, value)
    return config


@pytest.mark.parametrize("status", [429, 500, 502, 503, 504])
def test_one_controlled_fallback_only_for_transient_errors(monkeypatch, status):
    from google.genai.errors import APIError

    from opportunity_platform.ingestion.corpus_policy.live import OpenAIRole
    from opportunity_platform.ingestion.providers import controlled_worker_fallback

    config = authorize_backup(monkeypatch)
    calls = []

    def mock_generate(self, *args):
        calls.append(self.model)
        return "mock-candidate", {
            "provider": "openai",
            "model": self.model,
            "external_api_calls": 1,
            "input_tokens": 10,
        }

    monkeypatch.setattr(OpenAIRole, "generate", mock_generate)
    role = GeminiRole("extractor", "test-flash")
    role.last_usage = {"provider": "gemini", "external_api_calls": 2}
    error = APIError(status, {"error": {"message": "test-only outage"}})
    with budget.scope("document"):
        result, usage = controlled_worker_fallback(role, None, "public data", {}, error)
        assert result == "mock-candidate" and usage["provider"] == "openai"
        assert usage["external_api_calls"] == 3
        with pytest.raises(APIError):
            controlled_worker_fallback(role, None, "", {}, error)
    assert calls == ["explicit-test-model"]
    monkeypatch.setattr(config, "ai_openai_fallback_enabled", False)
    with budget.scope("second-document"), pytest.raises(APIError):
        controlled_worker_fallback(role, None, "", {}, error)
    assert len(calls) == 1


@pytest.mark.parametrize("error_kind", ["schema", "citation", "credentials", "model", "budget"])
def test_no_backup_for_quality_credentials_models_or_budget(monkeypatch, error_kind):
    from google.genai.errors import APIError

    from opportunity_platform.ingestion.corpus_policy.live import OpenAIRole
    from opportunity_platform.ingestion.providers import controlled_worker_fallback

    authorize_backup(monkeypatch)

    def forbidden(*args):
        pytest.fail("OpenAI must never run for this error")

    monkeypatch.setattr(OpenAIRole, "generate", forbidden)
    error = {
        "schema": ValueError("invalid schema"),
        "citation": ValueError("citation mismatch"),
        "credentials": APIError(401, {}),
        "model": APIError(404, {}),
        "budget": budget.BudgetDenied("budget exhausted"),
    }[error_kind]
    role = GeminiRole("extractor", "test-flash")
    role.last_usage = {}
    with budget.scope("document"), pytest.raises(type(error)):
        controlled_worker_fallback(role, None, "", {}, error)


def test_openai_provider_and_run_ceiling_reserved_before_request(db, monkeypatch):
    config = authorize_backup(monkeypatch)
    monkeypatch.setattr(
        config, "ai_price_ceilings", {"openai:explicit-test-model": {"input": 1, "output": 2}}
    )
    monkeypatch.setattr(config, "ai_openai_fallback_run_budget_usd", 0.0001)
    with pytest.raises(budget.BudgetDenied, match="provider/run ceiling"):
        budget.reserve_in(db, "openai", "explicit-test-model", 1000, 1000, key="one")
    assert not list(db.scalars(select(InferenceReservation)))


@pytest.mark.parametrize("failure", ["billing", "owner", "quotas", "model"])
def test_actual_proof_builder_rejects_wrong_account_or_missing_free_quota(monkeypatch, failure):
    from opportunity_platform.ingestion import free_tier

    config = enable(monkeypatch)

    def cloud(args):
        if args[0] == "projects":
            return {"projectNumber": "123"}
        return {"billingEnabled": failure == "billing", "billingAccountName": ""}

    def metadata(url, token):
        if "lookupKey" in url:
            return {
                "parent": "projects/"
                + ("999" if failure == "owner" else "123")
                + "/locations/global"
            }
        return {"metrics": []}

    monkeypatch.setattr(free_tier, "cloud_json", cloud)
    monkeypatch.setattr(free_tier, "metadata", metadata)
    monkeypatch.setattr(
        free_tier.subprocess, "run", lambda *a, **k: SimpleNamespace(stdout="mock-token")
    )
    free_tier._proof.cache_clear()
    with pytest.raises(budget.BudgetDenied, match="proof unavailable"):
        free_tier.verify(config.gemini_free_model)
    free_tier._proof.cache_clear()


def test_free_zero_dollar_usage_anomaly_and_concurrency_are_enforced(db, monkeypatch):
    from opportunity_platform.db import session as sessions

    enable(monkeypatch)
    monkeypatch.setattr(free_tier, "verify", lambda model: proof())
    monkeypatch.setattr(sessions, "engine", db.get_bind())
    identifier = budget.reserve_in(db, "gemini", "test-flash", 100, 100, key="one")
    db.commit()
    budget.settle(identifier, {"input_tokens": 101, "output_tokens": 1})
    db.expire_all()
    assert db.get(InferenceReservation, identifier).status == "usage_exceeded_reservation"
    with pytest.raises(budget.BudgetDenied, match="human review"):
        budget.reserve_in(db, "gemini", "test-flash", 1, 1, key="two")
    db.rollback()
    with budget.worker_slot(), pytest.raises(budget.BudgetDenied, match="worker is active"):
        with budget.worker_slot():
            pytest.fail("Concurrent free worker permitted")


def test_free_cached_proof_does_not_skip_fresh_billing_check(monkeypatch):
    enable(monkeypatch)
    monkeypatch.setattr(free_tier, "cloud_json", lambda args: {"billingEnabled": True})
    monkeypatch.setattr(free_tier, "_proof", lambda *a: pytest.fail("Billing-enabled inference"))
    with pytest.raises(budget.BudgetDenied, match="proof unavailable"):
        free_tier.verify("test-flash")
