"""Run repeatable disposable-schema demonstrations. No login/model/cloud bypass.

Default is a plan. --run-isolated executes PostgreSQL tests which create/drop only
randomly named test schemas and never update application data.
"""

import argparse
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-isolated", action="store_true")
    args = parser.parse_args()
    from opportunity_platform.core.config import settings

    if settings().environment == "production" or os.environ.get("ENVIRONMENT") == "production":
        raise SystemExit("Disposable demos are disabled in production.")
    command = [
        str(ROOT / "apps/api/.venv/bin/python"),
        "-m",
        "pytest",
        "-v",
        "tests/test_finale.py",
        "tests/test_workspaces.py::test_current_version_plan_preserves_history_and_replaces_dependencies",
        "tests/test_workspaces.py::test_shared_action_simulation_and_subject_context",
    ]
    print(
        "Isolated public-candidate copies + fictional profile/source-version scenarios; no live AI."
    )
    if args.run_isolated:
        subprocess.run(command, cwd=ROOT / "apps/api", check=True)
    else:
        print("Plan only. Pass --run-isolated to execute the disposable-schema demo.")


if __name__ == "__main__":
    main()
