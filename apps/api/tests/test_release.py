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
    assert api[api.index("--min") + 1] == "0" and api[api.index("--max") + 1] == "1"
    assert api[api.index("--timeout") + 1] == "60s"
    assert "DATABASE_URL=opportunity-migration-database-url:1" in migration
    assert all(
        "GEMINI_API_KEY=" not in arg and "OPENAI_API_KEY=" not in arg
        for _, cmd in plan
        for arg in cmd
    )
    # Existing local env files are preserved; execution refuses a developer checkout.
    (tmp_path / "infra").mkdir(exist_ok=True)
    for name in ["firebase.json", ".firebaserc"]:
        shutil.copy(ROOT / "infra" / name, tmp_path / "infra" / name)
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


@pytest.mark.parametrize("reuse_image", [False, True])
def test_execute_orders_candidate_smoke_build_promotion_and_hosting_without_cloud(
    tmp_path, monkeypatch, reuse_image
):
    deploy = module("deploy")
    c = config()
    path = tmp_path / "public.json"
    path.write_text(json.dumps(c))
    receipt = tmp_path / "receipt.json"
    calls = []
    (tmp_path / "infra").mkdir(exist_ok=True)
    for name in ["firebase.json", ".firebaserc"]:
        shutil.copy(ROOT / "infra" / name, tmp_path / "infra" / name)
    monkeypatch.setattr(deploy, "ROOT", tmp_path)
    monkeypatch.setattr(deploy, "image_tag", lambda: "release-test")
    monkeypatch.setattr(deploy, "prepare_hosting_assets", lambda: None)
    status = {
        "url": "https://api.run.app",
        "latestReadyRevisionName": "api-new",
        "traffic": [{"tag": "r-test", "url": "https://candidate.run.app"}],
    }

    def invoke(label, args, **kwargs):
        calls.append(label)
        if label == "check-existing-image":
            return "sha256:" + "a" * 64 if reuse_image else None
        if label == "hosting":
            assert args[args.index("--only") + 1] == "hosting:unclaimed"
            assert args[args.index("--project") + 1] == "venuesignal"
        if label == "migration-job":
            assert "--args=-m,opportunity_platform.operations.migration_gate,--mode=verify" in args
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

    checked_urls = []

    class HostingResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self):
            return b"<html>fictional mocked hosting</html>"

    def hosting_open(url, **kwargs):
        checked_urls.append(url)
        return HostingResponse()

    monkeypatch.setattr(deploy.urllib.request, "urlopen", hosting_open)
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
    assert checked_urls == ["https://unclaimed-ai-cup.web.app/profile"]
    assert ("build" in calls) is not reuse_image
    assert "NEVER_IN_RECEIPT" not in receipt.read_text()
    assert json.loads(receipt.read_text())["web"] == "https://unclaimed-ai-cup.web.app"
    assert json.loads(receipt.read_text())["migration_mode"] == "verify"

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


def test_neon_plan_and_hosting_are_explicit_and_exclusive(tmp_path, monkeypatch):
    deploy = module("deploy")
    c = deploy.validate(config())
    deploy.validate_hosting(c)
    assert deploy.backend_environment(c)["DATABASE_PROVIDER"] == "neon"
    assert json.loads(deploy.backend_environment(c)["CORS_ORIGINS"]) == [
        "https://unclaimed-ai-cup.web.app",
        "https://unclaimed-ai-cup.firebaseapp.com",
    ]
    commands = deploy.plan(c, "public.json")
    assert not any(
        "cloudsql" in arg.lower() or "/cloudsql/" in arg for _, cmd in commands for arg in cmd
    )
    assert (
        "--args=-m,opportunity_platform.operations.migration_gate,--mode=verify" in commands[1][1]
    )
    assert "upgrade,head" not in commands[1][1]
    bad = {**c, "cloud_sql_connection": "not-allowed"}
    with pytest.raises(ValueError):
        deploy.validate(bad)
    (tmp_path / "infra").mkdir()
    shutil.copy(ROOT / "infra/firebase.json", tmp_path / "infra/firebase.json")
    rc = json.loads((ROOT / "infra/.firebaserc").read_text())
    rc["targets"]["venuesignal"]["hosting"]["unclaimed"] = ["venuesignal", "unclaimed-ai-cup"]
    (tmp_path / "infra/.firebaserc").write_text(json.dumps(rc))
    monkeypatch.setattr(deploy, "ROOT", tmp_path)
    with pytest.raises(ValueError):
        deploy.validate_hosting(c)


def test_neon_ssl_and_pooler_configuration():
    from opportunity_platform.core.config import Settings
    from opportunity_platform.core.database import connect_args, validate_neon_url

    direct = "postgresql+psycopg://fake:fictional-password@ep-fictional.aws.neon.tech/db?sslmode=require&channel_binding=require"
    pooled = direct.replace("ep-fictional.", "ep-fictional-pooler.")
    validate_neon_url(direct, direct=True)
    validate_neon_url(pooled)
    assert connect_args("neon")["prepare_threshold"] is None
    assert "prepare_threshold" not in connect_args("postgresql")
    with pytest.raises(ValueError):
        validate_neon_url(pooled, direct=True)
    for bad in [
        direct.replace("sslmode=require", "sslmode=disable"),
        direct.replace(".neon.tech", ".invalid"),
        direct + "&hostaddr=127.0.0.1",
        "not-a-url",
    ]:
        with pytest.raises(ValueError) as error:
            validate_neon_url(bad)
        assert "fictional-password" not in str(error.value)
    settings = Settings(
        _env_file=None,
        database_provider="neon",
        database_url=pooled,
        environment="production",
        firebase_project_id="venuesignal",
        cors_origins=["https://unclaimed-ai-cup.web.app"],
    )
    assert settings.database_provider == "neon"


def test_schema_verification_is_read_only_and_never_initializes(db):
    from sqlalchemy import text

    from opportunity_platform.operations.migration_gate import main, verify_head

    with pytest.raises(SystemExit):
        main(["--mode", "upgrade"])
    with db.bind.begin() as conn:
        conn.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32))"))
        conn.execute(text("INSERT INTO alembic_version VALUES ('f24a1000abcd')"))
    with db.bind.connect() as conn:
        verify_head(conn, ["f24a1000abcd"])
        assert conn.scalar(text("SHOW transaction_read_only")) == "on"
    with db.bind.connect() as conn:
        with pytest.raises(RuntimeError):
            verify_head(conn, ["not-the-head"])
    with db.bind.connect() as conn:
        assert conn.scalar(text("SELECT version_num FROM alembic_version")) == "f24a1000abcd"


def test_schema_gate_missing_metadata_does_not_initialize(db):
    from sqlalchemy import text
    from sqlalchemy.exc import ProgrammingError

    from opportunity_platform.operations.migration_gate import verify_head

    with db.bind.connect() as connection:
        with pytest.raises(ProgrammingError):
            verify_head(connection, ["f24a1000abcd"])
    with db.bind.connect() as connection:
        assert connection.scalar(text("SELECT to_regclass('alembic_version')")) is None


def test_upgrade_requires_separate_runner_authorization(tmp_path, monkeypatch, capsys):
    deploy = module("deploy")
    c = config()
    c["migration_mode"] = "upgrade"
    path = tmp_path / "public.json"
    path.write_text(json.dumps(c))

    def forbidden(*args, **kwargs):
        raise AssertionError("Unexpected cloud operation")

    monkeypatch.setattr(deploy, "invoke", forbidden)
    with pytest.raises(SystemExit):
        deploy.main(["--config", str(path), "--execute", "--approved-project", "venuesignal"])
    assert "--approve-migrations" in capsys.readouterr().err
    assert any(
        "--approve-upgrade" in arg for _, cmd in deploy.plan(c, "public.json") for arg in cmd
    )


def test_native_production_approval_fails_closed():
    gate = module("production_gate")
    environment = {
        "protection_rules": [
            {
                "type": "required_reviewers",
                "prevent_self_review": True,
                "reviewers": [{"type": "User", "reviewer": {"id": 1}}],
            }
        ],
        "deployment_branch_policy": {"custom_branch_policies": True, "protected_branches": False},
        "can_admins_bypass": False,
    }
    policies = {"branch_policies": [{"name": "master", "type": "branch"}]}
    gate.validate(environment, policies, "master", "refs/heads/master")
    import copy

    for change in [
        {"protection_rules": []},
        {"can_admins_bypass": True},
        {"deployment_branch_policy": None},
        {
            "protection_rules": [
                {"type": "required_reviewers", "reviewers": [1], "prevent_self_review": False}
            ]
        },
    ]:
        bad = copy.deepcopy(environment)
        bad.update(change)
        with pytest.raises(ValueError):
            gate.validate(bad, policies, "master", "refs/heads/master")
    with pytest.raises(ValueError):
        gate.validate(environment, policies, "master", "refs/heads/other")
    with pytest.raises(ValueError):
        gate.validate(
            environment, {"branch_policies": [{"name": "*"}]}, "master", "refs/heads/master"
        )
    for name in ["deploy.yml", "deploy-frontend.yml", "corpus-import.yml"]:
        workflow = (ROOT / ".github/workflows" / name).read_text()
        assert workflow.index("python3 infra/production_gate.py") < workflow.index(
            "google-github-actions/auth@"
        )


def test_worker_direct_secret_plan_never_reads_or_writes_credentials(tmp_path, monkeypatch):
    worker = module("worker_secret")
    c = config()
    corpus = json.loads((ROOT / "infra/corpus.example.json").read_text())
    deploy_path = tmp_path / "deploy.json"
    corpus_path = tmp_path / "corpus.json"
    deploy_path.write_text(json.dumps(c))
    corpus_path.write_text(json.dumps(corpus))

    def forbidden(*args, **kwargs):
        raise AssertionError("Unexpected credential/cloud operation")

    monkeypatch.setattr(worker, "read_secret", forbidden)
    monkeypatch.setattr(worker, "invoke", forbidden)
    assert (
        worker.main(["--deploy-config", str(deploy_path), "--corpus-config", str(corpus_path)]) == 0
    )
    with pytest.raises(SystemExit):
        worker.main(
            [
                "--deploy-config",
                str(deploy_path),
                "--corpus-config",
                str(corpus_path),
                "--execute",
                "--approved-project",
                "wrong",
            ]
        )
    direct = (
        "postgresql+psycopg://app:fictional-password@ep-fictional.aws.neon.tech/db?sslmode=require"
    )
    assert worker.direct_url(direct.replace("ep-fictional.", "ep-fictional-pooler.")) == direct
    for bad in [direct.replace("require", "disable"), direct.replace("neon.tech", "invalid")]:
        with pytest.raises(ValueError) as error:
            worker.direct_url(bad)
        assert "fictional-password" not in str(error.value)


def test_runtime_privilege_gate_is_read_only_and_rejects_missing_grants(db):
    from sqlalchemy import text

    from opportunity_platform.operations.runtime_gate import verify

    with db.bind.connect() as connection:
        assert verify(connection)["runtime_privileges"] == "passed"
        assert connection.scalar(text("SHOW transaction_read_only")) == "on"

    class Denied:
        def execute(self, query):
            assert str(query) == "SET TRANSACTION READ ONLY"

        def scalar(self, query, params):
            assert "has_table_privilege" in str(query)
            return False

    with pytest.raises(RuntimeError, match="lacks SELECT on policy_embeddings"):
        verify(Denied())


def test_explicit_runtime_grants_precede_privilege_gate_and_need_separate_approval(
    tmp_path, monkeypatch
):
    deploy = module("deploy")
    config_path = tmp_path / "public.json"
    config_path.write_text(json.dumps(config()))
    monkeypatch.setattr(
        deploy, "invoke", lambda *a, **k: pytest.fail("Cloud operation before authorization")
    )
    with pytest.raises(SystemExit):
        deploy.main(
            [
                "--config",
                str(config_path),
                "--execute",
                "--approved-project",
                "venuesignal",
                "--grant-runtime-role",
                "fictional_app",
            ]
        )
    commands = deploy.plan(deploy.validate(config()), "public-env.json", "fictional_app")
    labels = [label for label, _ in commands]
    assert (
        labels.index("migrate")
        < labels.index("runtime-grants")
        < labels.index("runtime-permissions")
        < labels.index("api")
    )
    grant_job = next(cmd for label, cmd in commands if label == "runtime-grants-job")
    assert "opportunity-migrations@venuesignal.iam.gserviceaccount.com" in grant_job
    assert any("runtime_grants" in arg and "fictional_app" in arg for arg in grant_job)
    for bad in ["owner,other", "app;DROP TABLE users", ""]:
        if bad:
            with pytest.raises(ValueError):
                deploy.plan(deploy.validate(config()), "env.json", bad)


def test_corpus_batches_use_exact_reviewed_manifest_size(tmp_path, monkeypatch, capsys):
    job = module("corpus_job")
    path = tmp_path / "corpus.json"
    path.write_text((ROOT / "infra/corpus.example.json").read_text())
    monkeypatch.setattr(
        job, "invoke", lambda *a, **k: pytest.fail("Plan attempted a cloud mutation")
    )
    assert job.main(["--config", str(path), "--all-batches", "--record-count", "42"]) == 0
    output = capsys.readouterr().out
    assert sum(line.startswith("corpus-job:") for line in output.splitlines()) == 3
    assert "--offset=40" in output and "--offset=60" not in output
    assert job.main(["--config", str(path), "--operation", "probe"]) == 0
    assert "neural_probe" in capsys.readouterr().out
    assert (
        job.main(
            [
                "--config",
                str(path),
                "--all-batches",
                "--record-count",
                "3",
                "--state-name",
                "rajasthan-supplement-20261017",
            ]
        )
        == 0
    )
    output = capsys.readouterr().out
    assert sum(line.startswith("corpus-job:") for line in output.splitlines()) == 1
    assert "--state-name=rajasthan-supplement-20261017" in output
    with pytest.raises(SystemExit):
        job.main(["--config", str(path), "--state-name", "../private"])
    with pytest.raises(SystemExit):
        job.main(["--config", str(path), "--record-count", "10001"])


def test_runtime_grants_plan_has_no_connection_and_does_not_grant_ddl(monkeypatch, capsys):
    from opportunity_platform.operations import runtime_grants as grants

    monkeypatch.setattr(
        grants, "create_engine", lambda *a, **k: pytest.fail("Plan opened a database")
    )
    assert grants.main(["--project", "venuesignal", "--runtime-role", "fictional_app"]) == 0
    assert json.loads(capsys.readouterr().out)["ddl_granted"] is False
    with pytest.raises(SystemExit):
        grants.main(["--project", "venuesignal", "--runtime-role", "fictional_app", "--execute"])
    for role in ["app,owner", "app;owner", "x" * 64]:
        with pytest.raises(ValueError):
            grants.validate_role(role)

    class FakeConnection:
        dialect = type(
            "Dialect",
            (),
            {
                "identifier_preparer": type(
                    "Q", (), {"quote": lambda self, value: '"' + value + '"'}
                )()
            },
        )()
        statements = []

        def scalar(self, query, params):
            return True

        def execute(self, query):
            self.statements.append(str(query))

    connection = FakeConnection()
    result = grants.grant(connection, "fictional_app")
    assert result["tables"] == ["policy_embeddings", "inference_reservations"]
    assert all("GRANT SELECT, INSERT, UPDATE ON TABLE" in q for q in connection.statements)
    assert not any("DELETE" in q or "CREATE" in q for q in connection.statements)
    connection.scalar = lambda *a, **k: False
    with pytest.raises(ValueError):
        grants.grant(connection, "fictional_owner")


def test_exact_gcloud_missing_image_allows_build_but_auth_errors_do_not(monkeypatch):
    from types import SimpleNamespace

    deploy = module("deploy")
    args = ["gcloud", "artifacts", "docker", "images", "describe", "fictional:image"]
    message = "ERROR: (gcloud.artifacts.docker.images.describe) Image not found.\n"
    monkeypatch.setattr(
        deploy.subprocess,
        "run",
        lambda *a, **k: SimpleNamespace(
            returncode=1, stderr=message, stdout="NEVER_PRINT_PROVIDER_OUTPUT"
        ),
    )
    assert deploy.invoke("check-existing-image", args, allow_not_found=True) is None
    message += "PERMISSION_DENIED: private diagnostic"
    with pytest.raises(RuntimeError, match="PERMISSION_DENIED"):
        deploy.invoke("check-existing-image", args, allow_not_found=True)
    message = "UNAUTHENTICATED: private diagnostic"
    with pytest.raises(RuntimeError, match="UNAUTHENTICATED"):
        deploy.invoke("check-existing-image", args, allow_not_found=True)


def test_live_routing_tag_limit_keeps_image_fingerprint(monkeypatch):
    deploy = module("deploy")
    original = deploy.image_tag()
    tag = deploy.routing_tag("opportunity-api")
    assert len(tag + "opportunity-api") <= 46
    assert tag == "r-" + original.removeprefix("release-")
    assert deploy.image_tag() == original
    with pytest.raises(ValueError):
        deploy.routing_tag("s" * 40)


def test_job_argument_transport_keeps_repeated_project_and_source_semantics():
    deploy = module("deploy")
    command = [
        "gcloud",
        "run",
        "jobs",
        "deploy",
        "fictional-worker",
        "--args=-m,module,import,--project,venuesignal,--execute,--approved-project,"
        "venuesignal,--source,source-one,--source,source-two",
    ]
    transported = deploy.normalize_job_arguments(command)
    parts = transported[-1].removeprefix("--args=").split(",")
    assert len(parts) == len(set(parts))
    assert "--project=venuesignal" in parts and "--approved-project=venuesignal" in parts
    assert "--source=source-one" in parts and "--source=source-two" in parts
    assert "--execute" in parts and "-m" in parts
    assert deploy.normalize_job_arguments(transported) == transported


def test_hosting_assets_are_fresh_and_stay_inside_project(tmp_path, monkeypatch):
    deploy = module("deploy")
    monkeypatch.setattr(deploy, "ROOT", tmp_path)
    source = tmp_path / "apps/web/dist"
    target = tmp_path / "infra/deploy-dist"
    source.mkdir(parents=True)
    target.mkdir(parents=True)
    (target / "stale.js").write_text("stale")
    (source / "index.html").write_text("<html>fresh</html>")
    (source / "current.js").write_text("fresh")
    deploy.prepare_hosting_assets()
    assert (target / "index.html").read_bytes() == (source / "index.html").read_bytes()
    assert (target / "current.js").read_text() == "fresh"
    assert not (target / "stale.js").exists()
    (source / "private-link").symlink_to(tmp_path)
    with pytest.raises(ValueError):
        deploy.prepare_hosting_assets()
