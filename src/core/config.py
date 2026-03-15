from functools import lru_cache

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", case_sensitive=True)

    # Application
    APP_NAME: str = "api_label"
    DEBUG: bool = False
    ROOT_PATH: str = "/label"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/api_label_psql"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/3"

    # JWT
    SECRET_KEY: str = "change_this_secret_key_min_32_chars_in_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/3"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/3"

    # Barcode API
    BARCODE_API_URL: str = "https://api.pibico.es/barcode"
    BARCODE_API_KEY: str = ""

    # PDF Generation
    PDF_OUTPUT_DIR: str = "/tmp/api_label_pdfs"

    # Security — login lockout
    LOGIN_MAX_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_MINUTES: int = 15

    # Trial limits (public preview without auth)
    TRIAL_MAX_SESSION: int = 3       # Max previews per session cookie
    TRIAL_MAX_IP: int = 10           # Max previews per IP (higher for shared networks)
    TRIAL_SESSION_TTL: int = 2592000 # 30 days in seconds
    TRIAL_IP_TTL: int = 604800       # 7 days in seconds

    # i18n
    SUPPORTED_LANGUAGES: list = ["es", "en"]
    DEFAULT_LANGUAGE: str = "es"

    # External integrations
    OFFER_API_URL: str = "http://127.0.0.1:6958"
    OFFER_ADMIN_API_KEY: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
