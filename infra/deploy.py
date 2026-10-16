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
    "database_provider",
    "migration_mode",
    "hosting_site",
    "hosting_target",
    "runtime_service_account",
    "migration_service_account",
    "database_secret",
    "database_secret_version",
    "migration_database_secret",
    "migration_database_secret_version",
    "document_signing_secret",
    "document_signing_secret_version",
    "build_service_account",
    "build_source_bucket",
    "gemini_model",
    "firebase_web",
}


def validate(config):
    if set(config) != FIELDS:
        raise ValueError("Deployment config must contain exactly the documented public fields")
    project = config["project_id"]
    if not re.fullmatch(r"[a-z][a-z0-9-]{4,28}[a-z0-9]", project):
        raise ValueError("Select an explicit valid project ID")
    if not re.fullmatch(re.escape(project) + r"-[a-z0-9-]{1,30}", config["build_source_bucket"]):
        raise ValueError("Use an existing project-prefixed release source bucket")
    for field in ["region", "service", "repository"]:
        if not re.fullmatch(r"[a-z][a-z0-9-]{1,61}[a-z0-9]", config[field]):
            raise ValueError("Invalid public deployment identifier")
    if not re.fullmatch(r"[a-z][a-z0-9.-]{1,100}", config["gemini_model"]):
        raise ValueError("Invalid model identifier")
    for field in ["runtime_service_account", "migration_service_account", "build_service_account"]:
        if not re.fullmatch(
            r"[a-z][a-z0-9-]+@" + re.escape(project) + r"\.iam\.gserviceaccount\.com", config[field]
        ):
            raise ValueError("Service accounts must belong to the selected project")
    if config["database_provider"] != "neon":
        raise ValueError("This release path supports external Neon, without Cloud SQL")
    if config["migration_mode"] not in {"verify", "upgrade"}:
        raise ValueError("Choose read-only schema verification or explicitly approved upgrade")
    for field in ["hosting_site", "hosting_target"]:
        if not re.fullmatch(r"[a-z][a-z0-9-]{1,61}[a-z0-9]", config[field]):
            raise ValueError("Invalid Hosting identifier")
    for field in ["database_secret", "migration_database_secret", "document_signing_secret"]:
        if not re.fullmatch(r"[a-zA-Z0-9_-]{1,255}", config[field]):
            raise ValueError("Use Secret Manager names, never secret values")
    for field in [
        "database_secret_version",
        "migration_database_secret_version",
        "document_signing_secret_version",
    ]:
        if not re.fullmatch(r"[1-9][0-9]*", str(config[field])):
            raise ValueError("Pin explicit numeric secret versions")
    web = config["firebase_web"]
    if set(web) != {"project_id", "api_key", "auth_domain", "app_id"}:
        raise ValueError("Only the public Firebase web configuration belongs here")
    if web["project_id"] != project or web["auth_domain"] != project + ".firebaseapp.com":
        raise ValueError("Frontend, backend and deployment Firebase projects must match")
    if not web["api_key"] or not web["app_id"]:
        raise ValueError("Fill the Firebase public web configuration")
    if (
        len(
            {
                config[k]
                for k in [
                    "runtime_service_account",
                    "migration_service_account",
                    "build_service_account",
                ]
            }
        )
        != 3
    ):
        raise ValueError("Use separate runtime, migration and build identities")
    if config["database_secret"] == config["migration_database_secret"]:
        raise ValueError("Use separate DML and migration database credentials")
    return config


def validate_hosting(config):
    """Read local public mapping; fail closed before any cloud command."""
    hosting = json.loads((ROOT / "infra/firebase.json").read_text())["hosting"]
    rc = json.loads((ROOT / "infra/.firebaserc").read_text())
    expected = (
        rc.get("targets", {})
        .get(config["project_id"], {})
        .get("hosting", {})
        .get(config["hosting_target"])
    )
    if (
        not isinstance(hosting, dict)
        or hosting.get("target") != config["hosting_target"]
        or hosting.get("site") is not None
        or expected != [config["hosting_site"]]
    ):
        raise ValueError("Hosting configuration must target exactly the selected Unclaimed site")


def hosting_origin(config):
    return "https://" + config["hosting_site"] + ".web.app"


def hosting_command(config):
    # Firebase resolves .firebaserc from the directory containing the explicit config.
    return [
        "firebase",
        "deploy",
        "--only",
        "hosting:" + config["hosting_target"],
        "--config",
        "infra/firebase.json",
        "--project",
        config["project_id"],
        "--non-interactive",
    ]


def image_inputs(base=None):
    """One explicit runtime/build manifest, shared with packaging validation.

    All regular files under runtime source and migrations participate, regardless
    of suffix. Generated bytecode/caches are excluded, and symlinks fail closed.
    """
    base = base or ROOT / "apps/api"
    names = [
        "Dockerfile",
        "pyproject.toml",
        "uv.lock",
        "alembic.ini",
        ".dockerignore",
        ".gcloudignore",
        "cloudbuild.yaml",
    ]
    files = [base / name for name in names]
    for directory in ["src", "alembic"]:
        files += [
            p
            for p in (base / directory).rglob("*")
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"
        ]
    for path in files:
        if path.is_symlink() or not path.is_file():
            raise ValueError("Build inputs must be regular files")
        relative = path.relative_to(base)
        if any(part.startswith(".") for part in relative.parts) and relative.name not in {
            ".dockerignore",
            ".gcloudignore",
        }:
            raise ValueError("Hidden runtime input is not allowed")
        if path.suffix in {".pem", ".key"} or "credentials" in path.name.lower():
            raise ValueError("Credential-like build input is not allowed")
    return sorted(files)


def image_tag(base=None):
    base = base or ROOT / "apps/api"
    digest = hashlib.sha256()
    for path in image_inputs(base):
        name = path.relative_to(base).as_posix().encode()
        content = path.read_bytes()
        digest.update(len(name).to_bytes(8, "big") + name)
        digest.update(len(content).to_bytes(8, "big") + content)
    return "release-" + digest.hexdigest()[:24]


def backend_environment(c):
    project = c["project_id"]
    return {
        "ENVIRONMENT": "production",
        "DATABASE_PROVIDER": c["database_provider"],
        "FIREBASE_PROJECT_ID": project,
        "CORS_ORIGINS": json.dumps(
            [hosting_origin(c), f"https://{c['hosting_site']}.firebaseapp.com"]
        ),
        "ENABLE_DEVELOPMENT_CATALOGUE": "false",
        "AI_EXTRACTION_PROVIDER": "gemini",
        "AI_INGESTION_LIVE_ENABLED": "false",
        "AI_ASSISTANT_LIVE_ENABLED": "false",
        "DOCUMENT_UPLOADS_ENABLED": "false",
        "RETRIEVAL_SHORTLIST_SIZE": "150",
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
    migration_db = (
        f"DATABASE_URL={c['migration_database_secret']}:{c['migration_database_secret_version']}"
    )
    signing = (
        f"DOCUMENT_SIGNING_KEY={c['document_signing_secret']}:"
        f"{c['document_signing_secret_version']}"
    )
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
                "--config",
                "apps/api/cloudbuild.yaml",
                "--substitutions",
                "_IMAGE=" + image,
                "--service-account",
                f"projects/{project}/serviceAccounts/{c['build_service_account']}",
                "--gcs-source-staging-dir",
                f"gs://{c['build_source_bucket']}/api",
                "--region",
                region,
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
                "--set-secrets",
                migration_db,
                "--env-vars-file",
                str(env_file),
                "--command",
                "/app/.venv/bin/python",
                "--args",
                "-m,opportunity_platform.operations.migration_gate,--mode,"
                + c["migration_mode"]
                + (",--approve-upgrade" if c["migration_mode"] == "upgrade" else ""),
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
                "--set-secrets",
                db + "," + signing,
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
                "1",
                "--cpu-throttling",
                "--timeout",
                "60s",
                "--no-traffic",
                "--tag",
                image_tag(),
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
    from smoke import public_smoke

    public_smoke(url, origins)


def web_environment(config, url):
    # Only allow public build inputs; never inherit VITE_* values from .env.local
    # or a shell (an emulator URL or developer catalogue flag could otherwise leak).
    web = config["firebase_web"]
    environment = {k: v for k, v in os.environ.items() if not k.startswith("VITE_")}
    environment.update(
        {
            "VITE_API_BASE_URL": url,
            "VITE_FIREBASE_PROJECT_ID": config["project_id"],
            "VITE_FIREBASE_API_KEY": web["api_key"],
            "VITE_FIREBASE_AUTH_DOMAIN": web["auth_domain"],
            "VITE_FIREBASE_APP_ID": web["app_id"],
            "VITE_ENABLE_DEVELOPMENT_CATALOGUE": "false",
            "VITE_FIREBASE_AUTH_EMULATOR_URL": "",
        }
    )
    return environment


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--approved-project")
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--approve-migrations", action="store_true")
    args = parser.parse_args(argv)
    config = validate(json.loads(args.config.read_text()))
    validate_hosting(config)
    if not args.execute:
        for label, command in plan(config, "TEMP_PUBLIC_ENV.json"):
            print(label + ": " + shlex.join(command))
        print("Then smoke the tagged candidate; build web; promote API traffic; deploy Hosting.")
        print("Authenticated hosted acceptance is a separate gate, not inferred from public smoke.")
        print("web-install: pnpm --dir apps/web install --frozen-lockfile")
        print("web-build: pnpm --dir apps/web build (explicit public production Firebase/API env)")
        print(
            "promote-api: "
            + shlex.join(
                [
                    "gcloud",
                    "run",
                    "services",
                    "update-traffic",
                    config["service"],
                    "--project",
                    config["project_id"],
                    "--region",
                    config["region"],
                    "--to-revisions",
                    "CANDIDATE_READY_REVISION=100",
                    "--quiet",
                ]
            )
        )
        print("hosting: " + shlex.join(hosting_command(config)))
        print("frontend: " + hosting_origin(config))
        print(
            "Schema mode: "
            + config["migration_mode"]
            + "; existing Neon head is verified read-only by default."
        )
        print("Plan only. No cloud commands executed. Neon secrets, IAM and billing must be ready.")
        return 0
    if args.approved_project != config["project_id"]:
        parser.error("Execution needs --approved-project matching the reviewed project")
    if config["migration_mode"] == "upgrade" and not args.approve_migrations:
        parser.error("Schema upgrade requires separate --approve-migrations authorization")
    if any(config["firebase_web"][key].startswith("YOUR_") for key in ["api_key", "app_id"]):
        parser.error("Fill the public Firebase web configuration before execution")
    if any(
        (ROOT / "apps/web" / name).exists()
        for name in [".env", ".env.local", ".env.production", ".env.production.local"]
    ):
        parser.error(
            "Execute from a clean checkout without frontend .env files; do not overwrite them"
        )
    project, region, service = config["project_id"], config["region"], config["service"]
    invoke(
        "check-existing-source-bucket",
        [
            "gcloud",
            "storage",
            "buckets",
            "describe",
            "gs://" + config["build_source_bucket"],
            "--project",
            project,
            "--format=value(name)",
        ],
    )
    previous = json.loads(
        invoke(
            "record-existing-traffic",
            [
                "gcloud",
                "run",
                "services",
                "list",
                "--project",
                project,
                "--region",
                region,
                "--filter",
                f"metadata.name={service}",
                "--format=json",
            ],
        )
    )
    if any(
        item.get("metadata", {}).get("annotations", {}).get("run.googleapis.com/cloudsql-instances")
        for item in previous
    ):
        raise ValueError("Existing service has unexpected Cloud SQL attachments; resolve manually")
    if args.receipt:
        args.receipt.write_text(
            json.dumps(
                {
                    "project": project,
                    "service": service,
                    "region": region,
                    "previous_traffic": [
                        {
                            "revision": t.get("revisionName"),
                            "percent": t.get("percent", 0),
                            "tag": t.get("tag"),
                        }
                        for item in previous
                        for t in item.get("status", {}).get("traffic", [])
                    ],
                    "image_tag": image_tag(),
                    "database_provider": config["database_provider"],
                    "migration_mode": config["migration_mode"],
                    "hosting_site": config["hosting_site"],
                    "hosting_target": config["hosting_target"],
                    "web": hosting_origin(config),
                },
                indent=2,
            )
        )
    with tempfile.TemporaryDirectory(prefix="opportunity-deploy-") as directory:
        env_file = Path(directory) / "backend-env.json"
        env_file.write_text(json.dumps(backend_environment(config)))
        for label, command in plan(config, env_file):
            invoke(label, command)
        project, region, service = config["project_id"], config["region"], config["service"]
        status = json.loads(
            invoke(
                "read-candidate",
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
                    "--format=json",
                ],
            )
        )["status"]
        url = status["url"]
        candidate = next(t["url"] for t in status["traffic"] if t.get("tag") == image_tag())
        smoke(candidate, json.loads(backend_environment(config)["CORS_ORIGINS"]))
        if args.receipt:
            receipt = json.loads(args.receipt.read_text())
            receipt.update(
                candidate_revision=status["latestReadyRevisionName"],
                candidate_url=candidate,
                api_url=url,
            )
            args.receipt.write_text(json.dumps(receipt, indent=2))
        environment = web_environment(config, url)
        invoke("install-web", ["pnpm", "--dir", "apps/web", "install", "--frozen-lockfile"])
        invoke("build-web", ["pnpm", "--dir", "apps/web", "build"], env=environment)
        invoke(
            "promote-api",
            [
                "gcloud",
                "run",
                "services",
                "update-traffic",
                service,
                "--project",
                project,
                "--region",
                region,
                "--to-revisions",
                status["latestReadyRevisionName"] + "=100",
                "--quiet",
            ],
        )
        smoke(url, json.loads(backend_environment(config)["CORS_ORIGINS"]))
        invoke("hosting", hosting_command(config))
        with urllib.request.urlopen(hosting_origin(config) + "/profile", timeout=30) as response:
            if response.status != 200 or "<html" not in response.read().decode().lower():
                raise RuntimeError("Hosting SPA routing failed")
        print(
            json.dumps(
                {
                    "api": url,
                    "web": hosting_origin(config),
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
