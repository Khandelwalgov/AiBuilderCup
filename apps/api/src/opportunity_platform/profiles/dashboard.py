"""Read-only personal dashboard counts; never runs evaluation or an external model."""

from pydantic import BaseModel
from sqlalchemy import distinct, func, select

from opportunity_platform.db.models import (
    ActionDependency,
    ActionItem,
    BusinessMembership,
    Household,
    MatchEvaluation,
    Opportunity,
    OpportunityVersion,
    Person,
    Requirement,
)
from opportunity_platform.profiles.service import account


class DashboardView(BaseModel):
    profile_name: str | None
    personal_pending_actions: int
    assessed_current_opportunities: int
    households: int
    businesses: int
    review_candidates: int | None


def summary(session, uid):
    user = account(session, uid)
    person = session.scalar(select(Person).where(Person.user_id == user.id))
    actions = 0
    matches = 0
    if person:
        actions = session.scalar(
            select(func.count(distinct(ActionItem.id)))
            .join(ActionDependency, ActionDependency.action_id == ActionItem.id)
            .join(Requirement, Requirement.id == ActionDependency.requirement_id)
            .join(Opportunity, Opportunity.published_version_id == Requirement.version_id)
            .where(
                ActionItem.person_id == person.id,
                ActionItem.status == "pending",
                Opportunity.is_synthetic.is_(False),
            )
        )
        matches = session.scalar(
            select(func.count(distinct(MatchEvaluation.version_id)))
            .join(Opportunity, Opportunity.published_version_id == MatchEvaluation.version_id)
            .where(MatchEvaluation.person_id == person.id, Opportunity.is_synthetic.is_(False))
        )
    return DashboardView(
        profile_name=person.display_name if person else None,
        personal_pending_actions=actions,
        assessed_current_opportunities=matches,
        households=session.scalar(
            select(func.count()).select_from(Household).where(Household.owner_user_id == user.id)
        ),
        businesses=session.scalar(
            select(func.count())
            .select_from(BusinessMembership)
            .where(BusinessMembership.user_id == user.id)
        ),
        review_candidates=session.scalar(
            select(func.count())
            .select_from(OpportunityVersion)
            .where(
                OpportunityVersion.publication_state == "draft",
                OpportunityVersion.extraction.is_not(None),
            )
        )
        if user.is_admin
        else None,
    )
