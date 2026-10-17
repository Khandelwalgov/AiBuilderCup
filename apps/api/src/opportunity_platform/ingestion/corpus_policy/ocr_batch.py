"""Bounded local OCR backlog with immutable page checkpoints and failure isolation."""

import argparse
import concurrent.futures
import json
import os
import subprocess
import sys
from pathlib import Path

from .archive import TEXT_VERSION, load_manifest, original_bytes, registry_from


def plan(root, manifest, registry_path, max_pages):
    registry = registry_from(registry_path)
    seen, jobs, omitted = set(), [], 0
    for record in load_manifest(manifest):
        if record.sha256 in seen:
            continue
        seen.add(record.sha256)
        original_bytes(root, record, registry)
        packet = json.loads(
            (root / "processing/packets" / f"{record.snapshot_id}.{TEXT_VERSION}.json").read_text()
        )["packet"]
        pages = [
            p["page"]
            for p in packet["pages"]
            if record.format == "pdf" and p["quality"] != "readable_text_unverified"
        ]
        for page in pages:
            checkpoint = (
                root / "processing/ocr-checkpoints" / record.snapshot_id / f"page-{page}.json"
            )
            if checkpoint.exists():
                value = json.loads(checkpoint.read_text())
                if value["source_hash"] != record.sha256 or value["page"] != page:
                    raise ValueError("Existing OCR checkpoint identity conflict")
                continue
            if len(jobs) < max_pages:
                jobs.append(
                    {"snapshot_id": record.snapshot_id, "page": page, "source_hash": record.sha256}
                )
            else:
                omitted += 1
    # First-page attribution before remaining pages; all selected jobs remain explicit.
    jobs.sort(key=lambda job: (job["page"], job["snapshot_id"]))
    return jobs, omitted


def execute_job(job, root, manifest, registry, tessdata):
    command = [
        sys.executable,
        "-m",
        "opportunity_platform.ingestion.corpus_policy.ocr",
        "--corpus-root",
        str(root),
        "--manifest",
        str(manifest),
        "--registry",
        str(registry),
        "--snapshot-id",
        job["snapshot_id"],
        "--pages",
        str(job["page"]),
        "--tessdata-directory",
        str(tessdata),
        "--execute",
    ]
    attempts = []
    for attempt in range(2):
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=200,
                env={**os.environ, "OMP_THREAD_LIMIT": "1"},
            )
            attempts.append(
                {
                    "attempt": attempt,
                    "returncode": result.returncode,
                    "diagnostic": result.stderr[-1000:] if result.returncode else "",
                }
            )
            if result.returncode == 0:
                return {**job, "state": "ocr_checkpointed_requires_review", "attempts": attempts}
        except subprocess.TimeoutExpired:
            attempts.append(
                {"attempt": attempt, "returncode": None, "diagnostic": "local OCR timeout"}
            )
    return {**job, "state": "human_escalation", "attempts": attempts}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--tessdata-directory", type=Path)
    parser.add_argument("--max-pages", type=int, default=64)
    parser.add_argument("--workers", type=int, choices=range(1, 5), default=4)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.max_pages <= 1000:
        parser.error("max-pages must be between 1 and 1000")
    jobs, omitted = plan(args.corpus_root, args.manifest, args.registry, args.max_pages)
    print(
        json.dumps(
            {
                "selected_pages": len(jobs),
                "remaining_beyond_bound": omitted,
                "mode": "execute_local_ocr" if args.execute else "plan",
                "paid_calls": 0,
            }
        ),
        flush=True,
    )
    if not args.execute:
        return
    if args.tessdata_directory is None:
        parser.error("Explicit local tessdata directory required")
    log = args.corpus_root / "processing/ocr-batch-events.jsonl"
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [
            pool.submit(
                execute_job,
                job,
                args.corpus_root,
                args.manifest,
                args.registry,
                args.tessdata_directory,
            )
            for job in jobs
        ]
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            with log.open("a") as stream:
                stream.write(json.dumps(result) + "\n")
            print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
