from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from .config import BATCH_SIZE, MANIFEST_PATH, MASTER_MEALS_PATH
from .document_processor import build_document_text, build_metadata
from .vectorstore import get_collection, reset as reset_collection

logger = logging.getLogger(__name__)


def _file_hash(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_manifest() -> Dict[str, Any]:
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_manifest(manifest: Dict[str, Any]) -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)


def _load_master_meals(path: Path = MASTER_MEALS_PATH) -> List[Dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"master_meals_updated.json not found at: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("master_meals_updated.json must be a JSON array of meal objects")
    return data


def ensure_ingested(*, force: bool = False) -> Dict[str, Any]:
    """Ensure the master meals dataset is indexed in Chroma.

    Uses a manifest keyed by the hash of `master_meals_updated.json` to avoid
    re-ingesting on every request.

    Returns:
        Dict with keys: status, added, skipped, total, collection_size
    """
    manifest = _load_manifest()

    meals = _load_master_meals()
    current_hash = _file_hash(MASTER_MEALS_PATH)

    # Fast skip if nothing changed and collection already has expected count.
    if not force:
        if manifest.get("hash") == current_hash and manifest.get("count") == len(meals):
            try:
                collection = get_collection()
                if collection.count() == len(meals):
                    return {
                        "status": "skipped",
                        "added": 0,
                        "skipped": len(meals),
                        "total": len(meals),
                        "collection_size": collection.count(),
                    }
            except Exception:
                # fall through to re-ingest
                pass

    # Rebuild collection for consistency.
    reset_collection()
    collection = get_collection()

    ids: List[str] = []
    docs: List[str] = []
    metas: List[Dict[str, Any]] = []

    added = 0
    for meal in meals:
        meal_id = str(meal.get("Meal_ID", "")).strip()
        if not meal_id:
            continue

        ids.append(meal_id)
        docs.append(build_document_text(meal))
        metas.append(build_metadata(meal))
        added += 1

        if len(ids) >= BATCH_SIZE:
            collection.upsert(ids=ids, documents=docs, metadatas=metas)
            ids, docs, metas = [], [], []

    if ids:
        collection.upsert(ids=ids, documents=docs, metadatas=metas)

    manifest = {
        "file": str(MASTER_MEALS_PATH),
        "hash": current_hash,
        "count": len(meals),
        "ingested_at": datetime.now().isoformat(),
    }
    _save_manifest(manifest)

    logger.info(
        "Master meals ingest complete — indexed: %d, total: %d, collection size: %d",
        added,
        len(meals),
        collection.count(),
    )

    return {
        "status": "ingested",
        "added": added,
        "skipped": 0,
        "total": len(meals),
        "collection_size": collection.count(),
    }
