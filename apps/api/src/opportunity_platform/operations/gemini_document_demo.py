"""One explicit free-tier worker demonstration on an EXISTING immutable packet.

Plan-only by default. No source fetching, OCR, production access, import or publication.
Output is an evidence-bound, incomplete candidate dossier for human review, not a policy.
"""

import argparse
import importlib.metadata
import json
import re
from pathlib import Path

from opportunity_platform.corpus.schemas import ManifestRecord
from opportunity_platform.ingestion.corpus_policy.archive import (
    Audited,
    clauses_for,
    extract_pages,
    original_bytes,
    registry_from,
)
from opportunity_platform.ingestion.corpus_policy.live import GeminiRole
from opportunity_platform.ingestion.corpus_policy.transport import bounded_schema
from opportunity_platform.ingestion.corpus_policy.validation import digest
from opportunity_platform.ingestion.corpus_policy.workflow import run_pipeline


def attempt_key(report, prompt_schema_hash, focus):
    # Account verification timestamps and report paths are audit data, not attempt identity.
    return "free-document:" + digest(
        {
            "source_hash": report["source"]["sha256"],
            "selected_text_sha256": report["selected_text_sha256"],
            "selected_pages": report["selected_pages"],
            "model": report["model"],
            "focus": focus,
            "prompt_schema_hash": prompt_schema_hash,
            "independent_review_authorized": report["independent_review_authorized"],
            "maximum_role_requests": report["maximum_role_requests"],
        }
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-root", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--snapshot-id", required=True)
    parser.add_argument("--pages", type=int, nargs="+", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--execute-authorized-free-worker", action="store_true")
    parser.add_argument("--authorize-independent-review", action="store_true")
    parser.add_argument("--local-schema", help="Exact isolated gemini_demo_<32 hex> schema")
    args = parser.parse_args()
    # Snapshot identity cannot select arbitrary files outside the preserved packet directory.
    import uuid

    identifier = str(uuid.UUID(args.snapshot_id))
    packet = json.loads(
        (
            args.corpus_root / "processing/packets" / (identifier + ".archive-text-v1.json")
        ).read_text()
    )
    record = ManifestRecord.model_validate(packet["packet"]["record"])
    raw = original_bytes(args.corpus_root, record, registry_from(args.registry))
    if packet["source_hash"] != record.sha256:
        raise ValueError("Packet/source hash mismatch")
    pages = [p for p in packet["packet"]["pages"] if p["page"] in args.pages]
    if len(pages) != len(set(args.pages)) or len(pages) > 3:
        raise ValueError("Select at most three actual captured pages")
    # Plain-text validation only: do not run OCR or trust a modified packet derivative.
    actual = {p["page"]: p for p in extract_pages(raw, record)}
    for page in pages:
        if page["page"] not in actual or page["text"] != actual[page["page"]]["text"]:
            raise ValueError(
                "Packet text differs from original PDF/HTML text; stop for human review"
            )
    audited = Audited(
        record,
        packet["packet"]["audit"]["corrected_title"],
        "policy_guideline",
        pages,
        clauses_for(pages),
        flags=["bounded_excerpt_not_complete_policy"],
        technically_ingestible=True,
        suitable_for_extraction=True,
    )
    report = {
        "source": record.model_dump(mode="json"),
        "selected_pages": sorted(args.pages),
        "selected_text_sha256": digest(pages),
        "scope": "partial source; human review required",
        "model": args.model,
        "provider": "gemini",
        "publication": "none",
        "production_changes": 0,
        "paid_inference": False,
        "mode": "plan_only",
        "maximum_role_requests": 4 if args.authorize_independent_review else 1,
        "maximum_external_calls": 8 if args.authorize_independent_review else 2,
        "maximum_repair_cycles": 1 if args.authorize_independent_review else 0,
        "independent_review_authorized": args.authorize_independent_review,
        "transport": {
            "name": "bounded_extraction_v1",
            "schema_sha256": digest(bounded_schema()),
            "sdk_version": importlib.metadata.version("google-genai"),
            "max_input_tokens": 20000,
            "max_output_tokens": 4096,
        },
    }
    if args.output.exists():
        raise ValueError("Evidence output already exists; never overwrite a genuine attempt")
    if args.execute_authorized_free_worker:
        from sqlalchemy.engine import make_url

        from opportunity_platform.core.config import settings
        from opportunity_platform.ingestion import budget
        from opportunity_platform.ingestion.free_tier import verify

        if make_url(settings().database_url).host not in {"localhost", "127.0.0.1", "::1"}:
            raise ValueError("This demonstration requires an isolated local PostgreSQL database")
        config = settings()
        if (
            config.paid_ai_worker_enabled
            or config.ai_openai_fallback_enabled
            or (config.ai_global_budget_usd != 0 or config.ai_run_budget_usd != 0)
        ):
            raise ValueError(
                "This operation authorizes free Gemini only; paid fallback is forbidden"
            )
        if not args.local_schema or not re.fullmatch(
            r"gemini_demo_[a-f0-9]{32}", args.local_schema
        ):
            raise ValueError("An explicitly selected isolated local demo schema is required")

        from sqlalchemy import text
        from sqlalchemy.orm import Session

        from opportunity_platform.db.session import engine

        with Session(engine) as session:
            if session.scalar(text("SELECT current_schema()")) != args.local_schema:
                raise ValueError("Database search_path does not select the isolated demo schema")

        report["account_proof"] = verify(args.model)
        extractor = GeminiRole(
            "extractor", args.model, max_output_tokens=4096, bounded_transport=True
        )
        if args.authorize_independent_review:
            reviewer = GeminiRole("reviewer", args.model, max_output_tokens=4096)
        else:
            from opportunity_platform.ingestion.corpus_policy.prepared import (
                PendingIndependentReview,
            )

            reviewer = PendingIndependentReview()
        focus = (
            "Extract only the explicit programme identity and business eligibility conditions "
            "on these selected pages. This is a partial document, not comprehensive eligibility. "
            "Do not invent application dates, routes, benefits or absent conditions. "
            "Preserve exact quotations and page numbers. Unsupported facts use unknown. "
            "Keep each quote concise and return no more than six requirements. "
            "Include bounded_excerpt_not_complete_policy in review_flags."
        )
        key = attempt_key(report, extractor.input_hash, focus)
        from sqlalchemy import func, select
        from sqlalchemy.orm import Session

        from opportunity_platform.db.models import InferenceReservation
        from opportunity_platform.db.session import engine

        with Session(engine) as session:
            if not session.scalar(
                select(func.pg_try_advisory_xact_lock(int(digest(key)[:15], 16)))
            ):
                raise ValueError("This document/model/prompt attempt is already active")
            if session.scalar(
                select(InferenceReservation.id).where(InferenceReservation.run_key == key).limit(1)
            ):
                raise ValueError(
                    "This document/model/prompt attempt already has durable reservations"
                )
            with budget.scope(key):
                outcome = run_pipeline(
                    audited,
                    focus,
                    extractor,
                    reviewer,
                    max_repairs=1 if args.authorize_independent_review else 0,
                )
        report.update(mode="genuine_provider_attempt", workflow=outcome.model_dump(mode="json"))
        report["validation_stages"] = {
            key: bool(extractor.last_usage.get(key))
            for key in [
                "generation_succeeded",
                "transport_schema_valid",
                "original_contract_valid",
                "source_passages_valid",
            ]
        }
        report["validation_stages"].update(
            incomplete_draft_awaiting_human_review=outcome.candidate is not None,
            independent_ai_review_completed=bool(
                args.authorize_independent_review
                and any(
                    stage.independent_review
                    and not any(issue.code == "independent_review_failed" for issue in stage.issues)
                    for stage in outcome.stages
                )
            ),
        )
    with args.output.open("x") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(
        json.dumps(
            {
                "mode": report["mode"],
                "model": args.model,
                "source_hash": record.sha256,
                "status": report.get("workflow", {}).get("status"),
                "report": str(args.output),
            }
        )
    )


if __name__ == "__main__":
    main()
