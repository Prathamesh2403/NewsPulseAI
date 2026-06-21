"""
Dependency injection utilities for FastAPI endpoints.

Re-exports common dependencies so endpoints can import from a single module.
"""

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.db.vector_store import VectorStore, get_vector_store

__all__ = [
    "get_db",
    "get_vector_store",
    "get_settings",
    "Settings",
    "VectorStore",
]
