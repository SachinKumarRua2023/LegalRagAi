"""Embedding engine with local (sentence-transformers) and Google free-tier backends."""
from __future__ import annotations
import os
from functools import lru_cache
from typing import Protocol

from config.settings import EMBEDDING_MODEL, LOCAL_EMBEDDING_MODEL, GOOGLE_EMBEDDING_MODEL, GOOGLE_API_KEY


class EmbeddingEngine(Protocol):
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...
    def embed_query(self, text: str) -> list[float]: ...


# ── Local engine (sentence-transformers, 100% free) ──────────────────────────

class LocalEmbeddingEngine:
    """Uses all-MiniLM-L6-v2 — 384-dim, fast, no API key needed."""

    def __init__(self, model_name: str = LOCAL_EMBEDDING_MODEL):
        from sentence_transformers import SentenceTransformer
        print(f"[Embeddings] Loading local model: {model_name}")
        self._model = SentenceTransformer(model_name)
        self.dimension = self._model.get_sentence_embedding_dimension()
        print(f"[Embeddings] Ready. Dimension={self.dimension}")

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vecs = self._model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
        return vecs.tolist()

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


# ── Google Gemini embedding engine (free tier) ────────────────────────────────

class GoogleEmbeddingEngine:
    """Uses Google text-embedding-004 — free tier, excellent quality."""

    def __init__(self, model_name: str = GOOGLE_EMBEDDING_MODEL):
        import google.generativeai as genai
        if not GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY is not set. Use local embeddings instead.")
        genai.configure(api_key=GOOGLE_API_KEY)
        self._genai = genai
        self._model = model_name
        self.dimension = 768
        print(f"[Embeddings] Using Google: {model_name}")

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        results = []
        for text in texts:
            resp = self._genai.embed_content(
                model=self._model,
                content=text,
                task_type="retrieval_document",
            )
            results.append(resp["embedding"])
        return results

    def embed_query(self, text: str) -> list[float]:
        resp = self._genai.embed_content(
            model=self._model,
            content=text,
            task_type="retrieval_query",
        )
        return resp["embedding"]


# ── Factory ───────────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def get_embedding_engine() -> EmbeddingEngine:
    """Returns the configured embedding engine (cached singleton)."""
    provider = EMBEDDING_MODEL.lower()
    if provider == "google" and GOOGLE_API_KEY:
        try:
            return GoogleEmbeddingEngine()
        except Exception as e:
            print(f"[Embeddings] Google init failed ({e}), falling back to local.")
    return LocalEmbeddingEngine()
