from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "local"
    seed_demo_data: bool = False
    admin_email: str | None = None
    admin_password: str | None = None
    admin_full_name: str = "LineLink Admin"
    database_url: str = "postgresql+psycopg://linelink:linelink@localhost:5432/linelink"
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    upload_dir: str = "uploads"
    public_base_url: str = "http://localhost:8000"
    allowed_origins: str = Field(default="http://localhost:5173,http://localhost:3000")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def allowed_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
