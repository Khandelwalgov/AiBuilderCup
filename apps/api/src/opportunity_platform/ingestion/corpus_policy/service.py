"""Append-only corpus namespace adapter into existing private ingestion records."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select

from opportunity_platform.core.errors import APIError
from opportunity_platform.db.models import (
    AuditEvent,
    IngestionRun,
    Opportunity,
    OpportunityVersion,
    Source,
    SourceSnapshot,
    User,
)
from opportunity_platform.ingestion.service import source_lock_key

from .archive import TEXT_VERSION
from .contracts import VERSION
from .validation import digest
from .workflow import run_pipeline

NAMESPACE = uuid.UUID("c1f1748a-246c-4e09-8cd1-180ba2816c67")


def identifier(key):
    return uuid.uuid5(NAMESPACE, key)


def authorized(session, actor):
    # Re-read identity/role from the database, not just a caller-supplied User object.
    with session.no_autoflush:
        persisted_role = session.scalar(select(User.is_admin).where(User.id == actor.id))
    if not persisted_role:
        raise APIError(403, "admin_required", "Administrator access is required.")


def locked(session, key):
    acquired = session.scalar(select(func.pg_try_advisory_xact_lock(source_lock_key(session, key))))
    if not acquired:
        raise APIError(409, "corpus_source_busy", "This corpus source is being imported.")


def import_archive(session, audited, actor):
    authorized(session, actor)
    if not audited.technically_ingestible:
        raise APIError(422, "archive_not_ingestible", "Archive integrity/text extraction failed.")
    record = audited.record
    source_id = identifier("source:" + record.document_id)
    locked(session, "corpus-policy:" + record.document_id)
    source = session.get(Source, source_id)
    if source is None:
        source = Source(
            id=source_id,
            name=audited.corrected_title,
            authority=audited.document_issuer,
            url=record.canonical_source_url,
            is_synthetic=False,
            status="needs_review",
            last_checked_at=record.downloaded_at,
            last_successful_check_at=record.downloaded_at,
        )
        session.add(source)
        session.flush()
    elif source.url != record.canonical_source_url:
        raise APIError(
            409, "corpus_identity_conflict", "Document identity changed its canonical URL."
        )
    snapshot_id = identifier(f"snapshot:{record.document_id}:{record.sha256}")
    snapshot = session.get(SourceSnapshot, snapshot_id)
    if snapshot is None:
        if source.last_checked_at is None or record.downloaded_at > source.last_checked_at:
            source.last_checked_at = record.downloaded_at
            source.last_successful_check_at = record.downloaded_at
        source.status = (
            "needs_review"  # keep any previously published version; never auto-publish change
        )
        previous = session.scalar(
            select(SourceSnapshot)
            .where(SourceSnapshot.source_id == source_id)
            .order_by(SourceSnapshot.created_at.desc())
            .limit(1)
        )
        duplicate = session.scalar(
            select(SourceSnapshot)
            .where(
                SourceSnapshot.content_hash == record.sha256,
                SourceSnapshot.source_id != source_id,
            )
            .limit(1)
        )
        snapshot = SourceSnapshot(
            id=snapshot_id,
            source_id=source_id,
            content_hash=record.sha256,
            media_type="application/pdf" if record.format == "pdf" else "text/html",
            source_url=record.canonical_source_url,
            pages=audited.pages,
            byte_count=record.size_bytes,
            response_metadata={
                "origin": VERSION,
                "text_extractor": TEXT_VERSION,
                "acquisition_snapshot_id": record.snapshot_id,
                "acquisition_previous_snapshot_id": record.previous_snapshot_id,
                "previous_imported_snapshot_id": str(previous.id) if previous else None,
                "duplicate_content_snapshot_id": str(duplicate.id) if duplicate else None,
                "blob_path": record.blob_path,
                "captured_at": record.downloaded_at.isoformat(),
                "offline_import_not_new_source_check": True,
                "originating_domain": record.originating_domain,
                "final_url": record.final_url,
                "http_metadata": record.http_metadata,
                "discoveries": record.discoveries,
                "quality_audit": audited.public(),
            },
        )
        session.add(snapshot)
        session.flush()
    if snapshot.source_url != record.canonical_source_url or snapshot.content_hash != record.sha256:
        raise APIError(409, "corpus_snapshot_conflict", "Stored snapshot identity conflicts.")
    if digest(snapshot.pages) != digest(audited.pages):
        raise APIError(
            409,
            "corpus_text_derivative_conflict",
            "Existing immutable text differs; human reconciliation is required.",
        )
    run_id = identifier(f"import:{record.snapshot_id}:{TEXT_VERSION}")
    run = session.get(IngestionRun, run_id)
    if run is None:
        run = IngestionRun(
            id=run_id,
            source_id=source_id,
            snapshot_id=snapshot.id,
            actor_id=actor.id,
            status="archive_imported",
            provider="offline_archive",
            extractor_version=TEXT_VERSION,
            source_hash=record.sha256,
            finished_at=datetime.now(UTC),
            diagnostics={
                "origin": VERSION,
                "acquisition_snapshot_id": record.snapshot_id,
                "acquisition_previous_snapshot_id": record.previous_snapshot_id,
                "quality_audit": audited.public(),
                "publication": "none",
                "source_check": "archived_capture_only",
            },
        )
        session.add(run)
        session.add(
            AuditEvent(
                actor_id=actor.id,
                action="corpus_archive_imported",
                object_id=snapshot.id,
                details={"source_hash": record.sha256, "origin": VERSION},
            )
        )
        session.flush()
    # Caller owns transaction; never commit existing unrelated work implicitly.
    return snapshot, run


def extract_candidate(session, audited, actor, focus, extractor, reviewer, *, max_repairs=1):
    snapshot, _ = import_archive(session, audited, actor)
    # Idempotent within explicit focus/provider/version/budget; no repeated model calls.
    key = digest(
        {
            "snapshot": str(snapshot.id),
            "acquisition_snapshot_id": audited.record.snapshot_id,
            "focus": focus,
            "version": VERSION,
            "extractor": extractor.identity,
            "reviewer": reviewer.identity,
            "max_repairs": max_repairs,
            "prepared_candidate_hash": getattr(extractor, "input_hash", None),
        }
    )
    run_id = identifier("workflow:" + key)
    existing = session.get(IngestionRun, run_id)
    if existing:
        return existing
    run = IngestionRun(
        id=run_id,
        source_id=snapshot.source_id,
        snapshot_id=snapshot.id,
        actor_id=actor.id,
        status="running",
        source_hash=snapshot.content_hash,
        provider=extractor.identity,
        model=getattr(extractor, "model", None),
        extractor_version=VERSION,
    )
    session.add(run)
    session.flush()
    from opportunity_platform.ingestion.budget import scope

    with scope(run.id):
        outcome = run_pipeline(audited, focus, extractor, reviewer, max_repairs=max_repairs)
    run.status = outcome.status
    run.finished_at = datetime.now(UTC)
    run.usage = {
        "calls": sum(u.get("external_api_calls", 0) for u in outcome.usage),
        "attempted_role_calls": outcome.model_calls,
        "per_call": outcome.usage,
    }
    run.diagnostics = {
        "origin": VERSION,
        "focus": focus,
        "reviewer": reviewer.identity,
        "independence": "not_performed"
        if not getattr(reviewer, "invokes_model", True)
        else (
            "separate_requests_same_model"
            if getattr(extractor, "model", None) == getattr(reviewer, "model", None)
            else "separate_provider_or_model_requests"
        ),
        "workflow": outcome.model_dump(mode="json"),
    }
    if outcome.candidate:
        candidate = outcome.candidate.candidate
        opportunity_id = identifier(f"opportunity:{audited.record.document_id}:{digest(focus)}")
        opportunity = session.get(Opportunity, opportunity_id)
        if opportunity is None:
            opportunity = Opportunity(
                id=opportunity_id,
                source_id=snapshot.source_id,
                source_key=f"corpus:{audited.record.document_id}:{digest(focus)}",
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
        fields = candidate.model_dump(
            exclude={
                "requirements",
                "review_flags",
                "missing_fields",
                "field_evidence",
                "document_evidence",
            }
        )
        fields["country"] = candidate.country or "unknown"
        # Existing review architecture remains the only route to publication/Requirement rows.
        draft = OpportunityVersion(
            id=identifier("draft:" + key),
            opportunity_id=opportunity.id,
            version=number,
            **fields,
            publication_state="draft",
            status="needs_review",
            source_url=snapshot.source_url,
            content_hash=snapshot.content_hash,
            snapshot_id=snapshot.id,
            extraction=candidate.model_dump(mode="json"),
            extraction_provider=extractor.identity,
            extraction_model=getattr(extractor, "model", None),
            extractor_version=VERSION,
            extraction_usage=run.usage,
        )
        session.add(draft)
        session.flush()
        run.diagnostics = {
            **run.diagnostics,
            "draft_id": str(draft.id),
            "stored_candidate_hash": digest(candidate),
        }
    session.add(
        AuditEvent(
            actor_id=actor.id,
            action="corpus_policy_review_staged",
            object_id=run.id,
            details={
                "status": outcome.status,
                "repair_cycles": outcome.repair_cycles,
                "publication": "none",
            },
        )
    )
    session.flush()
    return run
