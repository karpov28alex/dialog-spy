from functools import lru_cache
from urllib.parse import urlparse

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str
    public_base_url: str
    mini_app_url: str
    database_url: str
    redis_url: str = "redis://redis:6379/0"
    jwt_secret: str
    webhook_secret: str
    admin_email: str
    admin_password: str
    trial_days: int = 3
    media_dir: str = "/data/media"
    max_media_mb: int = 50
    retention_days_default: int = 30
    dev_auth: bool = False
    dev_telegram_id: int = 1
    log_raw_updates: bool = True
    archive_grace_days: int = 7
    worker_enabled: bool = True
    admin_media_chat_id: int | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("public_base_url", "mini_app_url")
    @classmethod
    def validate_https_url(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("must be an absolute http(s) URL")
        return value.rstrip("/") if parsed.path in {"", "/"} else value

    @field_validator("max_media_mb")
    @classmethod
    def validate_media_limit(cls, value: int) -> int:
        if not 1 <= value <= 2000:
            raise ValueError("MAX_MEDIA_MB must be between 1 and 2000")
        return value

    @model_validator(mode="after")
    def reject_placeholders(self):
        if self.dev_auth:
            return self
        values = {
            "BOT_TOKEN": self.bot_token,
            "JWT_SECRET": self.jwt_secret,
            "WEBHOOK_SECRET": self.webhook_secret,
            "ADMIN_PASSWORD": self.admin_password,
        }
        bad = [name for name, value in values.items() if "REPLACE_" in value or value.startswith("change-")]
        if bad:
            raise ValueError(f"Replace placeholder values in .env: {', '.join(bad)}")
        if ":" not in self.bot_token:
            raise ValueError("BOT_TOKEN has an invalid format")
        if len(self.jwt_secret) < 32:
            raise ValueError("JWT_SECRET must contain at least 32 characters")
        if len(self.webhook_secret) < 24:
            raise ValueError("WEBHOOK_SECRET must contain at least 24 characters")
        if len(self.admin_password) < 10:
            raise ValueError("ADMIN_PASSWORD must contain at least 10 characters")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
