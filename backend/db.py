"""Database layer: engine, session factory, and the declarative base.

Everything that talks to Postgres goes through here so we have a single,
consistent connection setup (SQLAlchemy 2.x style).
"""

from collections.abc import Generator

from sqlalchemy import create_engine, event, text
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


# Key under which the request's tenant is stashed on the Session so it can be
# re-applied to EVERY transaction that Session opens (see the listener below).
_TENANT_KEY = "current_tenant_id"


def _guc_params(tenant_id: int | None) -> dict[str, str]:
    # app.current_tenant_id() maps the empty string back to NULL (no tenant).
    return {"tid": "" if tenant_id is None else str(tenant_id)}


def set_current_tenant(db: Session, tenant_id: int | None) -> None:
    """Publish the caller's institute for Postgres Row-Level Security (Phase 4).

    RLS policies read ``app.current_tenant_id`` - a per-CONNECTION setting. The
    subtlety that bit us: a Session hands its connection back to the pool on
    every ``commit()`` and may grab a *different* connection for the next
    statement, so a value set just once does not reliably follow the Session.
    That broke commit-then-refresh under RLS: the refresh SELECT ran on a fresh
    connection with no tenant set, saw zero rows, and raised
    "Could not refresh instance".

    Fix: remember the tenant on ``session.info`` and re-apply it at the start of
    EVERY transaction via the ``after_begin`` listener below, using
    ``SET LOCAL`` (transaction-scoped, so nothing leaks onto pooled
    connections). We also apply it now for the transaction already in flight.
    No-op on non-Postgres backends (e.g. the SQLite test DB).
    """
    db.info[_TENANT_KEY] = tenant_id
    bind = db.get_bind()
    if bind is None or bind.dialect.name != "postgresql":
        return
    db.execute(
        text("SELECT set_config('app.current_tenant_id', :tid, true)"),
        _guc_params(tenant_id),
    )


@event.listens_for(SessionLocal, "after_begin")
def _reapply_tenant_guc(session: Session, transaction, connection) -> None:
    """Re-stamp the tenant GUC whenever the Session opens a new transaction.

    A Session may run successive transactions on different pooled connections
    (e.g. the SELECT that ``refresh()`` issues after a ``commit()``); this makes
    every one of them satisfy RLS. No-op until a tenant has been set and on
    non-Postgres backends.
    """
    if _TENANT_KEY not in session.info:
        return
    if connection.dialect.name != "postgresql":
        return
    connection.execute(
        text("SELECT set_config('app.current_tenant_id', :tid, true)"),
        _guc_params(session.info[_TENANT_KEY]),
    )
