from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str
    anthropic_model: str = "claude-sonnet-4-6"
    database_url: str = "sqlite:///./demo.db"
    max_rows_returned: int = 500
    query_timeout_seconds: int = 10
    audit_log_path: str = "./audit_log.jsonl"


settings = Settings()
