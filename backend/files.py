"""File upload/download signing routes (Section 7, Part B).

These endpoints never touch the file bytes. The browser talks to Supabase
Storage directly using the short-lived signed URLs minted here; the backend
just does auth + validation + tenant-scoped path construction.

  POST /files/sign-upload    -> {path, upload_url, token}
  POST /files/sign-download  -> {download_url, expires_in}

When Supabase is not configured (storage_enabled() is False) both routes return
503 so the feature can ship dark and be switched on later via env vars.
"""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

import storage
from models import User
from security import get_current_user

router = APIRouter(prefix="/files", tags=["files"])

# Allowed file kinds -> permitted extensions. The `kind` becomes part of the
# storage path and gates what a caller may upload. Keep this conservative;
# widen deliberately as new upload surfaces are added.
ALLOWED_EXTENSIONS: dict[str, set[str]] = {
    "certificate": {".pdf", ".jpg", ".jpeg", ".png", ".webp"},
    "proof": {".pdf", ".jpg", ".jpeg", ".png", ".webp"},
    "resume": {".pdf"},
    "material": {
        ".pdf", ".ppt", ".pptx", ".doc", ".docx",
        ".txt", ".csv", ".zip", ".png", ".jpg", ".jpeg",
    },
}


class SignUploadIn(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    kind: str = Field(min_length=1, max_length=32)


class SignUploadOut(BaseModel):
    path: str
    upload_url: str
    token: str


class SignDownloadIn(BaseModel):
    path: str = Field(min_length=1, max_length=512)
    expires_in: int | None = Field(default=None, ge=1, le=86_400)


class SignDownloadOut(BaseModel):
    download_url: str
    expires_in: int


def _require_storage() -> None:
    if not storage.storage_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="File storage is not configured on this server.",
        )


@router.post("/sign-upload", response_model=SignUploadOut)
def sign_upload(
    payload: SignUploadIn,
    current_user: User = Depends(get_current_user),
) -> SignUploadOut:
    """Mint a one-time signed URL the caller can PUT a single file to.

    The returned ``path`` is tenant-scoped; the client stores it in the
    entity's existing ``*_url`` column and later calls /sign-download to view.
    """
    _require_storage()

    kind = payload.kind.strip().lower()
    allowed = ALLOWED_EXTENSIONS.get(kind)
    if allowed is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported upload kind '{payload.kind}'.",
        )

    ext = os.path.splitext(payload.filename)[1].lower()
    if ext not in allowed:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"File type '{ext or 'unknown'}' is not allowed for {kind}. "
                f"Allowed: {', '.join(sorted(allowed))}."
            ),
        )

    path = storage.build_object_path(
        tenant_id=current_user.tenant_id,
        kind=kind,
        user_id=current_user.id,
        filename=payload.filename,
    )
    try:
        signed = storage.create_signed_upload_url(path)
    except storage.StorageError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not create an upload URL. Please try again.",
        )
    return SignUploadOut(**signed)


@router.post("/sign-download", response_model=SignDownloadOut)
def sign_download(
    payload: SignDownloadIn,
    current_user: User = Depends(get_current_user),
) -> SignDownloadOut:
    """Return a short-lived URL to view/download a stored file.

    Tenant isolation: the path MUST start with the caller's own
    ``{tenant_id}/`` prefix, so one institute can never sign another's files.
    """
    _require_storage()

    path = payload.path.lstrip("/")
    prefix = f"{current_user.tenant_id}/"
    if ".." in path or not path.startswith(prefix):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this file.",
        )

    expires_in = payload.expires_in or storage.DEFAULT_DOWNLOAD_EXPIRY
    try:
        url = storage.create_signed_download_url(path, expires_in)
    except storage.StorageError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not create a download URL. Please try again.",
        )
    return SignDownloadOut(download_url=url, expires_in=expires_in)
