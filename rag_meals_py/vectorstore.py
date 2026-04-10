from __future__ import annotations

import logging
from typing import Optional

import chromadb
from chromadb.api.models.Collection import Collection

from .config import CHROMA_DIR, COLLECTION_NAME, EMBEDDING_MODEL

logger = logging.getLogger(__name__)

_client: Optional[chromadb.ClientAPI] = None


def _get_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        logger.info("ChromaDB client initialised at %s", CHROMA_DIR)
    return _client


def _get_embedding_function():
    from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

    return SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)


def get_collection() -> Collection:
    client = _get_client()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=_get_embedding_function(),
        metadata={"hnsw:space": "cosine"},
    )


def reset() -> None:
    client = _get_client()
    try:
        client.delete_collection(COLLECTION_NAME)
        logger.info("Collection '%s' deleted.", COLLECTION_NAME)
    except Exception:
        pass
