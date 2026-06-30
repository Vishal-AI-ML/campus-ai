"""Database layer: engine, session factory, and the declarative base.

Everything that talks to Postgres goes through here so we have a single,
consistent connection setup (SQLAlchemy 2.x style).
"""

from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from config import settings

# `pool_pre_ping` checks a connection is alive before using it - important for
# cloud databases (like Supabase) that may close idle connections.
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, future=True)

# Session factory. Each request gets its own short-lived session (see get_db).
SessionLocal = sessionmaker(
    bind=engine, autoflush=False, autocommit=False, future=True
)

# Base class that all ORM models will inherit from (users, attendance, ...).
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a DB session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def set_current_tenant(db: Session, tenant_id: int | None) -> None:
    """Set the per-session Postgres GUC used by Row-Level Security (Phase 4).

    RLS policies read ``app.current_tenant_id()`` which in turn reads the
    ``app.current_tenant_id`` connection setting. We set it **session-wide**
    (``set_config(..., is_local => false)``) so it survives the commits a single
    request may issue. Pass ``None`` to clear it (empty string, which
    ``app.current_tenant_id()`` maps back to NULL).

    No-op on non-Postgres backends (the SQLite test DB has no ``set_config``),
    so it is always safe to call.
    """
    bind = db.get_bind()
    if bind is None or bind.dialect.name != "postgresql":
        return
    db.execute(
        text("SELECT set_config('app.current_tenant_id', :tid, false)"),
        {"tid": "" if tenant_id is None else str(tenant_id)},
    )
