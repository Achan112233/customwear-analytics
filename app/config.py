from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "CustomWear Analytics API"
    app_env: str = "development"
    database_url: str = "sqlite:///./analytics.db"
    redis_url: str = "redis://localhost:6379/0"
    segmentation_queue: str = "analytics"
    api_key: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
