"""Observability: structured request logging + (optional) Sentry error tracking.

Why this exists
---------------
Once the product is live, unhandled errors and slow requests are otherwise
*invisible* - you only hear about them when a user complains. This module gives
you two cheap, always-on signals:

1. **Structured access log** - one JSON line per HTTP request (method, path,
   status, duration_ms, request_id). Log shippers (Render logs, Logtail, etc.)
   can parse these directly, and the per-request `request_id` lets you trace a
   single call end-to-end.
2. **Sentry** - captures every unhandled exception with a full stack trace +
   request context, and a sample of performance traces.

Sentry is OPTIONAL: it only initialises when `SENTRY_DSN` is set. With no DSN
(local dev, CI, or before you sign up) the app runs exactly as before and the
`sentry_sdk` package is never even imported. Turn it on later by setting
`SENTRY_DSN` in the host env - no code change needed.

Location:
    E:\\campus-ai\\backend\\observability.py   (identical copy in ai-worker/)
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from contextvars import ContextVar

# Holds the current request's id so log lines emitted anywhere during the
# request (not just the access log) can be correlated.
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


class _JsonFormatter(logging.Formatter):
    """Render log records as single-line JSON (easy to grep/ship/parse)."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": request_id_ctx.get(),
        }
        extra = getattr(record, "extra_fields", None)
        if isinstance(extra, dict):
            payload.update(extra)
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def setup_logging(level: int = logging.INFO) -> None:
    """Route the root logger through a single JSON stdout handler."""
    handler = logging.StreamHandler()
    handler.setFormatter(_JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
    # uvicorn's own access log is noisy + unstructured; our middleware already
    # logs every request, so silence the duplicate.
    logging.getLogger("uvicorn.access").handlers = []
    logging.getLogger("uvicorn.access").propagate = False


def init_sentry(
    dsn: str | None,
    environment: str = "development",
    release: str | None = None,
) -> bool:
    """Initialise Sentry IFF a DSN is configured. Returns True when enabled.

    Imports `sentry_sdk` lazily so the dependency is only needed in
    environments that actually set a DSN.
    """
    if not dsn:
        return False
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.starlette import StarletteIntegration

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=release,
        integrations=[StarletteIntegration(), FastApiIntegration()],
        # 10% of requests get a performance trace - enough to spot slow routes
        # without blowing the free-tier quota. Tune via taste/quota.
        traces_sample_rate=0.1,
        # Never ship personally identifiable info (emails, tokens) by default.
        send_default_pii=False,
    )
    return True


_access_logger = logging.getLogger("campus.request")


async def request_logging_middleware(request, call_next):
    """ASGI middleware: assign a request_id, time the request, log one line.

    Register with: `app.middleware("http")(request_logging_middleware)`.
    Echoes the id back as the `X-Request-ID` response header so a client/user
    can quote it in a bug report and you can find the exact log line.
    """
    rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
    token = request_id_ctx.set(rid)
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        duration_ms = round((time.perf_counter() - start) * 1000, 1)
        _access_logger.exception(
            "request_failed",
            extra={
                "extra_fields": {
                    "method": request.method,
                    "path": request.url.path,
                    "status": 500,
                    "duration_ms": duration_ms,
                }
            },
        )
        request_id_ctx.reset(token)
        raise
    duration_ms = round((time.perf_counter() - start) * 1000, 1)
    _access_logger.info(
        "request",
        extra={
            "extra_fields": {
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
            }
        },
    )
    response.headers["X-Request-ID"] = rid
    request_id_ctx.reset(token)
    return response
