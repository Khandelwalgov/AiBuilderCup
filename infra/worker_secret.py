#!/usr/bin/env python3
"""Prepare a direct Neon worker secret from the existing application credential.

Plan-only by default. Secret values stay in memory/stdin, never args, files or logs.
Does not create/change Neon roles, data or passwords. Never overwrites an existing secret.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from corpus_job import validate as validate_corpus
from deploy import invoke, validate


def direct_url(value):
    from opportunity_platform.core.database import validate_neon_url

    url = validate_neon_url(value)
    direct = url.set(host=url.host.replace("-pooler.", ".", 1)).render_as_string(
        hide_password=False
    )
    validate_neon_url(direct, direct=True)
    return direct


def read_secret(project, name, version):
    result = subprocess.run(
        [
            "gcloud",
            "secrets",
            "versions",
            "access",
            version,
            "--secret",
            name,
            "--project",
            project,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError("Authorized database secret read failed; values withheld")
    return result.stdout.strip()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deploy-config", type=Path, required=True)
    parser.add_argument("--corpus-config", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--approved-project")
    args = parser.parse_args(argv)
    deploy = validate(json.loads(args.deploy_config.read_text()))
    corpus = validate_corpus(json.loads(args.corpus_config.read_text()))
    if (
        deploy["project_id"] != corpus["project_id"]
        or corpus["database_secret"] == deploy["migration_database_secret"]
    ):
        parser.error(
            "Worker must use the same project and a distinct application credential secret"
        )
    if (
        corpus["database_secret"] == deploy["database_secret"]
        or corpus["database_secret_version"] != "1"
    ):
        parser.error("Worker requires a separate direct secret at immutable initial version 1")
    project = deploy["project_id"]
    if not args.execute:
        print(
            json.dumps(
                {
                    "mode": "plan",
                    "project": project,
                    "source_secret": deploy["database_secret"],
                    "target_secret": corpus["database_secret"],
                    "version": "1",
                    "role": "same application role; no migration-role credential",
                    "neon_mutations": 0,
                }
            )
        )
        return 0
    if args.approved_project != project:
        parser.error("Explicit matching --approved-project required")
    value = direct_url(
        read_secret(project, deploy["database_secret"], deploy["database_secret_version"])
    )
    exists = invoke(
        "check-existing-worker-secret",
        [
            "gcloud",
            "secrets",
            "describe",
            corpus["database_secret"],
            "--project",
            project,
            "--format=value(name)",
        ],
        allow_not_found=True,
    )
    if exists:
        from opportunity_platform.core.database import validate_neon_url

        stored = read_secret(project, corpus["database_secret"], "1")
        validate_neon_url(stored, direct=True)
        if direct_url(stored) != value:
            raise RuntimeError("Existing worker secret differs; explicit reconciliation required")
        print(json.dumps({"worker_secret": "already_present", "neon_mutations": 0}))
        return 0
    result = subprocess.run(
        [
            "gcloud",
            "secrets",
            "create",
            corpus["database_secret"],
            "--project",
            project,
            "--replication-policy=automatic",
            "--data-file=-",
        ],
        input=value,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(
            "Worker secret creation stopped; secret input and provider output withheld"
        )
    print(json.dumps({"worker_secret": "created", "version": "1", "neon_mutations": 0}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        raise SystemExit("Worker secret operation stopped; no credentials logged.") from None
