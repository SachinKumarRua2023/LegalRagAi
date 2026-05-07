"""Pinecone cloud vector DB client — for serverless deployment."""
from __future__ import annotations
from functools import lru_cache
from typing import Any
import time

from pinecone import Pinecone, ServerlessSpec

from config.settings import (
    PINECONE_API_KEY,
    PINECONE_INDEX_NAME,
    PINECONE_CLOUD,
    PINECONE_REGION,
)
from src.vector_db.embeddings import get_embedding_engine


# ── Client singleton ─────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def get_pinecone_client() -> Pinecone:
    """Get Pinecone client singleton."""
    if not PINECONE_API_KEY:
        raise ValueError("PINECONE_API_KEY not set. Get free key at https://pinecone.io")
    return Pinecone(api_key=PINECONE_API_KEY)


def _embedding_dimension() -> int:
    """Return the dimension of the active embedding engine."""
    return get_embedding_engine().dimension


def ensure_index_exists() -> str:
    """Create Pinecone index if it doesn't exist, using the active embedding dimension."""
    pc = get_pinecone_client()
    dimension = _embedding_dimension()
    existing = [idx.name for idx in pc.list_indexes()]
    if PINECONE_INDEX_NAME not in existing:
        print(f"[Pinecone] Creating index: {PINECONE_INDEX_NAME} ({dimension}d)")
        pc.create_index(
            name=PINECONE_INDEX_NAME,
            dimension=dimension,
            metric="cosine",
            spec=ServerlessSpec(cloud=PINECONE_CLOUD, region=PINECONE_REGION),
        )
        while PINECONE_INDEX_NAME not in [idx.name for idx in pc.list_indexes()]:
            time.sleep(1)
        print(f"[Pinecone] Index ready: {PINECONE_INDEX_NAME}")
    return PINECONE_INDEX_NAME


def get_index() -> Any:
    """Get Pinecone index handle."""
    pc = get_pinecone_client()
    ensure_index_exists()
    return pc.Index(PINECONE_INDEX_NAME)


# ── CRUD helpers ───────────────────────────────────────────────────────────────

def _sanitize_meta(meta: dict) -> dict:
    """Pinecone only accepts str values in metadata."""
    clean = {}
    for k, v in meta.items():
        if isinstance(v, str):
            clean[k] = v
        elif isinstance(v, (int, float)):
            # Pinecone supports numeric values
            clean[k] = v
        elif isinstance(v, bool):
            clean[k] = str(v)
        elif v is None:
            clean[k] = ""
        else:
            clean[k] = str(v)
    return clean


def add_chunks(
    chunks: list[dict[str, Any]],
    batch_size: int = 100,
) -> int:
    """Embed and upsert chunks into Pinecone. Returns count of added chunks."""
    if not chunks:
        return 0
    
    index = get_index()
    engine = get_embedding_engine()
    
    added = 0
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        texts = [c["text"] for c in batch]
        metas = [_sanitize_meta(c["metadata"]) for c in batch]
        
        # Generate embeddings
        embeddings = engine.embed_documents(texts)
        
        # Prepare vectors for upsert
        vectors = []
        for j, (emb, meta) in enumerate(zip(embeddings, metas)):
            # Create unique ID
            chunk_id = f"{meta.get('file_hash', 'x')}_{meta.get('chunk_index', j)}_{int(time.time() * 1000)}"
            vectors.append({
                "id": chunk_id,
                "values": emb,
                "metadata": {**meta, "text": texts[j][:1000]},  # Store text preview
            })
        
        # Upsert batch
        index.upsert(vectors=vectors)
        added += len(batch)
    
    return added


def query_collection(
    query_text: str,
    n_results: int = 5,
    where: dict | None = None,
) -> list[dict[str, Any]]:
    """
    Semantic search with Pinecone.
    Returns list of results with text preview, metadata, and score.
    """
    index = get_index()
    engine = get_embedding_engine()
    
    # Embed query
    query_embedding = engine.embed_query(query_text)
    
    # Build filter if provided
    filter_dict = {}
    if where:
        # Convert Chroma-style filters to Pinecone filters
        if "source_file" in where:
            filter_dict["source_file"] = where["source_file"]
        if "source_folder" in where:
            filter_dict["source_folder"] = where["source_folder"]
        if "file_type" in where:
            filter_dict["file_type"] = where["file_type"]
    
    # Query
    kwargs = {
        "vector": query_embedding,
        "top_k": n_results,
        "include_metadata": True,
    }
    if filter_dict:
        kwargs["filter"] = filter_dict
    
    results = index.query(**kwargs)
    
    # Format output to match ChromaDB format
    output = []
    for match in results.matches:
        meta = match.metadata or {}
        output.append({
            "text": meta.get("text", ""),  # Text preview stored in metadata
            "metadata": {k: v for k, v in meta.items() if k != "text"},
            "relevance_score": round(match.score, 4),
        })
    
    return output


def collection_stats() -> dict:
    """Get Pinecone index statistics."""
    try:
        index = get_index()
        stats = index.describe_index_stats()
        return {
            "collection": PINECONE_INDEX_NAME,
            "total_chunks": stats.total_vector_count,
            "db_path": f"pinecone.io/{PINECONE_INDEX_NAME}",
            "dimension": stats.dimension,
        }
    except Exception:
        return {"collection": PINECONE_INDEX_NAME, "total_chunks": 0, "db_path": "pinecone.io"}


_files_cache: tuple[float, list[dict]] | None = None
_FILES_CACHE_TTL = 300  # 5 minutes — avoids repeated 10k-vector Pinecone scans

def list_indexed_files() -> list[dict]:
    """List unique files. Result is cached for 5 min to keep memory usage low."""
    global _files_cache
    import time
    now = time.time()
    if _files_cache and now - _files_cache[0] < _FILES_CACHE_TTL:
        return _files_cache[1]
    try:
        index = get_index()
        dim = _embedding_dimension()
        results = index.query(
            vector=[0.0] * dim,
            top_k=1000,
            include_metadata=True,
        )
        seen: dict[str, dict] = {}
        for match in results.matches:
            meta = match.metadata or {}
            key = meta.get("source_path", meta.get("source_file", "unknown"))
            if key not in seen:
                seen[key] = {
                    "source_file": meta.get("source_file", ""),
                    "source_path": meta.get("source_path", ""),
                    "source_folder": meta.get("source_folder", ""),
                    "file_type": meta.get("file_type", ""),
                    "document_type": meta.get("document_type", ""),
                }
        result = list(seen.values())
        _files_cache = (now, result)
        return result
    except Exception:
        return []
