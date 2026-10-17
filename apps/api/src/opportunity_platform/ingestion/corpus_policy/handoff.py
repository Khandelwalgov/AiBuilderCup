"""Portable, offline corpus handoff. No cloud credentials or database connections.

Only manifest-referenced originals and explicitly public processing artifacts enter a
bundle. Verification completes before extraction, and existing destinations are refused.
"""

import argparse
import gzip
import hashlib
import io
import json
import sqlite3
import tarfile
import tempfile
from pathlib import Path, PurePosixPath

from opportunity_platform.corpus.schemas import ManifestRecord

from .archive import load_manifest, original_bytes, registry_from

VERSION = "corpus-handoff-v1"
MAX_TOTAL = 3 * 1024**3
MAX_MEMBERS = 20000
ACQUISITION_STATE = {
    "ledger.sqlite3",
    "events.jsonl",
    "runs.jsonl",
    "sources.jsonl",
    "discoveries.jsonl",
}
PROCESSORS = {"packets", "ocr-checkpoints", "codex-v1", "interactive-triage-v1", "completion-v1"}


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def safe_name(name):
    path = PurePosixPath(name)
    return (
        bool(name)
        and not path.is_absolute()
        and ".." not in path.parts
        and "\\" not in name
        and path.as_posix() == name
    )


def public_derivative(path):
    return (
        len(path.parts) >= 3
        and path.parts[0] == "processing"
        and path.parts[1] in PROCESSORS
        and path.suffix in {".json", ".png", ".txt", ".tsv"}
    )


def build(root, manifest, registry, destination, import_manifest=None):
    root, destination = Path(root).resolve(), Path(destination)
    records = load_manifest(manifest)
    specs = registry_from(registry)
    files = {"manifest.jsonl": Path(manifest), "registry.json": Path(registry)}
    ledger_directory = tempfile.TemporaryDirectory(prefix="corpus-handoff-ledger-")
    for name in ACQUISITION_STATE:
        path = root / name
        if path.exists():
            if path.is_symlink():
                raise ValueError("Symlink acquisition state refused")
            if name == "ledger.sqlite3":
                backup = Path(ledger_directory.name) / name
                source = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
                target = sqlite3.connect(backup)
                try:
                    source.backup(target)
                finally:
                    source.close()
                    target.close()
                files[name] = backup
            else:
                files[name] = path
    selection = (
        Path(import_manifest) if import_manifest else root / "processing/import-manifest-v1.json"
    )
    if selection.exists():
        files["processing/import-manifest-v1.json"] = selection
    for record in records:
        original_bytes(root, record, specs)
        files[record.blob_path] = root / record.blob_path
    for path in (root / "processing").rglob("*"):
        relative = path.relative_to(root)
        if path.is_file() and public_derivative(relative):
            if path.is_symlink() or not path.resolve().is_relative_to(root):
                raise ValueError("Symlink derivative refused")
            files[relative.as_posix()] = path
    inventory = {
        "version": VERSION,
        "manifest_sha256": sha(Path(manifest)),
        "registry_sha256": sha(Path(registry)),
        "snapshots": len(records),
        "unique_documents": len({r.sha256 for r in records}),
        "publication_authorized": False,
        "files": [
            {"path": name, "sha256": sha(path), "size_bytes": path.stat().st_size}
            for name, path in sorted(files.items())
        ],
    }
    if len(files) > MAX_MEMBERS or sum(f["size_bytes"] for f in inventory["files"]) > MAX_TOTAL:
        raise ValueError("Handoff bounds exceeded")
    # Exclusive creation; deterministic headers enable content-addressed transport.
    with (
        destination.open("xb") as output,
        gzip.GzipFile(fileobj=output, mode="wb", mtime=0, filename="") as compressed,
    ):
        with tarfile.open(fileobj=compressed, mode="w|") as archive:
            payload = json.dumps(inventory, sort_keys=True, ensure_ascii=False).encode()
            entries = [("handoff.json", io.BytesIO(payload), len(payload))]
            for name, path in sorted(files.items()):
                entries.append((name, path, path.stat().st_size))
            for name, source, size in entries:
                header = tarfile.TarInfo(name)
                header.size, header.mode = size, 0o600
                if isinstance(source, Path):
                    with source.open("rb") as stream:
                        archive.addfile(header, stream)
                else:
                    archive.addfile(header, source)
    verify(destination)
    ledger_directory.cleanup()
    return {
        "bundle": str(destination),
        "sha256": sha(destination),
        "files": len(files),
        "snapshots": len(records),
        "unique_documents": inventory["unique_documents"],
    }


def verify(bundle):
    with tarfile.open(bundle, "r:gz") as archive:
        members = archive.getmembers()
        names = [member.name for member in members]
        if len(members) > MAX_MEMBERS + 1 or len(names) != len(set(names)):
            raise ValueError("Duplicate or excessive handoff members")
        if sum(m.size for m in members) > MAX_TOTAL:
            raise ValueError("Oversized handoff")
        for member in members:
            if not member.isfile() or not safe_name(member.name) or member.size < 0:
                raise ValueError("Unsafe handoff member")
        index_member = archive.getmember("handoff.json")
        if index_member.size > 10 * 1024**2:
            raise ValueError("Oversized inventory")
        index = json.load(archive.extractfile(index_member))
        if index.get("version") != VERSION or index.get("publication_authorized") is not False:
            raise ValueError("Unsupported handoff contract")
        files = index["files"]
        if len({row["path"] for row in files}) != len(files):
            raise ValueError("Duplicate inventory path")
        if set(names) != {row["path"] for row in files} | {"handoff.json"}:
            raise ValueError("Inventory/member mismatch")
        for row in files:
            member = archive.getmember(row["path"])
            path = PurePosixPath(row["path"])
            if not (
                row["path"]
                in {"manifest.jsonl", "registry.json", "processing/import-manifest-v1.json"}
                | ACQUISITION_STATE
                or path.parts[0] == "blobs"
                or public_derivative(path)
            ):
                raise ValueError("Nonpublic handoff path")
            stream = archive.extractfile(member)
            if (
                member.size != row["size_bytes"]
                or hashlib.file_digest(stream, "sha256").hexdigest() != row["sha256"]
            ):
                raise ValueError("Handoff checksum mismatch")
        by_name = {row["path"]: row for row in files}
        if any(
            by_name[name]["sha256"] != index[key]
            for name, key in [
                ("manifest.jsonl", "manifest_sha256"),
                ("registry.json", "registry_sha256"),
            ]
        ):
            raise ValueError("Manifest/registry identity mismatch")
        records = [
            ManifestRecord.model_validate_json(line)
            for line in archive.extractfile("manifest.jsonl").read().decode().splitlines()
            if line.strip()
        ]
        if len({r.snapshot_id for r in records}) != len(records):
            raise ValueError("Duplicate source snapshots in handoff")
        expected_blobs = {}
        for record in records:
            expected = f"blobs/{record.sha256[:2]}/{record.sha256}.{record.format}"
            if record.blob_path != expected or not safe_name(expected):
                raise ValueError("Invalid original blob identity")
            expected_blobs[expected] = record
        actual_blobs = {name for name in by_name if name.startswith("blobs/")}
        if actual_blobs != set(expected_blobs):
            raise ValueError("Original blob inventory mismatch")
        for name, record in expected_blobs.items():
            if (
                by_name[name]["sha256"] != record.sha256
                or by_name[name]["size_bytes"] != record.size_bytes
            ):
                raise ValueError("Original manifest/blob hash mismatch")
        if (
            len(records) != index["snapshots"]
            or len({r.sha256 for r in records}) != index["unique_documents"]
        ):
            raise ValueError("Handoff source counts mismatch")
        return index


def restore(bundle, destination):
    index = verify(bundle)
    destination = Path(destination)
    # Refuse merging into a working collector or overwriting any prior checkpoint.
    destination.mkdir(parents=True, exist_ok=False)
    with tarfile.open(bundle, "r:gz") as archive:
        archive.extractall(destination, filter="data")
    records = load_manifest(destination / "manifest.jsonl")
    registry = registry_from(destination / "registry.json")
    for record in records:
        original_bytes(destination, record, registry)
    if (
        len(records) != index["snapshots"]
        or len({r.sha256 for r in records}) != index["unique_documents"]
    ):
        raise ValueError("Restored manifest counts mismatch")
    return index


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["build", "verify", "restore"])
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--corpus-root", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--registry", type=Path)
    parser.add_argument("--destination", type=Path)
    parser.add_argument(
        "--import-manifest", type=Path, help="Explicit immutable compatible selection"
    )
    args = parser.parse_args()
    if args.command == "build":
        if not all([args.corpus_root, args.manifest, args.registry]):
            parser.error("build requires corpus root, manifest and registry")
        report = build(
            args.corpus_root, args.manifest, args.registry, args.bundle, args.import_manifest
        )
    else:
        if args.command == "restore" and args.destination is None:
            parser.error("restore requires a new destination")
        index = (
            restore(args.bundle, args.destination)
            if args.command == "restore"
            else verify(args.bundle)
        )
        report = {
            "version": index["version"],
            "files": len(index["files"]),
            "snapshots": index["snapshots"],
            "unique_documents": index["unique_documents"],
            "sha256": sha(args.bundle),
        }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
