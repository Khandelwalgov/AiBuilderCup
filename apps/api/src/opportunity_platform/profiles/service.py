import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from opportunity_platform.core.errors import APIError
from opportunity_platform.db.models import AuditEvent, Person, ProfileFact, User
from opportunity_platform.eligibility.engine import FactRecord
from opportunity_platform.eligibility.rules import FactInput
from opportunity_platform.profiles.persistence import reconcile, revision


class ProfileWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    display_name: str = Field(min_length=1, max_length=80)
    facts: list[FactInput] = Field(max_length=48)
    expected_revision: str | None = Field(default=None, min_length=64, max_length=64)

    @model_validator(mode="after")
    def unique_keys(self):
        self.display_name = self.display_name.strip()
        if not self.display_name:
            raise ValueError("A name or nickname is required")
        if len({f.key for f in self.facts}) != len(self.facts):
            raise ValueError("Each fact key may appear only once")
        return self


class ProfileView(BaseModel):
    id: uuid.UUID
    display_name: str
    facts: list[FactRecord]
    revision: str = ""
    last_saved_at: datetime | None = None


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
    facts = facts_for(session, profile)
    saved_at = session.scalar(
        select(AuditEvent.created_at)
        .where(
            AuditEvent.object_id == profile.id,
            AuditEvent.action.in_(["profile_updated", "authorized_person_updated"]),
        )
        .order_by(AuditEvent.created_at.desc())
        .limit(1)
    )
    return ProfileView(
        id=profile.id,
        display_name=profile.display_name,
        facts=facts,
        revision=revision(profile.display_name, facts),
        last_saved_at=saved_at,
    )


def changed_fact_keys(before, after):
    def signature(f):
        context = getattr(f, "context", {})
        return (
            f.value,
            f.valid_from,
            f.valid_until,
            getattr(f, "income_period", context.get("income_period")),
            getattr(f, "income_definition", context.get("income_definition")),
        )

    old = {
        f.key: signature(f)
        for f in before
        if getattr(f, "origin", "user_supplied") in {"user_supplied", "unknown"}
    }
    new = {f.key: signature(f) for f in after}
    return {key for key in old.keys() | new.keys() if old.get(key) != new.get(key)}


def save_profile(session: Session, uid: str, data: ProfileWrite) -> ProfileView:
    user = account(session, uid)
    # Lock the identity row to serialize first-profile creation and replacements.
    session.execute(select(User).where(User.id == user.id).with_for_update())
    profile = session.scalar(select(Person).where(Person.user_id == user.id))
    if profile is None:
        profile = Person(user_id=user.id, display_name=data.display_name)
        session.add(profile)
        session.flush()
    session.execute(select(Person).where(Person.id == profile.id).with_for_update())
    session.refresh(profile)
    before = facts_for(session, profile)
    if data.expected_revision and data.expected_revision != revision(profile.display_name, before):
        raise APIError(
            409,
            "profile_conflict",
            "This profile changed. Reload the saved version before saving your changes.",
        )
    from opportunity_platform.profiles.semantics import validate_person

    validate_person(data.facts, before)
    renamed = profile.display_name != data.display_name
    profile.display_name = data.display_name
    changed_keys = reconcile(session, "person", profile.id, data.facts)
    if renamed or changed_keys or not before:
        # Creation is audited once; identical subsequent saves do not add events.
        existing_audit = session.scalar(
            select(AuditEvent.id).where(AuditEvent.object_id == profile.id).limit(1)
        )
        if renamed or changed_keys or existing_audit is None:
            session.add(
                AuditEvent(
                    actor_id=user.id,
                    action="profile_updated",
                    object_id=profile.id,
                    details={"changed_fields": sorted(changed_keys)},
                )
            )
    session.flush()
    from opportunity_platform.eligibility.refresh import affected

    if changed_keys:
        affected(session, uid, "person", profile.id, changed_keys)
    session.commit()
    return get_profile(session, uid)
