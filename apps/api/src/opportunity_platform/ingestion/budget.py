"""Fail-closed worker-only inference permits, reserved durably before remote requests."""

from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from decimal import ROUND_CEILING, Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from opportunity_platform.core.config import settings
from opportunity_platform.db.models import InferenceReservation

run_key = ContextVar("inference_run_key", default=None)


class BudgetDenied(ValueError):
    pass


@contextmanager
def scope(key):
    token = run_key.set(str(key))
    try:
        yield
    finally:
        run_key.reset(token)


def reserve_in(session, provider, model, input_bound, output_bound, *, key=None):
    config = settings()
    key = key or run_key.get()
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


def reserve(provider, model, input_bound, output_bound):
    # Check default zero policy before opening a connection or constructing a provider client.
    config = settings()
    if not config.paid_ai_worker_enabled or config.ai_global_budget_usd <= 0:
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
            "usage_exceeded_reservation" if row.recorded_usd > row.reserved_usd else "recorded"
        )
        session.commit()
