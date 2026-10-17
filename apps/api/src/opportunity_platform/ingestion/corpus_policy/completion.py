"""Resumable offline processing inventory; OCR is explicitly an unverified derivative.

A terminal triage state is not publication, complete extraction, or semantic approval.
Every count separates technical processing from interpretation and human decisions.
"""

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from .archive import TEXT_VERSION, load_manifest, original_bytes, quality, registry_from
from .handoff import sha
from .validation import digest

VERSION = "completion-v1"


def ocr_index(root, *, isolate=False, snapshot_hashes=None):
    index = {}
    for path in sorted((root / "processing/ocr-checkpoints").glob("*/page-*.json")):
        try:
            value = json.loads(path.read_text())
            image, text = path.with_suffix(".png"), path.with_suffix(".txt")
            if (
                sha(image) != value["image_sha256"]
                or sha(text) != value["text_sha256"]
                or text.read_text() != value["text"]
            ):
                raise ValueError("OCR checkpoint checksum mismatch")
            if snapshot_hashes and snapshot_hashes.get(path.parent.name) != value["source_hash"]:
                raise ValueError("OCR snapshot/source identity mismatch")
            if path.stem != f"page-{value['page']}":
                raise ValueError("OCR page identity mismatch")
            key = (value["source_hash"], value["page"])
            index.setdefault(key, (path, value))
        except (ValueError, OSError, KeyError, TypeError) as error:
            if not isolate:
                raise
            source_hash = (snapshot_hashes or {}).get(path.parent.name)
            if source_hash is None:
                raise ValueError("Unattributed OCR checkpoint cannot be safely isolated") from error
            key = (source_hash, int(path.stem.removeprefix("page-")))
            index[key] = (path, {"invalid_checkpoint": str(error)[:300]})
    return index


def classify(title, text, original_type):
    label = title.lower()
    if original_type == "document_index":
        return "document_index", "navigation_not_eligibility"
    if "citizen charter" in label:
        return "administrative_reference", "not_an_application_opportunity"
    if re.search(
        r"blacklist|blacklisted|debar|hold order|unhold|show cause|red flag|institute list", label
    ):
        return "institution_compliance", "eligibility_dependency_not_standalone_opportunity"
    if re.search(r"tender|nivida|निविदा", label):
        return "tender_notice", "requires_event_deadline_and_notice_linkage"
    if re.search(
        (
            r"date|extension|extend|pendancy|pendancy|pendency|portal open|"
            r"application close|reopen|opening order"
        ),
        label,
    ):
        return (
            "application_schedule_or_amendment",
            "requires_academic_year_and_baseline_reconciliation",
        )
    if re.search(
        r"faq|mobile application|sop|bio.?m[ae]tric|otr|payment process|pending application", label
    ):
        return "procedure_or_faq", "procedure_dependency_not_new_entitlement"
    if re.search(r"guideline|guidline|scheme|policy|योजना|दिशा|पुनर्वास", label) or re.search(
        r"(?i)operating guidelines|scheme guidelines", text[:12000]
    ):
        return "policy_or_guideline", "potential_opportunity_requires_component_extraction"
    return "announcement_or_unclassified", "requires_source_interpretation"


def evidence_inventory(pages):
    patterns = {
        "amount_or_threshold": (
            r"(?:Rs\.?|INR|₹|रु\.?|रूपये|"
            r"रुपये)\s*[0-9०-९][0-9०-९,. /-]*(?:lakh|crore|लाख|करोड़)?|"
            r"[0-9०-९]+(?:\.[0-9०-९]+)?\s*(?:%|प्रतिशत|lakh|crore|लाख|करोड़)"
        ),
        "date_mention": (
            r"\b[0-3]?[0-9][./-][01]?[0-9][./-](?:19|20)[0-9]{2}\b|\b(?:19|"
            r"20)[0-9]{2}-(?:20)?[0-9]{2}\b"
        ),
        "qualifier_or_exception": (
            r"(?i)\b(?:provided that|except|unless|whichever|subject to|"
            r"not eligible|shall not|only|amend|supersed)\b|किन्तु|परन्तु|"
            r"संशोधन|अपात्र|केवल"
        ),
    }
    result = []
    for page in pages:
        text = page["text"]
        for kind, pattern in patterns.items():
            for match in re.finditer(pattern, text):
                start, end = max(0, match.start() - 100), min(len(text), match.end() + 180)
                result.append(
                    {
                        "kind": kind,
                        "value_as_printed": match.group(),
                        "page": page["page"],
                        "source_url": page["source_url"],
                        "passage": text[start:end],
                        "basis": page["basis"],
                        "status": "mention_not_validated_interpretation",
                    }
                )
    return result


def source_artifact(root, record, registry, ocr, overrides=None):
    original_bytes(root, record, registry)
    if any(
        key[0] == record.sha256 and "invalid_checkpoint" in value for key, (_, value) in ocr.items()
    ):
        raise ValueError("Invalid OCR derivative for source; human reconciliation required")
    path = root / "processing/packets" / f"{record.snapshot_id}.{TEXT_VERSION}.json"
    envelope = json.loads(path.read_text())
    packet = envelope["packet"]
    if (
        packet["record"] != record.model_dump(mode="json")
        or envelope["source_hash"] != record.sha256
    ):
        raise ValueError("Extraction packet identity mismatch")
    pages, missing, low = [], [], []
    forced = set((overrides or {}).get(record.sha256, {}).get("pages", []))
    for original in packet["pages"]:
        page = {
            **original,
            "basis": "original_extracted_text",
            "text_sha256": digest(original["text"]),
        }
        if original["quality"] != "readable_text_unverified" or original["page"] in forced:
            recovered = ocr.get((record.sha256, original["page"]))
            if recovered:
                checkpoint, value = recovered
                page.update(
                    text=value["text"],
                    basis="unverified_local_ocr",
                    text_sha256=value["text_sha256"],
                    quality=quality(value["text"]),
                    ocr_checkpoint=checkpoint.relative_to(root).as_posix(),
                    image_sha256=value["image_sha256"],
                    mean_word_confidence=value["mean_word_confidence"],
                    original_extraction_quality=original["quality"],
                )
                if (
                    page["quality"] != "readable_text_unverified"
                    or value["mean_word_confidence"] < 70
                ):
                    low.append(original["page"])
            else:
                missing.append(original["page"])
        # URL aliases retain their exact captured identity, never dedupe citation URLs away.
        page["source_url"] = record.canonical_source_url
        pages.append(page)
    audit = packet["audit"]
    kind, relevance = classify(
        audit["corrected_title"], "\n".join(p["text"] for p in pages), audit["document_type"]
    )
    issuer = None
    for page in pages[:3]:
        match = re.search(
            (
                r"Ministry of (?:Micro,? Small[^\n]{0,70}|"
                r"Social Justice[^\n]{0,70})|"
                r"सामाजिक न्याय एवं अधिकारिता विभाग[^\n]{0,40}"
            ),
            page["text"],
            re.I,
        )
        if match:
            issuer = {
                "value_as_printed": match.group(),
                "page": page["page"],
                "passage": match.group(),
                "source_url": record.canonical_source_url,
                "basis": page["basis"],
                "verification": "literal_text_attribution_requires_review",
            }
            break
    mentions = evidence_inventory(pages)
    return {
        "version": VERSION,
        "snapshot_id": record.snapshot_id,
        "document_id": record.document_id,
        "source_hash": record.sha256,
        "idempotency_key": digest(
            {
                "snapshot_id": record.snapshot_id,
                "source_hash": record.sha256,
                "processor": VERSION,
                "page_hashes": [p["text_sha256"] for p in pages],
            }
        ),
        "source_url": record.canonical_source_url,
        "blob_path": record.blob_path,
        "captured_at": record.downloaded_at.isoformat(),
        "normalized_metadata": {
            "working_title": audit["corrected_title"],
            "title_basis": audit["title_basis"],
            "issuer": audit.get("document_issuer"),
            "issuer_evidence": audit.get("issuer_evidence"),
            "issuer_candidate": issuer,
            "publication_date": None,
            "effective_date": None,
            "application_deadline": None,
        },
        "classification": {
            "type": kind,
            "relevance": relevance,
            "method": "deterministic_triage_requires_review",
        },
        "pages": pages,
        "source_mentions": mentions,
        "processing": {
            "integrity_verified": True,
            "page_boundaries_preserved": True,
            "ocr_pages_required": sum(
                p["quality"] != "readable_text_unverified" or p["page"] in forced
                for p in packet["pages"]
            ),
            "ocr_pages_missing": missing,
            "ocr_low_confidence_or_empty_pages": low,
            "technical_state": "ocr_pending" if missing else "text_derivatives_checkpointed",
            "semantic_state": "pending_document_interpretation",
            "fully_processed": False,
        },
        "currentness": {
            "state": "unknown",
            "reason": (
                "Capture/index/HTTP dates are not legal effective or application dates; "
                "reconcile cited schedules and amendments before publication."
            ),
        },
        "human_required": True,
        "publication_authorized": False,
        "paid_inference_calls": 0,
    }


def process(root, manifest, registry_path, output):
    root, output = Path(root), Path(output)
    records, registry = load_manifest(manifest), registry_from(registry_path)
    ocr = ocr_index(root, isolate=True, snapshot_hashes={r.snapshot_id: r.sha256 for r in records})
    override_path = root / "processing/completion-v1/quality-overrides-v1.json"
    overrides = json.loads(override_path.read_text()) if override_path.exists() else {}
    for source_hash, override in overrides.items():
        if source_hash not in {r.sha256 for r in records} or not override.get("reason"):
            raise ValueError("Quality override lacks source identity or reason")
        if not override.get("pages") or any(
            type(p) is not int or not 1 <= p <= 500 for p in override["pages"]
        ):
            raise ValueError("Invalid quality override page")
    output.mkdir(parents=True, exist_ok=True)
    results, failures = [], []
    for record in records:
        try:
            artifact = source_artifact(root, record, registry, ocr, overrides)
            payload_hash = digest(artifact)
            target = output / f"{record.snapshot_id}.{payload_hash}.json"
            if target.exists():
                if digest(json.loads(target.read_text())) != payload_hash:
                    raise ValueError("Processing checkpoint conflict")
            else:
                with target.open("x") as stream:
                    json.dump(artifact, stream, ensure_ascii=False, indent=2)
            results.append(
                {
                    "snapshot_id": record.snapshot_id,
                    "source_hash": record.sha256,
                    "artifact": target.relative_to(root).as_posix(),
                    "artifact_sha256": sha(target),
                    "idempotency_key": artifact["idempotency_key"],
                    "processing": artifact["processing"],
                    "classification": artifact["classification"],
                }
            )
        except (ValueError, OSError, KeyError, TypeError) as error:
            failures.append(
                {
                    "snapshot_id": record.snapshot_id,
                    "code": type(error).__name__,
                    "error": str(error)[:300],
                }
            )
    unique = {item["source_hash"]: item for item in results}
    report = {
        "version": VERSION,
        "manifest_sha256": sha(Path(manifest)),
        "registry_sha256": sha(Path(registry_path)),
        "snapshots": len(records),
        "unique_documents": len({r.sha256 for r in records}),
        "source_artifacts": len(results),
        "unique_source_artifacts": len(unique),
        "fully_processed": sum(r["processing"]["fully_processed"] for r in unique.values()),
        "ocr_checkpoint_complete_documents": sum(
            r["processing"]["ocr_pages_required"] > 0 and not r["processing"]["ocr_pages_missing"]
            for r in unique.values()
        ),
        "ocr_pending_documents": sum(
            bool(r["processing"]["ocr_pages_missing"]) for r in unique.values()
        ),
        "ocr_unresolved_quality_documents": sum(
            bool(r["processing"]["ocr_low_confidence_or_empty_pages"]) for r in unique.values()
        ),
        "classifications": dict(Counter(r["classification"]["type"] for r in unique.values())),
        "records": results,
        "failures": failures,
        "publication_authorized": False,
    }
    target = output / f"inventory.{digest(report)}.json"
    if not target.exists():
        with target.open("x") as stream:
            json.dump(report, stream, indent=2)
    return target, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    args = parser.parse_args()
    target, report = process(
        args.corpus_root,
        args.manifest,
        args.registry,
        args.corpus_root / "processing/completion-v1",
    )
    print(
        json.dumps(
            {k: v for k, v in report.items() if k != "records"} | {"inventory": str(target)},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
