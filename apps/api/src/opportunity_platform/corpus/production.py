"""Durable, bounded GCS corpus jobs. Plan-only unless explicitly authorized.

Public government archive only. No AI client, private documents, publication or schema
initialization. A session advisory lock and GCS generation checks prevent lost updates.
"""

import argparse
import fcntl
import hashlib
import json
import re
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from google.api_core.exceptions import PreconditionFailed
from google.cloud import storage
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from opportunity_platform.db.models import IngestionRun, Source, SourceSnapshot
from opportunity_platform.ingestion.corpus_policy.archive import (
    audit_record,
    load_manifest,
    registry_from,
)
from opportunity_platform.ingestion.corpus_policy.prepared import (
    PendingIndependentReview,
    PreparedExtractor,
)
from opportunity_platform.ingestion.corpus_policy.service import (
    extract_candidate,
    identifier,
    import_archive,
)
from opportunity_platform.profiles.service import require_admin

STATE = "public-corpus/state/current.tar.gz"
REGISTRY = Path(__file__).with_name("sources.json")
MAX_STATE = 32 * 1024**2


def hash_file(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def state_member(name):
    path = PurePosixPath(name)
    return (
        not path.is_absolute()
        and ".." not in path.parts
        and (
            name
            in {
                "ledger.sqlite3",
                "manifest.jsonl",
                "events.jsonl",
                "runs.jsonl",
                "sources.jsonl",
                "discoveries.jsonl",
            }
            or (
                path.parts[0] in {"indexes", "processing", "reports"}
                and path.suffix in {".raw", ".json"}
            )
        )
    )


def unpack_state(archive, root):
    total = 0
    with tarfile.open(archive, "r:gz") as tar:
        members = tar.getmembers()
        if len(members) > 10000:
            raise ValueError("Corpus checkpoint member limit exceeded")
        for member in members:
            total += member.size
            if not member.isfile() or not state_member(member.name) or total > 256 * 1024**2:
                raise ValueError("Unsafe or oversized public corpus checkpoint")
        tar.extractall(root, members=members, filter="data")


def pack_state(root, archive):
    # SQLite backup includes committed WAL pages and does not package transient WAL files.
    with tempfile.TemporaryDirectory(prefix="public-corpus-ledger-") as directory:
        backup = Path(directory) / "ledger.sqlite3"
        if (root / "ledger.sqlite3").exists():
            with sqlite3.connect(root / "ledger.sqlite3") as src, sqlite3.connect(backup) as dest:
                src.backup(dest)
        with tarfile.open(archive, "w:gz") as tar:
            for path in sorted(root.rglob("*")):
                name = path.relative_to(root).as_posix()
                if path.is_file() and not path.is_symlink() and state_member(name):
                    tar.add(
                        backup if name == "ledger.sqlite3" else path, arcname=name, recursive=False
                    )
    if archive.stat().st_size > MAX_STATE:
        raise ValueError("Corpus metadata checkpoint exceeds bounded storage size")


def upload_blobs(bucket, root):
    uploaded = 0
    records = load_manifest(root / "manifest.jsonl")
    paths = set()
    for record in records:
        expected = f"blobs/{record.sha256[:2]}/{record.sha256}.{record.format}"
        if not re.fullmatch(r"[a-f0-9]{64}", record.sha256) or record.blob_path != expected:
            raise ValueError("Unexpected content-addressed corpus manifest path")
        path = (root / record.blob_path).resolve()
        if not path.is_relative_to(root.resolve()):
            raise ValueError("Corpus upload path escapes public archive")
        if path.exists():
            paths.add(path)
    for path in sorted(paths):
        if (
            path.is_symlink()
            or path.suffix not in {".pdf", ".html"}
            or path.stat().st_size > 20 * 1024**2
        ):
            raise ValueError("Unexpected public corpus blob")
        digest = hash_file(path)
        if path.stem != digest:
            raise ValueError("Content-addressed blob integrity failed")
        blob = bucket.blob("public-corpus/" + path.relative_to(root).as_posix())
        blob.metadata = {"sha256": digest, "classification": "public-government-source"}
        try:
            blob.upload_from_filename(
                str(path),
                if_generation_match=0,
                timeout=120,
                content_type="application/pdf" if path.suffix == ".pdf" else "text/html",
            )
            uploaded += 1
        except PreconditionFailed:
            blob.reload(timeout=30)
            if blob.size != path.stat().st_size or (blob.metadata or {}).get("sha256") != digest:
                raise ValueError("Stored corpus blob conflicts with immutable hash") from None
    return uploaded


def fetch_blob(bucket, root, record):
    import uuid

    uuid.UUID(record.snapshot_id)
    uuid.UUID(record.document_id)
    if (
        not re.fullmatch(r"[a-f0-9]{64}", record.sha256)
        or not 0 < record.size_bytes <= 20 * 1024**2
    ):
        raise ValueError("Invalid bounded corpus blob metadata")
    expected = f"blobs/{record.sha256[:2]}/{record.sha256}.{record.format}"
    if record.blob_path != expected:
        raise ValueError("Unexpected content-addressed blob path")
    path = (root / record.blob_path).resolve()
    if not path.is_relative_to((root / "blobs").resolve()):
        raise ValueError("Corpus blob path escapes archive")
    if path.is_file() and hash_file(path) == record.sha256:
        return path
    blob = bucket.blob("public-corpus/" + record.blob_path)
    blob.reload(timeout=30)
    if blob.size != record.size_bytes or blob.size > 20 * 1024**2:
        raise ValueError("Stored corpus blob size differs from immutable manifest")
    path.parent.mkdir(parents=True, exist_ok=True)
    blob.download_to_filename(str(path), if_generation_match=blob.generation, timeout=120)
    if hash_file(path) != record.sha256:
        raise ValueError("Downloaded corpus blob hash differs from manifest")
    return path


def import_batch(connection, bucket, root, args, records=None):
    if args.execute:
        with Session(connection) as session:
            require_admin(session, args.actor_uid)
    if records is None:
        records = load_manifest(root / "manifest.jsonl")[
            args.offset : args.offset + args.max_documents
        ]
    from opportunity_platform.corpus.prepared_import import packets, selection

    registry = registry_from(REGISTRY)
    selected = selection(root)
    result = {
        "planned": len(records),
        "would_insert": 0,
        "inserted": 0,
        "duplicates": 0,
        "excluded": 0,
        "failures": 0,
        "drafts_present": 0,
        "prepared_candidates_validated": 0,
        "paid_calls": 0,
        "errors": [],
    }
    for record in records:
        try:
            fetch_blob(bucket, root, record)
            audited = audit_record(record, root, registry)
            if not audited.technically_ingestible or audited.document_type == "irrelevant":
                result["excluded"] += 1
                continue
            with Session(connection) as session:
                sid = identifier(f"snapshot:{record.document_id}:{record.sha256}")
                existing = session.get(SourceSnapshot, sid)
                result["duplicates" if existing else "would_insert"] += 1
                from opportunity_platform.ingestion.corpus_policy.validation import validate

                prepared = []
                for item in packets(root, record, selected):
                    extractor = PreparedExtractor(item["packet"], record.sha256)
                    focus = item["focus"] or extractor.candidate.candidate.title
                    if not isinstance(focus, str) or not 1 <= len(focus.strip()) <= 2000:
                        raise ValueError("Invalid prepared component focus")
                    candidate, problems = validate(extractor.candidate, audited)
                    if candidate is None or any(
                        issue.severity in {"error", "critical"} for issue in problems
                    ):
                        raise ValueError("Prepared candidate failed captured-evidence validation")
                    prepared.append((extractor, focus))
                    result["prepared_candidates_validated"] += 1
                if not args.execute:
                    session.rollback()
                    continue
                actor = require_admin(session, args.actor_uid)
                snapshot, _ = import_archive(session, audited, actor)
                pointer = "gs://" + bucket.name + "/public-corpus/" + record.blob_path
                if snapshot.response_metadata.get("object_uri") not in {None, pointer}:
                    raise ValueError("Immutable object pointer conflict")
                snapshot.response_metadata = {**snapshot.response_metadata, "object_uri": pointer}
                for extractor, focus in prepared:
                    run = extract_candidate(
                        session,
                        audited,
                        actor,
                        focus,
                        extractor,
                        PendingIndependentReview(),
                        max_repairs=0,
                    )
                    if run.diagnostics.get("draft_id"):
                        result["drafts_present"] += 1
                session.commit()  # one document; a bad PDF never rolls back the entire batch
                result["inserted"] += int(existing is None)
        except Exception as error:
            result["failures"] += 1
            result["errors"].append(
                {"snapshot_id": record.snapshot_id, "diagnostic": type(error).__name__}
            )
    return result


def record_collection(connection, root, actor_uid, started_after=None):
    from opportunity_platform.corpus.cli import metrics
    from opportunity_platform.corpus.store import Store

    store = Store(root)
    try:
        latest = store.db.execute("SELECT id FROM runs ORDER BY started_at DESC LIMIT 1").fetchone()
        if latest is None:
            return
        report = metrics(store, latest["id"])
        if started_after and datetime.fromisoformat(report["run"]["started_at"]) < started_after:
            return  # a child that failed before starting must not refresh an older successful run
        configs = registry_from(REGISTRY)
        with Session(connection) as session:
            actor = require_admin(session, actor_uid)
            for group in report["per_source"]:
                spec = configs[group["source"]]
                sid = identifier("collector-registry:" + spec.key)
                source = session.get(Source, sid)
                successful = any(
                    group["statuses"].get(k, 0)
                    for k in ["listing_checked", "new", "updated", "duplicate", "unchanged"]
                )
                now = datetime.now(UTC)
                if source is None:
                    source = Source(
                        id=sid,
                        name="Registry: " + spec.key,
                        authority=spec.authority,
                        url=spec.seeds[0],
                        is_synthetic=False,
                        status="needs_review",
                    )
                    session.add(source)
                    session.flush()
                source.last_checked_at = now
                if successful:
                    source.last_successful_check_at = now
                    source.status = "needs_review"
                else:
                    source.status = "source_unreachable"
                run_id = identifier("collector-run:" + latest["id"] + ":" + spec.key)
                if session.get(IngestionRun, run_id) is None:
                    session.add(
                        IngestionRun(
                            id=run_id,
                            source_id=source.id,
                            actor_id=actor.id,
                            provider="offline_collector",
                            extractor_version="durable-collector-v1",
                            status="collection_completed"
                            if report["run"]["status"] == "completed" and successful
                            else "collection_partial",
                            finished_at=now,
                            diagnostic_code="bounded_public_collection",
                            source_hash=hash_file(root / "manifest.jsonl"),
                            usage={"external_api_calls": 0},
                            diagnostics={
                                "registry_group": spec.key,
                                "metrics": group,
                                "requests": report["run"]["requests"],
                                "wire_bytes": report["run"]["wire_bytes"],
                                "state_checkpointed": True,
                                "publication": "none",
                            },
                        )
                    )
            session.commit()
    finally:
        store.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["stage", "import", "collect"])
    parser.add_argument("--project", required=True)
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--state-name", default="current")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--approved-project")
    parser.add_argument("--actor-uid")
    parser.add_argument("--root", type=Path)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--max-documents", type=int, default=20)
    parser.add_argument("--source", action="append")
    args = parser.parse_args(argv)
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,63}", args.state_name):
        parser.error("Use a reviewed bounded corpus state name")
    state_key = f"public-corpus/state/{args.state_name}.tar.gz"
    if not 0 <= args.offset <= 10000 or not 1 <= args.max_documents <= 20:
        parser.error("Bounded import offset/size required")
    if args.execute and args.approved_project != args.project:
        parser.error("Execution requires --approved-project matching the project")
    if args.execute and args.operation == "import" and not args.actor_uid:
        parser.error("Import requires an explicitly authorized existing administrator")
    if args.execute and args.operation == "collect" and not args.actor_uid:
        parser.error("Collection requires the approved actor for changed-source queue records")
    if args.operation == "stage" and not args.root:
        parser.error("Staging requires the local public corpus root")
    if args.operation == "collect" and not args.source:
        parser.error("Select approved registry source keys explicitly")
    if args.operation == "stage" and not args.execute:
        records = load_manifest(args.root / "manifest.jsonl")
        unique = {r.sha256: r.size_bytes for r in records}
        print(
            json.dumps(
                {
                    "mode": "plan",
                    "snapshot_records": len(records),
                    "unique_blobs": len(unique),
                    "blob_bytes": sum(unique.values()),
                    "state_object": f"gs://{args.bucket}/{state_key}",
                    "paid_calls": 0,
                }
            )
        )
        return 0
    if args.operation == "collect" and not args.execute:
        print(
            json.dumps(
                {
                    "mode": "plan",
                    "sources": args.source,
                    "max_requests": 40,
                    "max_documents": 10,
                    "max_wire_mib": 50,
                    "paid_calls": 0,
                }
            )
        )
        return 0
    client = storage.Client(project=args.project)
    bucket = client.bucket(args.bucket)
    with tempfile.TemporaryDirectory(prefix="public-corpus-job-") as directory:
        temporary = Path(directory)
        if args.operation == "stage":
            root = args.root.resolve()
            with (root / "collector.lock").open("a") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                uploaded = upload_blobs(bucket, root)
                archive = temporary / "state.tar.gz"
                pack_state(root, archive)
                state = bucket.blob(state_key)
                state.metadata = {"manifest_sha256": hash_file(root / "manifest.jsonl")}
                try:
                    state.upload_from_filename(str(archive), if_generation_match=0, timeout=120)
                except PreconditionFailed:
                    state.reload(timeout=30)
                    if (state.metadata or {}).get("manifest_sha256") != hash_file(
                        root / "manifest.jsonl"
                    ):
                        raise ValueError(
                            "Existing durable corpus state differs; cannot overwrite it"
                        ) from None
            print(
                json.dumps(
                    {
                        "staged_new_blobs": uploaded,
                        "state_bytes": archive.stat().st_size,
                        "paid_calls": 0,
                    }
                )
            )
            return 0
        state = bucket.get_blob(state_key, timeout=30)
        if state is None or state.size > MAX_STATE:
            raise ValueError("Staged public corpus checkpoint is missing or oversized")
        archive = temporary / "state.tar.gz"
        state.download_to_filename(str(archive), if_generation_match=state.generation, timeout=120)
        root = temporary / "corpus"
        root.mkdir()
        unpack_state(archive, root)
        from opportunity_platform.core.config import settings
        from opportunity_platform.core.database import validate_neon_url
        from opportunity_platform.db.session import engine

        # Session advisory leases cannot cross commits safely through a transaction
        # pooler. Workers use a direct, least-privilege application credential.
        if settings().database_provider == "neon":
            validate_neon_url(settings().database_url, direct=True)
        with engine.connect() as connection:
            acquired = connection.scalar(select(func.pg_try_advisory_lock(837455020)))
            connection.commit()
            if not acquired:
                raise ValueError("Another durable corpus job is already running")
            try:
                if args.operation == "import":
                    result = import_batch(connection, bucket, root, args)
                    connection.commit()
                else:
                    with Session(connection) as session:
                        require_admin(session, args.actor_uid)
                    before = {r.snapshot_id for r in load_manifest(root / "manifest.jsonl")}
                    collection_started_at = datetime.now(UTC)
                    command = [
                        sys.executable,
                        "-m",
                        "opportunity_platform.corpus.cli",
                        "update",
                        "--root",
                        str(root),
                        "--registry",
                        str(REGISTRY),
                        "--max-documents",
                        "10",
                        "--max-requests",
                        "40",
                        "--max-total-mib",
                        "50",
                        "--delay",
                        "2",
                    ]
                    for source in args.source:
                        command.extend(["--source", source])
                    child = subprocess.run(command, check=False)
                    uploaded = upload_blobs(bucket, root)
                    pack_state(root, archive)
                    updated = bucket.blob(state_key)
                    updated.metadata = {"manifest_sha256": hash_file(root / "manifest.jsonl")}
                    updated.upload_from_filename(
                        str(archive), if_generation_match=state.generation, timeout=120
                    )
                    changed = [
                        r
                        for r in load_manifest(root / "manifest.jsonl")
                        if r.snapshot_id not in before
                    ]
                    imported = import_batch(connection, bucket, root, args, changed[:20])
                    record_collection(connection, root, args.actor_uid, collection_started_at)
                    result = {
                        "collector_exit": child.returncode,
                        "new_blobs": uploaded,
                        "paid_calls": 0,
                        "state_checkpointed": True,
                        "interpretation": "pending; no automatic model call or publication",
                        "changed_source_import": imported,
                        "failures": imported["failures"],
                    }
                print(json.dumps(result))
                return 1 if result.get("failures") or result.get("collector_exit") else 0
            finally:
                connection.rollback()
                connection.execute(select(func.pg_advisory_unlock(837455020)))
                connection.commit()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(
            json.dumps({"status": "failed", "diagnostic": type(error).__name__, "paid_calls": 0}),
            file=sys.stderr,
        )
        raise SystemExit(1) from None
