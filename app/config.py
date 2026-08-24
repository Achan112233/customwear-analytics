from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "CustomWear Analytics API"
    app_env: str = "development"
    database_url: str = "sqlite:///./analytics.db"
    redis_url: str = "redis://localhost:6379/0"
    segmentation_queue: str = "analytics"
    api_key: str | None = None
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()

