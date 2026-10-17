#!/usr/bin/env python3
"""Manual Firebase Hosting release only. Never builds Docker or changes Cloud Run/Neon."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from deploy import (
    ROOT,
    hosting_command,
    hosting_origin,
    invoke,
    prepare_hosting_assets,
    smoke,
    validate,
    validate_hosting,
    web_environment,
)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--approved-project")
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args(argv)
    config = validate(json.loads(args.config.read_text()))
    validate_hosting(config)
    if not args.execute:
        print(
            json.dumps(
                {
                    "mode": "plan",
                    "hosting_site": config["hosting_site"],
                    "frontend": hosting_origin(config),
                    "backend": "existing service, read only",
                    "docker_builds": 0,
                    "database_mutations": 0,
                }
            )
        )
        return 0
    if args.approved_project != config["project_id"]:
        parser.error("Explicit matching --approved-project required")
    if any(config["firebase_web"][key].startswith("YOUR_") for key in ["api_key", "app_id"]):
        parser.error("Complete the reviewed public Firebase web identifiers")
    if any(
        (ROOT / "apps/web" / name).exists()
        for name in [".env", ".env.local", ".env.production", ".env.production.local"]
    ):
        parser.error("Use a clean checkout; existing local environments must not be overwritten")
    service = json.loads(
        invoke(
            "read-existing-api",
            [
                "gcloud",
                "run",
                "services",
                "describe",
                config["service"],
                "--project",
                config["project_id"],
                "--region",
                config["region"],
                "--format=json",
            ],
        )
    )
    url = service["status"]["url"]
    smoke(url, [hosting_origin(config)])
    invoke("install-web", ["pnpm", "--dir", "apps/web", "install", "--frozen-lockfile"])
    invoke(
        "build-web",
        ["pnpm", "--dir", "apps/web", "build"],
        env=web_environment(config, url),
    )
    prepare_hosting_assets()
    invoke("hosting", hosting_command(config))
    receipt = {
        "frontend_only": True,
        "web": hosting_origin(config),
        "api": url,
        "docker_builds": 0,
        "database_mutations": 0,
        "backend_mutations": 0,
    }
    if args.receipt:
        args.receipt.write_text(json.dumps(receipt, indent=2))
    print(json.dumps(receipt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
