"""Core runtime module for config.
Provides shared runtime primitives such as config, auth, DB, and logging.
"""
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Core runtime component for settings."""
    app_name: str = "LaunchPad Conversion Lab API"
    env: str = "dev"
    secret_key: str = "dev-secret-change-me"
    access_token_expire_minutes: int = 120
    database_url: str = "postgresql+psycopg://postgres:postgres@db:5432/launchpad"
    local_database_url: str = "sqlite+pysqlite:///./launchpad.db"
    use_sqlite: bool = False
    codex_api_key: str | None = None
    codex_api_key_file: str | None = None
    codex_api_key_encrypted: str | None = None
    codex_api_key_decryption_key: str | None = None
    codex_api_key_decryption_key_file: str | None = None
    codex_provider: str = "cli"
    codex_cli_path: str = "codex"
    codex_cli_timeout_seconds: int = 90
    codex_model: str = "gpt-4.1-mini"
    codex_use_fallback: bool = True
    codex_max_retries: int = 3
    codex_retry_base_seconds: float = 0.75
    codex_max_concurrent_requests: int = 4
    codex_requests_per_minute: int = 30
    frontend_origin: str = "http://localhost:3000"
    demo_reset_on_start: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    @model_validator(mode="after")
    def validate_security_defaults(self):
        """Reject insecure default secrets in non-development environments."""
        if self.env.lower() != "dev" and self.secret_key == "dev-secret-change-me":
            raise ValueError("SECRET_KEY must be set to a non-default value when ENV is not 'dev'")
        return self


settings = Settings()
