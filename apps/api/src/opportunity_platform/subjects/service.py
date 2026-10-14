"""Explicit authorized subject resolution; relationships alone never grant access."""

import uuid
from datetime import date, datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from opportunity_platform.core.errors import APIError
from opportunity_platform.db.models import (
    AuditEvent,
    Business,
    BusinessMembership,
    ConsentGrant,
    Household,
    HouseholdMembership,
    Person,
    ProfileFact,
    Relationship,
)
from opportunity_platform.eligibility.engine import FactRecord
from opportunity_platform.eligibility.rules import FactInput
from opportunity_platform.profiles.service import ProfileWrite, account, person

Kind = Literal["person", "household", "business"]


class SubjectRef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Kind = "person"
    id: uuid.UUID | None = None


class WorkspaceView(BaseModel):
    id: uuid.UUID
    kind: Kind
    name: str
    role: str
    description: str | None = None
    legal_status: str | None = None
    facts: list[FactRecord] = []
    members: list[dict] = []


class HouseholdWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=100)
    primary: bool = True


class DependentWrite(ProfileWrite):
    guardian_responsibility_confirmed: Literal[True]
    relationship: Literal["parent", "legal_guardian"]
    starts_on: date = Field(default_factory=date.today)


class BusinessWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=1000)
    legal_status: Literal["unregistered", "sole_proprietor", "partnership", "company", "other"]
    facts: list[FactInput] = Field(default_factory=list, max_length=10)


def resolve(session: Session, uid: str, ref: SubjectRef, write=False):
    user = account(session, uid)
    if ref.kind == "person":
        obj = session.get(Person, ref.id) if ref.id else person(session, user)
        authorized = obj is not None and obj.user_id == user.id
        if obj is not None and obj.user_id is None:
            now = datetime.now(timezone.utc)
            grant = session.scalar(
                select(ConsentGrant).where(
                    ConsentGrant.person_id == obj.id,
                    ConsentGrant.grantee_user_id == user.id,
                    ConsentGrant.scope == "guardian",
                    ConsentGrant.revoked_at.is_(None),
                    (ConsentGrant.expires_at.is_(None) | (ConsentGrant.expires_at > now)),
                )
            )
            guardian = session.scalar(
                select(Relationship)
                .join(Person, Person.id == Relationship.person_id)
                .where(
                    Person.user_id == user.id,
                    Relationship.related_person_id == obj.id,
                    Relationship.kind.in_(["parent", "legal_guardian"]),
                    Relationship.starts_on <= date.today(),
                    (Relationship.ends_on.is_(None) | (Relationship.ends_on >= date.today())),
                )
            )
            authorized = grant is not None and guardian is not None
        role = "owner" if authorized else None
    elif ref.kind == "household":
        obj = session.get(Household, ref.id)
        role = "owner" if obj and obj.owner_user_id == user.id else None
    else:
        obj = session.get(Business, ref.id)
        member = session.scalar(
            select(BusinessMembership).where(
                BusinessMembership.business_id == ref.id, BusinessMembership.user_id == user.id
            )
        )
        role = member.role if obj and member else None
    if not role or (write and role not in {"owner", "admin", "editor"}):
        raise APIError(
            404, "subject_not_found", "This subject is not available with your permissions."
        )
    return user, obj, role


def subject_facts(session, kind, identifier):
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
            select(ProfileFact)
            .where(getattr(ProfileFact, kind + "_id") == identifier)
            .order_by(ProfileFact.key)
        )
    ]


def replace_facts(session, kind, identifier, facts):
    if len({f.key for f in facts}) != len(facts):
        raise APIError(422, "duplicate_fact", "Each fact may be entered once.")
    if kind == "business" and any(
        f.key
        not in {
            "business_registered",
            "business_turnover",
            "has_registration_certificate",
            "residence_state",
            "residence_district",
        }
        for f in facts
    ):
        raise APIError(
            422, "business_fact_required", "Only supported business facts can be stored here."
        )
    session.execute(
        delete(ProfileFact).where(
            getattr(ProfileFact, kind + "_id") == identifier,
            ProfileFact.origin.in_(["user_supplied", "unknown"]),
        )
    )
    for f in facts:
        session.add(
            ProfileFact(
                **{kind + "_id": identifier},
                key=f.key,
                value=f.value,
                origin="unknown" if f.value is None else "user_supplied",
                verification="unverified",
                valid_from=f.valid_from,
                valid_until=f.valid_until,
                context={
                    "income_period": f.income_period,
                    "income_definition": f.income_definition,
                },
            )
        )
    session.flush()


def view(session, uid, ref):
    user, obj, role = resolve(session, uid, ref)
    members = []
    if ref.kind == "household":
        for membership in session.scalars(
            select(HouseholdMembership).where(
                HouseholdMembership.household_id == obj.id,
                HouseholdMembership.starts_on <= date.today(),
                (
                    HouseholdMembership.ends_on.is_(None)
                    | (HouseholdMembership.ends_on >= date.today())
                ),
            )
        ):
            try:
                _, p, _ = resolve(session, uid, SubjectRef(kind="person", id=membership.person_id))
                members.append({"id": str(p.id), "name": p.display_name, "access": "authorized"})
            except APIError:
                # No private identity or facts for unconnected adults.
                members.append({"access": "restricted", "name": "Adult authorization required"})
    return WorkspaceView(
        id=obj.id,
        kind=ref.kind,
        name=obj.display_name if ref.kind == "person" else obj.name,
        role=role,
        description=getattr(obj, "description", None),
        legal_status=getattr(obj, "legal_status", None),
        facts=subject_facts(session, ref.kind, obj.id),
        members=members,
    )


def list_workspaces(session, uid):
    user = account(session, uid)
    refs = [
        SubjectRef(kind="household", id=h.id)
        for h in session.scalars(select(Household).where(Household.owner_user_id == user.id))
    ]
    refs += [
        SubjectRef(kind="business", id=m.business_id)
        for m in session.scalars(
            select(BusinessMembership).where(BusinessMembership.user_id == user.id)
        )
    ]
    return [view(session, uid, r) for r in refs]


def create_household(session, uid, data):
    user = account(session, uid)
    primary_person = person(session, user)
    h = Household(name=data.name, owner_user_id=user.id)
    session.add(h)
    session.flush()
    session.add(
        HouseholdMembership(household_id=h.id, person_id=primary_person.id, starts_on=date.today())
    )
    if data.primary:
        user.notification_preferences = {
            **user.notification_preferences,
            "primary_household_id": str(h.id),
        }
    session.add(AuditEvent(actor_id=user.id, action="household_created", object_id=h.id))
    session.commit()
    return view(session, uid, SubjectRef(kind="household", id=h.id))


def add_dependent(session, uid, identifier, data):
    user, h, _ = resolve(session, uid, SubjectRef(kind="household", id=identifier), True)
    if data.starts_on > date.today():
        raise APIError(422, "future_guardianship", "Guardianship must already be active.")
    guardian = person(session, user)
    p = Person(display_name=data.display_name)
    session.add(p)
    session.flush()
    session.add_all(
        [
            HouseholdMembership(household_id=h.id, person_id=p.id, starts_on=data.starts_on),
            Relationship(
                person_id=guardian.id,
                related_person_id=p.id,
                kind=data.relationship,
                starts_on=data.starts_on,
            ),
            ConsentGrant(
                person_id=p.id,
                grantee_user_id=user.id,
                scope="guardian",
                granted_at=datetime.now(timezone.utc),
            ),
        ]
    )
    replace_facts(session, "person", p.id, data.facts)
    session.add(
        AuditEvent(actor_id=user.id, action="dependent_created_guardian_asserted", object_id=p.id)
    )
    session.commit()
    return view(session, uid, SubjectRef(kind="person", id=p.id))


def update_person(session, uid, identifier, data):
    user, p, _ = resolve(session, uid, SubjectRef(kind="person", id=identifier), True)
    p.display_name = data.display_name
    replace_facts(session, "person", p.id, data.facts)
    session.add(AuditEvent(actor_id=user.id, action="authorized_person_updated", object_id=p.id))
    session.commit()
    return view(session, uid, SubjectRef(kind="person", id=p.id))


def save_business(session, uid, data, identifier=None):
    if identifier:
        user, b, _ = resolve(session, uid, SubjectRef(kind="business", id=identifier), True)
    else:
        user = account(session, uid)
        person(session, user)
        b = Business(name=data.name, legal_status=data.legal_status)
        session.add(b)
        session.flush()
        session.add(BusinessMembership(business_id=b.id, user_id=user.id, role="owner"))
    b.name, b.description, b.legal_status = data.name, data.description, data.legal_status
    replace_facts(session, "business", b.id, data.facts)
    session.add(AuditEvent(actor_id=user.id, action="business_saved", object_id=b.id))
    session.commit()
    return view(session, uid, SubjectRef(kind="business", id=b.id))
