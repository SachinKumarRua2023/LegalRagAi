"""ChromaDB persistent client — free, local, no cloud required."""
from __future__ import annotations
from functools import lru_cache
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from config.settings import CHROMA_DB_PATH, CHROMA_COLLECTION_NAME
from src.vector_db.embeddings import get_embedding_engine


# ── Client singleton ──────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def get_chroma_client() -> chromadb.PersistentClient:
    print(f"[ChromaDB] Connecting to: {CHROMA_DB_PATH}")
    client = chromadb.PersistentClient(
        path=CHROMA_DB_PATH,
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    return client


def get_collection(name: str = CHROMA_COLLECTION_NAME) -> chromadb.Collection:
    client = get_chroma_client()
    engine = get_embedding_engine()
    collection = client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )
    return collection


# ── CRUD helpers ──────────────────────────────────────────────────────────────

def _sanitize_meta(meta: dict) -> dict:
    """ChromaDB only accepts str/int/float/bool values in metadata."""
    clean = {}
    for k, v in meta.items():
        if isinstance(v, (str, int, float, bool)):
            clean[k] = v
        elif v is None:
            clean[k] = ""
        else:
            clean[k] = str(v)
    return clean


def add_chunks(
    chunks: list[dict[str, Any]],
    collection_name: str = CHROMA_COLLECTION_NAME,
    batch_size: int = 100,
) -> int:
    """Embed and upsert chunks into ChromaDB. Returns count of added chunks."""
    if not chunks:
        return 0

    collection = get_collection(collection_name)
    engine = get_embedding_engine()

    added = 0
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i: i + batch_size]
        texts = [c["text"] for c in batch]
        metas = [_sanitize_meta(c["metadata"]) for c in batch]
        ids = [
            f"{m.get('file_hash','x')}_{m.get('page_number', m.get('slide_number', m.get('chunk_index', j)))}"
            for j, m in enumerate(metas)
        ]

        # Ensure unique IDs within batch
        seen: dict[str, int] = {}
        unique_ids = []
        for uid in ids:
            if uid in seen:
                seen[uid] += 1
                unique_ids.append(f"{uid}_{seen[uid]}")
            else:
                seen[uid] = 0
                unique_ids.append(uid)

        embeddings = engine.embed_documents(texts)

        collection.upsert(
            ids=unique_ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metas,
        )
        added += len(batch)

    return added


def query_collection(
    query_text: str,
    n_results: int = 5,
    where: dict | None = None,
    collection_name: str = CHROMA_COLLECTION_NAME,
) -> list[dict[str, Any]]:
    """
    Semantic search. Returns list of results with text, metadata, and distance.
    Results always include source_file, source_path, source_folder.
    """
    collection = get_collection(collection_name)
    engine = get_embedding_engine()
    query_embedding = engine.embed_query(query_text)

    kwargs: dict = {"query_embeddings": [query_embedding], "n_results": min(n_results, collection.count() or 1)}
    if where:
        kwargs["where"] = where

    results = collection.query(**kwargs, include=["documents", "metadatas", "distances"])

    output = []
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    for doc, meta, dist in zip(docs, metas, distances):
        output.append({
            "text": doc,
            "metadata": meta,
            "relevance_score": round(1 - dist, 4),  # cosine: 1=identical, 0=unrelated
        })

    return output


def collection_stats(collection_name: str = CHROMA_COLLECTION_NAME) -> dict:
    try:
        col = get_collection(collection_name)
        count = col.count()
        return {"collection": collection_name, "total_chunks": count, "db_path": CHROMA_DB_PATH}
    except Exception:
        return {"collection": collection_name, "total_chunks": 0, "db_path": CHROMA_DB_PATH}


def list_indexed_files(collection_name: str = CHROMA_COLLECTION_NAME) -> list[dict]:
    """Return unique files stored in the collection with their metadata summary."""
    col = get_collection(collection_name)
    count = col.count()
    if count == 0:
        return []

    # Sample up to 10 000 to find unique files
    sample = col.get(limit=min(count, 10000), include=["metadatas"])
    metas = sample.get("metadatas", [])

    seen: dict[str, dict] = {}
    for m in metas:
        key = m.get("source_path", m.get("source_file", "unknown"))
        if key not in seen:
            seen[key] = {
                "source_file": m.get("source_file", ""),
                "source_path": m.get("source_path", ""),
                "source_folder": m.get("source_folder", ""),
                "file_type": m.get("file_type", ""),
                "document_type": m.get("document_type", ""),
            }
    return list(seen.values())
