"""Validate prepared drafts offline and select only deterministic-valid originals.

Rejected candidates remain in a separate report, never disappear into the import list.
This command cannot approve, publish, call inference or connect to a database.
"""

import argparse
import json
from pathlib import Path

from opportunity_platform.ingestion.schemas import validate_evidence

from .archive import audit_record, load_manifest, registry_from
from .contracts import PolicyCandidate
from .handoff import sha
from .validation import digest, validate


def inventory(root, manifest, registry_path):
    root = Path(root)
    records = {r.snapshot_id: r for r in load_manifest(manifest)}
    registry, audited, rows, entries, identities = registry_from(registry_path), {}, [], [], {}
    aliases = []
    directory = root / "processing/codex-v1"
    for path in sorted(directory.glob("*.candidate.json")):
        if path.with_name(
            path.name.replace(".candidate.json", ".repair-1.candidate.json")
        ).exists():
            continue
        sid = path.name[:36]
        try:
            if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
                raise ValueError("Candidate path escape")
            packet = json.loads(path.read_text())
            record = records[sid]
            if packet["source_hash"] != record.sha256:
                raise ValueError("Candidate source hash mismatch")
            candidate = PolicyCandidate.model_validate(packet["candidate"])
            focus = packet.get("focus") or candidate.candidate.title
            if not isinstance(focus, str) or not 1 <= len(focus) <= 2000:
                raise ValueError("Invalid component focus")
            identity = (sid, focus)
            if identity in identities:
                previous = identities[identity]
                if previous["candidate_sha256"] == sha(path):
                    aliases.append(
                        {
                            "candidate_path": path.relative_to(root).as_posix(),
                            "duplicate_of": previous["candidate_path"],
                        }
                    )
                    continue
                raise ValueError("Conflicting source/component candidates")
            identities[identity] = {
                "candidate_sha256": sha(path),
                "candidate_path": path.relative_to(root).as_posix(),
            }
            if sid not in audited:
                audited[sid] = audit_record(record, root, registry)
            source = audited[sid]
            validate_evidence(candidate.candidate, source.pages)
            _, findings = validate(packet["candidate"], source)
            valid = not any(f.severity in {"error", "critical"} for f in findings)
            entry = {
                "snapshot_id": sid,
                "source_hash": record.sha256,
                "candidate_path": path.relative_to(root).as_posix(),
                "candidate_sha256": sha(path),
                "focus": focus,
            }
            entry["idempotency_key"] = digest(
                {k: entry[k] for k in ["snapshot_id", "source_hash", "candidate_sha256", "focus"]}
            )
            row = {
                **entry,
                "citation_validation": "passed_original_page_text",
                "validation_state": "deterministic_valid_human_review_required"
                if valid
                else "human_escalation",
                "findings": [f.model_dump(mode="json") for f in findings],
                "independent_semantic_review": "not_performed",
                "human_required": True,
            }
            rows.append(row)
            if valid:
                entries.append({**entry, "validation_state": row["validation_state"]})
        except (ValueError, KeyError, TypeError, OSError) as error:
            rows.append(
                {
                    "candidate_path": path.relative_to(root).as_posix(),
                    "validation_state": "human_escalation",
                    "diagnostic": str(error)[:300],
                    "human_required": True,
                }
            )
    report = {
        "version": "candidate-verification-v1",
        "manifest_sha256": sha(Path(manifest)),
        "registry_sha256": sha(Path(registry_path)),
        "distinct_candidates": len(rows),
        "duplicate_aliases": aliases,
        "citation_validated": sum(
            r.get("citation_validation") == "passed_original_page_text" for r in rows
        ),
        "deterministic_valid": len(entries),
        "escalated": len(rows) - len(entries),
        "independent_semantic_reviews": 0,
        "publication_authorized": False,
        "candidates": rows,
    }
    directory = root / "processing/completion-v1"
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"candidate-verification.{digest(report)}.json"
    if not target.exists():
        with target.open("x") as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2)
    selection = {"version": "prepared-import-v1", "entries": entries}
    target = root / "processing/import-manifest-v1.json"
    if target.exists():
        if json.loads(target.read_text()) != selection:
            raise ValueError(
                "Immutable import selection changed; build a new versioned handoff root"
            )
    else:
        with target.open("x") as stream:
            json.dump(selection, stream, ensure_ascii=False, indent=2)
    return report, target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    args = parser.parse_args()
    report, target = inventory(args.corpus_root, args.manifest, args.registry)
    print(
        json.dumps(
            {k: v for k, v in report.items() if k != "candidates"}
            | {"import_manifest": str(target)},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
