import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from opportunity_platform.core.errors import APIError
from opportunity_platform.db.models import AuditEvent, Person, ProfileFact, User
from opportunity_platform.eligibility.engine import FactRecord
from opportunity_platform.eligibility.rules import FactInput


class ProfileWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    display_name: str = Field(min_length=1, max_length=80)
    facts: list[FactInput] = Field(max_length=30)

    @model_validator(mode="after")
    def unique_keys(self):
        if len({f.key for f in self.facts}) != len(self.facts):
            raise ValueError("Each fact key may appear only once")
        return self


class ProfileView(BaseModel):
    id: uuid.UUID
    display_name: str
    facts: list[FactRecord]


class AccountView(BaseModel):
    uid: str
    is_admin: bool


def account(session: Session, uid: str) -> User:
    # Atomic account resolution; only a validated Firebase UID reaches this function.
    session.execute(
        insert(User)
        .values(firebase_uid=uid, language="en", notification_preferences={})
        .on_conflict_do_nothing(index_elements=[User.firebase_uid])
    )
    session.flush()
    return session.scalar(select(User).where(User.firebase_uid == uid))


def require_admin(session: Session, uid: str) -> User:
    user = session.scalar(select(User).where(User.firebase_uid == uid))
    if user is None or not user.is_admin:
        raise APIError(403, "admin_required", "Administrator access is required.")
    return user


def person(session: Session, user: User) -> Person:
    result = session.scalar(select(Person).where(Person.user_id == user.id))
    if result is None:
        raise APIError(404, "profile_not_found", "Create your personal profile first.")
    return result


def facts_for(session: Session, profile: Person) -> list[FactRecord]:
    return [
        FactRecord(
            id=str(f.id),
            key=f.key,
            value=f.value,
            origin=f.origin,
            verification=f.verification,
            valid_from=f.valid_from,
            valid_until=f.valid_until,
            context=f.context,
        )
        for f in session.scalars(
            select(ProfileFact).where(ProfileFact.person_id == profile.id).order_by(ProfileFact.key)
        )
    ]


def get_profile(session: Session, uid: str) -> ProfileView:
    user = account(session, uid)
    profile = person(session, user)
    return ProfileView(
        id=profile.id, display_name=profile.display_name, facts=facts_for(session, profile)
    )


def save_profile(session: Session, uid: str, data: ProfileWrite) -> ProfileView:
    user = account(session, uid)
    # Lock the identity row to serialize first-profile creation and replacements.
    session.execute(select(User).where(User.id == user.id).with_for_update())
    profile = session.scalar(select(Person).where(Person.user_id == user.id))
    if profile is None:
        profile = Person(user_id=user.id, display_name=data.display_name)
        session.add(profile)
        session.flush()
    profile.display_name = data.display_name
    # Replace only user-owned user-supplied facts. Never overwrite verified evidence.
    session.execute(
        delete(ProfileFact).where(
            ProfileFact.person_id == profile.id,
            ProfileFact.origin.in_(["user_supplied", "unknown"]),
        )
    )
    for fact in data.facts:
        session.add(
            ProfileFact(
                person_id=profile.id,
                key=fact.key,
                value=fact.value,
                origin="unknown" if fact.value is None else "user_supplied",
                verification="unknown" if fact.value is None else "unverified",
                valid_from=fact.valid_from,
                valid_until=fact.valid_until,
                context={
                    "income_period": fact.income_period,
                    "income_definition": fact.income_definition,
                    "recorded_at": datetime.now(timezone.utc).isoformat(),
                },
            )
        )
    session.add(
        AuditEvent(
            actor_id=user.id,
            action="profile_updated",
            object_id=profile.id,
            details={"fact_count": len(data.facts)},
        )
    )
    session.commit()
    return get_profile(session, uid)
