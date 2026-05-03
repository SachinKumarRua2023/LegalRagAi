"""Smart text chunker that preserves source metadata on every chunk."""
from __future__ import annotations
import re
from typing import Any

from config.settings import CHUNK_SIZE, CHUNK_OVERLAP, MAX_CHUNKS_PER_DOC


def _split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Recursive character text splitter that prefers sentence boundaries."""
    if len(text) <= chunk_size:
        return [text]

    separators = ["\n\n", "\n", ". ", "? ", "! ", "; ", ", ", " ", ""]
    for sep in separators:
        if sep in text:
            parts = text.split(sep)
            chunks, current = [], []
            current_len = 0

            for part in parts:
                part_len = len(part) + len(sep)
                if current_len + part_len > chunk_size and current:
                    chunks.append(sep.join(current))
                    # Keep overlap
                    overlap_text = sep.join(current)[-overlap:]
                    current = [overlap_text] if overlap_text else []
                    current_len = len(overlap_text)
                current.append(part)
                current_len += part_len

            if current:
                chunks.append(sep.join(current))
            return [c for c in chunks if c.strip()]

    # Hard split fallback
    return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size - overlap)]


def chunk_document(
    raw_chunks: list[dict[str, Any]],
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
    max_chunks: int = MAX_CHUNKS_PER_DOC,
) -> list[dict[str, Any]]:
    """
    Takes raw parser output (one dict per page/section) and splits large
    texts into overlapping chunks.  Each output chunk keeps full metadata
    plus chunk_index and total_chunks_in_source.
    """
    output: list[dict] = []

    for raw in raw_chunks:
        text: str = raw.get("text", "")
        meta: dict = raw.get("metadata", {})

        sub_texts = _split_text(text.strip(), chunk_size, overlap)

        for idx, sub in enumerate(sub_texts):
            if not sub.strip():
                continue
            chunk_meta = {
                **meta,
                "chunk_index": idx,
                "total_sub_chunks": len(sub_texts),
                "char_count": len(sub),
            }
            output.append({"text": sub, "metadata": chunk_meta})

            if len(output) >= max_chunks:
                return output

    return output


def chunk_text(
    text: str,
    metadata: dict[str, Any],
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[dict[str, Any]]:
    """Chunk a plain text string with given metadata."""
    sub_texts = _split_text(text.strip(), chunk_size, overlap)
    return [
        {"text": sub, "metadata": {**metadata, "chunk_index": i, "total_sub_chunks": len(sub_texts)}}
        for i, sub in enumerate(sub_texts)
        if sub.strip()
    ]
