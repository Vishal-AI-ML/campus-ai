"""Upload hardening: size + type + magic-byte validation for user files.

Production hardening (§7): never let an oversized or wrong-type file reach the
DB, the AI worker, or a heavy parser. Two upload surfaces exist in this app:

  * multipart file uploads (admin bulk-CSV import)
      -> `read_csv_upload(file)`  (validates type, reads with a size cap)
  * base64-encoded images inside JSON bodies (face enroll / class-photo
    attendance)
      -> `validate_base64_image(b64)`  (size cap + magic-byte sniff)

All failures raise a clean HTTP 4xx (413 too-large / 415 wrong-type /
400 malformed) so the caller gets a precise, actionable error.

Location:
    E:\\campus-ai\\backend\\uploads.py
"""

from __future__ import annotations

import base64
import binascii

from fastapi import HTTPException, UploadFile, status

# --- size caps --------------------------------------------------------------
KB = 1024
MB = 1024 * KB

MAX_CSV_BYTES = 2 * MB  # admin bulk user import
MAX_IMAGE_BYTES = 8 * MB  # face enroll / class photo

# Browsers/clients send inconsistent content types for .csv; accept the common
# ones (and the generic fallbacks) - the real gate is the .csv extension + the
# UTF-8 decode that the caller already performs.
_CSV_CONTENT_TYPES = {
    "text/csv",
    "application/csv",
    "application/vnd.ms-excel",
    "text/plain",
    "application/octet-stream",
}


def _too_large(max_bytes: int) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        detail=f"File too large (max {max_bytes // MB} MB).",
    )


# --- multipart uploads (CSV) ------------------------------------------------
def _validate_csv_type(file: UploadFile) -> None:
    name = (file.filename or "").lower()
    if not name.endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only .csv files are accepted.",
        )
    ctype = (file.content_type or "").split(";")[0].strip().lower()
    if ctype and ctype not in _CSV_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported content type for a CSV upload: {ctype}",
        )


async def read_csv_upload(
    file: UploadFile, *, max_bytes: int = MAX_CSV_BYTES
) -> bytes:
    """Validate a multipart CSV upload and return its raw bytes.

    Enforces the .csv extension + an allowed content type, then streams the
    file in chunks, aborting with HTTP 413 the moment it exceeds `max_bytes`
    (so we never buffer a giant upload into memory).
    """
    _validate_csv_type(file)

    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(64 * KB)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise _too_large(max_bytes)
        chunks.append(chunk)
    return b"".join(chunks)


# --- base64 images (face enroll / class photo) ------------------------------
def _sniff_image(data: bytes) -> str | None:
    """Return the image kind from its magic bytes, or None if unrecognised.

    Sniffs the ACTUAL content so a renamed/disguised file (e.g. an executable
    claiming to be a .png) is rejected. Covers the formats OpenCV/InsightFace
    decode on the worker side: JPEG, PNG, WebP.
    """
    if data[:3] == b"\xff\xd8\xff":
        return "jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def validate_base64_image(
    data_b64: str, *, max_bytes: int = MAX_IMAGE_BYTES
) -> bytes:
    """Validate a base64-encoded image and return its decoded bytes.

    Steps: strip an optional `data:` URI prefix + whitespace, guard the size
    BEFORE decoding (base64 is ~4/3 of the raw size), decode strictly, enforce
    the size again on the raw bytes, then sniff the magic bytes. Raises
    413 (too large), 400 (malformed base64) or 415 (not a supported image).

    Note: callers can keep forwarding the original base64 string to the AI
    worker - this is purely a safety gate, not a transform.
    """
    s = data_b64.strip()
    if s.startswith("data:"):
        comma = s.find(",")
        if comma != -1:
            s = s[comma + 1 :]
    # Drop any embedded whitespace/newlines so strict decoding won't false-fail.
    s = "".join(s.split())

    # Cheap size guard before allocating the decoded buffer.
    if (len(s) * 3) // 4 > max_bytes:
        raise _too_large(max_bytes)

    try:
        raw = base64.b64decode(s, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid base64 image data.",
        )

    if len(raw) > max_bytes:
        raise _too_large(max_bytes)

    if _sniff_image(raw) is None:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported image format (use JPEG, PNG, or WebP).",
        )
    return raw
