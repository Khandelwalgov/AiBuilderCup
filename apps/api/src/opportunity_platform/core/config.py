from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = (
        "postgresql+psycopg://opportunity:local-development-only@localhost:5432/opportunity"
    )
    cors_origins: list[str] = ["http://localhost:5173"]
    firebase_project_id: str = ""
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def settings() -> Settings:
    return Settings()
