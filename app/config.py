"""Application configuration.

Central settings loaded from environment variables (and a local ``.env`` file
in development) via pydantic-settings. Import the shared ``settings`` instance
instead of reaching for ``os.getenv`` throughout the codebase.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    SECRET_KEY: str = "change-me-in-production"
    FRONTEND_URL: str = "http://localhost:5173"
    DATABASE_URL: str = "sqlite:///./crowdbeat.db"

    # YouTube Data API v3 — optional; without it, songs are approved without an
    # auto-resolved youtube_video_id and the frontend falls back to a search link.
    YOUTUBE_API_KEY: str = ""


settings = Settings()
