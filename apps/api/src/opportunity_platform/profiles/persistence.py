"""Stable editable-fact reconciliation; evidence facts and evaluation snapshots survive."""

import hashlib
import json
from datetime import datetime, timezone

from sqlalchemy import select

from opportunity_platform.db.models import ProfileFact


def revision(name, facts, metadata=None):
    payload = {
        "name": name,
        "facts": sorted(
            [f.model_dump(mode="json") for f in facts],
            key=lambda f: (f["key"], str(f.get("id", ""))),
        ),
    }
    if metadata is not None:
        payload["metadata"] = metadata
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def reconcile(session, kind, identifier, facts):
    rows = list(
        session.scalars(
            select(ProfileFact)
            .where(
                getattr(ProfileFact, kind + "_id") == identifier,
                ProfileFact.origin.in_(["user_supplied", "unknown"]),
            )
            .execution_options(populate_existing=True)
        )
    )
    by_key = {}
    changed = set()
    for row in rows:
        if row.key in by_key:
            # Only clean redundant editable rows for this explicitly saved subject.
            session.delete(row)
            changed.add(row.key)
        else:
            by_key[row.key] = row
    incoming = {f.key: f for f in facts}
    for key, row in by_key.items():
        if key not in incoming:
            session.delete(row)
            changed.add(key)
    for fact in facts:
        row = by_key.get(fact.key)
        signature = (
            fact.value,
            fact.valid_from,
            fact.valid_until,
            fact.income_period,
            fact.income_definition,
        )
        previous = (
            None
            if row is None
            else (
                row.value,
                row.valid_from,
                row.valid_until,
                row.context.get("income_period"),
                row.context.get("income_definition"),
            )
        )
        if row is not None and signature == previous:
            continue
        changed.add(fact.key)
        if row is None:
            row = ProfileFact(**{kind + "_id": identifier}, key=fact.key)
            session.add(row)
        history = list(row.context.get("history", [])) if row.context else []
        if previous is not None:
            history.append(
                {
                    "value": row.value,
                    "valid_from": str(row.valid_from) if row.valid_from else None,
                    "valid_until": str(row.valid_until) if row.valid_until else None,
                    "context": {k: v for k, v in row.context.items() if k != "history"},
                }
            )
        row.value = fact.value
        row.origin = "unknown" if fact.value is None else "user_supplied"
        row.verification = "unknown" if fact.value is None else "unverified"
        row.valid_from, row.valid_until = fact.valid_from, fact.valid_until
        row.context = {
            "history": history,
            "semantic_version": "education-v2",
            "income_period": fact.income_period,
            "income_definition": fact.income_definition,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }
    session.flush()
    return changed
