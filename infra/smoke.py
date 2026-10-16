#!/usr/bin/env python3
"""Hosted release checks. No seed, publication, model calls or profile writes."""

import argparse
import json
import stat
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def origin(url, allow_local=False):
    parsed = urlsplit(url)
    local = (
        allow_local and parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1"}
    )
    hosted = (
        parsed.scheme == "https"
        and parsed.hostname
        and parsed.hostname.endswith(".run.app")
        and parsed.port in {None, 443}
    )
    if (
        not (local or hosted)
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        raise ValueError("Use an explicit Cloud Run HTTPS origin (or opt in to loopback testing)")
    return url.rstrip("/")


def request(url, path, expected=200, body=None, token=None, method=None, headers=None):
    headers = dict(headers or {})
    if token:
        headers["Authorization"] = "Bearer " + token
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        url + path,
        data=json.dumps(body).encode() if body is not None else None,
        method=method,
        headers=headers,
    )
    try:
        response = urllib.request.build_opener(NoRedirect()).open(req, timeout=60)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        if response.status != expected:
            raise RuntimeError(f"Smoke failed: {path} expected {expected}, got {response.status}")
        raw = response.read()
        content = (
            json.loads(raw)
            if raw and response.headers.get("Content-Type", "").startswith("application/json")
            else None
        )
        return content, response.headers


def public_smoke(url, origins, allow_local=False):
    url = origin(url, allow_local)
    request(url, "/live")
    request(url, "/health")
    catalogue, _ = request(url, "/v1/opportunities")
    if not isinstance(catalogue, dict) or not isinstance(catalogue.get("items"), list):
        raise RuntimeError("Catalogue response shape failed")
    if any(i["is_synthetic"] or i["publication_state"] != "published" for i in catalogue["items"]):
        raise RuntimeError("Production exposed fictional/unreviewed records")
    request(url, "/v1/opportunities?development=true", expected=404)
    for path in ["/v1/me", "/v1/profile/me", "/v1/workspaces", "/v1/admin/reviews"]:
        request(url, path, expected=401)
    for path, body in [
        ("/v1/search", {"mode": "me"}),
        ("/v1/scenarios/evaluate", {"base": {"mode": "me"}}),
    ]:
        request(url, path, expected=401, body=body)
        request(url, path, expected=401, body=body, token="invalid-token")
    for allowed in origins:
        _, headers = request(
            url,
            "/v1/search",
            method="OPTIONS",
            headers={
                "Origin": allowed,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )
        if headers.get("Access-Control-Allow-Origin") != allowed:
            raise RuntimeError("Allowed CORS failed")
    _, headers = request(
        url,
        "/v1/search",
        method="OPTIONS",
        expected=400,
        headers={"Origin": "https://untrusted.invalid", "Access-Control-Request-Method": "POST"},
    )
    if headers.get("Access-Control-Allow-Origin"):
        raise RuntimeError("Untrusted CORS accepted")
    return {"public_smoke": "passed", "authenticated_acceptance": "not run"}


def authenticated_smoke(url, token, expected_uid, second_token):
    me, _ = request(url, "/v1/me", token=token)
    if me.get("uid") != expected_uid or me.get("is_admin") is not False:
        raise RuntimeError("Use the intended non-admin acceptance account")
    profile, _ = request(url, "/v1/profile/me", token=token)
    workspaces, _ = request(url, "/v1/workspaces", token=token)
    request(url, "/v1/admin/reviews", expected=403, token=token)
    search, headers = request(url, "/v1/search", body={"mode": "me"}, token=token)
    if headers.get("Cache-Control") != "private, no-store":
        raise RuntimeError("Private cache guard failed")
    result, _ = request(url, "/v1/scenarios/evaluate", body={"base": {"mode": "me"}}, token=token)
    if result.get("persistence") != "none" or any(
        c["change"] != "unchanged" for c in result["changes"]
    ):
        raise RuntimeError("Unmodified scenario must remain unchanged and ephemeral")
    if (
        request(url, "/v1/profile/me", token=token)[0] != profile
        or request(url, "/v1/workspaces", token=token)[0] != workspaces
    ):
        raise RuntimeError("Scenario changed actual profile/workspaces")
    other, _ = request(url, "/v1/me", token=second_token)
    if other["uid"] == me["uid"]:
        raise RuntimeError("Two distinct accounts are required")
    person_id = next(s["id"] for s in search["subjects"] if s["kind"] == "person")
    foreign = {"mode": "member", "subject_id": person_id}
    request(url, "/v1/search", body=foreign, token=second_token, expected=404)
    request(url, "/v1/scenarios/evaluate", body={"base": foreign}, token=second_token, expected=404)
    return {
        "authenticated_api_smoke": "passed",
        "browser_google_signin": "requires manual acceptance",
        "scenario_api_snapshots": "unchanged",
        "cross_account": "denied",
    }


def read_token(path):
    if path.is_symlink() or not path.is_file() or stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise ValueError("Token files must be regular private files (chmod 600)")
    token = path.read_text().strip()
    if not token or "\n" in token:
        raise ValueError("Invalid token file")
    return token


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", required=True)
    parser.add_argument("--hosting-origin", action="append", required=True)
    parser.add_argument("--allow-local", action="store_true")
    parser.add_argument("--token-file", type=Path)
    parser.add_argument("--second-token-file", type=Path)
    parser.add_argument("--expected-uid")
    args = parser.parse_args()
    if any([args.token_file, args.second_token_file, args.expected_uid]) and not all(
        [args.token_file, args.second_token_file, args.expected_uid]
    ):
        parser.error("Authenticated checks need two private token files and the intended UID")
    result = public_smoke(args.api_url, args.hosting_origin, args.allow_local)
    if args.token_file:
        result.update(
            authenticated_smoke(
                args.api_url,
                read_token(args.token_file),
                args.expected_uid,
                read_token(args.second_token_file),
            )
        )
    print(json.dumps(result))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, KeyError, StopIteration):
        raise SystemExit(
            "Smoke failed; inspect locally. Response bodies and credentials withheld."
        ) from None
