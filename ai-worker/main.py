"""Campus AI - AI Worker service entrypoint.

A SEPARATE FastAPI service (port 8100), decoupled from the main backend
(port 8000), that hosts the heavy/latency-prone AI work:
  * proof scoring for skills & project contributions (fills `ai_score`)
  * AI career mentor: grounded chat over the student's VERIFIED profile,
    augmented with vector RAG over a career knowledge base (in-process Chroma)
  * AI resume builder (from the verified profile) + ATS scoring vs a job description
  * face attendance: detect + embed faces (InsightFace) and match a class
    photo against enrolled students stored in Qdrant (teacher confirms result)

Provider-agnostic chat: switch between Groq and Gemini via LLM_PROVIDER in .env.
RAG embeddings run locally (Chroma's built-in model) - no extra key or service.

Location:
    E:\\campus-ai\\ai-worker\\main.py

Run (from the ai-worker folder):
    uv run uvicorn main:app --reload --port 8100
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from config import settings
from observability import (
    init_sentry,
    request_logging_middleware,
    setup_logging,
)
from face import router as face_router
from mentor import router as mentor_router
from resume import router as resume_router
from scoring import router as scoring_router

# --- Observability: structured logging + (optional) Sentry --------------
# setup_logging() => one JSON log line per request; init_sentry() only turns
# on when SENTRY_DSN is set, so local/CI runs need no DSN or extra package.
WORKER_VERSION = "0.7.0"
setup_logging()
init_sentry(
    settings.SENTRY_DSN,
    settings.ENVIRONMENT,
    release=f"campus-ai-worker@{WORKER_VERSION}",
)

app = FastAPI(title="Campus AI - AI Worker", version=WORKER_VERSION)

# Log every request (method, path, status, duration_ms, request_id).
app.middleware("http")(request_logging_middleware)

# Endpoints that stay open (no token): liveness, sanity, API docs. CORS
# preflight (OPTIONS) is also allowed through. Everything else requires the
# shared secret WHEN one is configured (AI_WORKER_TOKEN set).
_OPEN_PATHS = {"/", "/health", "/docs", "/openapi.json", "/redoc"}


@app.middleware("http")
async def _verify_worker_token(request: Request, call_next):
    token = settings.AI_WORKER_TOKEN
    if token and request.method != "OPTIONS" and request.url.path not in _OPEN_PATHS:
        if request.headers.get("X-Worker-Token") != token:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or missing worker token"},
            )
    return await call_next(request)


app.include_router(scoring_router)
app.include_router(mentor_router)
app.include_router(resume_router)
app.include_router(face_router)


@app.get("/")
def root() -> dict:
    """Quick sanity check that the AI worker process is alive."""
    return {
        "service": "campus-ai-ai-worker",
        "status": "ok",
        "llm_provider": settings.LLM_PROVIDER,
    }


@app.get("/health")
def health() -> dict:
    """Liveness probe for deploys/monitoring."""
    return {"status": "healthy"}
