#!/usr/bin/env python3
"""Plan/deploy one bounded corpus job. No inference, publication or provisioning."""

import argparse
import json
import re
import shlex
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from deploy import image_tag, invoke


def validate(config):
    expected = {
        "project_id",
        "region",
        "service",
        "repository",
        "bucket",
        "job",
        "service_account",
        "database_secret",
        "database_secret_version",
        "sources",
    }
    if set(config) != expected:
        raise ValueError("Only documented public corpus configuration identifiers are accepted")
    for key in expected - {"service_account", "sources"}:
        if not isinstance(config[key], str) or not re.fullmatch(
            r"[a-zA-Z0-9][a-zA-Z0-9.-]{0,100}", config[key]
        ):
            raise ValueError("Invalid public corpus resource identifier")
    if not re.fullmatch(
        r"[a-z0-9-]+@" + re.escape(config["project_id"]) + r"\.iam\.gserviceaccount\.com",
        config["service_account"],
    ):
        raise ValueError("Corpus worker identity must belong to the selected project")
    if not config["database_secret_version"].isdigit():
        raise ValueError("Pin an immutable database secret version")
    if (
        not isinstance(config["sources"], list)
        or not 1 <= len(config["sources"]) <= 4
        or any(not re.fullmatch("[a-z0-9-]+", key) for key in config["sources"])
    ):
        raise ValueError("Select at most four reviewed registry source keys")
    return config


def environment(config):
    return {
        "ENVIRONMENT": "production",
        "DATABASE_PROVIDER": "neon",
        "FIREBASE_PROJECT_ID": config["project_id"],
        "CORS_ORIGINS": '["https://unclaimed-ai-cup.web.app"]',
        "PROCESS_ROLE": "ingestion_worker",
        "PAID_AI_WORKER_ENABLED": "false",
        "AI_GLOBAL_BUDGET_USD": "0",
        "AI_RUN_BUDGET_USD": "0",
        "AI_INGESTION_LIVE_ENABLED": "false",
        "AI_ASSISTANT_LIVE_ENABLED": "false",
        "ENABLE_DEVELOPMENT_CATALOGUE": "false",
        "DOCUMENT_UPLOADS_ENABLED": "false",
    }


def plan(config, operation, env_file, actor_uid=None, execute_import=False, offset=0):
    project, region = config["project_id"], config["region"]
    image = (
        f"{region}-docker.pkg.dev/{project}/{config['repository']}/"
        f"{config['service']}:{image_tag()}"
    )
    arguments = [
        "-m",
        "opportunity_platform.corpus.production",
        operation,
        "--project",
        project,
        "--bucket",
        config["bucket"],
        "--offset",
        str(offset),
    ]
    if execute_import or operation == "collect":
        arguments += ["--execute", "--approved-project", project]
        if actor_uid:
            if not re.fullmatch(r"[a-zA-Z0-9:_-]{1,128}", actor_uid):
                raise ValueError("Use an exact Firebase UID, not an email or token")
            arguments += ["--actor-uid", actor_uid]
    if operation == "collect":
        for source in config["sources"]:
            arguments += ["--source", source]
    if operation == "bootstrap-admin":
        if not actor_uid or not execute_import:
            raise ValueError("First administrator requires explicit UID and security authorization")
        arguments = [
            "-m",
            "opportunity_platform.operations.bootstrap_admin",
            "--target-uid",
            actor_uid,
            "--execute",
            "--confirm-first-admin",
            "--approved-project",
            project,
        ]
    if operation == "index":
        arguments = ["-m", "opportunity_platform.retrieval.index"]
        if execute_import:
            arguments.append("--execute")
    common = ["--project", project, "--region", region, "--quiet"]
    return [
        (
            "corpus-job",
            [
                "gcloud",
                "run",
                "jobs",
                "deploy",
                config["job"],
                *common,
                "--image",
                image,
                "--service-account",
                config["service_account"],
                "--tasks",
                "1",
                "--parallelism",
                "1",
                "--max-retries",
                "0",
                "--task-timeout",
                "900s",
                "--cpu",
                "1",
                "--memory",
                "1Gi",
                "--env-vars-file",
                str(env_file),
                "--set-secrets",
                f"DATABASE_URL={config['database_secret']}:{config['database_secret_version']}",
                "--command",
                "/app/.venv/bin/python",
                "--args=" + ",".join(arguments),
            ],
        ),
        ("run-corpus-job", ["gcloud", "run", "jobs", "execute", config["job"], *common, "--wait"]),
    ]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument(
        "--operation", choices=["import", "collect", "bootstrap-admin", "index"], default="import"
    )
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--approved-project")
    parser.add_argument("--authorize-data-import", action="store_true")
    parser.add_argument("--authorize-admin-bootstrap", action="store_true")
    parser.add_argument("--authorize-embedding-index", action="store_true")
    parser.add_argument("--actor-uid")
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument(
        "--all-batches",
        action="store_true",
        help="Seven sequential 20-record jobs for the initial 125-record manifest",
    )
    args = parser.parse_args(argv)
    config = validate(json.loads(args.config.read_text()))
    if args.offset < 0 or args.offset > 10000:
        parser.error("Invalid bounded batch offset")
    if args.authorize_data_import and not args.actor_uid:
        parser.error("Import requires the explicitly approved existing administrator UID")
    if args.operation == "bootstrap-admin" and not (
        args.authorize_admin_bootstrap and args.actor_uid
    ):
        parser.error(
            "First administrator requires --authorize-admin-bootstrap and the selected UID"
        )
    authorized_write = (
        args.authorize_data_import
        or args.authorize_admin_bootstrap
        or args.authorize_embedding_index
    )
    if args.all_batches and args.operation != "import":
        parser.error("All-batches is restricted to the initial archive import or dry run")
    offsets = list(range(0, 125, 20)) if args.all_batches else [args.offset]
    if args.authorize_admin_bootstrap and args.operation != "bootstrap-admin":
        parser.error("Administrator authorization is only valid for bootstrap-admin")
    if args.authorize_data_import and args.operation != "import":
        parser.error("Data import authorization is only valid for import")
    if args.authorize_embedding_index and args.operation != "index":
        parser.error("Embedding authorization is only valid for index")
    if args.operation == "collect" and not args.actor_uid:
        parser.error(
            "Collection requires the selected administrator UID for changed-source queueing"
        )
    if not args.execute:
        for offset in offsets:
            for label, command in plan(
                config,
                args.operation,
                "TEMP_PUBLIC_WORKER_ENV.json",
                args.actor_uid,
                authorized_write,
                offset,
            ):
                safe_command = (
                    [part.replace(args.actor_uid, "<REVIEWED_ADMIN_UID>") for part in command]
                    if args.actor_uid
                    else command
                )
                print(label + ": " + shlex.join(safe_command))
        print("Plan only; bucket/IAM must exist. Paid AI budget is zero. No publication.")
        return 0
    if args.approved_project != config["project_id"]:
        parser.error("Explicit matching --approved-project required")
    with tempfile.TemporaryDirectory(prefix="public-corpus-job-config-") as directory:
        env_file = Path(directory) / "worker-env.json"
        env_file.write_text(json.dumps(environment(config)))
        for offset in offsets:
            for label, command in plan(
                config, args.operation, env_file, args.actor_uid, authorized_write, offset
            ):
                invoke(label, command)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
