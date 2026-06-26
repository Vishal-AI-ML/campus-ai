"""Face recognition engine for attendance (AI worker side).

This module powers the Campus AI face-attendance flow. It lives on the AI worker
(port 8100), kept separate from the main backend (port 8000) so the heavy
computer-vision work never blocks the user-facing API.

What it does
------------
* Detects faces in an image and computes a 512-dimension ArcFace embedding for
  each one, using InsightFace's ``buffalo_l`` model pack (CPU via onnxruntime).
* Stores ONE reference embedding per enrolled student in a Qdrant vector
  collection (cosine distance), keyed by the student's id.
* Given a class photo, detects every face, matches each against the enrolled
  students, and returns the matched student ids with confidence scores.

Verified-data philosophy stays intact: face matching only *suggests* who is
present. The teacher always confirms the roster before any attendance row is
written - the worker never marks attendance itself.

Qdrant is fully config-driven (read from ``.env``), so the SAME code runs against:
  * Qdrant Cloud          -> QDRANT_URL=https://...  + QDRANT_API_KEY=...
  * a local/Docker server -> QDRANT_URL=http://127.0.0.1:6333
  * an embedded on-disk store -> leave QDRANT_URL empty (uses QDRANT_LOCAL_PATH)
Switching environments is therefore a ``.env`` change only - no code edits.

Location:
    E:\\campus-ai\\ai-worker\\face.py

Routes (mounted under the ``/face`` prefix by main.py):
    GET    /face/health               - model + vector store status
    POST   /face/embed                - detect a single face -> its embedding
    POST   /face/enroll               - upsert a student's reference embedding
    DELETE /face/enroll/{student_id}  - remove a student's enrollment
    POST   /face/match                - class photo -> matched student ids
"""

from __future__ import annotations

import base64
import binascii
import threading
from functools import lru_cache
from typing import Optional

import numpy as np
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# ArcFace (buffalo_l) embedding dimension - fixed by the model pack.
EMBEDDING_DIM = 512


# ---------------------------------------------------------------------------
# Configuration (self-contained; reads the worker's .env directly)
# ---------------------------------------------------------------------------
class FaceSettings(BaseSettings):
    """Face-engine settings, loaded from the ai-worker ``.env`` file.

    Kept separate from the main ``config.Settings`` so this module is fully
    self-contained. ``extra="ignore"`` means unrelated keys (LLM, etc.) are
    simply skipped instead of raising.
    """

    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", protected_namespaces=()
    )

    # Vector store -----------------------------------------------------------
    # https://... (cloud) or http://... (server); empty string => embedded mode.
    QDRANT_URL: str = ""
    QDRANT_API_KEY: str = ""  # required for Qdrant Cloud
    QDRANT_LOCAL_PATH: str = "qdrant_data"  # used only when QDRANT_URL is empty
    FACE_COLLECTION: str = "student_faces"

    # Model / matching -------------------------------------------------------
    FACE_MODEL_PACK: str = "buffalo_l"  # InsightFace model bundle
    FACE_DET_SIZE: int = 640  # detector input size (square, pixels)
    FACE_MATCH_THRESHOLD: float = 0.35  # min cosine similarity to accept a match


@lru_cache(maxsize=1)
def get_settings() -> FaceSettings:
    """Return a cached settings instance (parsed once per process)."""
    return FaceSettings()


# ---------------------------------------------------------------------------
# InsightFace model (lazy singleton)
# ---------------------------------------------------------------------------
_model_lock = threading.Lock()
_face_app = None  # populated on first use


def _get_face_app():
    """Lazily build and cache the InsightFace analyzer.

    The model pack (~300 MB) downloads on first use and is then cached on disk.
    We pin the CPU execution provider because the dev/deploy targets have no
    GPU; swap in "CUDAExecutionProvider" later if a GPU is available.
    """
    global _face_app
    if _face_app is not None:
        return _face_app
    with _model_lock:
        if _face_app is None:
            from insightface.app import FaceAnalysis

            cfg = get_settings()
            app = FaceAnalysis(
                name=cfg.FACE_MODEL_PACK,
                providers=["CPUExecutionProvider"],
            )
            app.prepare(
                ctx_id=0,
                det_size=(cfg.FACE_DET_SIZE, cfg.FACE_DET_SIZE),
            )
            _face_app = app
    return _face_app


# ---------------------------------------------------------------------------
# Qdrant client (lazy singleton, config-driven)
# ---------------------------------------------------------------------------
_qdrant_lock = threading.Lock()
_qdrant_client = None  # populated on first use


def _ensure_collection(client) -> None:
    """Create the face collection if it does not exist yet."""
    from qdrant_client.models import Distance, VectorParams

    name = get_settings().FACE_COLLECTION
    if not client.collection_exists(name):
        client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(
                size=EMBEDDING_DIM, distance=Distance.COSINE
            ),
        )


def _get_qdrant():
    """Build and cache the Qdrant client based on .env configuration."""
    global _qdrant_client
    if _qdrant_client is not None:
        return _qdrant_client
    with _qdrant_lock:
        if _qdrant_client is None:
            from qdrant_client import QdrantClient

            cfg = get_settings()
            url = cfg.QDRANT_URL.strip()
            if url:
                # Cloud or self-hosted server (HTTPS uses the API key).
                client = QdrantClient(
                    url=url,
                    api_key=cfg.QDRANT_API_KEY or None,
                    timeout=30,
                )
            else:
                # Embedded, on-disk store - no server required.
                client = QdrantClient(path=cfg.QDRANT_LOCAL_PATH)
            _ensure_collection(client)
            _qdrant_client = client
    return _qdrant_client


# ---------------------------------------------------------------------------
# Image + face helpers
# ---------------------------------------------------------------------------
def _decode_image(image_base64: str) -> np.ndarray:
    """Decode a base64 (optionally data-URL) image into a BGR numpy array."""
    import cv2

    raw = image_base64.strip()
    if raw.startswith("data:"):
        # Strip a data-URL prefix such as "data:image/jpeg;base64,".
        _, _, raw = raw.partition(",")
    try:
        image_bytes = base64.b64decode(raw, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid base64 image data.",
        ) from exc
    buffer = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not decode the image (unsupported or corrupt file).",
        )
    return image


def _detect_faces(image: np.ndarray) -> list:
    """Run InsightFace detection + embedding on a BGR image."""
    return _get_face_app().get(image)


def _largest_face(faces: list):
    """Return the face with the biggest bounding box (the main subject)."""
    def _area(face) -> float:
        x1, y1, x2, y2 = face.bbox
        return float((x2 - x1) * (y2 - y1))

    return max(faces, key=_area)


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------
class EmbedRequest(BaseModel):
    image_base64: str = Field(min_length=1)


class EmbedResponse(BaseModel):
    face_count: int
    embedding: Optional[list[float]] = None
    det_score: Optional[float] = None


class EnrollRequest(BaseModel):
    student_id: int = Field(gt=0)
    image_base64: str = Field(min_length=1)


class EnrollResponse(BaseModel):
    student_id: int
    enrolled: bool
    det_score: float
    message: str


class MatchedStudent(BaseModel):
    student_id: int
    score: float


class MatchRequest(BaseModel):
    image_base64: str = Field(min_length=1)
    score_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class MatchResponse(BaseModel):
    detected_faces: int
    matched: list[MatchedStudent]
    unmatched_faces: int
    threshold: float


class FaceHealthResponse(BaseModel):
    status: str
    face_model: str
    embedding_dim: int
    vector_store: str
    collection: str
    enrolled_count: int


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
router = APIRouter(prefix="/face", tags=["face"])


@router.post("/embed", response_model=EmbedResponse)
def embed(payload: EmbedRequest) -> EmbedResponse:
    """Detect faces and return the embedding of the most prominent one."""
    image = _decode_image(payload.image_base64)
    faces = _detect_faces(image)
    if not faces:
        return EmbedResponse(face_count=0)
    face = _largest_face(faces)
    return EmbedResponse(
        face_count=len(faces),
        embedding=[float(x) for x in face.normed_embedding],
        det_score=float(face.det_score),
    )


@router.post("/enroll", response_model=EnrollResponse)
def enroll(payload: EnrollRequest) -> EnrollResponse:
    """Store a student's reference face embedding (exactly one face required)."""
    from qdrant_client.models import PointStruct

    image = _decode_image(payload.image_base64)
    faces = _detect_faces(image)
    if not faces:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No face detected. Use a clear, well-lit, front-facing photo.",
        )
    if len(faces) > 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{len(faces)} faces detected. The enrollment photo must contain exactly one face.",
        )
    face = faces[0]
    cfg = get_settings()
    client = _get_qdrant()
    client.upsert(
        collection_name=cfg.FACE_COLLECTION,
        points=[
            PointStruct(
                id=payload.student_id,
                vector=[float(x) for x in face.normed_embedding],
                payload={"student_id": payload.student_id},
            )
        ],
    )
    return EnrollResponse(
        student_id=payload.student_id,
        enrolled=True,
        det_score=float(face.det_score),
        message="Face enrolled successfully.",
    )


@router.delete("/enroll/{student_id}")
def delete_enrollment(student_id: int) -> dict:
    """Remove a student's enrolled face embedding."""
    from qdrant_client.models import PointIdsList

    cfg = get_settings()
    client = _get_qdrant()
    client.delete(
        collection_name=cfg.FACE_COLLECTION,
        points_selector=PointIdsList(points=[student_id]),
    )
    return {"student_id": student_id, "deleted": True}


@router.post("/match", response_model=MatchResponse)
def match(payload: MatchRequest) -> MatchResponse:
    """Detect all faces in a class photo and match each to an enrolled student.

    A student is reported at most once (the highest-scoring face wins), and any
    face whose best match is below the threshold is counted as unmatched.
    """
    cfg = get_settings()
    threshold = (
        payload.score_threshold
        if payload.score_threshold is not None
        else cfg.FACE_MATCH_THRESHOLD
    )
    image = _decode_image(payload.image_base64)
    faces = _detect_faces(image)
    if not faces:
        return MatchResponse(
            detected_faces=0, matched=[], unmatched_faces=0, threshold=threshold
        )

    client = _get_qdrant()
    best_by_student: dict[int, float] = {}
    unmatched = 0
    for face in faces:
        hits = client.query_points(
            collection_name=cfg.FACE_COLLECTION,
            query=[float(x) for x in face.normed_embedding],
            limit=1,
            with_payload=True,
        ).points
        if hits and hits[0].score >= threshold:
            top = hits[0]
            sid = int(top.payload.get("student_id", top.id))
            score = float(top.score)
            # Keep the best score if the same student matches more than once.
            if sid not in best_by_student or score > best_by_student[sid]:
                best_by_student[sid] = score
        else:
            unmatched += 1

    matched = [
        MatchedStudent(student_id=sid, score=round(score, 4))
        for sid, score in sorted(
            best_by_student.items(), key=lambda kv: kv[1], reverse=True
        )
    ]
    return MatchResponse(
        detected_faces=len(faces),
        matched=matched,
        unmatched_faces=unmatched,
        threshold=threshold,
    )


@router.get("/health", response_model=FaceHealthResponse)
def face_health() -> FaceHealthResponse:
    """Report vector-store connectivity and enrolled face count.

    Note: this does NOT load the InsightFace model (which would trigger the
    one-time ~300 MB download); the model loads lazily on the first embed call.
    """
    cfg = get_settings()
    vector_store = "cloud/server" if cfg.QDRANT_URL.strip() else "embedded"
    try:
        client = _get_qdrant()
        enrolled = client.count(
            collection_name=cfg.FACE_COLLECTION, exact=True
        ).count
        store_status = "connected"
    except Exception as exc:  # noqa: BLE001 - surface any vector-store issue
        enrolled = -1
        store_status = f"error: {exc}"
    return FaceHealthResponse(
        status=store_status,
        face_model=cfg.FACE_MODEL_PACK,
        embedding_dim=EMBEDDING_DIM,
        vector_store=vector_store,
        collection=cfg.FACE_COLLECTION,
        enrolled_count=enrolled,
    )
