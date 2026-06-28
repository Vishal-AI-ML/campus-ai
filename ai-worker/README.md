---
title: Campus AI Worker
emoji: 🤖
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# Campus AI — AI Worker

A FastAPI microservice that powers Campus AI's AI features:

- **Proof scoring** for skills & project contributions (LLM)
- **AI Career Mentor** — grounded chat over the student's verified profile (RAG, in-process Chroma)
- **AI Resume builder** + ATS scoring vs a job description
- **Face attendance** — detect/embed faces (InsightFace) and match against enrolled students (Qdrant)

## Configuration (Space Secrets)

Set these under **Settings → Variables and secrets** (never commit keys):

| Name | Type | Required |
|------|------|----------|
| `GROQ_API_KEY` | secret | yes (if `LLM_PROVIDER=groq`) |
| `QDRANT_URL` | secret | yes (face) |
| `QDRANT_API_KEY` | secret | yes (face) |
| `LLM_PROVIDER` | variable | optional (default `groq`) |
| `GROQ_MODEL` | variable | optional |
| `GOOGLE_API_KEY` | secret | optional (if using Gemini) |
| `GEMINI_MODEL` | variable | optional |

Health check: `GET /health`. API docs: `/docs`.
