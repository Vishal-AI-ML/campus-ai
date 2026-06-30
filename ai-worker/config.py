"""AI Worker configuration (env-driven).

Provider-agnostic: the worker can talk to either Google Gemini or Groq, chosen
at runtime via `LLM_PROVIDER`. You only need an API key for the provider(s) you
actually use.

Location:
    E:\\campus-ai\\ai-worker\\config.py
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Loaded from environment / a local `.env` file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Which LLM backend to use: "groq" or "gemini".
    LLM_PROVIDER: str = "groq"

    # API keys (only the selected provider's key is required at call time).
    GROQ_API_KEY: str | None = None
    GOOGLE_API_KEY: str | None = None

    # Default models per provider (override in .env if you like).
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # Lower temperature -> more consistent, less 'creative' scoring.
    LLM_TEMPERATURE: float = 0.2

    # Shared secret. When set, every request except the open paths (/health, /)
    # must send a matching X-Worker-Token header. Empty = check disabled.
    AI_WORKER_TOKEN: str = ""

    # --- Observability ----------------------------------------------------
    # Deploy environment label + optional Sentry error tracking.
    # SENTRY_DSN empty = disabled (worker runs fine without it).
    ENVIRONMENT: str = "development"
    SENTRY_DSN: str = ""

    # --- Langfuse LLM tracing (optional) ----------------------------------
    # When both keys are set, every LLM call (mentor/resume/ATS/scoring) is
    # traced to Langfuse. Empty = disabled (worker runs fine without it).
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"


settings = Settings()
