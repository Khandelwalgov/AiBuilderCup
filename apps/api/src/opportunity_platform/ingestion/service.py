import hashlib
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from opportunity_platform.core.config import settings
from opportunity_platform.core.errors import APIError
from opportunity_platform.db.models import (
    IngestionRun,
    Opportunity,
    OpportunityVersion,
    Source,
    SourceSnapshot,
    User,
)
from opportunity_platform.ingestion.adapters import ADAPTERS, FetchFailure, fetch
from opportunity_platform.ingestion.gemini import EXTRACTOR_VERSION, ExtractionFailure, extract
from opportunity_platform.ingestion.schemas import CandidateData, validate_evidence

NAMESPACE = uuid.UUID("ae887c25-9253-4cde-abaf-fd2ca622d69d")


def register(session: Session):
    for key, adapter in ADAPTERS.items():
        identifier = uuid.uuid5(NAMESPACE, key)
        if session.get(Source, identifier) is None:
            session.add(
                Source(
                    id=identifier,
                    name=adapter.name,
                    authority=adapter.authority,
                    url=adapter.url,
                    is_synthetic=False,
                    status="discovered",
                )
            )
    session.flush()


def ingest(session: Session, key: str, actor: User) -> IngestionRun:
    if not actor.is_admin:
        raise APIError(403, "admin_required", "Administrator access is required.")
    adapter = ADAPTERS.get(key)
    if adapter is None:
        raise APIError(404, "source_not_found", "Choose a registered source adapter.")
    source_id = uuid.uuid5(NAMESPACE, key)
    # Cross-process advisory lock covers fetch/extraction and serializes identical runs.
    lock = int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], "big", signed=True)
    acquired = session.scalar(text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": lock})
    if not acquired:
        raise APIError(409, "source_busy", "An ingestion run is already using this source.")
    register(session)
    source = session.get(Source, source_id)
    now = datetime.now(timezone.utc)
    if (
        source.last_checked_at
        and (now - source.last_checked_at).total_seconds()
        < settings().ingestion_min_interval_seconds
    ):
        raise APIError(429, "source_rate_limited", "Wait before checking this source again.")
    source.last_checked_at = now
    run = IngestionRun(
        source_id=source.id,
        actor_id=actor.id,
        status="running",
        model=settings().gemini_model,
        extractor_version=EXTRACTOR_VERSION,
    )
    session.add(run)
    session.flush()
    try:
        fetched = fetch(adapter)
        source.last_successful_check_at = datetime.now(timezone.utc)
        source.status = "parsed"
        digest = hashlib.sha256(fetched.raw).hexdigest()
        snapshot = session.scalar(
            select(SourceSnapshot).where(
                SourceSnapshot.source_id == source.id, SourceSnapshot.content_hash == digest
            )
        )
        previous_run = session.scalar(
            select(IngestionRun)
            .where(
                IngestionRun.source_id == source.id,
                IngestionRun.snapshot_id.is_not(None),
                IngestionRun.id != run.id,
            )
            .order_by(IngestionRun.created_at.desc())
            .limit(1)
        )
        previous_snapshot = (
            session.get(SourceSnapshot, previous_run.snapshot_id) if previous_run else None
        )
        run.changed = previous_snapshot is None or previous_snapshot.content_hash != digest
        if snapshot is None:
            snapshot = SourceSnapshot(
                source_id=source.id,
                content_hash=digest,
                media_type=fetched.media_type,
                source_url=adapter.url,
                pages=fetched.pages,
                byte_count=len(fetched.raw),
                response_metadata=fetched.metadata,
            )
            session.add(snapshot)
            session.flush()
        run.snapshot_id = snapshot.id
        run.http_status = 200
        opportunity = session.scalar(
            select(Opportunity).where(
                Opportunity.source_id == source.id, Opportunity.source_key == key
            )
        )
        existing = (
            session.scalar(
                select(OpportunityVersion)
                .where(
                    OpportunityVersion.opportunity_id == opportunity.id,
                )
                .order_by(OpportunityVersion.version.desc())
                .limit(1)
            )
            if opportunity
            else None
        )
        if existing and existing.snapshot_id == snapshot.id:
            run.status = "unchanged"
        else:
            with session.begin_nested():
                candidate = CandidateData.model_validate(extract(snapshot.pages, adapter.focus))
                try:
                    validate_evidence(candidate, snapshot.pages)
                except ValueError:
                    raise ExtractionFailure("candidate_evidence_validation_failed") from None
                if opportunity is None:
                    opportunity = Opportunity(
                        source_id=source.id,
                        source_key=key,
                        category=candidate.category,
                        is_synthetic=False,
                    )
                    session.add(opportunity)
                    session.flush()
                number = (
                    session.scalar(
                        select(func.max(OpportunityVersion.version)).where(
                            OpportunityVersion.opportunity_id == opportunity.id
                        )
                    )
                    or 0
                ) + 1
                data = candidate.model_dump(mode="json")
                session.add(
                    OpportunityVersion(
                        opportunity_id=opportunity.id,
                        version=number,
                        title=candidate.title,
                        summary=candidate.summary,
                        issuer=candidate.issuer,
                        category=candidate.category,
                        country=candidate.country or "unknown",
                        state=candidate.state,
                        district=candidate.district,
                        benefits=candidate.benefits,
                        restrictions=candidate.restrictions,
                        required_documents=candidate.required_documents,
                        opens_on=candidate.opens_on,
                        closes_on=candidate.closes_on,
                        apply_url=candidate.apply_url,
                        source_url=snapshot.source_url,
                        content_hash=digest,
                        snapshot_id=snapshot.id,
                        extraction=data,
                        publication_state="draft",
                        status="needs_review",
                    )
                )
                run.status = "candidate_created"
                session.flush()
    except FetchFailure as error:
        source.status = (
            "source_unreachable"
            if error.code in {"source_http_error", "timeout", "network_or_tls_error"}
            else "needs_review"
        )
        run.status = "fetch_failed"
        run.diagnostic_code = error.code
        run.http_status = error.status
    except ExtractionFailure as error:
        run.status = (
            "extraction_blocked" if error.code == "gemini_not_configured" else "extraction_failed"
        )
        run.diagnostic_code = error.code
        source.status = "needs_review"
    except Exception:
        # The candidate savepoint rolls back while retaining public source evidence.
        # Never expose exception messages or prompts in run diagnostics.
        run.status = "extraction_failed"
        run.diagnostic_code = "ingestion_internal_error"
        source.status = "needs_review"
    run.finished_at = datetime.now(timezone.utc)
    session.commit()
    return run


if __name__ == "__main__":
    import argparse

    from opportunity_platform.db.session import engine
    from opportunity_platform.profiles.service import require_admin

    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=list(ADAPTERS), required=True)
    parser.add_argument("--actor-uid", required=True)
    args = parser.parse_args()
    with Session(engine) as session:
        actor = require_admin(session, args.actor_uid)
        result = ingest(session, args.source, actor)
        print(f"Run {result.id}: {result.status}; diagnostic={result.diagnostic_code or 'none'}")
