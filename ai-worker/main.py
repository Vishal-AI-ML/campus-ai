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

from fastapi import FastAPI

from config import settings
from face import router as face_router
from mentor import router as mentor_router
from resume import router as resume_router
from scoring import router as scoring_router

app = FastAPI(title="Campus AI - AI Worker", version="0.6.0")

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
