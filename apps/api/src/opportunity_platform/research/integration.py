"""Read-only, hash-bound display overlays. Original captures and policy rules stay immutable."""

import hashlib
import json
from functools import lru_cache
from pathlib import Path


@lru_cache
def source_overlays():
    data = json.loads(Path(__file__).with_name("source_integrations.json").read_text())
    for value in data["source_hashes"].values():
        for page in value["pages"]:
            if "text" in page:
                if hashlib.sha256(page["text"].encode()).hexdigest() != page["text_sha256"]:
                    raise ValueError("Invalid prepared OCR text checksum")
                if not page.get("image_sha256"):
                    raise ValueError("OCR derivative lacks render provenance")
    return data["source_hashes"]


@lru_cache
def quality_overlays():
    return json.loads(Path(__file__).with_name("catalogue_quality.json").read_text())["listings"]


def quality(row):
    value = quality_overlays().get(row.identity_key, {})
    return value if value.get("payload_hash") == row.payload_hash else {}


def integrated_pages(snapshot):
    overlay = source_overlays().get(snapshot.content_hash, {})
    derivatives = {p["page"]: p for p in overlay.get("pages", [])}
    pages = []
    for original in snapshot.pages:
        derivative = derivatives.get(original["page"], {})
        value = {
            "page": original["page"],
            "text": original["text"],
            "source_url": snapshot.source_url,
            "basis": "original_extracted_text",
            "readability": "unreadable"
            if not original["text"].strip()
            or (
                not overlay and snapshot.response_metadata.get("quality_audit", {}).get("needs_ocr")
            )
            else "readable",
            "text_sha256": hashlib.sha256(original["text"].encode()).hexdigest(),
            "image_sha256": None,
            "mean_word_confidence": None,
        }
        value.update({k: v for k, v in derivative.items() if k != "acquisition_snapshot_id"})
        value["original_text"] = original["text"] if value["basis"] == "offline_ocr" else None
        value["acquisition_snapshot_id"] = derivative.get("acquisition_snapshot_id")
        pages.append(value)
    return pages
