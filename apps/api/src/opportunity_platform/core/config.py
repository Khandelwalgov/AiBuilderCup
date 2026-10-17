import os
from functools import lru_cache
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    environment: Literal["development", "production"] = "development"
    database_provider: Literal["postgresql", "neon"] = "postgresql"
    database_url: str = (
        "postgresql+psycopg://opportunity:local-development-only@localhost:5432/opportunity"
    )
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    firebase_project_id: str = ""
    ai_extraction_provider: Literal["gemini", "openai"] = "gemini"
    openai_api_key: str = ""
    openai_model: str = "gpt-5.6-terra"
    openai_timeout_seconds: int = Field(default=180, ge=10, le=300)
    openai_max_input_tokens: int = Field(default=160000, ge=1024, le=1000000)
    openai_max_output_tokens: int = Field(default=16384, ge=256, le=65536)
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.8-flash"
    gemini_timeout_seconds: int = Field(default=120, ge=30, le=180)
    gemini_max_input_tokens: int = Field(default=200000, ge=1024, le=1048576)
    gemini_max_output_tokens: int = Field(default=16384, ge=1024, le=65536)
    ai_assistant_live_enabled: bool = False
    ai_ingestion_live_enabled: bool = False
    ai_ingestion_test_budget_usd: float | None = Field(default=None, ge=0, le=1000)
    document_uploads_enabled: bool = False
    document_storage_backend: Literal["local", "gcs"] = "local"
    document_local_root: str = ".private-documents"
    document_gcs_bucket: str = ""
    document_signing_key: str = ""
    document_max_file_bytes: int = Field(default=5_242_880, ge=1024, le=10_485_760)
    document_max_count: int = Field(default=25, ge=1, le=100)
    document_max_total_bytes: int = Field(default=52_428_800, ge=1024, le=524_288_000)
    retrieval_shortlist_size: int = Field(default=150, ge=50, le=500)
    neural_retrieval_enabled: bool = True
    neural_model_directory: str = "/app/models/multilingual-minilm"
    process_role: Literal["api", "ingestion_worker"] = "api"
    paid_ai_worker_enabled: bool = False
    ai_global_budget_usd: float = Field(default=0, ge=0, le=1000)
    ai_run_budget_usd: float = Field(default=0, ge=0, le=100)
    ai_max_requests_per_run: int = Field(default=4, ge=1, le=20)
    ai_daily_call_limit: int = Field(default=10, ge=1, le=1000)
    ai_monthly_call_limit: int = Field(default=100, ge=1, le=10000)
    # Explicit, operator-reviewed USD ceilings per million tokens, keyed provider:model.
    ai_price_ceilings: dict[str, dict[str, float]] = {}
    enable_development_catalogue: bool = False
    ingestion_min_interval_seconds: int = Field(default=30, ge=0, le=3600)
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)

    @model_validator(mode="after")
    def production_configuration(self):
        if self.paid_ai_worker_enabled and self.process_role != "ingestion_worker":
            raise ValueError("Paid inference is restricted to an explicitly configured worker")
        if self.database_provider == "neon":
            from opportunity_platform.core.database import validate_neon_url

            validate_neon_url(self.database_url)
        if self.environment == "production":
            if os.environ.get("FIREBASE_AUTH_EMULATOR_HOST"):
                raise ValueError("Production must never use the Firebase Auth emulator")
            if self.ai_ingestion_live_enabled:
                raise ValueError(
                    "Production ingestion requires a separate approved cost/review release"
                )
            if self.document_uploads_enabled:
                raise ValueError(
                    "Production uploads require malware scanning and security acceptance"
                )
            if not self.firebase_project_id or self.enable_development_catalogue:
                raise ValueError("Production needs a Firebase project and real-only catalogue")
            if self.database_url == Settings.model_fields["database_url"].default or urlsplit(
                self.database_url
            ).hostname in {"localhost", "127.0.0.1", "::1"}:
                raise ValueError("Production needs an explicit hosted database connection")
            if not self.cors_origins:
                raise ValueError("Production needs explicit frontend CORS origins")
            for origin in self.cors_origins:
                value = urlsplit(origin)
                if (
                    value.scheme != "https"
                    or not value.hostname
                    or value.username
                    or value.password
                    or value.path not in ("", "/")
                    or value.query
                    or value.fragment
                    or value.hostname in {"localhost", "127.0.0.1"}
                ):
                    raise ValueError("Production CORS requires explicit HTTPS frontend origins")
        return self


@lru_cache
def settings() -> Settings:
    return Settings()
