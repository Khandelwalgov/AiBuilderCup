"""Provisional comparisons of a bounded, cited subset. Never published policy rules.

Every mapping is bound to both the listing's source and the immutable captured page.
Missing or changed evidence disables that comparison rather than guessing a condition.
"""

import json
from datetime import date
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel

from opportunity_platform.db.models import SourceSnapshot
from opportunity_platform.eligibility.engine import Result, evaluate
from opportunity_platform.eligibility.rules import Rule
from opportunity_platform.ingestion.schemas import normalize

from .integration import integrated_pages


class Comparison(BaseModel):
    title: str
    result: Result
    baseline: Result
    changed: bool
    rule: Rule
    snapshot_id: str
    source_hash: str
    source_url: str
    page: int
    passage: str
    action: str | None
    semantic: str
    evidence_available: bool
    gap_kind: str


@lru_cache
def definitions():
    data = json.loads(Path(__file__).with_name("conditions.json").read_text())
    for entry in data["conditions"]:
        Rule.model_validate(entry["rule"])
    return data["conditions"]


def compare(session, row, facts, baseline):
    results = []
    for entry in definitions():
        if entry["listing_key"] != row.identity_key:
            continue
        snapshot = session.get(SourceSnapshot, entry["snapshot_id"])
        bound = any(s["content_hash"] == entry["source_hash"] for s in row.payload["sources"])
        available = bool(
            bound
            and snapshot
            and snapshot.content_hash == entry["source_hash"]
            and snapshot.source_url == entry["source_url"]
            and any(
                p["page"] == entry["page"] and normalize(entry["passage"]) in normalize(p["text"])
                for p in integrated_pages(snapshot)
            )
        )
        rule = Rule.model_validate(entry["rule"])

        def outcome(values):
            return (
                evaluate(rule, values, date.today())
                if available
                else Result(
                    outcome="unknown",
                    reason="The exact captured evidence is unavailable; comparison disabled.",
                )
            )

        result, before = outcome(facts), outcome(baseline)
        key = rule.condition.fact
        gap = (
            "condition_met_by_supplied_facts"
            if result.outcome == "satisfied"
            else "unknown_policy"
            if rule.condition.op == "unknown" or not available
            else "evidence_gap"
            if result.kind == "evidence_gap"
            else "information_gap"
            if result.outcome == "unknown"
            else "potentially_actionable_gap"
            if key in {"student_status", "business_udyam_registered"}
            else "known_substantive_mismatch"
        )
        results.append(
            Comparison(
                **{
                    k: entry[k]
                    for k in [
                        "title",
                        "snapshot_id",
                        "source_hash",
                        "source_url",
                        "page",
                        "passage",
                        "semantic",
                    ]
                },
                rule=rule,
                result=result,
                baseline=before,
                changed=result.outcome != before.outcome,
                action=entry["action"] if available and result.outcome != "satisfied" else None,
                evidence_available=available,
                gap_kind=gap,
            )
        )
    return results


def parent_key(key):
    return "msme-team" if key.startswith("msme-team-") else key
