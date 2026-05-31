from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "local"
    seed_demo_data: bool = False

    admin_email: str | None = None
    admin_password: str | None = None
    admin_full_name: str = "Rentalink Admin"

    application_token_expire_days: int = 7

    database_url: str = (
        "postgresql+psycopg://rentalink:rentalink@localhost:5432/rentalink"
    )

    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    upload_dir: str = "uploads"

    public_base_url: str = "http://localhost:8000"

    resend_api_key: str | None = None

    email_from: str = (
        "Rentalink Security <onboarding@resend.dev>"
    )

    # =========================================================
    # CORS / FRONTEND ORIGINS
    # =========================================================

    allowed_origins: str = Field(
        default=(
            "http://localhost:5173,"
            "http://127.0.0.1:5173,"
            "http://localhost:3000,"
            "http://127.0.0.1:3000,"
            "http://localhost:8001,"
            "http://127.0.0.1:8001,"
            "https://rentalink.app,"
            "https://www.rentalink.app,"
            "https://app.rentalink.app,"
            "https://linelink-three.vercel.app"
        )
    )
    cors_origins: str | None = None

    # =========================================================
    # MPESA
    # =========================================================

    mpesa_base_url: str | None = None
    mpesa_client_id: str | None = None
    mpesa_client_secret: str | None = None
    mpesa_short_code: str | None = None
    mpesa_callback_url: str | None = None

    # =========================================================
    # ECOCASH
    # =========================================================

    ecocash_base_url: str | None = None
    ecocash_client_id: str | None = None
    ecocash_client_secret: str | None = None
    ecocash_merchant_code: str | None = None
    ecocash_callback_url: str | None = None

    # =========================================================
    # MOPAY
    # =========================================================

    mopay_base_url: str | None = None
    mopay_api_key: str | None = None
    mopay_merchant_id: str | None = None
    mopay_webhook_secret: str | None = None
    mopay_callback_url: str | None = None
    mopay_return_url: str | None = None
    mopay_environment: str = "sandbox"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    @property
    def allowed_origin_list(self) -> list[str]:
        fallback_origins = [
            "https://rentalink.app",
            "https://www.rentalink.app",
            "https://app.rentalink.app",
            "https://linelink-three.vercel.app",
        ]

        configured: list[str] = []

        for raw_value in (self.allowed_origins, self.cors_origins or ""):
            configured.extend(
                origin.strip()
                for origin in raw_value.split(",")
                if origin.strip()
            )

        configured.extend(fallback_origins)

        if self.app_env.lower() in {
            "local",
            "development",
            "dev",
        }:
            configured.extend(
                [
                    "http://localhost:5173",
                    "http://127.0.0.1:5173",
                    "http://localhost:3000",
                    "http://127.0.0.1:3000",
                    "http://localhost:8001",
                    "http://127.0.0.1:8001",
                ]
            )

        return list(dict.fromkeys(configured))


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
