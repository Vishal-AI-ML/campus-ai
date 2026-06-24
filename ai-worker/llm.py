"""LLM factory - returns a LangChain chat model for the configured provider.

Keeping this in one place means the rest of the worker (scoring, mentor, future
LangGraph agents) never cares which provider is active - just call
`get_chat_model()`.

Location:
    E:\\campus-ai\\ai-worker\\llm.py
"""

from functools import lru_cache

from langchain_core.language_models.chat_models import BaseChatModel

from config import settings


@lru_cache(maxsize=1)
def get_chat_model() -> BaseChatModel:
    """Build (once) the chat model for `settings.LLM_PROVIDER`.

    Imports are done lazily so you only need the SDK / key for the provider you
    actually use.
    """
    provider = settings.LLM_PROVIDER.strip().lower()

    if provider == "groq":
        from langchain_groq import ChatGroq

        if not settings.GROQ_API_KEY:
            raise RuntimeError("GROQ_API_KEY is not set (.env) but LLM_PROVIDER=groq")
        return ChatGroq(
            model=settings.GROQ_MODEL,
            api_key=settings.GROQ_API_KEY,
            temperature=settings.LLM_TEMPERATURE,
        )

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        if not settings.GOOGLE_API_KEY:
            raise RuntimeError(
                "GOOGLE_API_KEY is not set (.env) but LLM_PROVIDER=gemini"
            )
        return ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=settings.LLM_TEMPERATURE,
        )

    raise ValueError(
        f"Unknown LLM_PROVIDER {settings.LLM_PROVIDER!r} (use 'groq' or 'gemini')"
    )
