from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_", env_file=".env", extra="ignore")

    env: str = "development"
    database_url: str = ""
    migration_table_name: str = "schema_migrations"
    database_pool_min_size: int = 1
    database_pool_max_size: int = 10
    default_registration_role_name: str = "user"
    access_token_ttl_seconds: int = 900
    refresh_token_ttl_seconds: int = 2592000
    jwt_algorithm: str = "HS256"
    jwt_secret: str = "dev-only-change-in-production"
    jwt_issuer: str = "authentication-service"
    jwt_audience: str = "api"
    log_level: str = "INFO"
    metrics_enabled: bool = True
    request_id_header_name: str = "X-Request-ID"
    readiness_query_timeout_ms: int = 2000


def load_settings() -> AppSettings:
    return AppSettings()
