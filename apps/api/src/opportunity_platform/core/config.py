from functools import lru_cache
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    environment: Literal["development", "production"] = "development"
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
    enable_development_catalogue: bool = False
    ingestion_min_interval_seconds: int = Field(default=30, ge=0, le=3600)
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)

    @model_validator(mode="after")
    def production_configuration(self):
        if self.environment == "production":
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
