"""Alembic migration environment for Campus AI.

Customised so that:
  * the database URL comes from our app settings (.env) - NOT alembic.ini,
    so secrets never sit in a committed file;
  * Alembic sees our `Base.metadata` and every model, enabling --autogenerate.

This file REPLACES the default `alembic/env.py` created by `alembic init`.
It is run from the `backend/` folder, so `config`, `db`, and `models` import
cleanly.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# --- App imports -----------------------------------------------------------
from config import settings
from db import Base
import models  # noqa: F401  -> importing registers all tables on Base.metadata

# Alembic Config object (gives access to values in alembic.ini).
config = context.config

# Inject the real DB URL from settings. Escape '%' so ConfigParser does not
# treat it as interpolation (passwords can contain '%').
config.set_main_option(
    "sqlalchemy.url", settings.DATABASE_URL.replace("%", "%%")
)

# Configure Python logging from the ini file, if present.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for 'autogenerate' support.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations without a live DB connection (emits SQL)."""
    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live database connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
