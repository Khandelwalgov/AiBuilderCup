"""Selective local OCR checkpoints, never a replacement for original captured evidence.

Requires explicitly installed Poppler/Tesseract. No hosted OCR or inference fallback.
OCR text remains unverified; it cannot silently replace immutable SourceSnapshot pages.
"""

import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from .archive import load_manifest, original_bytes, registry_from

HINDI_SHA256 = "4c73ffc59d497c186b19d1e90f5d721d678ea6b2e277b719bee4e2af12271825"


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--snapshot-id", required=True)
    parser.add_argument(
        "--pages",
        required=True,
        help="Explicit original page ordinals, comma-separated; at most eight",
    )
    parser.add_argument("--tessdata-directory", type=Path, required=True)
    parser.add_argument("--languages", choices=["eng", "hin+eng"], default="hin+eng")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    pages = sorted({int(value) for value in args.pages.split(",")})
    if not pages or len(pages) > 8 or not all(1 <= page <= 500 for page in pages):
        parser.error("Select one to eight bounded physical PDF pages")
    record = next(
        (r for r in load_manifest(args.manifest) if r.snapshot_id == args.snapshot_id), None
    )
    if record is None or record.format != "pdf":
        parser.error("Select an exact captured public PDF snapshot")
    original_bytes(args.corpus_root, record, registry_from(args.registry))
    if not args.execute:
        print(
            json.dumps(
                {"mode": "plan", "pages": pages, "source_hash": record.sha256, "paid_calls": 0}
            )
        )
        return
    if not shutil.which("pdftoppm") or not shutil.which("tesseract"):
        parser.error("Local Poppler/Tesseract unavailable; no cloud OCR fallback")
    if "hin" in args.languages and sha(args.tessdata_directory / "hin.traineddata") != HINDI_SHA256:
        parser.error("Hindi OCR weights do not match the pinned tessdata_fast 4.1.0 artifact")
    tool = subprocess.check_output(["tesseract", "--version"], text=True).splitlines()[0]
    language_hashes = {
        language: sha(args.tessdata_directory / (language + ".traineddata"))
        for language in args.languages.split("+")
    }
    root = args.corpus_root / "processing/ocr-checkpoints" / record.snapshot_id
    root.mkdir(parents=True, exist_ok=True)
    results = []
    render_environment = dict(os.environ)
    # Bundled Poppler may reference build-host Fontconfig paths on macOS. Use
    # local system fonts and a temporary writable cache, without touching HOME.
    render_directory = tempfile.TemporaryDirectory(prefix="corpus-fontconfig-")
    if sys.platform == "darwin" and not render_environment.get("FONTCONFIG_FILE"):
        fontconfig = Path(render_directory.name) / "fonts.conf"
        fontconfig.write_text(
            '<?xml version="1.0"?><fontconfig>'
            "<dir>/System/Library/Fonts</dir><dir>/System/Library/Fonts/Supplemental</dir>"
            "<dir>/Library/Fonts</dir><cachedir>" + render_directory.name + "</cachedir>"
            "</fontconfig>"
        )
        render_environment["FONTCONFIG_FILE"] = str(fontconfig)
    for page in pages:
        output = root / f"page-{page}.json"
        if output.exists():
            existing = json.loads(output.read_text())
            if (
                existing["source_hash"] != record.sha256
                or existing["tool"] != tool
                or existing["language_hashes"] != language_hashes
            ):
                raise ValueError(
                    "OCR checkpoint identity conflict; use a new explicit processor version"
                )
            results.append({"page": page, "state": "checkpoint_reused"})
            continue
        prefix = root / f"page-{page}"
        subprocess.run(
            [
                "pdftoppm",
                "-f",
                str(page),
                "-l",
                str(page),
                "-scale-to",
                "2200",
                "-singlefile",
                "-png",
                str(args.corpus_root / record.blob_path),
                str(prefix),
            ],
            check=True,
            timeout=90,
            capture_output=True,
            env=render_environment,
        )
        subprocess.run(
            [
                "tesseract",
                str(prefix.with_suffix(".png")),
                str(prefix),
                "--tessdata-dir",
                str(args.tessdata_directory),
                "-l",
                args.languages,
                "--psm",
                "3",
                "-c",
                "tessedit_create_txt=1",
                "-c",
                "tessedit_create_tsv=1",
            ],
            check=True,
            timeout=90,
            capture_output=True,
        )
        text = prefix.with_suffix(".txt").read_text()
        if len(text) > 100000:
            raise ValueError("OCR page text exceeds bound")
        with prefix.with_suffix(".tsv").open() as stream:
            words = [
                row
                for row in csv.DictReader(stream, delimiter="\t")
                if float(row.get("conf", -1)) >= 0 and row.get("text", "").strip()
            ]
        confidences = [float(word["conf"]) for word in words]
        packet = {
            "state": "needs_human_ocr_review",
            "source_hash": record.sha256,
            "snapshot_id": record.snapshot_id,
            "source_url": record.canonical_source_url,
            "page": page,
            "tool": tool,
            "language_hashes": language_hashes,
            "created_at": datetime.now(UTC).isoformat(),
            "render_scale_to": 2200,
            "render_font_configuration": "local_system_fonts"
            if sys.platform == "darwin"
            else "system_default",
            "image_sha256": sha(prefix.with_suffix(".png")),
            "text_sha256": sha(prefix.with_suffix(".txt")),
            "text": text,
            "mean_word_confidence": sum(confidences) / len(confidences) if confidences else 0,
            "low_confidence_words": sum(value < 70 for value in confidences),
            "word_count": len(words),
            "original_snapshot_pages_modified": False,
            "paid_calls": 0,
        }
        with output.open("x") as stream:
            json.dump(packet, stream, ensure_ascii=False, indent=2)
        results.append({"page": page, "state": packet["state"], "word_count": len(words)})
    render_directory.cleanup()
    print(json.dumps({"results": results, "paid_calls": 0, "original_modified": False}))


if __name__ == "__main__":
    main()
