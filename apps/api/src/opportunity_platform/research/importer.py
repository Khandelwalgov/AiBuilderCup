"""Bounded, idempotent research import. Plan-only; never approves eligibility policies."""

import argparse
import hashlib
import json
import uuid
from pathlib import Path

from sqlalchemy import select

from opportunity_platform.db.models import AuditEvent, ResearchListing, Source, SourceSnapshot, User
from opportunity_platform.ingestion.corpus_policy.contracts import VERSION as CORPUS_ORIGIN
from opportunity_platform.ingestion.corpus_policy.service import authorized
from opportunity_platform.ingestion.corpus_policy.service import identifier as corpus_id

from .schemas import CapturedResearchSource, ResearchInput

VERSION = "research-catalogue-v1"


def digest(value):
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()


def identifier(key):
    return uuid.uuid5(uuid.NAMESPACE_URL, "unclaimed:research:" + key)


def load(path):
    raw = Path(path).read_bytes()
    if len(raw) > 30_000_000:
        raise ValueError("Research bundle exceeds bounded import size")
    data = json.loads(raw)
    if (
        set(data)
        != {"schema_version", "as_of", "inventory", "listings", "exclusions", "captured_sources"}
        or data["schema_version"] != VERSION
    ):
        raise ValueError("Invalid research catalogue bundle")
    if not 1 <= len(data["listings"]) <= 200:
        raise ValueError("A bounded research batch needs one to 200 listings")
    listings = [ResearchInput.model_validate(value) for value in data["listings"]]
    if len({v.key for v in listings}) != len(listings):
        raise ValueError("Duplicate programme/component identity")
    identities = [(v.title.casefold(), v.jurisdiction, v.district) for v in listings]
    if len(set(identities)) != len(identities):
        raise ValueError("Duplicate title/jurisdiction; reconcile programme identity")
    if any(v.as_of.isoformat() != data["as_of"] for v in listings):
        raise ValueError("Catalogue as-of mismatch")
    data["captured_sources"] = [
        CapturedResearchSource.model_validate(v) for v in data["captured_sources"]
    ]
    return data, listings, hashlib.sha256(raw).hexdigest()


def validate_sources(session, listing, projected=None):
    for source in listing.sources:
        row = session.execute(
            select(SourceSnapshot, Source)
            .join(Source)
            .where(SourceSnapshot.id == source.snapshot_id)
        ).first()
        if row is None:
            candidate = (projected or {}).get(source.snapshot_id)
            if candidate is None:
                raise ValueError("Public source snapshot is missing")
            record = candidate.acquisition
            snapshot = SourceSnapshot(
                content_hash=record.sha256,
                source_url=record.canonical_source_url,
                pages=[p.model_dump() for p in candidate.original_pages],
                response_metadata={"origin": VERSION},
            )
            publisher = Source(is_synthetic=False)
        else:
            snapshot, publisher = row
        if publisher.is_synthetic or snapshot.response_metadata.get("origin") not in {
            CORPUS_ORIGIN,
            VERSION,
        }:
            raise ValueError("Only previously captured real official corpus sources are allowed")
        if snapshot.content_hash != source.content_hash or snapshot.source_url != source.source_url:
            raise ValueError("Source hash or exact source URL changed")
        for page in source.pages:
            original = next((p for p in snapshot.pages if p["page"] == page.page), None)
            if original is None:
                raise ValueError("Evidence page not present in original capture")
            if page.basis == "original_extracted_text" and page.text != original["text"]:
                raise ValueError("Original text cannot be silently replaced by an OCR derivative")


def import_listings(session, listings, actor, *, make_public=False, captured_sources=()):
    if actor is None:
        raise ValueError("An existing persisted administrator must authorize the import")
    authorized(session, actor)
    projected = {}
    for capture in captured_sources:
        record = capture.acquisition
        snapshot_id = corpus_id(f"snapshot:{record.document_id}:{record.sha256}")
        if snapshot_id in projected:
            raise ValueError("Duplicate captured source")
        projected[snapshot_id] = capture
        old = session.get(SourceSnapshot, snapshot_id)
        if old and (
            old.content_hash != record.sha256
            or old.source_url != record.canonical_source_url
            or old.pages != [p.model_dump() for p in capture.original_pages]
        ):
            raise ValueError("Existing immutable capture differs")
        publisher = session.get(Source, corpus_id("source:" + record.document_id))
        if publisher and (publisher.is_synthetic or publisher.url != record.canonical_source_url):
            raise ValueError("Captured publisher identity conflict")
    prepared = []
    # All source/schema/conflict checks precede any insert or visibility change.
    for value in sorted(listings, key=lambda row: row.key):
        validate_sources(session, value, projected)
        payload = value.model_dump(mode="json")
        fingerprint = digest(payload)
        existing = session.scalar(
            select(ResearchListing)
            .where(ResearchListing.identity_key == value.key)
            .with_for_update()
        )
        if existing and existing.payload_hash != fingerprint:
            raise ValueError(
                "Existing research identity differs; explicit revision review required"
            )
        prepared.append((value, payload, fingerprint, existing))
    sources_inserted = 0
    for snapshot_id, capture in projected.items():
        if session.get(SourceSnapshot, snapshot_id):
            continue
        record = capture.acquisition
        source_id = corpus_id("source:" + record.document_id)
        if session.get(Source, source_id) is None:
            session.add(
                Source(
                    id=source_id,
                    name=capture.title,
                    authority=capture.authority,
                    url=record.canonical_source_url,
                    is_synthetic=False,
                    status="needs_review",
                    last_checked_at=record.downloaded_at,
                    last_successful_check_at=record.downloaded_at,
                )
            )
            session.flush()
        session.add(
            SourceSnapshot(
                id=snapshot_id,
                source_id=source_id,
                content_hash=record.sha256,
                media_type="application/pdf" if record.format == "pdf" else "text/html",
                source_url=record.canonical_source_url,
                pages=[p.model_dump() for p in capture.original_pages],
                byte_count=record.size_bytes,
                response_metadata={
                    "origin": VERSION,
                    "acquisition_snapshot_id": record.snapshot_id,
                    "captured_at": record.downloaded_at.isoformat(),
                    "blob_path": record.blob_path,
                    "discoveries": record.discoveries,
                    "quality_audit": {
                        "document_type": "administrative_reference",
                        "needs_ocr": True,
                    },
                    "research_derivatives_only": True,
                    "eligibility_policy_publication": False,
                },
            )
        )
        session.flush()
        session.add(
            AuditEvent(
                actor_id=actor.id,
                action="research_source_imported",
                object_id=snapshot_id,
                details={
                    "source_hash": record.sha256,
                    "original_pages_preserved": True,
                    "eligibility_policy_publication": False,
                },
            )
        )
        sources_inserted += 1
    inserted, activated = 0, 0
    for value, payload, fingerprint, existing in prepared:
        if existing:
            if make_public and not existing.is_public:
                existing.is_public = True
                session.add(
                    AuditEvent(
                        actor_id=actor.id,
                        action="research_listing_public",
                        object_id=existing.id,
                        details={
                            "payload_hash": fingerprint,
                            "eligibility_policy_publication": False,
                        },
                    )
                )
                activated += 1
            continue
        row = ResearchListing(
            id=identifier(value.key),
            identity_key=value.key,
            title=value.title,
            summary=value.summary,
            search_text="\n".join(
                [
                    value.title,
                    value.summary,
                    value.benefit or "",
                    *(c.passage for c in value.citations),
                ]
            ),
            authority=value.authority,
            category=value.category,
            jurisdiction=value.jurisdiction,
            availability=value.availability,
            application_status=value.application_status,
            source_snapshot_id=value.sources[0].snapshot_id,
            source_hash=value.sources[0].content_hash,
            payload_hash=fingerprint,
            payload=payload,
            is_public=make_public,
        )
        session.add(row)
        session.add(
            AuditEvent(
                actor_id=actor.id,
                action="research_listing_imported",
                object_id=row.id,
                details={
                    "payload_hash": fingerprint,
                    "source_snapshot_ids": [str(s.snapshot_id) for s in value.sources],
                    "public": make_public,
                    "eligibility_policy_publication": False,
                },
            )
        )
        inserted += 1
    session.flush()
    return {
        "research_listings_inserted": inserted,
        "existing_public_captures_added": sources_inserted,
        "existing_listings_activated": activated,
        "batch_listings": len(listings),
        "public_import": make_public,
        "eligibility_policies_published": 0,
        "paid_ai_calls": 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--make-public", action="store_true")
    parser.add_argument("--approved-bundle-sha256")
    parser.add_argument("--actor-id", type=uuid.UUID)
    args = parser.parse_args()
    data, listings, fingerprint = load(args.bundle)
    if not args.execute:
        print(
            json.dumps(
                {
                    "mode": "plan",
                    "bundle_sha256": fingerprint,
                    "listings": len(listings),
                    "public_visibility_requested": args.make_public,
                    "eligibility_policy_mutations": 0,
                    "inventory": data["inventory"],
                }
            )
        )
        return
    if not args.actor_id or args.approved_bundle_sha256 != fingerprint:
        parser.error(
            "Execution requires an existing administrator and exact approved bundle SHA-256"
        )
    from sqlalchemy.orm import Session

    from opportunity_platform.db.session import engine

    with Session(engine) as session:
        # Serialize imports without changing another programme's source or policy history.
        actor = session.scalar(select(User).where(User.id == args.actor_id).with_for_update())
        result = import_listings(
            session,
            listings,
            actor,
            make_public=args.make_public,
            captured_sources=data["captured_sources"],
        )
        session.commit()
        print(json.dumps(result))


if __name__ == "__main__":
    main()
