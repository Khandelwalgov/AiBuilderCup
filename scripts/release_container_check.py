#!/usr/bin/env python3
"""Disposable local Docker validation; never connects to cloud/application databases."""

import json
import subprocess
import time
import uuid


def run(*args, check=True):
    result = subprocess.run(["docker", *args], capture_output=True, text=True)
    if check and result.returncode:
        raise RuntimeError("Local container validation failed; inspect locally")
    return result


def main():
    suffix = uuid.uuid4().hex[:12]
    network = "release-check-" + suffix
    db = network + "-db"
    image = "opportunity-release-local:readiness"
    try:
        run("network", "create", network)
        run(
            "run",
            "-d",
            "--name",
            db,
            "--network",
            network,
            "-e",
            "POSTGRES_USER=release",
            "-e",
            "POSTGRES_PASSWORD=fictional-local-only",
            "-e",
            "POSTGRES_DB=release",
            "postgres:17-alpine",
        )
        for _ in range(60):
            if run("exec", db, "pg_isready", "-U", "release", check=False).returncode == 0:
                break
            time.sleep(0.5)
        else:
            raise RuntimeError("Fresh PostgreSQL container did not start")
        environment = [
            "--network",
            network,
            "-e",
            f"DATABASE_URL=postgresql+psycopg://release:fictional-local-only@{db}/release",
            "-e",
            "ENVIRONMENT=production",
            "-e",
            "FIREBASE_PROJECT_ID=fictional-release-project",
            "-e",
            'CORS_ORIGINS=["https://fictional-release-project.web.app"]',
        ]
        run("run", "--rm", *environment, image, "alembic", "upgrade", "head")
        run("run", "--rm", *environment, image, "alembic", "check")
        run(
            "run",
            "--rm",
            *environment,
            image,
            "python",
            "-m",
            "opportunity_platform.operations.migration_gate",
            "--mode",
            "verify",
        )
        audit = """
import json,os
from pathlib import Path
from sqlalchemy import text
from opportunity_platform.profiles import semantics
from opportunity_platform.main import app
from opportunity_platform.db.session import engine
from opportunity_platform.core.config import settings
assert os.getuid()!=0
assert Path(semantics.__file__).with_name('semantics.json').is_file()
assert len(semantics.SPEC['rules'])>0
assert '/v1/search' in app.openapi()['paths']
assert '/v1/scenarios/evaluate' in app.openapi()['paths']
assert not settings().enable_development_catalogue
assert not settings().document_uploads_enabled
assert not settings().ai_ingestion_live_enabled
assert not settings().ai_assistant_live_enabled
root=Path('/app')
for forbidden in ['.env','.env.local','.private-documents','.corpus','data','tests']:
 assert not (root/forbidden).exists(),forbidden
assert not any(root.glob('**/*credentials*.json'))
with engine.connect() as conn:
 assert conn.scalar(text('SELECT version_num FROM alembic_version'))=='f24a1000abcd'
 index_query="SELECT count(*) FROM pg_indexes WHERE indexname='ix_version_search_vector'"
 assert conn.scalar(text(index_query))==1
 assert conn.scalar(text('SELECT count(*) FROM opportunity_versions'))==0
print(json.dumps({'runtime_json':'present','phase4_routes':'present','migration_head':'f24a1000abcd',
 'fresh_database':'passed','fictional_seed':'absent','non_root':True}))
"""
        result = run("run", "--rm", *environment, image, "python", "-c", audit)
        print(result.stdout.strip())
        print(json.dumps({"local_docker_validation": "passed", "cloud_operations": 0}))
    finally:
        run("rm", "-f", db, check=False)
        run("network", "rm", network, check=False)


if __name__ == "__main__":
    main()
