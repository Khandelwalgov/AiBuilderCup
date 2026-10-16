"""Durable local acquisition ledger; no writes to the product PostgreSQL database."""

import hashlib
import json
import os
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

from .schemas import ManifestRecord


def now():
    return datetime.now(UTC).isoformat()


def identity(value):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, value))


DDL = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS runs (
 id TEXT PRIMARY KEY, started_at TEXT NOT NULL, finished_at TEXT, status TEXT NOT NULL,
 config TEXT NOT NULL, requests INTEGER NOT NULL DEFAULT 0, wire_bytes INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS sources (
 id TEXT PRIMARY KEY, source_key TEXT UNIQUE NOT NULL, config TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tasks (
 id INTEGER PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id),
 source_id TEXT NOT NULL REFERENCES sources(id), kind TEXT NOT NULL,
 url TEXT NOT NULL, depth INTEGER NOT NULL DEFAULT 0, candidate TEXT,
 status TEXT NOT NULL DEFAULT 'queued', UNIQUE(run_id,source_id,kind,url)
);
CREATE TABLE IF NOT EXISTS documents (
 id TEXT PRIMARY KEY, canonical_url TEXT UNIQUE NOT NULL, current_snapshot_id TEXT
);
CREATE TABLE IF NOT EXISTS snapshots (
 id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(id),
 previous_id TEXT REFERENCES snapshots(id), sha256 TEXT NOT NULL,
 blob_path TEXT NOT NULL, size_bytes INTEGER NOT NULL, format TEXT NOT NULL,
 downloaded_at TEXT NOT NULL, final_url TEXT NOT NULL,
 metadata TEXT NOT NULL, validation TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS discoveries (
 id INTEGER PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id),
 source_id TEXT NOT NULL REFERENCES sources(id), document_url TEXT NOT NULL,
 discovery_url TEXT NOT NULL, metadata TEXT NOT NULL,
 UNIQUE(run_id,source_id,document_url,discovery_url)
);
CREATE TABLE IF NOT EXISTS events (
 id INTEGER PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id),
 source_id TEXT NOT NULL REFERENCES sources(id), url TEXT NOT NULL,
 kind TEXT NOT NULL, status TEXT NOT NULL, recorded_at TEXT NOT NULL,
 snapshot_id TEXT REFERENCES snapshots(id), detail TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS tasks_pending ON tasks(run_id,status,kind);
CREATE INDEX IF NOT EXISTS events_run ON events(run_id);
CREATE UNIQUE INDEX IF NOT EXISTS events_idempotent ON events(run_id,source_id,url,kind,status);
"""


class Store:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.root / "ledger.sqlite3")
        self.db.row_factory = sqlite3.Row
        self.db.executescript(DDL)
        self.db.execute("PRAGMA journal_mode=WAL")

    def close(self):
        self.db.close()

    def register(self, sources):
        with self.db:
            for source in sources:
                self.db.execute(
                    "INSERT INTO sources VALUES(?,?,?) ON CONFLICT(id) DO UPDATE "
                    "SET config=excluded.config",
                    (identity(source.key), source.key, source.model_dump_json()),
                )

    def start(self, config):
        run_id = str(uuid.uuid4())
        with self.db:
            self.db.execute(
                "INSERT INTO runs(id,started_at,status,config) VALUES(?,?,?,?)",
                (run_id, now(), "running", json.dumps(config)),
            )
        return run_id

    def progress(self, run_id, requests, size):
        with self.db:
            self.db.execute(
                "UPDATE runs SET requests=?, wire_bytes=? WHERE id=?", (requests, size, run_id)
            )

    def enqueue(self, run_id, source, kind, url, depth=0, candidate=None):
        with self.db:
            self.db.execute(
                "INSERT OR IGNORE INTO tasks "
                "(run_id,source_id,kind,url,depth,candidate) VALUES(?,?,?,?,?,?)",
                (
                    run_id,
                    identity(source.key),
                    kind,
                    url,
                    depth,
                    candidate.model_dump_json() if candidate else None,
                ),
            )

    def discovery(self, run_id, source, candidate):
        with self.db:
            self.db.execute(
                "INSERT OR IGNORE INTO discoveries "
                "(run_id,source_id,document_url,discovery_url,metadata) VALUES(?,?,?,?,?)",
                (
                    run_id,
                    identity(source.key),
                    candidate.url,
                    candidate.discovery_url,
                    json.dumps(
                        {
                            **candidate.model_dump(mode="json"),
                            "registry_metadata": {
                                "authority": source.authority,
                                "jurisdiction": source.jurisdiction,
                                "category": source.category,
                            },
                        }
                    ),
                ),
            )

    def event(self, run_id, source_id, url, kind, status, *, snapshot_id=None, detail=None):
        self.db.execute(
            "INSERT OR IGNORE INTO events "
            "(run_id,source_id,url,kind,status,recorded_at,snapshot_id,detail) "
            "VALUES(?,?,?,?,?,?,?,?)",
            (run_id, source_id, url, kind, status, now(), snapshot_id, json.dumps(detail or {})),
        )

    def finish_task(self, task, status, detail=None):
        with self.db:
            self.event(
                task["run_id"], task["source_id"], task["url"], task["kind"], status, detail=detail
            )
            self.db.execute("UPDATE tasks SET status='done' WHERE id=?", (task["id"],))

    def observe_missing(self, task, listing_url, current_urls):
        previous = self.db.execute(
            "SELECT DISTINCT document_url FROM discoveries WHERE source_id=? "
            "AND discovery_url=? AND run_id!=?",
            (task["source_id"], listing_url, task["run_id"]),
        )
        with self.db:
            for row in previous:
                if row[0] not in current_urls:
                    self.event(
                        task["run_id"],
                        task["source_id"],
                        row[0],
                        "observation",
                        "not_seen_in_listing_needs_review",
                        detail={
                            "listing_url": listing_url,
                            "meaning": "Absence in this index response; not official withdrawal",
                        },
                    )

    def capture(self, task, source, payload, fmt, validation):
        digest = hashlib.sha256(payload.raw).hexdigest()
        relative = f"blobs/{digest[:2]}/{digest}.{fmt}"
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        # Atomic no-overwrite installation: a crash may leave an unreferenced valid blob.
        temp = path.parent / (".tmp-" + uuid.uuid4().hex)
        try:
            with temp.open("xb") as stream:
                stream.write(payload.raw)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.link(temp, path)
            except FileExistsError:
                if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                    raise RuntimeError("Existing content-addressed blob failed integrity check")
        finally:
            temp.unlink(missing_ok=True)
        document_id = identity(task["url"])
        with self.db:
            self.db.execute(
                "INSERT OR IGNORE INTO documents(id,canonical_url) VALUES(?,?)",
                (document_id, task["url"]),
            )
            doc = self.db.execute("SELECT * FROM documents WHERE id=?", (document_id,)).fetchone()
            previous = self.db.execute(
                "SELECT * FROM snapshots WHERE id=?", (doc["current_snapshot_id"],)
            ).fetchone()
            duplicate = self.db.execute(
                "SELECT id FROM snapshots WHERE sha256=? LIMIT 1", (digest,)
            ).fetchone()
            if previous and previous["sha256"] == digest:
                status, snapshot_id = "unchanged", previous["id"]
            else:
                status = "updated" if previous else "duplicate" if duplicate else "new"
                snapshot_id = str(uuid.uuid4())
                self.db.execute(
                    "INSERT INTO snapshots VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        snapshot_id,
                        document_id,
                        previous["id"] if previous else None,
                        digest,
                        relative,
                        len(payload.raw),
                        fmt,
                        now(),
                        payload.final_url,
                        json.dumps(
                            {**payload.headers, **payload.policy, "http_status": payload.status}
                        ),
                        json.dumps(validation),
                    ),
                )
                self.db.execute(
                    "UPDATE documents SET current_snapshot_id=? WHERE id=?",
                    (snapshot_id, document_id),
                )
            self.event(
                task["run_id"],
                identity(source.key),
                task["url"],
                "document",
                status,
                snapshot_id=snapshot_id,
                detail={"sha256": digest, "bytes": len(payload.raw), "format": fmt},
            )
            self.db.execute("UPDATE tasks SET status='done' WHERE id=?", (task["id"],))
        return status

    def archive_index(self, payload):
        digest = hashlib.sha256(payload.raw).hexdigest()
        relative = f"indexes/{digest}.raw"
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(".tmp-" + uuid.uuid4().hex)
        try:
            with temporary.open("xb") as stream:
                stream.write(payload.raw)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.link(temporary, path)
            except FileExistsError:
                if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                    raise RuntimeError("Existing index archive failed integrity check")
        finally:
            temporary.unlink(missing_ok=True)
        return {
            "index_sha256": digest,
            "index_path": relative,
            "index_size_bytes": len(payload.raw),
            "http_metadata": payload.headers,
        }

    def records(self):
        for snapshot in self.db.execute(
            "SELECT s.*,d.canonical_url FROM snapshots s JOIN documents d ON s.document_id=d.id "
            "ORDER BY s.downloaded_at,s.id"
        ):
            associations = []
            for row in self.db.execute(
                "SELECT DISTINCT d.source_id,s.source_key,s.config,d.metadata,"
                "d.run_id,r.started_at "
                "FROM discoveries d JOIN sources s ON s.id=d.source_id "
                "JOIN runs r ON r.id=d.run_id WHERE d.document_url=? ORDER BY r.started_at DESC",
                (snapshot["canonical_url"],),
            ):
                source, meta = json.loads(row["config"]), json.loads(row["metadata"])
                source = meta.get("registry_metadata", source)
                closes_on = meta.get("closes_on")
                deadline_state = "unknown"
                if closes_on:
                    deadline_state = (
                        "expired"
                        if closes_on < snapshot["downloaded_at"][:10]
                        else "not_expired_at_capture"
                    )
                associations.append(
                    {
                        **meta,
                        "discovery_run_id": row["run_id"],
                        "discovered_at": row["started_at"],
                        "deadline_state_at_capture": deadline_state,
                        "source_id": row["source_id"],
                        "source_key": row["source_key"],
                        "issuing_authority": source["authority"],
                        "authority_basis": "reviewed_source_registry_not_document_extraction",
                        "jurisdiction": source["jurisdiction"],
                        "document_category": source["category"],
                    }
                )
            yield ManifestRecord(
                snapshot_id=snapshot["id"],
                document_id=snapshot["document_id"],
                previous_snapshot_id=snapshot["previous_id"],
                canonical_source_url=snapshot["canonical_url"],
                originating_domain=urlsplit(snapshot["canonical_url"]).hostname,
                final_url=snapshot["final_url"],
                downloaded_at=snapshot["downloaded_at"],
                sha256=snapshot["sha256"],
                size_bytes=snapshot["size_bytes"],
                format=snapshot["format"],
                blob_path=snapshot["blob_path"],
                http_metadata=json.loads(snapshot["metadata"]),
                validation=json.loads(snapshot["validation"]),
                discoveries=associations,
            )

    def export(self):
        def atomic(name, lines):
            path = self.root / name
            temp = path.with_suffix(path.suffix + ".tmp")
            with temp.open("w") as stream:
                for line in lines:
                    stream.write(line + "\n")
            temp.replace(path)

        atomic("manifest.jsonl", (record.model_dump_json() for record in self.records()))
        atomic(
            "events.jsonl",
            (json.dumps(dict(row)) for row in self.db.execute("SELECT * FROM events ORDER BY id")),
        )
        for name in ("runs", "sources", "discoveries"):
            atomic(
                f"{name}.jsonl",
                (json.dumps(dict(row)) for row in self.db.execute(f"SELECT * FROM {name}")),
            )

    def verify(self, validator):
        errors, checked, seen = [], 0, set()
        for row in self.db.execute("SELECT * FROM snapshots"):
            if row["blob_path"] in seen:
                continue
            seen.add(row["blob_path"])
            checked += 1
            try:
                raw = (self.root / row["blob_path"]).read_bytes()
                assert len(raw) == row["size_bytes"], "size mismatch"
                assert hashlib.sha256(raw).hexdigest() == row["sha256"], "hash mismatch"
                validator(
                    raw,
                    "application/pdf" if row["format"] == "pdf" else "text/html",
                    row["final_url"],
                )
            except Exception as exc:
                errors.append({"blob_path": row["blob_path"], "error": str(exc)})
        return {"unique_blobs_checked": checked, "errors": errors}
