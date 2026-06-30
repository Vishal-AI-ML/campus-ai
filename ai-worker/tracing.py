"""Langfuse LLM tracing for the AI worker (optional, env-gated).

Mirrors the Sentry pattern in observability.py: tracing only turns ON when the
LANGFUSE_* env vars are set. With no keys, `trace_config()` returns an empty
RunnableConfig, so every LLM call behaves EXACTLY as before and neither the
`langfuse` package nor any network call is required (local / CI safe).

Enable in production by `uv add langfuse` and setting on the worker:
    LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY,
    LANGFUSE_HOST (optional, defaults to Langfuse Cloud)

Then every mentor / resume / ATS / proof-scoring LLM call shows up as a trace
in your Langfuse project (prompt, completion, latency, token usage).

Location:
    E:\\campus-ai\\ai-worker\\tracing.py
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger("campus_ai.tracing")

_initialized = False
_enabled = False
_handler: Any = None  # cached LangChain CallbackHandler when tracing is on


def _present(*values: str | None) -> bool:
    """True only when every value is a non-empty, non-whitespace string."""
    return all(bool(v and v.strip()) for v in values)


def init_tracing(public_key: str, secret_key: str, host: str = "") -> bool:
    """Set up Langfuse tracing once. Returns True if enabled.

    No-op (returns False) unless BOTH keys are provided. The `langfuse` package
    is imported lazily so it is only needed when tracing is actually on. Any
    failure here is swallowed (logged) so tracing can never break the worker.
    """
    global _initialized, _enabled, _handler
    if _initialized:
        return _enabled
    _initialized = True

    if not _present(public_key, secret_key):
        logger.info("Langfuse tracing disabled (no LANGFUSE keys set).")
        return False

    try:
        # The Langfuse client reads these env vars; set them so BOTH SDK
        # versions (v2 and v3) pick up the same config regardless of import
        # path below.
        os.environ.setdefault("LANGFUSE_PUBLIC_KEY", public_key)
        os.environ.setdefault("LANGFUSE_SECRET_KEY", secret_key)
        if host and host.strip():
            os.environ.setdefault("LANGFUSE_HOST", host.strip())

        # langfuse >= 3 moved the handler; fall back to the v2 import path.
        try:
            from langfuse.langchain import CallbackHandler
        except ImportError:  # pragma: no cover - depends on installed version
            from langfuse.callback import CallbackHandler

        _handler = CallbackHandler()
        _enabled = True
        logger.info("Langfuse tracing enabled (host=%s).", host or "default")
    except Exception as exc:  # noqa: BLE001 - tracing must never break the app
        _enabled = False
        _handler = None
        logger.warning(
            "Langfuse tracing init failed (%s); continuing without it.", exc
        )
    return _enabled


def tracing_enabled() -> bool:
    """Whether Langfuse tracing is currently active."""
    return _enabled


def trace_config(name: str, **metadata: Any) -> dict[str, Any]:
    """Return a LangChain RunnableConfig that traces this call to Langfuse.

    Pass it straight into `.invoke(messages, config=trace_config("mentor_chat"))`.
    When tracing is disabled it returns ``{}`` - an empty RunnableConfig - so the
    call is byte-for-byte the same behavior as before (no callback, no overhead).
    """
    if not _enabled or _handler is None:
        return {}
    config: dict[str, Any] = {"callbacks": [_handler], "run_name": name}
    if metadata:
        config["metadata"] = metadata
    return config
