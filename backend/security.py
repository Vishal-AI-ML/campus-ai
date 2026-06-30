"""Security helpers: password hashing (bcrypt), JWT handling, and RBAC deps.

  * hash_password / verify_password - bcrypt
  * create_access_token             - issue a signed JWT
  * get_current_user                - resolve the logged-in user from a token
  * get_current_tenant_id           - the tenant the logged-in user belongs to
  * require_roles(*roles)           - dependency factory for role-gated routes
"""

from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from config import settings
from db import get_db, set_current_tenant
from models import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

_BCRYPT_MAX_BYTES = 72  # bcrypt only hashes the first 72 bytes of input


def hash_password(password: str) -> str:
    """Return a salted bcrypt hash of the given plaintext password."""
    pw = password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    return bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Check a plaintext password against a stored bcrypt hash."""
    pw = plain.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    return bcrypt.checkpw(pw, hashed.encode("utf-8"))


def create_access_token(subject: str) -> str:
    """Create a signed JWT whose `sub` claim identifies the user."""
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Decode the bearer token and return the matching active user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        subject = payload.get("sub")
        if subject is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.get(User, int(subject))
    if user is None or not user.is_active:
        raise credentials_exception
    return user


def get_current_tenant_id(current_user: User = Depends(get_current_user)) -> int:
    """Return the tenant id of the logged-in user.

    This is the single source of truth for "which institute is this request
    for?". Routes that read or write tenant-scoped data should depend on this
    and filter every query with ``WHERE tenant_id == <this value>`` so one
    institute can never see or touch another institute's data.

    Usage:
        @router.get("/skills")
        def list_skills(
            tenant_id: int = Depends(get_current_tenant_id),
            db: Session = Depends(get_db),
        ):
            return db.query(Skill).filter(Skill.tenant_id == tenant_id).all()
    """
    return current_user.tenant_id


def require_roles(*allowed_roles: UserRole):
    """Build a dependency that allows only users with one of `allowed_roles`.

    Usage:
        admin_only = require_roles(UserRole.admin)
        @router.post(..., dependencies=[Depends(admin_only)])
    """

    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return current_user

    return role_checker


def apply_tenant_guc(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Publish the caller's tenant into the DB session for Postgres RLS (Phase 4).

    Add this as a router-level dependency on tenant-scoped routers
    (``APIRouter(..., dependencies=[Depends(apply_tenant_guc)])``) so every
    authenticated request stamps its institute onto the session via
    ``set_current_tenant`` *before* the route's queries run. FastAPI caches
    ``Depends(get_db)`` per request, so this runs on the SAME session the route
    uses - no contextvars, no threadpool-propagation pitfalls. No-op on
    non-Postgres backends, so it is safe everywhere.
    """
    set_current_tenant(db, current_user.tenant_id)
