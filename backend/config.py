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
    # Runtime connection string. MUST point at a NOBYPASSRLS role in prod
    # (e.g. app_user) so Row-Level Security actually filters rows. The
    # default Supabase `postgres` role has BYPASSRLS and silently ignores
    # all policies.
    DATABASE_URL: str

    # Owner-role URL used ONLY by Alembic migrations (DDL: create tables,
    # policies, FORCE RLS). Needs the table owner (Supabase `postgres`).
    # Falls back to DATABASE_URL when unset (e.g. local SQLite tests).
    MIGRATION_DATABASE_URL: str | None = None

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


# Values that must never be used as real production secrets.
_INSECURE_SECRET_KEYS = {"", "dev-secret-change-me", "changeme", "secret"}


def insecure_secret_issues(s: Settings = settings) -> list[str]:
    """Return a list of weak/missing secret problems (empty list = all good).

    Called at startup (see main.py): the issues are always logged, and in
    production we refuse to boot - so a real deployment can never silently run
    with the throwaway dev JWT key or a token-less (open) AI worker. This is
    the §7 'secrets in env' gate: secrets must come from the host env, not the
    insecure code defaults.
    """
    issues: list[str] = []
    if s.SECRET_KEY.strip() in _INSECURE_SECRET_KEYS:
        issues.append(
            "SECRET_KEY is unset or the dev default - set a strong random "
            'value (python -c "import secrets; print(secrets.token_hex(32))").'
        )
    if not s.AI_WORKER_TOKEN.strip():
        issues.append(
            "AI_WORKER_TOKEN is empty - the AI worker would answer anyone; set "
            "the same shared secret here and on the worker."
        )
    return issues
