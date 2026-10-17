import copy
import io
import json
import tarfile

import pytest
from test_corpus_policy import record

from opportunity_platform.corpus.schemas import SourceSpec
from opportunity_platform.ingestion.corpus_policy import completion, handoff, ocr_batch
from opportunity_platform.ingestion.corpus_policy.archive import audit_record
from opportunity_platform.ingestion.corpus_policy.packets import checkpoint


@pytest.fixture
def corpus(tmp_path):
    root = tmp_path / "corpus"
    root.mkdir()
    raw = (
        b"<html><main><h1>Student grant guidelines</h1><p>Applicants must be Indian. "
        b"Annual parental income up to Rs. 2.5 lakh, "
        b"except specified exclusions.</p></main></html>"
    )
    item = record(raw, fmt="html", url="https://test.gov.in/grant.html")
    blob = root / item.blob_path
    blob.parent.mkdir(parents=True)
    blob.write_bytes(raw)
    manifest = root / "manifest.jsonl"
    manifest.write_text(item.model_dump_json() + "\n")
    spec = SourceSpec(
        key="test",
        authority="Test authority",
        jurisdiction="India",
        category="education",
        seeds=["https://test.gov.in/index"],
        allowed_hosts=["test.gov.in"],
        access="public",
        access_note="Synthetic test only",
    )
    registry = root / "registry.json"
    registry.write_text(json.dumps([spec.model_dump(mode="json")]))
    audited = audit_record(item, root, {"test": spec})
    checkpoint(audited, root / "processing/packets")
    return root, manifest, registry, item


def test_completion_resume_mentions_and_no_false_semantic_approval(corpus):
    root, manifest, registry, _ = corpus
    target, first = completion.process(root, manifest, registry, root / "processing/completion-v1")
    again, second = completion.process(root, manifest, registry, root / "processing/completion-v1")
    assert target == again and first == second
    assert first["fully_processed"] == 0
    artifact = json.loads((root / first["records"][0]["artifact"]).read_text())
    assert artifact["currentness"]["state"] == "unknown"
    assert artifact["human_required"] and not artifact["publication_authorized"]
    assert {m["kind"] for m in artifact["source_mentions"]} >= {
        "amount_or_threshold",
        "qualifier_or_exception",
    }


def test_failed_source_isolated_and_previous_checkpoint_preserved(corpus):
    root, manifest, registry, item = corpus
    _, good = completion.process(root, manifest, registry, root / "processing/completion-v1")
    prior = root / good["records"][0]["artifact"]
    old_hash = handoff.sha(prior)
    bad = copy.deepcopy(item)
    bad.snapshot_id = "different-snapshot"
    bad.sha256 = "f" * 64
    manifest.write_text(item.model_dump_json() + "\n" + bad.model_dump_json() + "\n")
    _, report = completion.process(root, manifest, registry, root / "processing/completion-v1")
    assert len(report["records"]) == 1 and len(report["failures"]) == 1
    assert handoff.sha(prior) == old_hash


def test_ocr_checkpoint_integrity_rejects_altered_text(tmp_path):
    folder = tmp_path / "processing/ocr-checkpoints/snapshot"
    folder.mkdir(parents=True)
    (folder / "page-1.png").write_bytes(b"test image")
    (folder / "page-1.txt").write_text("original OCR")
    packet = {
        "source_hash": "a" * 64,
        "page": 1,
        "text": "original OCR",
        "image_sha256": handoff.sha(folder / "page-1.png"),
        "text_sha256": handoff.sha(folder / "page-1.txt"),
    }
    (folder / "page-1.json").write_text(json.dumps(packet))
    assert completion.ocr_index(tmp_path)
    (folder / "page-1.txt").write_text("changed OCR")
    with pytest.raises(ValueError, match="checksum"):
        completion.ocr_index(tmp_path)


def test_portable_bundle_roundtrip_determinism_allowlist_and_exclusive_restore(corpus, tmp_path):
    root, manifest, registry, item = corpus
    (root / ".env").write_text("DO_NOT_TRANSPORT")
    (root / "processing/private").mkdir()
    (root / "processing/private/user.json").write_text("DO_NOT_TRANSPORT")
    first, second = tmp_path / "one.tar.gz", tmp_path / "two.tar.gz"
    a = handoff.build(root, manifest, registry, first)
    b = handoff.build(root, manifest, registry, second)
    assert a["sha256"] == b["sha256"]
    index = handoff.verify(first)
    assert not any("private" in f["path"] or ".env" in f["path"] for f in index["files"])
    restored = tmp_path / "restored"
    handoff.restore(first, restored)
    assert (restored / item.blob_path).read_bytes() == (root / item.blob_path).read_bytes()
    with pytest.raises(FileExistsError):
        handoff.restore(first, restored)
    with pytest.raises(FileExistsError):
        handoff.build(root, manifest, registry, first)


@pytest.mark.parametrize(
    "name", ["../escape", "/absolute", "processing/../escape", "processing\\escape"]
)
def test_malicious_bundle_paths_refused_before_restore(tmp_path, name):
    bundle = tmp_path / "bad.tar.gz"
    with tarfile.open(bundle, "w:gz") as archive:
        member = tarfile.TarInfo(name)
        member.size = 3
        archive.addfile(member, io.BytesIO(b"bad"))
    with pytest.raises(ValueError, match="Unsafe"):
        handoff.restore(bundle, tmp_path / "never_created")
    assert not (tmp_path / "never_created").exists()


def test_ocr_failure_one_retry_then_escalation(monkeypatch, tmp_path):
    calls = []

    def fail(*args, **kwargs):
        calls.append(args)
        from types import SimpleNamespace

        return SimpleNamespace(returncode=1, stderr="local parser failure")

    monkeypatch.setattr(ocr_batch.subprocess, "run", fail)
    result = ocr_batch.execute_job(
        {"snapshot_id": "s", "page": 1},
        tmp_path,
        tmp_path / "manifest",
        tmp_path / "registry",
        tmp_path,
    )
    assert len(calls) == 2 and result["state"] == "human_escalation"


def test_existing_completed_ocr_not_repeated_for_html(corpus):
    root, manifest, registry, _ = corpus
    assert ocr_batch.plan(root, manifest, registry, 8) == ([], 0)


def test_candidate_inventory_validates_citations_hashes_and_duplicate_focus(corpus, monkeypatch):
    from test_corpus_policy import audited, envelope

    from opportunity_platform.ingestion.corpus_policy import import_inventory

    root, manifest, registry, item = corpus
    source = audited()
    source.record = item
    monkeypatch.setattr(import_inventory, "audit_record", lambda *args: source)
    directory = root / "processing/codex-v1"
    directory.mkdir()
    packet = {"source_hash": item.sha256, "candidate": envelope(source), "focus": "test-focus"}
    path = directory / f"{item.snapshot_id}.candidate.json"
    path.write_text(json.dumps(packet))
    invalid = {**packet, "source_hash": "f" * 64}
    (directory / f"{item.snapshot_id}.bad.candidate.json").write_text(json.dumps(invalid))
    report, selection = import_inventory.inventory(root, manifest, registry)
    assert report["deterministic_valid"] == 1 and report["escalated"] == 1
    entry = json.loads(selection.read_text())["entries"][0]
    assert entry["candidate_sha256"] == handoff.sha(path)
    assert entry["validation_state"] == "deterministic_valid_human_review_required"
    (directory / f"{item.snapshot_id}.duplicate.candidate.json").write_text(json.dumps(packet))
    report, _ = import_inventory.inventory(root, manifest, registry)
    assert report["deterministic_valid"] == 1 and report["escalated"] == 1
    assert len(report["duplicate_aliases"]) == 1


def test_bundle_altered_blob_fails_before_destination_creation(corpus, tmp_path):
    root, manifest, registry, item = corpus
    original = tmp_path / "valid.tar.gz"
    handoff.build(root, manifest, registry, original)
    altered = tmp_path / "altered.tar.gz"
    with tarfile.open(original, "r:gz") as source, tarfile.open(altered, "w:gz") as target:
        for member in source.getmembers():
            value = source.extractfile(member).read()
            if member.name == item.blob_path:
                value = b"X" + value[1:]
            target.addfile(member, io.BytesIO(value))
    with pytest.raises(ValueError, match="checksum"):
        handoff.restore(altered, tmp_path / "refused")
    assert not (tmp_path / "refused").exists()


def test_noncanonical_alias_paths_refused():
    assert not handoff.safe_name("processing//codex-v1/x.json")
    assert not handoff.safe_name("./manifest.jsonl")
    assert handoff.safe_name("processing/codex-v1/x.json")


def test_bad_ocr_document_isolated_from_other_sources(corpus):
    from opportunity_platform.ingestion.corpus_policy.archive import registry_from

    root, manifest, registry, item = corpus
    raw = (
        b"<html><main>Different source. A grant applicant must hold "
        b"an income certificate.</main></html>"
    )
    other = record(raw, fmt="html", url="https://test.gov.in/other.html")
    blob = root / other.blob_path
    blob.parent.mkdir(parents=True, exist_ok=True)
    blob.write_bytes(raw)
    manifest.write_text(item.model_dump_json() + "\n" + other.model_dump_json() + "\n")
    checkpoint(audit_record(other, root, registry_from(registry)), root / "processing/packets")
    broken = root / "processing/ocr-checkpoints" / item.snapshot_id
    broken.mkdir(parents=True)
    (broken / "page-1.json").write_text('{"invalid": "checkpoint"}')
    _, report = completion.process(root, manifest, registry, root / "processing/completion-v1")
    assert len(report["records"]) == 1
    assert report["records"][0]["snapshot_id"] == other.snapshot_id
    assert len(report["failures"]) == 1
    assert report["failures"][0]["snapshot_id"] == item.snapshot_id
