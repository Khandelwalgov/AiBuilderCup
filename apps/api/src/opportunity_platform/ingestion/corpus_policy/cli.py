"""Offline audit/import by default; live extraction requires three explicit opt-ins."""

import argparse
import json
from pathlib import Path

from .archive import audit_record, load_manifest, registry_from, summarize

REPO = Path(__file__).resolve().parents[6]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["audit", "import", "live-test"])
    parser.add_argument(
        "--manifest", type=Path, default=REPO / "data/corpus/acquired-manifest.jsonl"
    )
    parser.add_argument("--registry", type=Path, default=REPO / "data/corpus/sources.json")
    parser.add_argument("--corpus-root", type=Path, required=True)
    parser.add_argument("--document-id", action="append")
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--output", type=Path, help="New report path, exclusively created")
    parser.add_argument(
        "--execute", action="store_true", help="Explicitly append private DB records"
    )
    parser.add_argument("--actor-uid")
    parser.add_argument("--authorize-paid", action="store_true")
    parser.add_argument("--model")
    parser.add_argument("--review-model")
    parser.add_argument("--focus")
    parser.add_argument("--max-repairs", type=int, choices=[0, 1, 2], default=0)
    parser.add_argument("--max-input-tokens", type=int, default=20000)
    parser.add_argument("--max-output-tokens", type=int, default=8192)
    args = parser.parse_args()
    if not 1 <= args.limit <= 20:
        parser.error("Import/test limit must be between 1 and 20")
    if args.execute and not args.actor_uid:
        parser.error("An existing administrator actor UID is required for writes")
    if args.command == "live-test" and args.execute:
        if not (
            args.authorize_paid
            and args.document_id
            and args.focus
            and args.model
            and args.review_model
            and args.limit == 1
        ):
            parser.error(
                "Live test requires --authorize-paid, one document, --limit 1, "
                "explicit focus, extractor model and review model"
            )
        if len(args.document_id) != 1:
            parser.error("A future live test is bounded to one explicitly selected document")
    records = load_manifest(args.manifest)
    if args.document_id:
        unknown = set(args.document_id) - {r.document_id for r in records}
        if unknown:
            parser.error("Document identity is not in the immutable manifest")
        records = [r for r in records if r.document_id in args.document_id]
    if args.command != "audit":
        # Distinct source URL/hash, with chronological snapshot order retained.
        records = records[: args.limit]
    registry = registry_from(args.registry)
    audited = [audit_record(r, args.corpus_root, registry) for r in records]
    report = {
        "summary": summarize(audited),
        "documents": [a.public() for a in audited],
        "mode": "offline_read_only",
        "original_manifest_modified": False,
    }
    if args.command != "audit" and args.execute:
        from sqlalchemy.orm import Session

        from opportunity_platform.db.session import engine
        from opportunity_platform.profiles.service import require_admin

        from .service import extract_candidate, import_archive

        with Session(engine) as session:
            actor = require_admin(session, args.actor_uid)
            results = []
            for item in audited:
                if not item.technically_ingestible:
                    results.append({"document_id": item.record.document_id, "status": "skipped"})
                    continue
                if args.command == "import":
                    snapshot, run = import_archive(session, item, actor)
                    results.append(
                        {
                            "snapshot_id": str(snapshot.id),
                            "run_id": str(run.id),
                            "status": run.status,
                        }
                    )
                else:
                    from .live import GeminiRole

                    extractor = GeminiRole(
                        "extractor",
                        args.model,
                        max_input_tokens=args.max_input_tokens,
                        max_output_tokens=args.max_output_tokens,
                    )
                    reviewer = GeminiRole(
                        "reviewer",
                        args.review_model,
                        max_input_tokens=args.max_input_tokens,
                        max_output_tokens=args.max_output_tokens,
                    )
                    run = extract_candidate(
                        session,
                        item,
                        actor,
                        args.focus,
                        extractor,
                        reviewer,
                        max_repairs=args.max_repairs,
                    )
                    results.append({"run_id": str(run.id), "status": run.status})
            session.commit()
            report.update(mode="private_database_append", results=results)
    if args.output:
        with args.output.open("x") as stream:
            json.dump(report, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
    print(
        json.dumps(
            {
                "mode": report["mode"],
                "summary": report["summary"],
                "results": report.get("results", []),
                "report": str(args.output) if args.output else None,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
