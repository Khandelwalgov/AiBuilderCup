"""Read-only Google account proof for the explicitly authorized, local Gemini worker.

No billing changes, generation requests, persisted credentials or implicit model selection.
The project must own the key AND have billing disabled AND expose positive model-specific
free-tier quotas. Metadata failure denies inference. The short cache is process-local only.
"""

import hashlib
import json
import subprocess
import time
import urllib.parse
import urllib.request
from functools import lru_cache


def cloud_json(arguments):
    result = subprocess.run(
        ["gcloud", *arguments, "--format=json", "--quiet"],
        capture_output=True,
        text=True,
        check=True,
        timeout=20,
    )
    return json.loads(result.stdout)


def metadata(path, token):
    request = urllib.request.Request(path, headers={"Authorization": "Bearer " + token})
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


@lru_cache(maxsize=4)
def _proof(project, model, key_hash, minute):
    from google import genai
    from google.genai import types

    from opportunity_platform.core.config import settings

    config = settings()
    key = config.gemini_api_key
    if hashlib.sha256(key.encode()).hexdigest() != key_hash:
        raise ValueError("Credential changed during free-tier verification")
    project_number = str(cloud_json(["projects", "describe", project])["projectNumber"])
    billing = cloud_json(["billing", "projects", "describe", project])
    if billing.get("billingEnabled") is not False or billing.get("billingAccountName"):
        raise ValueError("Billing-disabled project proof required")
    token = subprocess.run(
        ["gcloud", "auth", "print-access-token"],
        capture_output=True,
        text=True,
        check=True,
        timeout=20,
    ).stdout.strip()
    owner = metadata(
        "https://apikeys.googleapis.com/v2/keys:lookupKey?"
        + urllib.parse.urlencode({"keyString": key}),
        token,
    )
    if owner.get("parent") != f"projects/{project_number}/locations/global":
        raise ValueError("Key does not belong to the authorized project")
    quotas = metadata(
        "https://serviceusage.googleapis.com/v1beta1/projects/"
        + project_number
        + "/services/generativelanguage.googleapis.com/consumerQuotaMetrics?view=FULL&pageSize=200",
        token,
    )
    if quotas.get("nextPageToken"):
        raise ValueError("Incomplete quota metadata")
    limits = {}
    for metric in quotas.get("metrics", []):
        name = metric.get("metric", "").split("/")[-1]
        if name not in {
            "generate_content_free_tier_requests",
            "generate_content_free_tier_input_token_count",
        }:
            continue
        for limit in metric.get("consumerQuotaLimits", []):
            for bucket in limit.get("quotaBuckets", []):
                if bucket.get("dimensions", {}).get("model") != model:
                    continue
                value = int(bucket.get("effectiveLimit", 0))
                unit = limit.get("unit", "")
                if value > 0 and "/min/" in unit:
                    limits["rpm" if name.endswith("requests") else "tpm"] = value
                if value > 0 and "/d/" in unit and name.endswith("requests"):
                    limits["rpd"] = value
    if set(limits) != {"rpm", "tpm", "rpd"}:
        raise ValueError("Positive model-specific free quotas could not be established")
    with genai.Client(
        api_key=key,
        http_options=types.HttpOptions(
            timeout=20000, retry_options=types.HttpRetryOptions(attempts=1)
        ),
    ) as client:
        info = client.models.get(model=model)
    if "generateContent" not in (info.supported_actions or []):
        raise ValueError("Model does not expose generation")
    return {
        "mode": "verified_free_gemini",
        "project": project,
        "model": model,
        "key_sha256": key_hash,
        "billing_enabled": False,
        "verified_at_unix": int(time.time()),
        "free_quotas": limits,
        "input": 0,
        "output": 0,
    }


def verify(model):
    from opportunity_platform.core.config import settings
    from opportunity_platform.ingestion.budget import BudgetDenied

    config = settings()
    if not (
        config.gemini_free_worker_enabled
        and config.process_role == "ingestion_worker"
        and (
            (
                not config.paid_ai_worker_enabled
                and config.ai_global_budget_usd == 0
                and config.ai_run_budget_usd == 0
            )
            or (
                config.ai_openai_fallback_enabled
                and config.paid_ai_worker_enabled
                and config.ai_global_budget_usd > 0
                and config.ai_run_budget_usd > 0
                and config.ai_openai_fallback_budget_usd > 0
                and config.ai_openai_fallback_run_budget_usd > 0
            )
        )
        and config.gemini_free_project_id
        and model == config.gemini_free_model
        and config.gemini_api_key
    ):
        raise BudgetDenied("Free Gemini worker/project/model authorization is missing")
    try:
        # Check billing immediately before every reserved request, even when model/quota
        # metadata is cached. No local proof can prevent an external concurrent billing change.
        billing = cloud_json(["billing", "projects", "describe", config.gemini_free_project_id])
        if billing.get("billingEnabled") is not False or billing.get("billingAccountName"):
            raise ValueError("Billing-disabled project proof required")
        return _proof(
            config.gemini_free_project_id,
            model,
            hashlib.sha256(config.gemini_api_key.encode()).hexdigest(),
            int(time.time() // 30),
        )
    except Exception:
        # Never propagate HTTP URLs (key lookup), credentials or subprocess output.
        raise BudgetDenied(
            "Free-tier account/model proof unavailable; no inference permitted"
        ) from None
