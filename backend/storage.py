"""File storage via Supabase Storage signed URLs (Section 7, Part B).

Why signed URLs?
----------------
The browser uploads/downloads files DIRECTLY to Supabase Storage - the file
bytes never pass through this API server. The backend only mints short-lived,
single-purpose signed URLs after doing auth + validation. The powerful
``service_role`` key stays server-side and is NEVER sent to the client.

Flow
----
  upload:   client -> POST /files/sign-upload  -> {upload_url, path, token}
            client -> PUT <upload_url> (raw file body)  -> file lands in bucket
            client saves ``path`` into the entity's existing *_url column
  download: client -> POST /files/sign-download {path} -> {download_url}
            client -> GET <download_url> (valid for a few minutes)

Env-gated (like Sentry/Langfuse): if the three SUPABASE_* settings are not all
configured, ``storage_enabled()`` is False and the /files routes return 503.
The rest of the app is completely unaffected, so this is safe to ship dark and
turn on later by setting env vars.
"""

from __future__ import annotations

import logging
import os
import re
import uuid

import httpx

from config import settings

logger = logging.getLogger("campus_ai.storage")

# Signing is a single quick round-trip to Supabase; keep the timeout tight so a
# storage hiccup can never hang a user's request for long.
_TIMEOUT = httpx.Timeout(15.0)

# Default lifetime for a download link. Short by design - the client mints a
# fresh one each time it needs to show/download a file.
DEFAULT_DOWNLOAD_EXPIRY = 60 * 10  # 10 minutes
_MAX_DOWNLOAD_EXPIRY = 60 * 60 * 24  # 24h hard cap

# Keep object paths clean + predictable across OSes: collapse anything that is
# not alnum/dot/dash/underscore, and never allow path traversal.
_SAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


class StorageError(RuntimeError):
    """Raised when Supabase Storage is misconfigured or returns an error."""


def storage_enabled() -> bool:
    """True only when all three Supabase settings are configured."""
    return bool(
        settings.SUPABASE_URL
        and settings.SUPABASE_SERVICE_KEY
        and settings.SUPABASE_STORAGE_BUCKET
    )


def _base_url() -> str:
    """Supabase project URL without a trailing slash."""
    return settings.SUPABASE_URL.rstrip("/")


def _bucket() -> str:
    return settings.SUPABASE_STORAGE_BUCKET


def _headers() -> dict[str, str]:
    """Auth headers for the Storage REST API (service_role key)."""
    key = settings.SUPABASE_SERVICE_KEY
    return {"Authorization": f"Bearer {key}", "apikey": key}


def sanitize_filename(filename: str) -> str:
    """Return a safe basename: no directories, no traversal, bounded length."""
    # Drop any directory component the client may have sent (both separators).
    base = os.path.basename(filename.replace("\\", "/")).strip()
    base = _SAFE_CHARS.sub("-", base).strip("-.") or "file"
    # Normalise the extension to lower-case so stored paths are predictable
    # (storage keys are case-sensitive; avoids ".PDF" vs ".pdf" mismatches).
    root, dot, ext = base.rpartition(".")
    if dot:
        base = f"{root}.{ext.lower()}"
    # Keep names reasonable; preserve the extension when we truncate.
    if len(base) > 120:
        root, _, ext = base.rpartition(".")
        base = (root[:100] + "." + ext) if ext else base[:120]
    return base


def build_object_path(tenant_id: int, kind: str, user_id: int, filename: str) -> str:
    """Tenant-scoped storage path: ``{tenant}/{kind}/{user}/{uuid}-{name}``.

    The leading ``{tenant_id}/`` prefix is the isolation boundary: download
    signing refuses any path that does not start with the caller's own tenant.
    """
    safe = sanitize_filename(filename)
    return f"{int(tenant_id)}/{kind}/{int(user_id)}/{uuid.uuid4().hex}-{safe}"


def create_signed_upload_url(path: str) -> dict[str, str]:
    """Ask Supabase for a one-time signed URL the client can PUT a file to.

    Returns ``{"path", "upload_url", "token"}``. Raises ``StorageError`` on any
    failure so the route can translate it into a clean 5xx.
    """
    if not storage_enabled():
        raise StorageError("storage_not_configured")
    url = f"{_base_url()}/storage/v1/object/upload/sign/{_bucket()}/{path}"
    try:
        resp = httpx.post(url, headers=_headers(), timeout=_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPError as exc:
        logger.warning("signed upload URL failed for %s: %s", path, exc)
        raise StorageError("signed_upload_failed") from exc
    # REST returns {"url": "/object/upload/sign/<bucket>/<path>?token=<jwt>"}.
    relative = data.get("url") or ""
    if not relative:
        raise StorageError("signed_upload_failed")
    upload_url = (
        f"{_base_url()}/storage/v1{relative}"
        if relative.startswith("/")
        else relative
    )
    # The token is embedded in the query string; expose it too so a client that
    # prefers supabase-js `uploadToSignedUrl(path, token, file)` can use it.
    token = ""
    if "token=" in relative:
        token = relative.split("token=", 1)[1]
    return {"path": path, "upload_url": upload_url, "token": token}


def create_signed_download_url(
    path: str, expires_in: int = DEFAULT_DOWNLOAD_EXPIRY
) -> str:
    """Return a short-lived signed URL to GET a private object."""
    if not storage_enabled():
        raise StorageError("storage_not_configured")
    expires_in = max(1, min(int(expires_in), _MAX_DOWNLOAD_EXPIRY))
    url = f"{_base_url()}/storage/v1/object/sign/{_bucket()}/{path}"
    try:
        resp = httpx.post(
            url, headers=_headers(), json={"expiresIn": expires_in}, timeout=_TIMEOUT
        )
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPError as exc:
        logger.warning("signed download URL failed for %s: %s", path, exc)
        raise StorageError("signed_download_failed") from exc
    # REST returns {"signedURL": "/object/sign/<bucket>/<path>?token=<jwt>"}.
    relative = data.get("signedURL") or data.get("signedUrl") or ""
    if not relative:
        raise StorageError("signed_download_failed")
    return (
        f"{_base_url()}/storage/v1{relative}"
        if relative.startswith("/")
        else relative
    )
