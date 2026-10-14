"""Public smoke by default; explicit fresh-account fictional journey is optional.

Run with the API venv. FIREBASE_ID_TOKEN is read from the environment and never printed.
No administrator action, external model call, identity upload or application submission.
"""

import argparse
import os
from urllib.parse import urlsplit

import httpx


def run(base, fictional=False):
    parsed = urlsplit(base)
    if parsed.username or parsed.password or parsed.query or parsed.fragment or not parsed.hostname:
        raise ValueError("Use a plain API origin")
    if parsed.scheme != "https" and not (
        parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost"}
    ):
        raise ValueError("Use HTTPS or local loopback")
    with httpx.Client(base_url=base, timeout=30, follow_redirects=False) as client:
        for path in ["/live", "/health", "/v1/opportunities"]:
            response = client.get(path)
            response.raise_for_status()
            print({"check": path, "status": response.status_code})
        assert client.get("/v1/admin/reviews").status_code == 401
        assert client.get("/v1/workspaces").status_code == 401
        if not fictional:
            return
        token = os.environ.get("FIREBASE_ID_TOKEN")
        if not token:
            raise ValueError(
                "A real Firebase token for a dedicated fictional-test account is required"
            )
        client.headers["Authorization"] = "Bearer " + token
        client.get("/v1/me").raise_for_status()
        existing = client.get("/v1/profile/me")
        if (
            existing.status_code != 404
            or existing.json().get("error", {}).get("code") != "profile_not_found"
        ):
            raise ValueError(
                "Refusing to overwrite an existing profile; "
                "use a fresh dedicated fictional-test account"
            )

        def post(path, body):
            response = client.post(path, json=body)
            response.raise_for_status()
            return response.json()

        response = client.put(
            "/v1/profile/me",
            json={
                "display_name": "Fictional smoke account",
                "facts": [{"key": "age", "value": 20}],
            },
        )
        response.raise_for_status()
        household = post("/v1/households", {"name": "Fictional smoke household", "primary": True})
        dependent = post(
            "/v1/households/" + household["id"] + "/dependents",
            {
                "display_name": "Fictional dependent",
                "facts": [{"key": "age", "value": 12}],
                "guardian_responsibility_confirmed": True,
                "relationship": "legal_guardian",
            },
        )
        business = post(
            "/v1/businesses",
            {
                "name": "Fictional unregistered enterprise",
                "legal_status": "unregistered",
                "facts": [{"key": "business_registered", "value": False}],
            },
        )
        for ref in [
            {"kind": "person"},
            {"kind": "person", "id": dependent["id"]},
            {"kind": "household", "id": household["id"]},
            {"kind": "business", "id": business["id"]},
        ]:
            plan = post("/v1/plan", {"subject": ref})
            print(
                {
                    "check": "authorized_subject_plan",
                    "kind": ref["kind"],
                    "evaluations": len(plan["evaluations"]),
                    "actions": len(plan["actions"]),
                }
            )
            if plan["evaluations"]:
                post(
                    "/v1/assistant/explain",
                    {
                        "evaluation_id": plan["evaluations"][0]["id"],
                        "question": "Which documents are needed?",
                        "language": "hi",
                        "use_ai": False,
                    },
                )
        post(
            "/v1/plan/simulate",
            {"subject": {"kind": "person"}, "facts": [{"key": "age", "value": 12}]},
        )
        print({"fictional_journey": "passed", "live_ai_calls": 0, "publication_actions": 0})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument("--create-fictional-workspaces", action="store_true")
    args = parser.parse_args()
    try:
        run(args.api_url, args.create_fictional_workspaces)
    except Exception:
        raise SystemExit(
            "Smoke failed. Details withheld; inspect locally without printing tokens."
        ) from None
