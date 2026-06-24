"""Backend -> AI worker client (Simple HTTP integration).

Two kinds of calls:
  * proof scoring (skills/projects) -> runs in a BackgroundTask, fills `ai_score`
  * mentor chat -> runs synchronously in the request (the user awaits a reply)

We use our OWN database session for background work, because the request-scoped
session from `get_db` is already closed by the time a background task runs.

No message broker/queue yet; that's a later upgrade (Celery+Redis) for
bulk/retry/heavy workloads.
"""

from __future__ import annotations

import logging

import httpx
from sqlalchemy import select

from config import settings
from db import SessionLocal
from models import Project, ProjectMember, Skill

logger = logging.getLogger("campus_ai.ai_client")

# Scoring is one quick LLM round-trip; mentor chat can take a little longer.
_SCORE_TIMEOUT = httpx.Timeout(30.0)
_CHAT_TIMEOUT = httpx.Timeout(60.0)


def _request_score(
    claim_type: str,
    title: str,
    evidence_url: str | None,
    evidence_note: str | None,
) -> int | None:
    """Call the worker's /score/proof. Returns the 0-100 score, or None on error.

    Failures are swallowed (logged only): a missing AI score must never break
    the user's create/claim flow - the mentor can still verify manually.
    """
    try:
        resp = httpx.post(
            f"{settings.AI_WORKER_URL}/score/proof",
            json={
                "claim_type": claim_type,
                "title": title,
                "evidence_url": evidence_url,
                "evidence_note": evidence_note,
            },
            timeout=_SCORE_TIMEOUT,
        )
        resp.raise_for_status()
        return int(resp.json()["score"])
    except Exception as exc:  # noqa: BLE001 - best-effort, never fatal
        logger.warning("AI worker scoring failed (%s): %s", title, exc)
        return None


def score_skill(skill_id: int) -> None:
    """Background task: score one skill claim and persist its `ai_score`."""
    db = SessionLocal()
    try:
        skill = db.get(Skill, skill_id)
        if skill is None:
            return
        score = _request_score(
            "skill", skill.name, skill.evidence_url, skill.evidence_note
        )
        if score is not None:
            skill.ai_score = score
            db.commit()
    finally:
        db.close()


def score_project_members(project_id: int) -> None:
    """Background task: score every member's contribution on a project.

    Each member is scored individually (with the project as context) so the
    per-member verification stays meaningful.
    """
    db = SessionLocal()
    try:
        project = db.get(Project, project_id)
        if project is None:
            return
        members = list(
            db.scalars(
                select(ProjectMember).where(ProjectMember.project_id == project_id)
            )
        )
        for member in members:
            title = f"{project.title} - {member.contribution or 'contribution'}"
            score = _request_score(
                "project", title, project.repo_url, member.contribution
            )
            if score is not None:
                member.ai_score = score
        db.commit()
    finally:
        db.close()


def ask_mentor(
    profile: dict, question: str, history: list[dict]
) -> dict | None:
    """Synchronous mentor chat: send the verified profile + question to the
    worker and return its JSON reply ({answer, provider}), or None on error.
    """
    try:
        resp = httpx.post(
            f"{settings.AI_WORKER_URL}/mentor/chat",
            json={"profile": profile, "question": question, "history": history},
            timeout=_CHAT_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning("AI mentor chat failed: %s", exc)
        return None
