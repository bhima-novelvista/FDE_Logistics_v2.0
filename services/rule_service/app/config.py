"""
Settings of the rule service.

Values come from environment variables. When the service runs on your
computer (not in Docker) they are also read from the project-root ``.env``
(the same file Step 1 and Step 3 created). In Docker, docker compose passes
only the settings this service needs (never the MySQL root password).

Secrets are ``SecretStr``: they never appear in logs, error messages or
``repr()``.
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

SERVICE_DIR = Path(__file__).resolve().parents[1]          # services/rule_service (in Docker: /app)
# FDE_PB_Sol on your computer; in Docker there is no project folder (and no .env file).
PROJECT_ROOT = SERVICE_DIR.parents[1] if len(SERVICE_DIR.parents) > 1 else SERVICE_DIR
DEFAULT_RULES_FILE = SERVICE_DIR / "app" / "rules" / "sop_rules_v2.4.yaml"

_IDENTIFIER = re.compile(r"^[A-Za-z0-9_]{1,64}$")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",          # .env also holds settings of other steps
        case_sensitive=True,
    )

    # --- database (Step 3) ---
    MYSQL_HOST: str = "127.0.0.1"
    MYSQL_PORT: int = Field(default=3306, ge=1, le=65535)
    RULE_SVC_USER: str = "rule_svc"
    RULE_SVC_PASSWORD: SecretStr
    FDE_VIEWS_DB: str = "fde_views"
    FDE_AUDIT_DB: str = "fde_audit"
    DB_CONNECT_TIMEOUT_S: int = Field(default=5, ge=1, le=60)
    DB_QUERY_TIMEOUT_MS: int = Field(default=10_000, ge=100, le=120_000)

    # --- API logins (Step 4) ---
    JWT_SECRET: SecretStr
    JWT_EXPIRE_MINUTES: int = Field(default=30, ge=1, le=24 * 60)
    JWT_ISSUER: str = "fde-rule-service"
    RULE_API_KEY: SecretStr
    API_USER_DISPATCHER_PASSWORD: SecretStr
    API_USER_SUPERVISOR_PASSWORD: SecretStr
    API_USER_ADMIN_PASSWORD: SecretStr

    # --- service ---
    RULES_FILE: Path = DEFAULT_RULES_FILE
    RULE_API_PORT: int = Field(default=8101, ge=1, le=65535)
    LOG_LEVEL: str = "INFO"

    @field_validator("FDE_VIEWS_DB", "FDE_AUDIT_DB", "RULE_SVC_USER")
    @classmethod
    def plain_identifier(cls, v: str) -> str:
        # These names are put into SQL text, so only letters, digits and _ are allowed.
        if not _IDENTIFIER.match(v):
            raise ValueError("use only letters, digits and _ (max 64)")
        return v

    @field_validator("JWT_SECRET")
    @classmethod
    def long_enough(cls, v: SecretStr) -> SecretStr:
        if len(v.get_secret_value()) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters (update_env creates 64)")
        return v

    @property
    def view_name(self) -> str:
        return f"{self.FDE_VIEWS_DB}.vw_fleet_readings"

    @property
    def audit_table(self) -> str:
        return f"{self.FDE_AUDIT_DB}.RuleDecisionLog"

    def user_passwords(self) -> dict[str, tuple[str, SecretStr]]:
        """The API users: user name -> (role, password)."""
        return {
            "dispatcher": ("dispatcher", self.API_USER_DISPATCHER_PASSWORD),
            "supervisor": ("supervisor", self.API_USER_SUPERVISOR_PASSWORD),
            "admin": ("admin", self.API_USER_ADMIN_PASSWORD),
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
