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
        run(
            "run",
            "--rm",
            *environment,
            image,
            "python",
            "-m",
            "opportunity_platform.operations.runtime_gate",
        )
        audit = """
import json,os,time,resource
from pathlib import Path
from sqlalchemy import text
from opportunity_platform.profiles import semantics
from opportunity_platform.operations.runtime_grants import grant
from opportunity_platform.main import app
from opportunity_platform.db.session import engine
from opportunity_platform.core.config import settings
with engine.begin() as connection:
    connection.execute(text("CREATE ROLE release_probe_app "
                            "NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT"))
    connection.execute(text("GRANT USAGE ON SCHEMA public TO release_probe_app"))
    granted=grant(connection,"release_probe_app")
    assert not granted['ddl_granted']
    for table in ['policy_embeddings','inference_reservations']:
        for privilege in ['SELECT','INSERT','UPDATE']:
            assert connection.scalar(
                text("SELECT has_table_privilege('release_probe_app',:t,:p)"),
                {'t':table,'p':privilege})
    ddl_query="SELECT has_schema_privilege('release_probe_app','public','CREATE')"
    assert not connection.scalar(text(ddl_query))
assert os.getuid()!=0
assert Path(semantics.__file__).with_name('semantics.json').is_file()
assert len(semantics.SPEC['rules'])>0
assert '/v1/search' in app.openapi()['paths']
assert '/v1/scenarios/evaluate' in app.openapi()['paths']
assert not settings().enable_development_catalogue
assert not settings().document_uploads_enabled
assert not settings().ai_ingestion_live_enabled
assert not settings().ai_assistant_live_enabled
assert not settings().paid_ai_worker_enabled
assert settings().ai_global_budget_usd==0
assert '/v1/government-sources' in app.openapi()['paths']
assert '/v1/research-opportunities' in app.openapi()['paths']
assert '/v1/research-opportunities/guidance' in app.openapi()['paths']
from opportunity_platform.research.conditions import definitions
assert len(definitions()) == 36
from opportunity_platform.retrieval.neural import encoder_for
start=time.perf_counter()
encoder=encoder_for(settings().neural_model_directory)
vector=encoder.encode('पढ़ाई के लिए आर्थिक सहायता')
assert vector.shape==(384,)
model_ms=round((time.perf_counter()-start)*1000)
memory_mib=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024)
root=Path('/app')
for forbidden in ['.env','.env.local','.private-documents','.corpus','data','tests']:
 assert not (root/forbidden).exists(),forbidden
assert not any(root.glob('**/*credentials*.json'))
with engine.connect() as conn:
 assert conn.scalar(text('SELECT version_num FROM alembic_version'))=='f26c1000abcd'
 index_query="SELECT count(*) FROM pg_indexes WHERE indexname='ix_version_search_vector'"
 assert conn.scalar(text(index_query))==1
 assert conn.scalar(text('SELECT count(*) FROM opportunity_versions'))==0
print(json.dumps({'runtime_json':'present','phase4_routes':'present','migration_head':'f26c1000abcd',
 'fresh_database':'passed','fictional_seed':'absent','non_root':True,
 'runtime_new_table_grants':'passed','local_model_dimensions':len(vector),'load_and_encode_ms':model_ms,'peak_memory_mib':memory_mib}))
"""
        result = run("run", "--rm", *environment, image, "python", "-c", audit)
        print(result.stdout.strip())
        print(json.dumps({"local_docker_validation": "passed", "cloud_operations": 0}))
    finally:
        run("rm", "-f", db, check=False)
        run("network", "rm", network, check=False)


if __name__ == "__main__":
    main()
