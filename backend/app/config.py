from functools import lru_cache
from urllib.parse import quote_plus

from pydantic import Field
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = ""
    app_environment: str = "development"
    postgres_host: str = "127.0.0.1"
    postgres_port: int = 5432
    postgres_user: str = "study"
    postgres_password: str = "study"
    postgres_db: str = "study_for_job"
    postgres_sslmode: str = ""
    postgres_pool_size: int = Field(default=5, ge=1)
    postgres_max_overflow: int = Field(default=10, ge=0)
    cors_origins: str = "http://localhost:5173"
    ai_provider: str = "fake"
    ai_request_timeout_seconds: float = Field(default=30, ge=1, le=120)
    ai_fake_model: str = "local-deterministic-v1"
    deepseek_base_url: str = "https://www.sophnet.com/api/open-apis/v1"
    deepseek_model: str = ""
    deepseek_api_key: SecretStr = SecretStr("")
    sophnet_api_key: SecretStr = SecretStr("")

    @property
    def resolved_deepseek_api_key(self) -> str:
        explicit = self.deepseek_api_key.get_secret_value().strip()
        return explicit or self.sophnet_api_key.get_secret_value().strip()

    @property
    def deepseek_configured(self) -> bool:
        return bool(
            self.deepseek_base_url.strip()
            and self.deepseek_model.strip()
            and self.resolved_deepseek_api_key
        )

    @property
    def resolved_database_url(self) -> str:
        configured_url = self.database_url.strip()
        if configured_url:
            if configured_url.startswith("postgresql://"):
                return configured_url.replace("postgresql://", "postgresql+psycopg://", 1)
            if configured_url.startswith("postgres://"):
                return configured_url.replace("postgres://", "postgresql+psycopg://", 1)
            return configured_url
        dsn = (
            f"postgresql+psycopg://{quote_plus(self.postgres_user)}:"
            f"{quote_plus(self.postgres_password)}@{self.postgres_host}:"
            f"{self.postgres_port}/{self.postgres_db}"
        )
        return f"{dsn}?sslmode={quote_plus(self.postgres_sslmode)}" if self.postgres_sslmode.strip() else dsn


@lru_cache
def get_settings() -> Settings:
    return Settings()
