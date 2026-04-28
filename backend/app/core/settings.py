from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "BenchFile"
    app_host: str = "0.0.0.0"
    app_port: int = 8100

    promptbench_base_url: str = "http://localhost:8020"
    default_model: str = "gemma3:4b"
    request_timeout_seconds: int = 300

    storage_root: Path = Path("storage")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="BENCHFILE_",
        extra="ignore",
    )


settings = Settings()
