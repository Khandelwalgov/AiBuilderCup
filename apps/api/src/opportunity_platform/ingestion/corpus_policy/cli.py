"""Offline audit/import by default; live extraction requires three explicit opt-ins."""

import argparse
import hashlib
import json
from pathlib import Path

from .archive import audit_record, load_manifest, registry_from, summarize

REPO = Path(__file__).resolve().parents[6]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["audit", "prepare", "import", "stage", "live-test"])
    parser.add_argument(
        "--manifest", type=Path, default=REPO / "data/corpus/acquired-manifest.jsonl"
    )
    parser.add_argument("--registry", type=Path, default=REPO / "data/corpus/sources.json")
    parser.add_argument("--corpus-root", type=Path, required=True)
    parser.add_argument("--document-id", action="append")
    parser.add_argument("--snapshot-id", action="append")
    parser.add_argument("--provider", choices=["gemini", "openai"])
    parser.add_argument("--review-provider", choices=["gemini", "openai"])
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--output", type=Path, help="New report path, exclusively created")
    parser.add_argument(
        "--execute", action="store_true", help="Explicitly append private DB records"
    )
    parser.add_argument("--actor-uid")
    authorization = parser.add_mutually_exclusive_group()
    authorization.add_argument("--authorize-paid", action="store_true")
    authorization.add_argument("--authorize-free-gemini", action="store_true")
    parser.add_argument("--model")
    parser.add_argument("--review-model")
    parser.add_argument("--focus")
    parser.add_argument("--candidate-json", type=Path)
    parser.add_argument("--max-repairs", type=int, choices=[0, 1], default=1)
    parser.add_argument("--max-input-tokens", type=int, default=20000)
    parser.add_argument("--max-output-tokens", type=int, default=4096)
    args = parser.parse_args()
    if not 1 <= args.limit <= 20:
        parser.error("Import/test limit must be between 1 and 20")
    if args.execute and not args.actor_uid:
        parser.error("An existing administrator actor UID is required for writes")
    if args.command == "stage" and not (
        args.candidate_json
        and args.focus
        and args.snapshot_id
        and len(args.snapshot_id) == 1
        and args.limit == 1
    ):
        parser.error("Staging requires one --snapshot-id, --limit 1, --focus and --candidate-json")
    if args.command == "live-test" and args.execute:
        if not (
            (args.authorize_paid or args.authorize_free_gemini)
            and (args.document_id or args.snapshot_id)
            and args.provider in {"gemini", "openai"}
            and args.focus
            and args.model
            and args.review_model
            and args.limit == 1
        ):
            parser.error(
                "Live test requires explicit paid/free authorization, one document, --limit 1, "
                "explicit focus, extractor model and review model"
            )
        if len(args.document_id or args.snapshot_id) != 1:
            parser.error("A future live test is bounded to one explicitly selected document")
    if args.command == "live-test" and args.execute:
        from opportunity_platform.core.config import settings

        config = settings()
        calls_per_cycle = (2 if args.provider == "gemini" else 1) + (
            2 if (args.review_provider or args.provider) == "gemini" else 1
        )
        if config.ai_max_requests_per_run < calls_per_cycle * (1 + args.max_repairs):
            parser.error(
                "Request capacity cannot cover extraction/review and the selected repair limit; "
                "explicitly configure sufficient bounded capacity or select --max-repairs 0"
            )
        if args.authorize_free_gemini:
            from opportunity_platform.ingestion.free_tier import verify

            if args.provider != "gemini" or args.review_provider not in {None, "gemini"}:
                parser.error("Free worker cannot switch providers")
            verify(args.model)
            verify(args.review_model)
        elif not (
            config.process_role == "ingestion_worker"
            and config.paid_ai_worker_enabled
            and config.ai_global_budget_usd > 0
            and config.ai_run_budget_usd > 0
        ):
            parser.error(
                "Paid worker permission and positive budgets are required; no database writes"
            )
    records = load_manifest(args.manifest)
    if args.document_id:
        unknown = set(args.document_id) - {r.document_id for r in records}
        if unknown:
            parser.error("Document identity is not in the immutable manifest")
        records = [r for r in records if r.document_id in args.document_id]
    if args.snapshot_id:
        if set(args.snapshot_id) - {r.snapshot_id for r in records}:
            parser.error("Snapshot identity is not in the selected immutable manifest")
        records = [r for r in records if r.snapshot_id in args.snapshot_id]
    if args.command == "live-test" and args.execute and len(records) != 1:
        parser.error("Select one exact snapshot; document identity has multiple archived versions")
    if args.command not in {"audit", "prepare"}:
        # Distinct source URL/hash, with chronological snapshot order retained.
        records = records[: args.limit]
    registry = registry_from(args.registry)
    audited = [audit_record(r, args.corpus_root, registry) for r in records]
    report = {
        "summary": summarize(audited),
        "documents": [a.public() for a in audited],
        "mode": "offline_read_only",
        "original_manifest_modified": False,
        "immutable_manifest_sha256": hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
    }
    if args.command == "prepare":
        from .packets import checkpoint

        results = [
            checkpoint(item, args.corpus_root / "processing" / "packets") for item in audited
        ]
        report["checkpoints"] = {
            "created": sum(created for _, created in results),
            "reused": sum(not created for _, created in results),
        }
    if args.command == "stage":
        from .prepared import PendingIndependentReview, PreparedExtractor
        from .validation import validate

        prepared = PreparedExtractor(
            json.loads(args.candidate_json.read_text()), audited[0].record.sha256
        )
        _, findings = validate(prepared.candidate.model_dump(mode="json"), audited[0])
        report["deterministic_findings"] = [p.model_dump(mode="json") for p in findings]
        report["independent_semantic_review"] = "pending; this session cannot self-verify"
        if any(p.severity in {"error", "critical"} for p in findings):
            parser.error("Prepared candidate failed deterministic checks; no database writes")
    if args.command not in {"audit", "prepare"} and args.execute:
        from sqlalchemy.orm import Session

        from opportunity_platform.db.session import engine
        from opportunity_platform.profiles.service import require_admin

        from .service import extract_candidate, import_archive

        with Session(engine) as session:
            actor = require_admin(session, args.actor_uid)
            results = []
            for item in audited:
                if not item.technically_ingestible or item.document_type == "irrelevant":
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
                    if args.command == "stage":
                        extractor, reviewer = prepared, PendingIndependentReview()
                    else:
                        from .live import GeminiRole, OpenAIRole

                        roles = {"gemini": GeminiRole, "openai": OpenAIRole}
                        extractor = roles[args.provider](
                            "extractor",
                            args.model,
                            max_input_tokens=args.max_input_tokens,
                            max_output_tokens=args.max_output_tokens,
                        )
                        reviewer = roles[args.review_provider or args.provider](
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
