from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: Literal["development", "test", "production"] = "development"
    debug: bool = False
    api_prefix: str = "/v1"
    currency: Literal["BRL"] = "BRL"
    cors_allowed_origins: str = ""
    trust_proxy_headers: bool = False
    log_level: str = "INFO"

    database_url: str = "postgresql+psycopg://artbid:artbid@127.0.0.1:5432/artbid"
    database_pool_size: int = 10
    database_max_overflow: int = 10
    database_statement_timeout_ms: int = 15_000

    redis_url: str | None = "redis://127.0.0.1:6379/0"
    celery_broker_url: str = "redis://127.0.0.1:6379/1"
    celery_result_backend: str = "redis://127.0.0.1:6379/2"

    token_ttl_seconds: int = 900
    password_min_length: int = 12
    password_max_length: int = 128

    deposit_min_cents: int = 1_000
    deposit_max_cents: int = 100_000_000
    wallet_max_total_cents: int = 1_000_000_000
    bid_min_cents: int = 1_000
    bid_max_cents: int = 1_000_000_000
    lot_starting_bid_min_cents: int = 1_000
    lot_starting_bid_max_cents: int = 100_000_000
    lot_min_increment_min_cents: int = 100
    lot_min_increment_max_cents: int = 10_000_000
    lot_min_duration_seconds: int = 1_800
    lot_max_duration_seconds: int = 2_592_000
    lot_max_lead_seconds: int = 7_776_000
    lot_clock_skew_seconds: int = 60

    anti_sniping_window_seconds: int = 120
    anti_sniping_extension_seconds: int = 120
    anti_sniping_max_extensions: int = 10

    settlement_commission_bps: int = 0

    idempotency_ttl_hours: int = 24

    rate_limit_enabled: bool = True
    rate_limit_login_per_minute: int = 10
    rate_limit_register_per_hour: int = 5
    rate_limit_deposit_per_minute: int = 20
    rate_limit_bid_per_minute: int = 30
    rate_limit_artwork_search_per_minute: int = 30

    aic_base_url: str = "https://api.artic.edu/api/v1"
    aic_timeout_connect_seconds: float = 3.0
    aic_timeout_read_seconds: float = 6.0
    aic_max_response_bytes: int = 2_000_000
    aic_page_size_max: int = 24
    aic_contact_email: str = ""

    sse_heartbeat_seconds: int = 15
    sse_max_duration_seconds: int = 300
    sse_poll_seconds: float = 2.0
    sse_replay_limit: int = 200
    sse_max_connections: int = 500
    sse_max_connections_per_user: int = 4

    audit_chain_version: int = 1
    audit_alias_secret: str = "dev-only-alias-secret-change-me"
    audit_checkpoint_private_key: str = ""
    audit_checkpoint_public_key: str = ""
    audit_checkpoint_key_id: str = "dev-key-1"
    audit_checkpoint_interval_seconds: int = 60
    audit_checkpoint_batch_lots: int = 200

    lot_tick_seconds: int = 5
    outbox_dispatch_seconds: int = 2
    idempotency_cleanup_seconds: int = 3_600
    audit_verify_seconds: int = 900

    @field_validator("token_ttl_seconds")
    @classmethod
    def _token_ttl(cls, value: int) -> int:
        if value < 60 or value > 86_400:
            raise ValueError("TOKEN_TTL_SECONDS deve estar entre 60 e 86400")
        return value

    @field_validator("settlement_commission_bps")
    @classmethod
    def _commission(cls, value: int) -> int:
        if value < 0 or value > 10_000:
            raise ValueError("SETTLEMENT_COMMISSION_BPS deve estar entre 0 e 10000")
        return value

    @property
    def cors_origins_list(self) -> list[str]:
        return [item.strip() for item in self.cors_allowed_origins.split(",") if item.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    def validate_runtime_safety(self) -> None:
        if not self.is_production:
            return
        problems: list[str] = []
        if self.debug:
            problems.append("DEBUG não pode estar activo em produção")
        if len(self.audit_alias_secret) < 32 or self.audit_alias_secret.startswith("dev-only"):
            problems.append("AUDIT_ALIAS_SECRET inseguro para produção")
        if self.cors_origins_list == ["*"]:
            problems.append("CORS wildcard não é permitido")
        if problems:
            raise RuntimeError("Configuração insegura: " + "; ".join(problems))


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
