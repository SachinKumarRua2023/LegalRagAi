"""Unified vector DB client — routes to ChromaDB (local) or Pinecone (cloud)."""
from __future__ import annotations
from typing import Any

from config.settings import VECTOR_DB_PROVIDER


def _get_client():
    """Return active vector DB client based on config (lazy import — avoids loading unused DB)."""
    if VECTOR_DB_PROVIDER.lower() == "pinecone":
        from src.vector_db import pinecone_client
        return pinecone_client
    from src.vector_db import chroma_client
    return chroma_client


# ── Unified API ──────────────────────────────────────────────────────────────

def add_chunks(chunks: list[dict[str, Any]], batch_size: int = 100) -> int:
    """Add chunks to vector DB (ChromaDB or Pinecone)."""
    return _get_client().add_chunks(chunks, batch_size)


def query_collection(
    query_text: str,
    n_results: int = 5,
    where: dict | None = None,
) -> list[dict[str, Any]]:
    """Query vector DB for similar chunks."""
    return _get_client().query_collection(query_text, n_results, where)


def collection_stats() -> dict:
    """Get collection statistics."""
    return _get_client().collection_stats()


def list_indexed_files() -> list[dict]:
    """List all unique indexed files."""
    return _get_client().list_indexed_files()
