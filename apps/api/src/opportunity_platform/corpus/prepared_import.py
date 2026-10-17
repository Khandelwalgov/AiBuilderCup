"""Explicit checksum-bound selection of public, unapproved prepared components."""

import hashlib
import json
import re
import uuid
from pathlib import Path

from opportunity_platform.ingestion.corpus_policy.archive import load_manifest
from opportunity_platform.ingestion.corpus_policy.validation import digest

VERSION = "prepared-import-v1"
PATH = "processing/import-manifest-v1.json"
FIELDS = {
    "snapshot_id",
    "source_hash",
    "candidate_path",
    "candidate_sha256",
    "focus",
    "validation_state",
    "idempotency_key",
}


def read_packet(root, relative):
    path = root / relative
    if (
        path.is_symlink()
        or not path.resolve().is_relative_to(root.resolve())
        or path.stat().st_size > 2 * 1024**2
    ):
        raise ValueError("Unsafe or oversized prepared candidate path")
    raw = path.read_bytes()
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def selection(root: Path):
    path = root / PATH
    if not path.exists():
        return None  # Explicit compatibility with the original three single-component files.
    manifest, _ = read_packet(root, PATH)
    if set(manifest) != {"version", "entries"} or manifest["version"] != VERSION:
        raise ValueError("Unsupported prepared import manifest")
    entries = manifest["entries"]
    if not isinstance(entries, list) or len(entries) > 2000:
        raise ValueError("Prepared import entry bound exceeded")
    sources = {r.snapshot_id: r.sha256 for r in load_manifest(root / "manifest.jsonl")}
    result, identities, paths = {}, set(), set()
    total_candidate_bytes = 0
    for entry in entries:
        if set(entry) != FIELDS:
            raise ValueError("Unexpected prepared import fields")
        sid = str(uuid.UUID(entry["snapshot_id"]))
        if sid != entry["snapshot_id"] or sources.get(sid) != entry["source_hash"]:
            raise ValueError("Prepared import source identity mismatch")
        if not re.fullmatch(r"[a-f0-9]{64}", entry["candidate_sha256"]):
            raise ValueError("Invalid prepared file checksum")
        if not isinstance(entry["focus"], str) or not 1 <= len(entry["focus"].strip()) <= 2000:
            raise ValueError("Explicit bounded component focus required")
        if not re.fullmatch(
            r"processing/codex-v1/"
            + re.escape(sid)
            + r"(?:\.[a-zA-Z0-9_-]{1,80})?\.candidate\.json",
            entry["candidate_path"],
        ):
            raise ValueError("Prepared path must name the selected snapshot component")
        if entry["validation_state"] != "deterministic_valid_human_review_required":
            raise ValueError("Only unapproved deterministic-valid packets may be selected")
        key = {
            name: entry[name]
            for name in ["snapshot_id", "source_hash", "candidate_sha256", "focus"]
        }
        if entry["idempotency_key"] != digest(key):
            raise ValueError("Prepared import idempotency key mismatch")
        identity = (sid, entry["focus"])
        if identity in identities or entry["candidate_path"] in paths:
            raise ValueError("Duplicate prepared component selection")
        total_candidate_bytes += (root / entry["candidate_path"]).stat().st_size
        if total_candidate_bytes > 16 * 1024**2:
            raise ValueError("Prepared candidate memory budget exceeded")
        packet, checksum = read_packet(root, entry["candidate_path"])
        if (
            checksum != entry["candidate_sha256"]
            or packet.get("source_hash") != entry["source_hash"]
        ):
            raise ValueError("Prepared candidate checksum/source mismatch")
        if packet.get("focus", entry["focus"]) != entry["focus"]:
            raise ValueError("Prepared focus conflicts with import selection")
        identities.add(identity)
        paths.add(entry["candidate_path"])
        result.setdefault(sid, []).append({"packet": packet, "focus": entry["focus"]})
        if len(result[sid]) > 20:
            raise ValueError("Per-document component limit exceeded")
    return result


def packets(root, record, selected):
    if selected is not None:
        return selected.get(record.snapshot_id, [])
    relative = "processing/codex-v1/" + record.snapshot_id + ".candidate.json"
    if not (root / relative).exists():
        return []
    packet, _ = read_packet(root, relative)
    return [{"packet": packet, "focus": packet.get("focus")}]
