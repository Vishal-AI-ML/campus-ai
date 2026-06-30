"""Phase 4 RLS-foundation tests.

Real Postgres RLS (policies + FORCE ROW LEVEL SECURITY) can only run on
Postgres; this suite runs on SQLite, so here we only verify that the tenant-GUC
plumbing is a harmless no-op on non-Postgres backends and never breaks a
session.
"""

from sqlalchemy import text

from db import set_current_tenant
from models import UserRole
from security import apply_tenant_guc


def test_set_current_tenant_is_noop_on_sqlite(session):
    # On SQLite there is no set_config(); the helper must skip silently.
    set_current_tenant(session, 1)
    set_current_tenant(session, None)
    # And the session must remain perfectly usable afterwards.
    assert session.execute(text("SELECT 1")).scalar() == 1


def test_apply_tenant_guc_runs_clean(session, make_tenant, make_user):
    # The router-level RLS dependency must run without error on SQLite
    # (set_config is a no-op there) and leave the session usable.
    tenant = make_tenant(slug="rls-acme")
    admin = make_user(
        email="rls.admin@test.dev", role=UserRole.admin, tenant=tenant
    )
    apply_tenant_guc(current_user=admin, db=session)
    assert session.execute(text("SELECT 1")).scalar() == 1
