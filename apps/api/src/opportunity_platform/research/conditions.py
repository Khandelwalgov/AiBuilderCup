"""Provisional comparisons of a bounded, cited subset. Never published policy rules.

Every mapping is bound to both the listing's source and the immutable captured page.
Missing or changed evidence disables that comparison rather than guessing a condition.
"""

import json
from datetime import date
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field

from opportunity_platform.db.models import SourceSnapshot
from opportunity_platform.eligibility.engine import Result, evaluate
from opportunity_platform.eligibility.rules import Rule
from opportunity_platform.ingestion.schemas import normalize

from .integration import integrated_pages


class SourceCondition(BaseModel):
    title: str
    rule: Rule
    snapshot_id: str
    source_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_url: str
    page: int = Field(ge=1, le=10000)
    passage: str = Field(min_length=1)
    action: str | None
    semantic: str
    evidence_available: bool
    applicability: str = "Captured source baseline; current application availability is unverified."
    exceptions: list[str] = []
    unresolved_conditions: list[str] = []
    interpretation_note: str | None = None
    visual_review_image_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")


class Comparison(SourceCondition):
    result: Result
    baseline: Result
    changed: bool
    gap_kind: str


def leaves(rule):
    """Keep AND/OR trees intact for evaluation; inspect their leaves only for explanations."""
    return (
        [rule.condition]
        if rule.op == "condition"
        else [leaf for child in rule.children for leaf in leaves(child)]
    )


@lru_cache
def definitions():
    data = json.loads(Path(__file__).with_name("conditions.json").read_text())
    for entry in data["conditions"]:
        SourceCondition.model_validate({**entry, "evidence_available": False})
    return data["conditions"]


def compare(session, row, facts, baseline):
    results = []
    for entry in definitions():
        if entry["listing_key"] != row.identity_key:
            continue
        snapshot = session.get(SourceSnapshot, entry["snapshot_id"])
        bound = any(
            s["content_hash"] == entry["source_hash"]
            and s["source_url"] == entry["source_url"]
            and str(s["snapshot_id"]) == entry["snapshot_id"]
            for s in row.payload["sources"]
        )
        available = bool(
            bound
            and snapshot
            and snapshot.content_hash == entry["source_hash"]
            and snapshot.source_url == entry["source_url"]
            and any(
                p["page"] == entry["page"]
                and normalize(entry["passage"]) in normalize(p["text"])
                and (
                    not entry.get("visual_review_image_sha256")
                    or p.get("image_sha256") == entry["visual_review_image_sha256"]
                )
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
        conditions = leaves(rule)
        keys = {condition.fact for condition in conditions}
        gap = (
            "condition_met_by_supplied_facts"
            if result.outcome == "satisfied"
            else "unknown_policy"
            if (result.outcome == "unknown" and not result.missing) or not available
            else "evidence_gap"
            if result.kind == "evidence_gap"
            else "information_gap"
            if result.outcome == "unknown"
            else "potentially_actionable_gap"
            if keys
            <= {"student_status", "business_udyam_registered", "business_udyam_assist_registered"}
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
                applicability=entry.get(
                    "applicability", Comparison.model_fields["applicability"].default
                ),
                exceptions=entry.get("exceptions", []),
                unresolved_conditions=entry.get("unresolved_conditions", []),
                interpretation_note=entry.get("interpretation_note"),
                visual_review_image_sha256=entry.get("visual_review_image_sha256"),
            )
        )
    return results


def parent_key(key):
    return "msme-team" if key.startswith("msme-team-") else key
