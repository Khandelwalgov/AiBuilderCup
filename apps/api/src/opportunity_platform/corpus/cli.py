"""Bounded local acquisition job: python -m opportunity_platform.corpus.cli --help."""

import argparse
import fcntl
import json
from collections import Counter
from pathlib import Path

import httpx

from .discovery import discover, validate
from .network import AcquisitionError, Fetcher, canonical
from .schemas import Candidate, ManifestRecord, SourceSpec
from .store import Store, identity, now

REPO = Path(__file__).resolve().parents[5]


def load_sources(path):
    sources = [SourceSpec.model_validate(row) for row in json.loads(Path(path).read_text())]
    if len({s.key for s in sources}) != len(sources):
        raise ValueError("Source keys must be unique")
    return sources


def metrics(store, run_id):
    rows = list(store.db.execute("SELECT * FROM events WHERE run_id=?", (run_id,)))
    docs = [r for r in rows if r["kind"] == "document" and r["snapshot_id"]]
    successful = {r["source_id"] for r in docs}
    detail = [json.loads(r["detail"]) for r in docs]
    sources = {r["id"]: json.loads(r["config"]) for r in store.db.execute("SELECT * FROM sources")}
    snapshot_ids = {r["snapshot_id"] for r in docs}
    hashes = {d["sha256"] for d in detail}
    failures = [
        dict(r)
        for r in rows
        if r["status"]
        not in ("new", "duplicate", "unchanged", "updated", "listing_checked", "duplicate_link")
    ]
    run = dict(store.db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone())
    source_metrics = []
    for sid in sorted({r["source_id"] for r in rows}):
        selected = [r for r in rows if r["source_id"] == sid]
        selected_docs = [r for r in selected if r["snapshot_id"]]
        source_metrics.append(
            {
                "source": sources[sid]["key"],
                "jurisdiction": sources[sid]["jurisdiction"],
                "category": sources[sid]["category"],
                "documents": len(selected_docs),
                "statuses": dict(Counter(r["status"] for r in selected)),
            }
        )
    blob_files = list((store.root / "blobs").glob("*/*"))
    return {
        "run": run,
        "corpus_location": str(store.root),
        "sources_registered": len(sources),
        "sources_considered": len({r["source_id"] for r in rows}),
        "sources_attempted_network": len(
            {r["source_id"] for r in rows if r["kind"] != "access_review"}
        ),
        "sources_with_documents": len(successful),
        "successful_document_fetches": len(docs),
        "snapshot_count_in_run": len(snapshot_ids),
        "distinct_content_in_run": len(hashes),
        "total_unique_blobs": len(blob_files),
        "format_fetch_counts": dict(Counter(d["format"] for d in detail)),
        "change_counts": dict(Counter(r["status"] for r in docs)),
        "category_fetch_counts": dict(Counter(sources[r["source_id"]]["category"] for r in docs)),
        "successful_source_jurisdictions": dict(
            Counter(sources[s]["jurisdiction"] for s in successful)
        ),
        "blob_storage_bytes": sum(p.stat().st_size for p in blob_files),
        "local_storage_bytes": sum(p.stat().st_size for p in store.root.rglob("*") if p.is_file()),
        "pending_tasks": store.db.execute(
            "SELECT count(*) FROM tasks WHERE run_id=? AND status!='done'", (run_id,)
        ).fetchone()[0],
        "failures": failures,
        "per_source": source_metrics,
    }


def collect(store, sources, options, client, resume=None):
    if resume:
        run = store.db.execute("SELECT * FROM runs WHERE id=?", (resume,)).fetchone()
        if not run:
            raise ValueError("Resume run ID does not exist")
        if run["status"] == "completed":
            raise ValueError("Completed runs cannot be resumed; use update")
        saved = json.loads(run["config"])
        sources = [SourceSpec.model_validate(s) for s in saved["sources"]]
        options = saved["options"]
        run_id = resume
        with store.db:
            store.db.execute(
                "UPDATE runs SET status='running', finished_at=NULL WHERE id=?", (run_id,)
            )
            store.db.execute(
                "UPDATE tasks SET status='queued' WHERE run_id=? AND status='working'", (run_id,)
            )
    else:
        store.register(sources)
        run_id = store.start({"sources": [s.model_dump() for s in sources], "options": options})
        for source in sources:
            if source.access != "public":
                with store.db:
                    store.event(
                        run_id,
                        identity(source.key),
                        source.seeds[0],
                        "access_review",
                        source.access,
                        detail={"note": source.access_note},
                    )
                continue
            for seed in source.seeds:
                url = canonical(seed)
                kind = "document" if source.adapter == "pdf" else "listing"
                candidate = Candidate(url=url, discovery_url=url, title=source.key)
                if kind == "document":
                    store.discovery(run_id, source, candidate)
                    if options.get("discovery_only"):
                        continue
                store.enqueue(run_id, source, kind, url, candidate=candidate)
    print(json.dumps({"event": "run_started", "run_id": run_id}), flush=True)
    lookup = {identity(s.key): s for s in sources}
    fetcher = Fetcher(
        client,
        max_bytes=options["max_file_bytes"],
        max_total_bytes=options["max_total_bytes"],
        max_requests=options["max_requests"],
        delay=options["delay"],
        progress=lambda requests, size: store.progress(run_id, requests, size),
    )
    previous = store.db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
    fetcher.requests, fetcher.bytes = previous["requests"], previous["wire_bytes"]
    stop_status = "completed"
    try:
        # Discover first; then round-robin document tasks across sources for diverse coverage.
        for phase in ("listing", "document"):
            while True:
                task = store.db.execute(
                    "SELECT t.* FROM tasks t WHERE t.run_id=? AND t.kind=? AND t.status='queued' "
                    "ORDER BY (SELECT count(*) FROM tasks d WHERE d.run_id=t.run_id "
                    "AND d.source_id=t.source_id AND d.kind=t.kind AND d.status='done'),"
                    "t.id LIMIT 1",
                    (run_id, phase),
                ).fetchone()
                if task is None:
                    break
                count = store.db.execute(
                    "SELECT count(*) FROM events WHERE run_id=? AND snapshot_id IS NOT NULL",
                    (run_id,),
                ).fetchone()[0]
                if count >= options["max_documents"]:
                    stop_status = "budget_exhausted"
                    break
                source = lookup[task["source_id"]]
                with store.db:
                    store.db.execute("UPDATE tasks SET status='working' WHERE id=?", (task["id"],))
                try:
                    if phase == "document":
                        prior = store.db.execute(
                            "SELECT snapshot_id FROM events WHERE run_id=? "
                            "AND url=? AND snapshot_id IS NOT NULL LIMIT 1",
                            (run_id, task["url"]),
                        ).fetchone()
                        if prior:
                            store.finish_task(task, "duplicate_link", {"snapshot_id": prior[0]})
                            continue
                    payload = fetcher.fetch(task["url"], source)
                    if phase == "document":
                        fmt, validation = validate(
                            payload.raw, payload.headers.get("content-type") or "", task["url"]
                        )
                        status = store.capture(task, source, payload, fmt, validation)
                    else:
                        candidates, pages = discover(payload, source, fetcher)
                        index_metadata = store.archive_index(payload)
                        if candidates:
                            store.observe_missing(
                                task, payload.final_url, {candidate.url for candidate in candidates}
                            )
                        # Every candidate is recorded, even if the run's download cap is reached.
                        for candidate in candidates:
                            store.discovery(run_id, source, candidate)
                            queued = store.db.execute(
                                "SELECT count(*) FROM tasks WHERE run_id=? "
                                "AND source_id=? AND kind='document'",
                                (run_id, task["source_id"]),
                            ).fetchone()[0]
                            if queued < source.max_documents and not options.get("discovery_only"):
                                store.enqueue(
                                    run_id, source, "document", candidate.url, candidate=candidate
                                )
                        if task["depth"] < source.max_depth:
                            for page in pages:
                                queued = store.db.execute(
                                    "SELECT count(*) FROM tasks WHERE run_id=? "
                                    "AND source_id=? AND kind='listing'",
                                    (run_id, task["source_id"]),
                                ).fetchone()[0]
                                if queued < source.max_pages:
                                    store.enqueue(
                                        run_id, source, "listing", page, task["depth"] + 1
                                    )
                        status = "listing_checked" if candidates or pages else "no_documents_found"
                        store.finish_task(
                            task,
                            status,
                            {
                                "candidate_links": len(candidates),
                                "traversal_links": len(pages),
                                "final_url": payload.final_url,
                                "policy": payload.policy,
                                **index_metadata,
                            },
                        )
                    print(
                        json.dumps(
                            {
                                "event": phase,
                                "source": source.key,
                                "status": status,
                                "url": task["url"],
                            }
                        ),
                        flush=True,
                    )
                except AcquisitionError as exc:
                    detail = {"http_status": exc.status, "reason": exc.detail}
                    if exc.code == "run_budget_exhausted":
                        with store.db:
                            store.db.execute(
                                "UPDATE tasks SET status='queued' WHERE id=?", (task["id"],)
                            )
                        stop_status = "budget_exhausted"
                        break
                    store.finish_task(task, exc.code, detail)
                    print(
                        json.dumps(
                            {
                                "event": "retrieval_failure",
                                "source": source.key,
                                "url": task["url"],
                                "code": exc.code,
                                **detail,
                            }
                        ),
                        flush=True,
                    )
            if stop_status == "budget_exhausted":
                break
    except KeyboardInterrupt:
        stop_status = "interrupted"
    except Exception:
        stop_status = "failed"
        raise
    finally:
        with store.db:
            store.db.execute(
                "UPDATE runs SET finished_at=?,status=? WHERE id=?", (now(), stop_status, run_id)
            )
        store.export()
        result = metrics(store, run_id)
        (store.root / "reports").mkdir(exist_ok=True)
        (store.root / "reports" / f"{run_id}.json").write_text(json.dumps(result, indent=2))
        print(
            json.dumps(
                {
                    "event": "run_finished",
                    "run_id": run_id,
                    "status": stop_status,
                    "successful_document_fetches": result["successful_document_fetches"],
                    "distinct_content": result["distinct_content_in_run"],
                }
            ),
            flush=True,
        )
    return run_id


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["collect", "update", "verify", "report", "schema"])
    parser.add_argument("--registry", type=Path, default=REPO / "data/corpus/sources.json")
    parser.add_argument("--root", type=Path, default=REPO / ".corpus")
    parser.add_argument("--source", action="append", help="Repeat to select registry keys")
    parser.add_argument(
        "--resume", help="Resume unfinished run with original configuration/budgets"
    )
    parser.add_argument("--run-id", help="Report this run; defaults to latest")
    parser.add_argument(
        "--dry-run", action="store_true", help="Print plan; no network or ledger writes"
    )
    parser.add_argument("--max-documents", type=int, default=200)
    parser.add_argument(
        "--discovery-only",
        action="store_true",
        help="Archive indexes and candidate metadata without downloading documents",
    )
    parser.add_argument("--max-requests", type=int, default=1200)
    parser.add_argument("--max-file-mib", type=int, default=20)
    parser.add_argument("--max-total-mib", type=int, default=600)
    parser.add_argument("--delay", type=float, default=1.0)
    args = parser.parse_args()
    if args.command == "schema":
        print(json.dumps(ManifestRecord.model_json_schema(), indent=2))
        return
    if (
        any(
            v < 1
            for v in (args.max_documents, args.max_requests, args.max_file_mib, args.max_total_mib)
        )
        or args.delay < 1
    ):
        parser.error("Budgets must be positive; minimum host delay is one second")
    sources = load_sources(args.registry)
    if args.source:
        unknown = set(args.source) - {s.key for s in sources}
        if unknown:
            parser.error(f"Unknown sources: {sorted(unknown)}")
        sources = [s for s in sources if s.key in args.source]
    options = {
        "discovery_only": args.discovery_only,
        "max_documents": args.max_documents,
        "max_requests": args.max_requests,
        "max_file_bytes": args.max_file_mib * 1024**2,
        "max_total_bytes": args.max_total_mib * 1024**2,
        "delay": args.delay,
    }
    if args.dry_run:
        print(
            json.dumps(
                {
                    "command": args.command,
                    "root": str(args.root.resolve()),
                    "sources": [s.model_dump() for s in sources],
                    "options": options,
                },
                indent=2,
            )
        )
        return
    args.root.mkdir(parents=True, exist_ok=True)
    with (args.root / "collector.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            parser.error("Another collector holds this corpus lock")
        store = Store(args.root)
        try:
            if args.command == "verify":
                result = store.verify(validate)
                print(json.dumps(result, indent=2))
                if result["errors"]:
                    raise SystemExit(1)
            elif args.command == "report":
                row = store.db.execute(
                    "SELECT id FROM runs ORDER BY started_at DESC LIMIT 1"
                ).fetchone()
                if not row:
                    parser.error("No acquisition runs recorded")
                print(json.dumps(metrics(store, args.run_id or row[0]), indent=2))
            else:
                with httpx.Client(
                    timeout=httpx.Timeout(15, read=30), follow_redirects=False, trust_env=False
                ) as client:
                    collect(store, sources, options, client, args.resume)
        finally:
            store.close()


if __name__ == "__main__":
    main()
