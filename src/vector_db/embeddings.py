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
    """Uses gemini-embedding-001 via google-genai SDK — free, 768-dim output."""

    def __init__(self):
        from google import genai
        if not GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY is not set.")
        self._client = genai.Client(api_key=GOOGLE_API_KEY)
        self._genai = genai
        self._model = "gemini-embedding-001"
        self.dimension = 768
        print(f"[Embeddings] Using Google: {self._model} (768-dim)")

    def _embed(self, texts: list[str]) -> list[list[float]]:
        import time, re
        for attempt in range(8):
            try:
                resp = self._client.models.embed_content(
                    model=self._model,
                    contents=texts,
                    config=self._genai.types.EmbedContentConfig(output_dimensionality=768),
                )
                return [list(e.values) for e in resp.embeddings]
            except Exception as e:
                err = str(e)
                if "429" in err or "RESOURCE_EXHAUSTED" in err:
                    # Extract retry-after hint from error, fall back to 65s
                    m = re.search(r"retryDelay.*?(\d+)s", err)
                    wait = int(m.group(1)) + 3 if m else 65
                    print(f"\n[Embeddings] Rate limited — waiting {wait}s (attempt {attempt+1}/8)…")
                    time.sleep(wait)
                else:
                    raise
        raise RuntimeError("Google Embeddings: max retries exceeded on rate limit")

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        import time
        results = []
        # 20 texts per call — free tier counts each text toward 100/min quota
        for i in range(0, len(texts), 20):
            results.extend(self._embed(texts[i:i + 20]))
            # Proactive throttle: 20 texts every 13s ≈ 92 texts/min (under 100 limit)
            if i + 20 < len(texts):
                time.sleep(13)
        return results

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text])[0]


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
