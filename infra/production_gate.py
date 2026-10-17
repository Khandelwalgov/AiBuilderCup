#!/usr/bin/env python3
"""Fail closed unless native production reviewer/branch protection actually exists."""

import json
import os
import urllib.parse
import urllib.request


def validate(environment, policies, default_branch, ref):
    reviewers = [
        rule
        for rule in environment.get("protection_rules", [])
        if rule.get("type") == "required_reviewers"
    ]
    if not reviewers or not all(
        rule.get("reviewers") and rule.get("prevent_self_review") is True for rule in reviewers
    ):
        raise ValueError("A real required-reviewer rule with prevent-self-review is required")
    if environment.get("can_admins_bypass") is True:
        raise ValueError("Administrator bypass must be disabled")
    if ref != "refs/heads/" + default_branch:
        raise ValueError("Only the repository default branch can release")
    branch_policy = environment.get("deployment_branch_policy") or {}
    if not branch_policy.get("custom_branch_policies") or branch_policy.get("protected_branches"):
        raise ValueError(
            "Configure selected deployment branches restricted to the exact default branch"
        )
    rows = policies.get("branch_policies", [])
    if not rows or any(
        row.get("name") != default_branch or row.get("type", "branch") != "branch" for row in rows
    ):
        raise ValueError("Deployment branch policy must contain only the exact default branch")


def main():
    repository = os.environ["GITHUB_REPOSITORY"]
    if repository != "Khandelwalgov/AiBuilderCup":
        raise ValueError("Unexpected repository approval context")
    token = os.environ["GITHUB_TOKEN"]

    def get(path):
        request = urllib.request.Request(
            "https://api.github.com/repos/" + repository + path,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": "Bearer " + token,
                "User-Agent": "Unclaimed-production-approval-gate",
            },
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.load(response)

    repo = get("")
    environment = get("/environments/production")
    policies = get("/environments/production/deployment-branch-policies")
    validate(environment, policies, repo["default_branch"], os.environ["GITHUB_REF"])
    print(
        json.dumps(
            {
                "production_approval_configuration": "verified",
                "cloud_authentication_performed": False,
            }
        )
    )


if __name__ == "__main__":
    try:
        main()
    except Exception:
        raise SystemExit(
            "Production approval gate failed: native reviewer/branch protection is "
            "missing or inaccessible. No cloud authentication attempted."
        ) from None
