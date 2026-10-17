import io
import json
import sqlite3
import tarfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from opportunity_platform.corpus import production
from opportunity_platform.db.models import User


def test_checkpoint_contains_only_public_allowlisted_state_and_rejects_traversal(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    (root / ".env").write_text("PRIVATE_NEVER_PACKAGE")
    (root / "private-user.pdf").write_bytes(b"PRIVATE_NEVER_PACKAGE")
    (root / "manifest.jsonl").write_text("public source metadata")
    with sqlite3.connect(root / "ledger.sqlite3") as conn:
        conn.execute("create table test(id integer)")
    archive = tmp_path / "checkpoint.tar.gz"
    production.pack_state(root, archive)
    restored = tmp_path / "restored"
    restored.mkdir()
    production.unpack_state(archive, restored)
    assert (restored / "manifest.jsonl").read_text() == "public source metadata"
    assert not (restored / ".env").exists()
    assert not (restored / "private-user.pdf").exists()
    with tarfile.open(archive, "w:gz") as tar:
        entry = tarfile.TarInfo("../escape")
        entry.size = 3
        tar.addfile(entry, io.BytesIO(b"bad"))
    with pytest.raises(ValueError, match="Unsafe"):
        production.unpack_state(archive, restored)


def test_runtime_source_registry_matches_reviewed_canonical_registry():
    repo = Path(__file__).resolve().parents[3]
    assert json.loads(production.REGISTRY.read_text()) == json.loads(
        (repo / "data/corpus/sources.json").read_text()
    )


def test_bootstrap_needs_explicit_existing_profile_and_closes_after_first_admin(db):
    from opportunity_platform.operations.bootstrap_admin import bootstrap
    from opportunity_platform.profiles.service import ProfileWrite, save_profile

    save_profile(
        db,
        "fictional-first-admin",
        ProfileWrite(display_name="Fictional first administrator", facts=[]),
    )
    save_profile(
        db,
        "fictional-other-account",
        ProfileWrite(display_name="Fictional other account", facts=[]),
    )
    db.commit()
    plan = bootstrap(db, "fictional-first-admin")
    assert plan["mode"] == "plan" and not plan["administrator_present"]
    with pytest.raises(ValueError, match="Explicit"):
        bootstrap(db, "fictional-first-admin", execute=True)
    bootstrap(db, "fictional-first-admin", execute=True, confirmed=True)
    db.commit()
    with pytest.raises(ValueError, match="closed"):
        bootstrap(db, "fictional-other-account", execute=True, confirmed=True)
    with pytest.raises(ValueError, match="existing authenticated"):
        bootstrap(db, "nonexistent", execute=True, confirmed=True)


def test_bounded_import_plan_commit_and_repeat(db, tmp_path, monkeypatch):
    from test_corpus import spec
    from test_corpus_policy import record

    raw = (
        b"<html><h1>Public learner scholarship notice</h1><p>Applicants must be students. "
        b"Assistance conditions require official review and evidence. "
        b"This is a fictional offline test only, not an actual government opportunity.</p></html>"
    )
    first = record(raw, fmt="html", url="https://test.gov.in/guidelines.html")
    second = record(raw, fmt="html", url="https://test.gov.in/alias.html")
    for item in [first, second]:
        target = tmp_path / item.blob_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    (tmp_path / "manifest.jsonl").write_text(
        first.model_dump_json() + "\n" + second.model_dump_json() + "\n"
    )
    registry = tmp_path / "registry.json"
    registry.write_text(json.dumps([spec().model_dump(mode="json")]))
    monkeypatch.setattr(production, "REGISTRY", registry)
    actor = User(firebase_uid="fictional-durable-corpus-admin", is_admin=True)
    db.add(actor)
    db.commit()
    args = SimpleNamespace(offset=0, max_documents=20, execute=False, actor_uid=actor.firebase_uid)
    bucket = SimpleNamespace(name="fictional-corpus-bucket")
    planned = production.import_batch(db.get_bind(), bucket, tmp_path, args)
    assert planned["would_insert"] == 2 and planned["inserted"] == planned["failures"] == 0
    args.execute = True
    committed = production.import_batch(db.get_bind(), bucket, tmp_path, args)
    assert committed["inserted"] == 2 and committed["failures"] == 0
    repeated = production.import_batch(db.get_bind(), bucket, tmp_path, args)
    assert repeated["duplicates"] == 2 and repeated["inserted"] == 0
    assert repeated["paid_calls"] == 0
