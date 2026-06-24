"""Database layer: engine, session factory, and the declarative base.

Everything that talks to Postgres goes through here so we have a single,
consistent connection setup (SQLAlchemy 2.x style).
"""

from collections.abc import Generator

from sqlalchemy import create_engine
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
