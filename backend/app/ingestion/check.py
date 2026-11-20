"""Compatibility import for earlier experiments.

Use :mod:`backend.app.ingestion.vector_store` for new code. This module used to
contain a second implementation with a different default database directory.
"""

from backend.app.ingestion.vector_store import VectorStore

__all__ = ["VectorStore"]
