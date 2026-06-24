"""Career knowledge base retrieval (vector RAG) - in-memory Chroma.

Why this design:
  * Chroma runs IN-PROCESS (no separate vector service / Docker).
  * It uses its built-in local embedding model (MiniLM ONNX), so there's NO
    embedding API key and NO extra cost.
  * The KB is small and static (kb.py), so we rebuild the index on startup -
    nothing to persist or provision at deploy time.

At deploy, the only one-time cost is downloading the small embedding model into
the image cache; after that it's fully self-contained.

Location:
    E:\\campus-ai\\ai-worker\\rag.py
"""

import logging

import chromadb

from kb import CAREER_KB

logger = logging.getLogger("campus_ai.rag")

_collection = None


def _get_collection():
    """Build (once, lazily) and return the in-memory career-KB collection."""
    global _collection
    if _collection is None:
        client = chromadb.EphemeralClient()
        collection = client.get_or_create_collection("career_kb")
        collection.add(
            ids=[doc["id"] for doc in CAREER_KB],
            documents=[doc["text"] for doc in CAREER_KB],
            metadatas=[{"topic": doc["topic"]} for doc in CAREER_KB],
        )
        _collection = collection
        logger.info("Career KB indexed: %d documents", len(CAREER_KB))
    return _collection


def retrieve(query: str, k: int = 3) -> list[str]:
    """Return up to `k` KB chunks most relevant to `query`.

    Retrieval failures are non-fatal: the mentor can still answer from the
    student's verified profile, just without extra general guidance.
    """
    try:
        collection = _get_collection()
        result = collection.query(query_texts=[query], n_results=k)
        documents = result.get("documents") or [[]]
        return documents[0] or []
    except Exception as exc:  # noqa: BLE001 - best-effort augmentation
        logger.warning("KB retrieval failed: %s", exc)
        return []
