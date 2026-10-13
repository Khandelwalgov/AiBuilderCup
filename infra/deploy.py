#!/usr/bin/env python3
"""Plan by default. Execute only with an explicitly approved project. No secret values."""

import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIELDS = {
    "project_id",
    "region",
    "service",
    "repository",
    "cloud_sql_connection",
    "runtime_service_account",
    "migration_service_account",
    "database_secret",
    "database_secret_version",
    "gemini_secret",
    "gemini_secret_version",
    "gemini_model",
    "firebase_web",
}


def validate(config):
    if set(config) != FIELDS:
        raise ValueError("Deployment config must contain exactly the documented public fields")
    project = config["project_id"]
    if not re.fullmatch(r"[a-z][a-z0-9-]{4,28}[a-z0-9]", project):
        raise ValueError("Select an explicit valid project ID")
    for field in ["region", "service", "repository"]:
        if not re.fullmatch(r"[a-z][a-z0-9-]{1,61}[a-z0-9]", config[field]):
            raise ValueError("Invalid public deployment identifier")
    if not re.fullmatch(r"[a-z][a-z0-9.-]{1,100}", config["gemini_model"]):
        raise ValueError("Invalid model identifier")
    for field in ["runtime_service_account", "migration_service_account"]:
        if not re.fullmatch(
            r"[a-z][a-z0-9-]+@" + re.escape(project) + r"\.iam\.gserviceaccount\.com", config[field]
        ):
            raise ValueError("Service accounts must belong to the selected project")
    if not re.fullmatch(
        re.escape(project + ":" + config["region"] + ":") + r"[a-z][a-z0-9-]+",
        config["cloud_sql_connection"],
    ):
        raise ValueError("Cloud SQL must use the selected project and region")
    for field in ["database_secret", "gemini_secret"]:
        if not re.fullmatch(r"[a-zA-Z0-9_-]{1,255}", config[field]):
            raise ValueError("Use Secret Manager names, never secret values")
    for field in ["database_secret_version", "gemini_secret_version"]:
        if not re.fullmatch(r"[1-9][0-9]*", str(config[field])):
            raise ValueError("Pin explicit numeric secret versions")
    web = config["firebase_web"]
    if set(web) != {"project_id", "api_key", "auth_domain", "app_id"}:
        raise ValueError("Only the public Firebase web configuration belongs here")
    if web["project_id"] != project or web["auth_domain"] != project + ".firebaseapp.com":
        raise ValueError("Frontend, backend and deployment Firebase projects must match")
    if not web["api_key"] or not web["app_id"]:
        raise ValueError("Fill the Firebase public web configuration")
    return config


def image_tag():
    digest = hashlib.sha256()
    base = ROOT / "apps/api"
    files = [
        base / name
        for name in [
            "Dockerfile",
            "pyproject.toml",
            "uv.lock",
            "alembic.ini",
            ".dockerignore",
            ".gcloudignore",
        ]
    ]
    files += list((base / "src").rglob("*.py")) + list((base / "alembic").rglob("*.py"))
    for path in sorted(files):
        digest.update(str(path.relative_to(base)).encode())
        digest.update(path.read_bytes())
    return "phase25-" + digest.hexdigest()[:16]


def backend_environment(c):
    project = c["project_id"]
    return {
        "ENVIRONMENT": "production",
        "FIREBASE_PROJECT_ID": project,
        "CORS_ORIGINS": json.dumps(
            [f"https://{project}.web.app", f"https://{project}.firebaseapp.com"]
        ),
        "ENABLE_DEVELOPMENT_CATALOGUE": "false",
        "GEMINI_MODEL": c["gemini_model"],
        "GEMINI_TIMEOUT_SECONDS": "120",
        "GEMINI_MAX_INPUT_TOKENS": "200000",
        "GEMINI_MAX_OUTPUT_TOKENS": "16384",
        "INGESTION_MIN_INTERVAL_SECONDS": "60",
    }


def plan(c, env_file):
    project, region, service = c["project_id"], c["region"], c["service"]
    common = ["--project", project, "--region", region, "--quiet"]
    image = f"{region}-docker.pkg.dev/{project}/{c['repository']}/{service}:{image_tag()}"
    db = f"DATABASE_URL={c['database_secret']}:{c['database_secret_version']}"
    gemini = f"GEMINI_API_KEY={c['gemini_secret']}:{c['gemini_secret_version']}"
    commands = [
        (
            "build",
            [
                "gcloud",
                "builds",
                "submit",
                "apps/api",
                "--project",
                project,
                "--tag",
                image,
                "--timeout",
                "1200s",
                "--quiet",
            ],
        ),
        (
            "migration-job",
            [
                "gcloud",
                "run",
                "jobs",
                "deploy",
                service + "-migrate",
                *common,
                "--image",
                image,
                "--service-account",
                c["migration_service_account"],
                "--set-cloudsql-instances",
                c["cloud_sql_connection"],
                "--set-secrets",
                db,
                "--env-vars-file",
                str(env_file),
                "--command",
                "/app/.venv/bin/alembic",
                "--args",
                "upgrade,head",
                "--tasks",
                "1",
                "--parallelism",
                "1",
                "--max-retries",
                "0",
                "--task-timeout",
                "300s",
                "--cpu",
                "1",
                "--memory",
                "512Mi",
            ],
        ),
        ("migrate", ["gcloud", "run", "jobs", "execute", service + "-migrate", *common, "--wait"]),
        (
            "api",
            [
                "gcloud",
                "run",
                "deploy",
                service,
                *common,
                "--image",
                image,
                "--service-account",
                c["runtime_service_account"],
                "--execution-environment",
                "gen2",
                "--add-cloudsql-instances",
                c["cloud_sql_connection"],
                "--set-secrets",
                db + "," + gemini,
                "--env-vars-file",
                str(env_file),
                "--allow-unauthenticated",
                "--port",
                "8080",
                "--cpu",
                "1",
                "--memory",
                "1Gi",
                "--concurrency",
                "4",
                "--min",
                "0",
                "--max",
                "2",
                "--timeout",
                "900s",
                "--startup-probe",
                "httpGet.path=/health,httpGet.port=8080,periodSeconds=10,timeoutSeconds=5,failureThreshold=12",
                "--liveness-probe",
                "httpGet.path=/live,httpGet.port=8080,periodSeconds=30,timeoutSeconds=5,failureThreshold=3",
            ],
        ),
    ]
    return commands


def invoke(label, args, **kwargs):
    print("Running " + label + "...", flush=True)
    result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, **kwargs)
    if result.returncode:
        # Keep possible CLI credential/error content out of application validation logs.
        raise RuntimeError(label + " failed; inspect authorized provider logs locally")
    return result.stdout.strip()


def smoke(url, origins):
    if not url.startswith("https://") or not url.endswith(".run.app"):
        raise RuntimeError("Cloud Run returned an unexpected API origin")
    for path in ["/live", "/health", "/v1/opportunities"]:
        with urllib.request.urlopen(url + path, timeout=30) as response:
            if response.status != 200:
                raise RuntimeError("Hosted readiness failed")
    from urllib.error import HTTPError

    try:
        urllib.request.urlopen(url + "/v1/profile/me", timeout=30)
    except HTTPError as error:
        if error.code != 401:
            raise RuntimeError("Hosted authentication guard failed") from None
    else:
        raise RuntimeError("Hosted profile endpoint allowed unauthenticated access")
    for origin in origins:
        req = urllib.request.Request(
            url + "/v1/profile/me",
            method="OPTIONS",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "PUT",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            if response.headers.get("Access-Control-Allow-Origin") != origin:
                raise RuntimeError("Hosted mutation CORS check failed")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--approved-project")
    args = parser.parse_args(argv)
    config = validate(json.loads(args.config.read_text()))
    if not args.execute:
        for label, command in plan(config, "TEMP_PUBLIC_ENV.json"):
            print(label + ": " + shlex.join(command))
        print("Build web with matching public Firebase values and the actual API URL.")
        print(
            "and run firebase deploy --only hosting --config infra/firebase.json --project "
            + config["project_id"]
        )
        print(
            "Plan only. No cloud commands executed. Cloud SQL, IAM and secrets must already exist."
        )
        return 0
    if args.approved_project != config["project_id"]:
        parser.error("Execution needs --approved-project matching the reviewed project")
    with tempfile.TemporaryDirectory(prefix="opportunity-deploy-") as directory:
        env_file = Path(directory) / "backend-env.json"
        env_file.write_text(json.dumps(backend_environment(config)))
        for label, command in plan(config, env_file):
            invoke(label, command)
        project, region, service = config["project_id"], config["region"], config["service"]
        url = invoke(
            "read-api-origin",
            [
                "gcloud",
                "run",
                "services",
                "describe",
                service,
                "--project",
                project,
                "--region",
                region,
                "--format=value(status.url)",
            ],
        )
        smoke(url, json.loads(backend_environment(config)["CORS_ORIGINS"]))
        web = config["firebase_web"]
        environment = {
            **os.environ,
            "VITE_API_BASE_URL": url,
            "VITE_FIREBASE_PROJECT_ID": project,
            "VITE_FIREBASE_API_KEY": web["api_key"],
            "VITE_FIREBASE_AUTH_DOMAIN": web["auth_domain"],
            "VITE_FIREBASE_APP_ID": web["app_id"],
            "VITE_ENABLE_DEVELOPMENT_CATALOGUE": "false",
        }
        invoke("install-web", ["pnpm", "--dir", "apps/web", "install", "--frozen-lockfile"])
        invoke("build-web", ["pnpm", "--dir", "apps/web", "build"], env=environment)
        invoke(
            "hosting",
            [
                "firebase",
                "deploy",
                "--only",
                "hosting",
                "--config",
                "infra/firebase.json",
                "--project",
                project,
                "--non-interactive",
            ],
        )
        with urllib.request.urlopen(f"https://{project}.web.app/profile", timeout=30) as response:
            if response.status != 200 or "<html" not in response.read().decode().lower():
                raise RuntimeError("Hosting SPA routing failed")
        print(
            json.dumps(
                {
                    "api": url,
                    "web": f"https://{project}.web.app",
                    "acceptance": "Public smoke only; authenticated acceptance remains unverified.",
                }
            )
        )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, RuntimeError, OSError, KeyError):
        raise SystemExit(
            "Deployment stopped. Check prerequisites locally; details withheld."
        ) from None
