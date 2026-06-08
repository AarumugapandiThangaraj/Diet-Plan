import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="NUTRI_")

    ollama_model: str = "gemma3:4b"
    data_root: str = str(Path(__file__).resolve().parents[2] / "Data new")
    cache_size: int = 32
    database_url: str = os.getenv(
        "DATABASE_URL", 
        "postgresql+asyncpg://postgres:postgres@localhost:5432/nutri"
    )

settings = Settings()

