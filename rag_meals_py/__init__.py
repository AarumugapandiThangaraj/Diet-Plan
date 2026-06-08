"""RAG over master meals (ChromaDB).

This package indexes the flat meal dataset (Diet Plan/data/master_meals_updated.json)
into a persistent Chroma collection and exposes helpers to retrieve meals.
"""

from .ingest import ensure_ingested

__all__ = ["ensure_ingested"]
