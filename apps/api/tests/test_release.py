"""Release guard tests. Cloud commands are mocked and never executed."""

import importlib.util
import json
import shutil
from pathlib import Path

import pytest
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[3]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "infra" / f"{name}.py")
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def config():
    result = json.loads(
        (ROOT / "infra/deploy.example.json")
        .read_text()
        .replace("YOUR_PROJECT_ID", "release-test-project")
    )
    result["firebase_web"]["api_key"] = "fictional-public-web-key"
    result["firebase_web"]["app_id"] = "1:123456:web:fictional"
    return result


def test_all_runtime_files_and_locks_invalidate_fingerprint(tmp_path):
    deploy = module("deploy")
    base = tmp_path / "api"
    shutil.copytree(
        ROOT / "apps/api/src", base / "src", ignore=shutil.ignore_patterns("__pycache__")
    )
    shutil.copytree(
        ROOT / "apps/api/alembic", base / "alembic", ignore=shutil.ignore_patterns("__pycache__")
    )
    for name in [
        "Dockerfile",
        "pyproject.toml",
        "uv.lock",
        "alembic.ini",
        ".dockerignore",
        ".gcloudignore",
        "cloudbuild.yaml",
    ]:
        shutil.copy(ROOT / "apps/api" / name, base / name)
    baseline = deploy.image_tag(base)
    for name in [
        "src/opportunity_platform/profiles/semantics.json",
        "uv.lock",
        "alembic/versions/f24a1000abcd_retrieval.py",
        "Dockerfile",
    ]:
        path = base / name
        original = path.read_bytes()
        path.write_bytes(original + b"\n")
        assert deploy.image_tag(base) != baseline
        path.write_bytes(original)
    new = base / "src/opportunity_platform/runtime-config.toml"
    new.write_text("config=1")
    assert deploy.image_tag(base) != baseline
    new.unlink()
    assert deploy.image_tag(base) == baseline
    (base / ".env").write_text("PRIVATE_NOT_A_BUILD_INPUT=secret")
    assert deploy.image_tag(base) == baseline
    (base / "src/credentials.json").write_text("{}")
    with pytest.raises(ValueError):
        deploy.image_tag(base)


def test_plan_and_execute_guards_and_safe_environment(tmp_path, monkeypatch):
    deploy = module("deploy")
    c = deploy.validate(config())
    path = tmp_path / "public.json"
    path.write_text(json.dumps(c))

    def forbidden(*args, **kwargs):
        raise AssertionError("Cloud command attempted")

    monkeypatch.setattr(deploy, "invoke", forbidden)
    assert deploy.main(["--config", str(path)]) == 0
    with pytest.raises(SystemExit):
        deploy.main(["--config", str(path), "--execute", "--approved-project", "wrong-project"])
    env = deploy.backend_environment(c)
    for flag in [
        "ENABLE_DEVELOPMENT_CATALOGUE",
        "AI_INGESTION_LIVE_ENABLED",
        "AI_ASSISTANT_LIVE_ENABLED",
        "DOCUMENT_UPLOADS_ENABLED",
    ]:
        assert env[flag] == "false"
    assert env["AI_EXTRACTION_PROVIDER"] == "gemini"
    monkeypatch.setenv("VITE_FIREBASE_AUTH_EMULATOR_URL", "http://localhost:9099")
    monkeypatch.setenv("VITE_UNEXPECTED_SECRET", "never-copy")
    web = deploy.web_environment(c, "https://release.run.app")
    assert web["VITE_FIREBASE_AUTH_EMULATOR_URL"] == ""
    assert "VITE_UNEXPECTED_SECRET" not in web
    plan = deploy.plan(c, "public-env.json")
    api = plan[-1][1]
    migration = plan[1][1]
    assert "--no-traffic" in api and "--cpu-throttling" in api
    assert api[api.index("--min") + 1] == "0" and api[api.index("--max") + 1] == "2"
    assert api[api.index("--timeout") + 1] == "60s"
    assert "DATABASE_URL=opportunity-migration-database-url:1" in migration
    assert all(
        "GEMINI_API_KEY=" not in arg and "OPENAI_API_KEY=" not in arg
        for _, cmd in plan
        for arg in cmd
    )
    # Existing local env files are preserved; execution refuses a developer checkout.
    monkeypatch.setattr(deploy, "ROOT", tmp_path)
    (tmp_path / "apps/web").mkdir(parents=True)
    (tmp_path / "apps/web/.env.local").write_text("keep me")
    with pytest.raises(SystemExit):
        deploy.main(["--config", str(path), "--execute", "--approved-project", c["project_id"]])
    assert (tmp_path / "apps/web/.env.local").read_text() == "keep me"


def test_production_rejects_paid_ingestion_and_emulator(monkeypatch):
    from opportunity_platform.core.config import Settings

    kwargs = dict(
        _env_file=None,
        environment="production",
        firebase_project_id="release-project",
        database_url="postgresql+psycopg://app:password@/opportunity?host=/cloudsql/project:region:db",
        cors_origins=["https://release-project.web.app"],
    )
    with pytest.raises(ValidationError):
        Settings(**kwargs, ai_ingestion_live_enabled=True)
    monkeypatch.setenv("FIREBASE_AUTH_EMULATOR_HOST", "127.0.0.1:9099")
    with pytest.raises(ValidationError):
        Settings(**kwargs)


def test_smoke_exercises_phase4_and_does_not_log_private_bodies(monkeypatch):
    smoke = module("smoke")
    calls = []

    def fake(url, path, expected=200, body=None, token=None, method=None, headers=None):
        calls.append((path, expected, body))
        if path == "/v1/opportunities":
            return {"items": []}, {}
        if method == "OPTIONS":
            return None, {
                "Access-Control-Allow-Origin": headers["Origin"]
            } if expected == 200 else {}
        return {}, {}

    monkeypatch.setattr(smoke, "request", fake)
    assert (
        smoke.public_smoke("https://service.run.app", ["https://release.web.app"])["public_smoke"]
        == "passed"
    )
    assert ("/v1/search", 401, {"mode": "me"}) in calls
    assert ("/v1/scenarios/evaluate", 401, {"base": {"mode": "me"}}) in calls
    for bad in [
        "https://attacker.invalid",
        "https://service.run.app@attacker.invalid",
        "https://service.run.app/path",
    ]:
        with pytest.raises(ValueError):
            smoke.origin(bad)


def test_authenticated_smoke_snapshot_and_cross_account(monkeypatch):
    smoke = module("smoke")
    calls = []

    def fake(url, path, expected=200, body=None, token=None, **kwargs):
        calls.append((path, expected, token, body))
        if path == "/v1/me":
            return {"uid": "first" if token == "token1" else "second", "is_admin": False}, {}
        if path == "/v1/search" and expected == 200:
            return {"subjects": [{"id": "person1", "kind": "person"}]}, {
                "Cache-Control": "private, no-store"
            }
        if path == "/v1/scenarios/evaluate" and expected == 200:
            return {"persistence": "none", "changes": [{"change": "unchanged"}]}, {}
        return {}, {}

    monkeypatch.setattr(smoke, "request", fake)
    assert (
        smoke.authenticated_smoke("https://service.run.app", "token1", "first", "token2")[
            "cross_account"
        ]
        == "denied"
    )
    assert ("/v1/search", 404, "token2", {"mode": "member", "subject_id": "person1"}) in calls
    assert all(
        path not in {"/v1/profile/me", "/v1/workspaces"} or body is None
        for path, _, _, body in calls
    )


def test_execute_orders_candidate_smoke_build_promotion_and_hosting_without_cloud(
    tmp_path, monkeypatch
):
    deploy = module("deploy")
    c = config()
    path = tmp_path / "public.json"
    path.write_text(json.dumps(c))
    receipt = tmp_path / "receipt.json"
    calls = []
    monkeypatch.setattr(deploy, "ROOT", tmp_path)
    monkeypatch.setattr(deploy, "image_tag", lambda: "release-test")
    status = {
        "url": "https://api.run.app",
        "latestReadyRevisionName": "api-new",
        "traffic": [{"tag": "release-test", "url": "https://candidate.run.app"}],
    }

    def invoke(label, args, **kwargs):
        calls.append(label)
        if label == "record-existing-traffic":
            return json.dumps(
                [
                    {
                        "status": {"traffic": [{"revisionName": "api-old", "percent": 100}]},
                        "spec": {"sensitive": "NEVER_IN_RECEIPT"},
                    }
                ]
            )
        if label == "read-candidate":
            return json.dumps({"status": status})
        return ""

    monkeypatch.setattr(deploy, "invoke", invoke)
    monkeypatch.setattr(deploy, "smoke", lambda *args: calls.append("smoke"))

    class HostingResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self):
            return b"<html>fictional mocked hosting</html>"

    monkeypatch.setattr(deploy.urllib.request, "urlopen", lambda *args, **kwargs: HostingResponse())
    assert (
        deploy.main(
            [
                "--config",
                str(path),
                "--execute",
                "--approved-project",
                c["project_id"],
                "--receipt",
                str(receipt),
            ]
        )
        == 0
    )
    assert (
        calls.index("migrate")
        < calls.index("api")
        < calls.index("smoke")
        < calls.index("build-web")
        < calls.index("promote-api")
        < calls.index("hosting")
    )
    assert "NEVER_IN_RECEIPT" not in receipt.read_text()

    def failed_smoke(*args):
        raise RuntimeError("candidate failed")

    calls.clear()
    monkeypatch.setattr(deploy, "smoke", failed_smoke)
    with pytest.raises(RuntimeError):
        deploy.main(["--config", str(path), "--execute", "--approved-project", c["project_id"]])
    assert "promote-api" not in calls and "hosting" not in calls


def test_workflow_is_manual_keyless_and_ci_never_deploys():
    import yaml

    deploy = yaml.load((ROOT / ".github/workflows/deploy.yml").read_text(), Loader=yaml.BaseLoader)
    assert set(deploy["on"]) == {"workflow_dispatch"}
    job = deploy["jobs"]["deploy"]
    assert job["environment"] == "production" and job["permissions"]["id-token"] == "write"
    assert job["needs"] == "validate"
    workflow = (ROOT / ".github/workflows/deploy.yml").read_text()
    assert "google-github-actions/auth@v3" in workflow
    assert "credentials_json" not in workflow and "FIREBASE_TOKEN" not in workflow
    ci = (ROOT / ".github/workflows/ci.yml").read_text()
    assert "--execute" not in ci and "firebase deploy" not in ci and "gcloud" not in ci
