"""Re-evaluate only previously assessed current opportunities depending on changed fact keys."""

from sqlalchemy import select

from opportunity_platform.db.models import (
    MatchEvaluation,
    Opportunity,
    OpportunityVersion,
    Requirement,
)
from opportunity_platform.eligibility.rules import Rule
from opportunity_platform.subjects.service import SubjectRef


def keys(rule):
    if rule.op == "condition":
        return {rule.condition.fact} if rule.condition.fact else set()
    return set().union(*(keys(child) for child in rule.children))


def affected(session, uid, kind, identifier, changed):
    from opportunity_platform.eligibility.service import check
    from opportunity_platform.planning.service import application_context

    refs = set(
        session.scalars(
            select(OpportunityVersion.opportunity_id)
            .join(MatchEvaluation, MatchEvaluation.version_id == OpportunityVersion.id)
            .where(getattr(MatchEvaluation, kind + "_id") == identifier)
        )
    )
    for oppid in refs:
        opp = session.get(Opportunity, oppid)
        if not opp.published_version_id or opp.is_synthetic:
            continue
        rules = session.scalars(
            select(Requirement).where(Requirement.version_id == opp.published_version_id)
        )
        if any(keys(Rule.model_validate(r.rule)) & changed for r in rules):
            check(
                session,
                uid,
                oppid,
                SubjectRef(kind=kind, id=identifier),
                commit=False,
                application_type=application_context(
                    session, kind, identifier, opp.published_version_id
                ),
            )
    session.flush()
