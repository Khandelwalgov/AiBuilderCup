"""Resumable public document packets for bounded interactive interpretation."""

import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from .archive import TEXT_VERSION
from .validation import digest


def checkpoint(audited, directory: Path):
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{audited.record.snapshot_id}.{TEXT_VERSION}.json"
    packet = {
        "record": audited.record.model_dump(mode="json"),
        "audit": audited.public(),
        "pages": audited.pages,
        "clauses": [c.model_dump(mode="json") for c in audited.clauses],
    }
    if target.exists():
        if digest(json.loads(target.read_text())["packet"]) != digest(packet):
            raise ValueError("Checkpoint conflict: choose a new parser version")
        return target, False
    states = (
        ["integrity_verified", "text_extracted", "classified"]
        if audited.technically_ingestible
        else ["failed"]
    )
    states.append(
        "needs_ocr"
        if audited.needs_ocr
        else "extraction_pending"
        if audited.suitable_for_extraction
        else "human_review_required"
    )
    envelope = {
        "packet": packet,
        "source_hash": audited.record.sha256,
        "parser_version": TEXT_VERSION,
        "state": states[-1],
        "events": [{"state": state, "at": datetime.now(UTC).isoformat()} for state in states],
        "external_inference_calls": 0,
    }
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", dir=directory, delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(envelope, stream, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, target)  # atomic exclusive creation, never overwrite evidence
        except FileExistsError:
            if digest(json.loads(target.read_text())["packet"]) != digest(packet):
                raise ValueError("Concurrent checkpoint conflict") from None
            return target, False
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)
    return target, True
