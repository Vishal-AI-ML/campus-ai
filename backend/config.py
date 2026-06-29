"""Application configuration.

Values are read from environment variables and, in local development, from a
`.env` file next to this module (validated/typed via pydantic-settings).

Security note: `SECRET_KEY` has a throwaway default so the app runs locally,
but you MUST set a strong random value in `.env` before any real deployment.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "Campus AI API"
    ENVIRONMENT: str = "development"

    # --- Database ---------------------------------------------------------
    # Supabase Postgres connection string (psycopg3 driver).
    DATABASE_URL: str

    # --- Auth / JWT -------------------------------------------------------
    # Generate a strong value for production, e.g. `python -c "import secrets; print(secrets.token_hex(32))"`
    SECRET_KEY: str = "dev-secret-change-me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day

    # --- AI worker --------------------------------------------------------
    # Base URL of the separate AI worker service (proof scoring, mentor, ...).
    # Backend calls this over HTTP in a background task to fill `ai_score`.
    AI_WORKER_URL: str = "http://127.0.0.1:8100"

    # Shared secret sent to the AI worker (X-Worker-Token header) so a public
    # worker (e.g. Hugging Face Space) only answers our backend. Empty = off.
    AI_WORKER_TOKEN: str = ""

    # --- CORS -------------------------------------------------------------
    # Comma-separated list of allowed frontend origins for production, e.g.
    # "https://campus-ai.vercel.app". Local dev origins are always allowed
    # (see main.py). Set this on the host (Koyeb) to your deployed Vercel URL.
    CORS_ORIGINS: str = ""

    # --- Observability ----------------------------------------------------
    # Sentry error tracking DSN. Empty = disabled (app runs fine without it).
    # Set this in the Render env to turn on production error capture.
    SENTRY_DSN: str = ""


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (parsed once per process)."""
    return Settings()


settings = get_settings()
