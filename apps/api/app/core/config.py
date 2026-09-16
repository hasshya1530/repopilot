from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "RepoPilot"
    app_env: str = "development"
    debug: bool = True

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    web_url: str = "http://localhost:3000"
    api_url: str = "http://localhost:8000"

    database_url: str = ""
    redis_url: str = ""

    github_client_id: str = ""
    github_client_secret: str = ""
    github_redirect_uri: str = ""
    github_token: str = ""

    model_provider: str = "ollama"
    model_name: str = ""
    ollama_base_url: str = "http://localhost:11434"

    embedding_provider: str = "local"
    embedding_model: str = ""
    vector_dimension: int | None = None

    sandbox_enabled: bool = True
    sandbox_image: str = "repopilot-sandbox:latest"
    sandbox_timeout_seconds: int = 300
    sandbox_memory_limit: str = "512m"
    sandbox_cpu_limit: int = 1

    secret_key: str = ""
    jwt_secret_key: str = ""

    otel_enabled: bool = False
    otel_service_name: str = "repopilot-api"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
