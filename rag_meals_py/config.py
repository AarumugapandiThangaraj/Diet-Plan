from __future__ import annotations

from pathlib import Path


# Diet Plan/rag_meals_py/config.py -> rag_meals_py -> Diet Plan
PROJECT_ROOT = Path(__file__).resolve().parents[1]

MASTER_MEALS_PATH = PROJECT_ROOT / "data" / "master_meals_updated.json"

OUTPUTS_DIR = PROJECT_ROOT / "outputs"
CHROMA_DIR = OUTPUTS_DIR / "chroma_master_meals"
MANIFEST_PATH = OUTPUTS_DIR / "rag_master_meals_manifest.json"

COLLECTION_NAME = "master_meals"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

DEFAULT_TOP_K = 25
BATCH_SIZE = 64
