"""Hash-bound append-only correction of existing drafts; never publishes.

Offline plan is the default. Staging requires an existing persisted administrator,
unchanged baseline drafts and unchanged original snapshot text. Held policies are
never staged. No network, extraction model, OCR or published catalogue writes are performed.
"""

import argparse
import hashlib
import json
import uuid
from datetime import UTC, date, datetime
from pathlib import Path

from sqlalchemy import func, select

from opportunity_platform.admin.service import digest as approval_digest
from opportunity_platform.db.models import (
    IngestionRun,
    Opportunity,
    OpportunityVersion,
    SourceSnapshot,
    User,
)
from opportunity_platform.ingestion.schemas import CandidateData, validate_evidence

from .service import authorized, identifier
from .validation import digest

SCHEMA = "policy-review-batch-v1"


def draft_id(record):
    return identifier(
        "review-correction:" + record["baseline"]["version_id"] + ":" + record["candidate_hash"]
    )


def load(path):
    path = Path(path).resolve()
    batch = json.loads(path.read_text())
    if (
        set(batch) != {"schema_version", "as_of", "publication_authorized", "policies"}
        or batch["schema_version"] != SCHEMA
        or batch["publication_authorized"] is not False
    ):
        raise ValueError("Invalid or publication-authorized review batch")
    if not 1 <= len(batch["policies"]) <= 8:
        raise ValueError("Review batch must contain one to eight policies")
    records = []
    keys = set()
    for entry in batch["policies"]:
        target = (path.parent / entry["path"]).resolve()
        if target.parent != path.parent or target.suffix != ".json":
            raise ValueError("Candidate path escapes batch directory")
        raw = target.read_bytes()
        if hashlib.sha256(raw).hexdigest() != entry["sha256"]:
            raise ValueError("Candidate file hash changed")
        record = json.loads(raw)
        candidate = CandidateData.model_validate(record["candidate"])
        if candidate.model_dump(mode="json") != record["candidate"]:
            raise ValueError("Candidate must be normalized before hashing")
        validate_evidence(candidate, record["pages"])
        if (
            digest(record["candidate"]) != record["candidate_hash"]
            or approval_digest(record["candidate"]) != record["approval_hash"]
            or digest(record["pages"]) != record["pages_hash"]
        ):
            raise ValueError("Candidate, approval or page digest mismatch")
        if record["original_binary_hash"] != record["baseline"]["content_hash"]:
            raise ValueError("Original binary hash mismatch")
        if (
            record["publication_authorized"] is not False
            or record["human_required"] is not True
            or record["independent_review"]["status"] != "unavailable"
        ):
            raise ValueError(
                "This batch requires explicit human review without independent verification"
            )
        for name in ("key", "candidate_hash", "approval_hash", "disposition"):
            if record[name] != entry[name]:
                raise ValueError("Manifest binding mismatch: " + name)
        if (
            record["baseline"]["version_id"] != entry["baseline_version_id"]
            or record["baseline"]["stored_candidate_hash"] != entry["baseline_hash"]
        ):
            raise ValueError("Baseline binding mismatch")
        if record["key"] in keys or record["disposition"] not in {
            "human_approval_candidate",
            "blocked_do_not_publish",
        }:
            raise ValueError("Duplicate key or invalid disposition")
        keys.add(record["key"])
        records.append(record)
    return records


def plan(records):
    return [
        {
            "key": r["key"],
            "disposition": r["disposition"],
            "draft_id": str(draft_id(r))
            if r["disposition"] == "human_approval_candidate"
            else None,
            "approval_hash": r["approval_hash"],
            "publication": "none",
        }
        for r in records
    ]


def stage(session, records, actor):
    """Caller owns transaction. All preconditions checked before any insert."""
    authorized(session, actor)
    for r in records:
        if (
            digest(r["candidate"]) != r["candidate_hash"]
            or approval_digest(r["candidate"]) != r["approval_hash"]
            or digest(r["pages"]) != r["pages_hash"]
        ):
            raise ValueError("In-memory review artifact changed")
    ready = [r for r in records if r["disposition"] == "human_approval_candidate"]
    prepared = []
    for r in sorted(ready, key=lambda r: r["baseline"]["opportunity_id"]):
        b = r["baseline"]
        opp = session.scalar(
            select(Opportunity)
            .where(Opportunity.id == uuid.UUID(b["opportunity_id"]))
            .with_for_update()
        )
        old = session.get(OpportunityVersion, uuid.UUID(b["version_id"]))
        snap = session.get(SourceSnapshot, uuid.UUID(b["snapshot_id"]))
        if (
            not opp
            or not old
            or not snap
            or opp.is_synthetic
            or opp.published_version_id
            or old.publication_state != "draft"
            or old.version != b["version"]
            or old.opportunity_id != opp.id
            or old.snapshot_id != snap.id
            or str(opp.source_id) != b["source_id"]
            or snap.source_id != opp.source_id
        ):
            raise ValueError("Baseline identity/publication state changed: " + r["key"])
        # Production baseline reports use corpus digest, NOT admin expected_hash.
        if digest(old.extraction) != b["stored_candidate_hash"]:
            raise ValueError("Baseline candidate changed: " + r["key"])
        if (
            snap.content_hash != r["original_binary_hash"]
            or snap.source_url != b["source_url"]
            or digest(snap.pages) != r["pages_hash"]
        ):
            raise ValueError("Immutable source changed: " + r["key"])
        validate_evidence(CandidateData.model_validate(r["candidate"]), snap.pages)
        existing = session.get(OpportunityVersion, draft_id(r))
        if existing:
            if (
                existing.opportunity_id != opp.id
                or existing.snapshot_id != snap.id
                or digest(existing.extraction) != r["candidate_hash"]
            ):
                raise ValueError("Correction identity conflict")
        else:
            latest = session.scalar(
                select(func.max(OpportunityVersion.version)).where(
                    OpportunityVersion.opportunity_id == opp.id
                )
            )
            if latest != old.version:
                raise ValueError("Another correction exists; reconcile rather than overwrite")
        prepared.append((r, opp, old, snap, existing))
    for r, opp, old, snap, existing in prepared:
        if existing:
            continue
        c = r["candidate"]
        fields = {
            k: c[k]
            for k in (
                "title",
                "summary",
                "issuer",
                "category",
                "country",
                "state",
                "district",
                "benefits",
                "restrictions",
                "required_documents",
                "apply_url",
            )
        }
        fields.update(
            {k: date.fromisoformat(c[k]) if c[k] else None for k in ("opens_on", "closes_on")}
        )
        session.add(
            OpportunityVersion(
                id=draft_id(r),
                opportunity_id=opp.id,
                version=old.version + 1,
                snapshot_id=snap.id,
                publication_state="draft",
                status="needs_review",
                extraction=c,
                extraction_provider="codex_interactive",
                extraction_model="not-independently-attested",
                extractor_version=SCHEMA,
                extraction_usage={"external_api_calls": 0},
                source_url=snap.source_url,
                content_hash=snap.content_hash,
                **fields,
            )
        )
        session.flush()
        session.add(
            IngestionRun(
                id=identifier("review-correction-run:" + str(draft_id(r))),
                source_id=opp.source_id,
                actor_id=actor.id,
                snapshot_id=snap.id,
                finished_at=datetime.now(UTC),
                status="human_escalation",
                provider="codex_interactive",
                extractor_version=SCHEMA,
                source_hash=snap.content_hash,
                usage={"external_api_calls": 0},
                changed=True,
                diagnostics={
                    "draft_id": str(draft_id(r)),
                    "baseline_draft_id": str(old.id),
                    "baseline_corpus_digest": r["baseline"]["stored_candidate_hash"],
                    "candidate_corpus_digest": r["candidate_hash"],
                    "approval_admin_digest": r["approval_hash"],
                    "independent_review": r["independent_review"],
                    "publication": "none",
                    "human_required": True,
                },
            )
        )
    session.flush()
    return plan(records)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batch", type=Path)
    parser.add_argument(
        "--execute", action="store_true", help="Append private drafts only; does not publish"
    )
    parser.add_argument("--actor-id", type=uuid.UUID)
    args = parser.parse_args()
    records = load(args.batch)
    if args.execute:
        if not args.actor_id:
            parser.error("--execute requires --actor-id of a persisted administrator")
        from sqlalchemy.orm import Session

        from opportunity_platform.db.session import engine

        with Session(engine) as session:
            actor = session.get(User, args.actor_id)
            if actor is None:
                raise ValueError("Administrator not found")
            result = stage(session, records, actor)
            session.commit()
    else:
        result = plan(records)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
