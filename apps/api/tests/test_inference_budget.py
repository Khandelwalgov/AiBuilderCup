from decimal import Decimal

import pytest
from sqlalchemy import func, select

from opportunity_platform.core.config import settings
from opportunity_platform.db.models import InferenceReservation
from opportunity_platform.ingestion.budget import BudgetDenied, reserve, reserve_in


def permit_config(monkeypatch):
    config = settings()
    for key, value in {
        "paid_ai_worker_enabled": True,
        "process_role": "ingestion_worker",
        "ai_global_budget_usd": 0.1,
        "ai_run_budget_usd": 0.05,
        "ai_max_requests_per_run": 2,
        "ai_daily_call_limit": 3,
        "ai_monthly_call_limit": 4,
        "ai_price_ceilings": {"gemini:test-model": {"input": 1, "output": 2}},
    }.items():
        monkeypatch.setattr(config, key, value)


def test_zero_budget_rejects_before_database_or_provider(monkeypatch):
    monkeypatch.setattr(settings(), "ai_global_budget_usd", 0)
    with pytest.raises(BudgetDenied, match="zero"):
        reserve("gemini", "test-model", 10, 10)


def test_global_run_daily_and_provider_limits_are_durable(db, monkeypatch):
    permit_config(monkeypatch)
    first = reserve_in(db, "gemini", "test-model", 1000, 1000, key="run-a")
    db.commit()
    assert db.get(InferenceReservation, first).reserved_usd == Decimal("0.003")
    reserve_in(db, "gemini", "test-model", 1000, 1000, key="run-a")
    db.commit()
    with pytest.raises(BudgetDenied, match="request limit"):
        reserve_in(db, "gemini", "test-model", 1000, 1000, key="run-a")
    db.rollback()
    reserve_in(db, "gemini", "test-model", 1000, 1000, key="run-b")
    db.commit()
    with pytest.raises(BudgetDenied, match="request limit"):
        reserve_in(db, "gemini", "test-model", 1000, 1000, key="run-c")
    db.rollback()
    monkeypatch.setattr(settings(), "ai_daily_call_limit", 20)
    monkeypatch.setattr(settings(), "ai_global_budget_usd", 0.009)
    with pytest.raises(BudgetDenied, match="spending reservation"):
        reserve_in(db, "gemini", "test-model", 1000, 1000, key="run-c")
    db.rollback()
    with pytest.raises(BudgetDenied, match="price ceiling"):
        reserve_in(db, "openai", "not-approved", 1, 1, key="run-c")
    with pytest.raises(BudgetDenied, match="token bounds"):
        reserve_in(db, "gemini", "test-model", 20001, 1, key="run-c")
    assert db.scalar(select(func.count()).select_from(InferenceReservation)) == 3


def test_unapproved_process_and_usage_anomaly_fail_closed(db, monkeypatch):
    permit_config(monkeypatch)
    monkeypatch.setattr(settings(), "process_role", "api")
    with pytest.raises(BudgetDenied, match="authorized worker"):
        reserve_in(db, "gemini", "test-model", 1, 1, key="run")
    monkeypatch.setattr(settings(), "process_role", "ingestion_worker")
    identifier = reserve_in(db, "gemini", "test-model", 1, 1, key="run")
    db.commit()
    db.get(InferenceReservation, identifier).status = "usage_exceeded_reservation"
    db.commit()
    with pytest.raises(BudgetDenied, match="human review"):
        reserve_in(db, "gemini", "test-model", 1, 1, key="run2")
