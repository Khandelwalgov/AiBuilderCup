"""Fail-closed worker-only inference permits, reserved durably before remote requests."""

from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime, timedelta
from decimal import ROUND_CEILING, Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from opportunity_platform.core.config import settings
from opportunity_platform.db.models import InferenceReservation

run_key = ContextVar("inference_run_key", default=None)
fallback_used = ContextVar("inference_fallback_used", default=False)


class BudgetDenied(ValueError):
    pass


@contextmanager
def scope(key):
    token = run_key.set(str(key))
    fallback_token = fallback_used.set(False)
    try:
        yield
    finally:
        run_key.reset(token)
        fallback_used.reset(fallback_token)


def reserve_in(session, provider, model, input_bound, output_bound, *, key=None):
    config = settings()
    key = key or run_key.get()
    if config.gemini_free_worker_enabled and provider == "gemini":
        return reserve_free_in(session, model, input_bound, output_bound, key=key)
    if not (
        config.paid_ai_worker_enabled
        and config.process_role == "ingestion_worker"
        and config.ai_global_budget_usd > 0
        and config.ai_run_budget_usd > 0
        and key
    ):
        raise BudgetDenied(
            "Paid AI is disabled: an authorized worker and positive budgets are required"
        )
    rates = config.ai_price_ceilings.get(f"{provider}:{model}", {})
    if not (rates.get("input", 0) > 0 and rates.get("output", 0) > 0):
        raise BudgetDenied("An explicit reviewed price ceiling is required for this provider/model")
    if not (0 <= input_bound <= 20000 and 0 <= output_bound <= 8192):
        raise BudgetDenied("Worker token bounds exceeded")
    maximum = (
        (
            Decimal(input_bound) * Decimal(str(rates["input"]))
            + Decimal(output_bound) * Decimal(str(rates["output"]))
        )
        / 1_000_000
    ).quantize(
        Decimal("0.00000001"),
        rounding=ROUND_CEILING,
    )
    # One transaction lock serializes accounting across processes/providers and workers.
    session.execute(select(func.pg_advisory_xact_lock(837455019)))
    now = datetime.now(UTC)
    rows = list(session.scalars(select(InferenceReservation)))
    if any(row.status == "usage_exceeded_reservation" for row in rows):
        raise BudgetDenied(
            "Previous provider usage exceeded its reservation; human review required"
        )
    same = [row for row in rows if row.run_key == key]
    day = sum(
        row.created_at >= now.replace(hour=0, minute=0, second=0, microsecond=0) for row in rows
    )
    month = sum(
        row.created_at >= now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        for row in rows
    )
    if (
        len(same) >= config.ai_max_requests_per_run
        or day >= config.ai_daily_call_limit
        or month >= config.ai_monthly_call_limit
    ):
        raise BudgetDenied("Inference request limit exhausted")
    if sum(row.reserved_usd for row in rows) + maximum > Decimal(
        str(config.ai_global_budget_usd)
    ) or sum(row.reserved_usd for row in same) + maximum > Decimal(str(config.ai_run_budget_usd)):
        raise BudgetDenied("Inference spending reservation would exceed the configured budget")
    if provider == "openai" and config.ai_openai_fallback_enabled:
        provider_rows = [row for row in rows if row.provider == "openai"]
        if (
            model != config.ai_openai_fallback_model
            or sum(row.reserved_usd for row in provider_rows) + maximum
            > Decimal(str(config.ai_openai_fallback_budget_usd))
            or sum(row.reserved_usd for row in provider_rows if row.run_key == key) + maximum
            > Decimal(str(config.ai_openai_fallback_run_budget_usd))
        ):
            raise BudgetDenied("OpenAI fallback provider/run ceiling exhausted or model mismatch")
    reservation = InferenceReservation(
        run_key=key,
        provider=provider,
        model=model,
        input_bound=input_bound,
        output_bound=output_bound,
        reserved_usd=maximum,
        prices=rates,
        status="reserved",
    )
    session.add(reservation)
    session.flush()
    return reservation.id


def reserve_free_in(session, model, input_bound, output_bound, *, key):
    from opportunity_platform.ingestion.free_tier import verify

    proof = verify(model)
    config = settings()
    if not key or not (0 <= input_bound <= 20000 and 0 <= output_bound <= 4096):
        raise BudgetDenied("Free worker run identity/token bounds exceeded")
    session.execute(select(func.pg_advisory_xact_lock(837455019)))
    rows = list(session.scalars(select(InferenceReservation)))
    if any(row.status == "usage_exceeded_reservation" for row in rows):
        raise BudgetDenied("Previous usage exceeded token reservation; human review required")
    free = [row for row in rows if row.prices.get("mode") == "verified_free_gemini"]
    now = datetime.now(UTC)
    day = [
        r for r in free if r.created_at >= now.replace(hour=0, minute=0, second=0, microsecond=0)
    ]
    minute = [r for r in free if r.created_at >= now - timedelta(minutes=1)]
    quotas = proof["free_quotas"]
    if (
        len([r for r in rows if r.run_key == key]) >= min(config.ai_max_requests_per_run, 8)
        or len(day) >= min(config.gemini_free_daily_requests, quotas["rpd"])
        or len(minute) >= min(4, quotas["rpm"])
        or sum(r.input_bound for r in minute) + input_bound > quotas["tpm"]
        or sum(r.input_bound + r.output_bound for r in day) + input_bound + output_bound
        > config.gemini_free_daily_tokens
    ):
        raise BudgetDenied("Free worker request/token limit exhausted; no automatic retry")
    reservation = InferenceReservation(
        run_key=key,
        provider="gemini",
        model=model,
        input_bound=input_bound,
        output_bound=output_bound,
        reserved_usd=Decimal(0),
        prices=proof,
        status="reserved",
    )
    session.add(reservation)
    session.flush()
    return reservation.id


@contextmanager
def worker_slot():
    """One Gemini free worker request sequence across processes; fail rather than wait."""
    if not settings().gemini_free_worker_enabled:
        yield
        return
    from opportunity_platform.db.session import engine

    with Session(engine) as session:
        if not session.scalar(select(func.pg_try_advisory_xact_lock(837455020))):
            raise BudgetDenied("Another free Gemini worker is active")
        yield


def reserve(provider, model, input_bound, output_bound):
    # Check default zero policy before opening a connection or constructing a provider client.
    config = settings()
    free = config.gemini_free_worker_enabled and provider == "gemini"
    if not free and (not config.paid_ai_worker_enabled or config.ai_global_budget_usd <= 0):
        raise BudgetDenied("External paid inference budget is zero; no provider request permitted")
    from opportunity_platform.db.session import engine

    with Session(engine) as session:
        identifier = reserve_in(session, provider, model, input_bound, output_bound)
        session.commit()  # A failed/ambiguous HTTP call retains its entire reservation.
        return identifier


def settle(identifier, usage):
    from opportunity_platform.db.session import engine

    with Session(engine) as session:
        row = session.get(InferenceReservation, identifier)
        if not row:
            raise BudgetDenied("Inference reservation missing")
        safe = {
            k: v
            for k, v in usage.items()
            if k in {"input_tokens", "output_tokens", "thinking_tokens", "total_tokens"}
            and type(v) is int
            and v >= 0
        }
        row.usage = safe
        input_tokens = safe.get("input_tokens", row.input_bound)
        output_tokens = safe.get("output_tokens", row.output_bound) + safe.get("thinking_tokens", 0)
        row.recorded_usd = (
            Decimal(input_tokens) * Decimal(str(row.prices["input"]))
            + Decimal(output_tokens) * Decimal(str(row.prices["output"]))
        ) / 1_000_000
        row.status = (
            "usage_exceeded_reservation"
            if row.recorded_usd > row.reserved_usd
            or input_tokens > row.input_bound
            or output_tokens > row.output_bound
            else "recorded"
        )
        session.commit()
