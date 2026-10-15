"""Configuration-only checks. Never print credentials or make auth substitutes."""

import argparse
import json
import os
from pathlib import Path

from dotenv import dotenv_values

from opportunity_platform.core.config import settings


def configuration_report(web_file: Path) -> dict:
    config = settings()
    web = {**dotenv_values(web_file), **os.environ}
    required = [
        "VITE_FIREBASE_API_KEY",
        "VITE_FIREBASE_AUTH_DOMAIN",
        "VITE_FIREBASE_PROJECT_ID",
        "VITE_FIREBASE_APP_ID",
    ]
    provider = config.ai_extraction_provider
    key = config.openai_api_key if provider == "openai" else config.gemini_api_key
    model = config.openai_model if provider == "openai" else config.gemini_model
    checks = {
        "firebase_backend_project": bool(config.firebase_project_id),
        "firebase_web_configuration": all(web.get(key) for key in required),
        "firebase_projects_match": bool(config.firebase_project_id)
        and web.get("VITE_FIREBASE_PROJECT_ID") == config.firebase_project_id,
        "extraction_server_key": bool(key),
        "extraction_model_selected": bool(model),
        "provider_key_consistent": provider != "gemini" or not key.startswith("sk-"),
        "no_private_keys_in_frontend": not any(
            web.get(key)
            for key in [
                "VITE_GEMINI_API_KEY",
                "VITE_GOOGLE_API_KEY",
                "VITE_OPENAI_API_KEY",
                "VITE_DATABASE_URL",
                "VITE_GOOGLE_APPLICATION_CREDENTIALS",
            ]
        ),
    }
    explicit_adc = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    adc_file = (
        Path(explicit_adc)
        if explicit_adc
        else (Path.home() / ".config/gcloud/application_default_credentials.json")
    )
    return {
        "checks": checks,
        "configuration_ready": all(checks.values()),
        "adc_file_present": adc_file.is_file(),
        "adc_note": (
            "File presence is not proof of usable permissions. Cloud Run uses its service account."
        ),
        "provider": provider,
        "model": model,
        "database": "configured (value withheld)",
        "documents": {
            "uploads_enabled": config.document_uploads_enabled
            and config.environment == "development",
            "storage_backend": config.document_storage_backend,
            "production_uploads_ready": False,
            "malware_scanning": "not configured; production uploads remain gated",
        },
        "frontend_api_origin": "configured" if web.get("VITE_API_BASE_URL") else "local Vite proxy",
        "token_limits": {
            "input": config.openai_max_input_tokens
            if provider == "openai"
            else config.gemini_max_input_tokens,
            "output": config.openai_max_output_tokens
            if provider == "openai"
            else config.gemini_max_output_tokens,
        },
        "timeout_seconds_per_model_request": config.openai_timeout_seconds
        if provider == "openai"
        else config.gemini_timeout_seconds,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--web-env", type=Path, default=Path("../web/.env.local"))
    args = parser.parse_args()
    report = configuration_report(args.web_env)
    print(json.dumps(report, indent=2))
    return 0 if report["configuration_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
