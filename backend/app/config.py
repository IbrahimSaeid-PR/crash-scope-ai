from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./storage/crashscope.db"
    storage_dir: Path = Path("storage")
    max_upload_bytes: int = 500 * 1024 * 1024
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    openai_model: str | None = None
    llm_provider: str | None = None
    qdrant_url: str | None = None
    redis_url: str | None = None
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
