from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)


class Settings(BaseSettings):
    # -----------------------------------------------------
    # Application
    # -----------------------------------------------------

    app_name: str = "SentinelAI"
    app_version: str = "0.1.0"

    # -----------------------------------------------------
    # Database
    # -----------------------------------------------------

    database_url: str = (
        "sqlite:///./sentinel.db"
    )

    # -----------------------------------------------------
    # Ollama
    # -----------------------------------------------------

    ollama_base_url: str = (
        "http://127.0.0.1:11434"
    )

    ollama_model: str = (
        "qwen3:1.7b"
    )

    ollama_timeout_seconds: float = 120.0

    ollama_think: bool = False

    # -----------------------------------------------------
    # Environment file
    # -----------------------------------------------------

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()