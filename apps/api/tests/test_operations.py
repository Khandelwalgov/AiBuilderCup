import json

import pytest
from pydantic import ValidationError

from opportunity_platform.core.config import Settings, settings
from opportunity_platform.operations.readiness import configuration_report


def test_preflight_requires_matching_projects_and_never_prints_keys(tmp_path, monkeypatch):
    monkeypatch.setattr(settings(), "firebase_project_id", "synthetic-project")
    monkeypatch.setattr(settings(), "gemini_api_key", "synthetic-server-secret")
    web = tmp_path / ".env.local"
    web.write_text(
        "VITE_FIREBASE_PROJECT_ID=other-project\n"
        "VITE_FIREBASE_API_KEY=synthetic-web-key\n"
        "VITE_FIREBASE_AUTH_DOMAIN=synthetic-project.firebaseapp.com\n"
        "VITE_FIREBASE_APP_ID=synthetic-app-id\n"
    )
    report = configuration_report(web)
    assert report["checks"]["firebase_projects_match"] is False
    assert "synthetic-server-secret" not in json.dumps(report)
    assert "synthetic-web-key" not in json.dumps(report)
    assert report["configuration_ready"] is False


def test_production_fails_closed_for_development_configuration():
    with pytest.raises(ValidationError) as caught:
        Settings(_env_file=None, environment="production", gemini_api_key="synthetic-secret")
    assert "synthetic-secret" not in str(caught.value)
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            environment="production",
            firebase_project_id="synthetic-project",
            database_url="postgresql+psycopg://user:password@remote.test/opportunity",
            cors_origins=["*"],
        )
    valid = Settings(
        _env_file=None,
        environment="production",
        firebase_project_id="synthetic-project",
        database_url="postgresql+psycopg://user:password@/opportunity?host=/cloudsql/test",
        cors_origins=["https://synthetic-project.web.app"],
    )
    assert valid.enable_development_catalogue is False


def test_liveness_is_independent_of_database_health(client):
    assert client.get("/live").json() == {"status": "ok", "database": "not_checked"}


def test_deployment_plan_has_migration_before_traffic_and_pinned_secrets(tmp_path):
    import importlib.util
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    spec = importlib.util.spec_from_file_location("deploy", root / "infra/deploy.py")
    deploy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(deploy)
    raw = (
        (root / "infra/deploy.example.json")
        .read_text()
        .replace("YOUR_PROJECT_ID", "synthetic-project")
    )
    config = deploy.validate(json.loads(raw))
    commands = deploy.plan(config, "PUBLIC_ENV.json")
    assert [label for label, _ in commands] == [
        "build",
        "migration-job",
        "migrate",
        "runtime-permission-job",
        "runtime-permissions",
        "api",
    ]
    api = commands[-1][1]
    assert (
        "DATABASE_URL=opportunity-database-url:1,DOCUMENT_SIGNING_KEY=opportunity-document-signing-key:1"
        in api
    )
    assert api[api.index("--max") + 1] == "1"
    assert deploy.backend_environment(config)["ENABLE_DEVELOPMENT_CATALOGUE"] == "false"
    config_path = tmp_path / "public.json"
    config_path.write_text(json.dumps(config))
    assert deploy.main(["--config", str(config_path)]) == 0
    with pytest.raises(SystemExit):
        deploy.main(["--config", str(config_path), "--execute"])
    config["database_secret_version"] = "latest"
    with pytest.raises(ValueError):
        deploy.validate(config)
    config["database_secret_version"] = "1"
    config["GEMINI_API_KEY"] = "synthetic-private-value"
    with pytest.raises(ValueError):
        deploy.validate(config)
