"""Shared pytest fixtures for the Campus AI backend test-suite.

Design notes
------------
* Tests run against a THROWAWAY SQLite database (a temp file), never the real
  Supabase Postgres. We set DATABASE_URL to that SQLite file *before* the app's
  config/db modules are imported, so the app's own engine + SessionLocal point
  at the test DB. The ORM models are dialect-neutral (generic Enum, func.now(),
  no JSONB/ARRAY), so the schema builds cleanly on SQLite via create_all.
* The schema is rebuilt before every test for full isolation.
* Staff/admin users are inserted directly (the public /auth/register endpoint
  deliberately only ever creates students), then we mint a real JWT via
  /auth/login through the API.
* The skill-claim background AI-worker call is monkeypatched to a no-op so the
  suite stays offline and deterministic.
"""

import os
import tempfile

# --- Point the app at a throwaway SQLite DB BEFORE importing its modules -----
# config.Settings requires DATABASE_URL; an env var wins over any local .env, so
# this guarantees tests never touch the real Supabase database.
_TMP_DB = os.path.join(tempfile.gettempdir(), "campus_ai_test.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP_DB}"
os.environ.setdefault("SECRET_KEY", "test-secret-not-for-prod")
os.environ.setdefault("AI_WORKER_TOKEN", "")
os.environ.setdefault("ENVIRONMENT", "test")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import db  # noqa: E402
import models  # noqa: E402  (importing registers every ORM table on db.Base)
import skills  # noqa: E402
from main import app  # noqa: E402
from rate_limit import limiter  # noqa: E402
from security import hash_password  # noqa: E402


def _reset_rate_limiter() -> None:
    """Clear slowapi's in-memory counters so each test starts with a fresh quota."""
    for attr in ("_storage", "storage"):
        store = getattr(limiter, attr, None)
        if store is not None and hasattr(store, "reset"):
            try:
                store.reset()
            except Exception:
                pass


@pytest.fixture(autouse=True)
def _fresh_state(monkeypatch):
    """Rebuild the schema and reset global state before/after every test."""
    # Offline, deterministic skill claims (no AI-worker HTTP call in the bg task).
    monkeypatch.setattr(skills, "score_skill", lambda *args, **kwargs: None)
    _reset_rate_limiter()
    db.Base.metadata.drop_all(bind=db.engine)
    db.Base.metadata.create_all(bind=db.engine)
    yield
    db.Base.metadata.drop_all(bind=db.engine)


@pytest.fixture
def client() -> TestClient:
    """A FastAPI test client backed by the throwaway SQLite database."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def session():
    """A direct DB session for seeding rows the public API cannot create."""
    db_session = db.SessionLocal()
    try:
        yield db_session
    finally:
        db_session.close()


@pytest.fixture
def make_user(session):
    """Factory that inserts a user with any role (staff can't be self-registered).

    Multi-tenancy: every user MUST belong to a tenant (users.tenant_id is NOT
    NULL). Callers may pass an explicit ``tenant``; otherwise we get-or-create a
    shared "default" institute so existing single-tenant tests keep working
    unchanged - mirroring how real code paths always set a tenant.
    """

    def _make(
        email,
        *,
        password="secret123",
        role=models.UserRole.student,
        full_name="Test User",
        is_active=True,
        tenant=None,
    ):
        if tenant is None:
            tenant = session.query(models.Tenant).filter_by(slug="default").first()
            if tenant is None:
                tenant = models.Tenant(
                    name="Default Institute", slug="default", is_active=True
                )
                session.add(tenant)
                session.commit()
                session.refresh(tenant)
        user = models.User(
            email=email,
            full_name=full_name,
            hashed_password=hash_password(password),
            role=role,
            is_active=is_active,
            tenant_id=tenant.id,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user

    return _make


@pytest.fixture
def make_tenant(session):
    """Factory that inserts a tenant (institute) for tenant-scoped signup tests."""

    def _make(slug="acme", *, name="Acme Institute", is_active=True):
        tenant = models.Tenant(name=name, slug=slug, is_active=is_active)
        session.add(tenant)
        session.commit()
        session.refresh(tenant)
        return tenant

    return _make


@pytest.fixture
def token_header(client):
    """Factory that logs a user in and returns an Authorization header."""

    def _header(email, password="secret123"):
        resp = client.post(
            "/auth/login", data={"username": email, "password": password}
        )
        assert resp.status_code == 200, resp.text
        return {"Authorization": f"Bearer {resp.json()['access_token']}"}

    return _header
