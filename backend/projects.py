"""Projects routes - individual or group projects, verified per member.

Role model (same moat as skills, but credit is split per contributor):
  * STUDENT (any logged-in user) creates a project. They are auto-added as a
    member. For a group project they also list teammates + each one's
    contribution. Every member starts `pending`.
  * MENTOR (teacher role) reviews each member's contribution from the queue and
    verifies or flags it individually -> a freeloader never gets credit.
  * TEACHER/TPO can read a given student's project contributions (eligibility).

On create, a BackgroundTask asks the AI worker to score each member's
contribution and fill `ai_score` (advisory; the mentor still decides).

Mounted under the `/projects` prefix by `main.py`.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ai_client import score_project_members
from db import get_db
from models import Project, ProjectMember, SkillStatus, User, UserRole
from schemas import (
    ProjectCreate,
    ProjectMemberDecision,
    ProjectMemberOut,
    ProjectMemberQueueOut,
    ProjectOut,
)
from security import get_current_tenant_id, get_current_user, require_roles

router = APIRouter(prefix="/projects", tags=["projects"])

# Mentors are teachers; some reads are open to TPO too.
mentor_only = require_roles(UserRole.teacher)
staff_only = require_roles(UserRole.teacher, UserRole.tpo)


# --- Student: create & view own projects -----------------------------------
@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Project:
    """Create a project. You are added as a member automatically; for a group
    project, listed teammates are added too. Every member starts `pending` and
    is scored by the AI worker in the background."""
    # Map student_id -> contribution. The creator (owner) is always included.
    member_contribs: dict[int, str | None] = {current_user.id: "Owner"}
    if payload.is_group:
        for m in payload.members:
            if m.student_id == current_user.id:
                # Let the creator override their own contribution text.
                if m.contribution:
                    member_contribs[current_user.id] = m.contribution
                continue
            member_contribs[m.student_id] = m.contribution

    # Validate every referenced student exists AND belongs to the creator's
    # institute. A project is scoped to a single tenant, so a teammate from
    # another institute is rejected (cross-tenant data isolation).
    ids = list(member_contribs.keys())
    rows = db.execute(
        select(User.id, User.tenant_id).where(User.id.in_(ids))
    ).all()
    found = {uid for uid, _ in rows}
    missing = [i for i in ids if i not in found]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown student id(s): {missing}",
        )
    outsiders = [uid for uid, tid in rows if tid != current_user.tenant_id]
    if outsiders:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "All teammates must belong to your institute; "
                f"outside student id(s): {outsiders}"
            ),
        )

    project = Project(
        owner_id=current_user.id,
        tenant_id=current_user.tenant_id,
        title=payload.title,
        description=payload.description,
        tech_stack=payload.tech_stack,
        repo_url=payload.repo_url,
        demo_url=payload.demo_url,
        is_group=payload.is_group,
    )
    db.add(project)
    db.flush()  # assign project.id before creating members
    project_id = project.id  # capture now (survives commit / expiry)

    for sid, contribution in member_contribs.items():
        db.add(
            ProjectMember(
                project_id=project_id,
                tenant_id=current_user.tenant_id,
                student_id=sid,
                contribution=contribution,
                status=SkillStatus.pending,
            )
        )
    db.commit()

    # Fire-and-forget AI proof scoring for each member; never blocks the user.
    background_tasks.add_task(score_project_members, project_id)

    # Re-fetch with members eagerly loaded for the response.
    return db.scalar(
        select(Project)
        .where(Project.id == project_id)
        .options(selectinload(Project.members))
    )


@router.get("/me", response_model=list[ProjectOut])
def my_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Project]:
    """Projects the logged-in user is part of (owner or teammate)."""
    return list(
        db.scalars(
            select(Project)
            .join(ProjectMember, ProjectMember.project_id == Project.id)
            .where(
                ProjectMember.student_id == current_user.id,
                Project.tenant_id == current_user.tenant_id,
            )
            .options(selectinload(Project.members))
            .order_by(Project.created_at.desc())
        )
        .unique()
    )


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a project you own (its members are removed automatically)."""
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )
    if project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the project owner can delete it",
        )
    db.delete(project)
    db.commit()


# --- Mentor: review queue & per-member decisions ---------------------------
@router.get(
    "/queue",
    response_model=list[ProjectMemberQueueOut],
    dependencies=[Depends(mentor_only)],
)
def review_queue(
    status_filter: SkillStatus = SkillStatus.pending,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
) -> list[ProjectMemberQueueOut]:
    """Pending member-contributions to review, each with its project context.

    Tenant-scoped: a mentor only ever sees contributions from their own
    institute.
    """
    rows = db.execute(
        select(ProjectMember, Project.title, Project.repo_url)
        .join(Project, ProjectMember.project_id == Project.id)
        .where(
            ProjectMember.tenant_id == tenant_id,
            ProjectMember.status == status_filter,
        )
        .order_by(ProjectMember.created_at.asc())
    ).all()
    return [
        ProjectMemberQueueOut(
            member_id=pm.id,
            project_id=pm.project_id,
            project_title=title,
            repo_url=repo_url,
            student_id=pm.student_id,
            contribution=pm.contribution,
            status=pm.status,
        )
        for pm, title, repo_url in rows
    ]


@router.patch("/members/{member_id}/decision", response_model=ProjectMemberOut)
def decide_member(
    member_id: int,
    payload: ProjectMemberDecision,
    db: Session = Depends(get_db),
    mentor: User = Depends(mentor_only),
) -> ProjectMember:
    """Verify or flag one member's contribution. `pending` is not a valid target."""
    if payload.status not in (SkillStatus.verified, SkillStatus.flagged):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Decision must be 'verified' or 'flagged'",
        )
    member = db.get(ProjectMember, member_id)
    # Tenant guard: a mentor can only act on contributions from their own
    # institute. Treating a cross-tenant row as 404 also hides its existence.
    if member is None or member.tenant_id != mentor.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project member not found"
        )
    member.status = payload.status
    member.review_note = payload.review_note
    member.reviewed_by_id = mentor.id
    member.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(member)
    return member


# --- Staff: read a student's contributions (e.g. for eligibility) ----------
@router.get(
    "/student/{student_id}",
    response_model=list[ProjectMemberOut],
    dependencies=[Depends(staff_only)],
)
def student_contributions(
    student_id: int,
    status_filter: SkillStatus | None = None,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
) -> list[ProjectMember]:
    """List a student's project contributions (teacher/TPO). Filter by status,
    e.g. verified, for resume/eligibility use.

    Tenant-scoped: staff can only read students within their own institute.
    """
    stmt = select(ProjectMember).where(
        ProjectMember.student_id == student_id,
        ProjectMember.tenant_id == tenant_id,
    )
    if status_filter is not None:
        stmt = stmt.where(ProjectMember.status == status_filter)
    return list(db.scalars(stmt.order_by(ProjectMember.created_at.desc())))
