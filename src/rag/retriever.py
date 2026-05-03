"""Semantic retriever with source citation and folder/file filtering."""
from __future__ import annotations
from pathlib import Path
from typing import Any

from src.vector_db.chroma_client import query_collection, list_indexed_files
from config.settings import TOP_K_RESULTS, SIMILARITY_THRESHOLD


def _format_source_citation(meta: dict) -> str:
    """Build a human-readable source string for a chunk."""
    parts = []
    file = meta.get("source_file", "Unknown file")
    parts.append(f"File: {file}")

    folder = meta.get("source_folder", "")
    if folder:
        parts.append(f"Folder: {folder}")

    if meta.get("page_number"):
        parts.append(f"Page {meta['page_number']}")
    elif meta.get("slide_number"):
        parts.append(f"Slide {meta['slide_number']}")
    elif meta.get("sheet"):
        parts.append(f"Sheet: {meta['sheet']}")

    section = meta.get("section", "")
    if section and section not in ("Full Document", "CSV Data", "JSON Document"):
        parts.append(f"Section: {section}")

    return " | ".join(parts)


def retrieve(
    query: str,
    n_results: int = TOP_K_RESULTS,
    min_score: float = SIMILARITY_THRESHOLD,
    filter_file: str | None = None,
    filter_folder: str | None = None,
    filter_file_type: str | None = None,
) -> list[dict[str, Any]]:
    """
    Semantic search against ChromaDB.

    Returns list of:
        {
          "text": str,
          "metadata": dict,
          "relevance_score": float,
          "source_citation": str,    # human-readable source ref
          "source_file": str,
          "source_path": str,
          "source_folder": str,
        }
    """
    where: dict | None = None
    filters = []

    if filter_file:
        filters.append({"source_file": {"$eq": filter_file}})
    if filter_folder:
        # Match files whose source_folder contains the given folder name
        filters.append({"source_folder": {"$contains": filter_folder}})
    if filter_file_type:
        ext = filter_file_type.lstrip(".").lower()
        filters.append({"file_type": {"$eq": ext}})

    if len(filters) == 1:
        where = filters[0]
    elif len(filters) > 1:
        where = {"$and": filters}

    raw = query_collection(query, n_results=n_results, where=where)

    results = []
    for item in raw:
        score = item.get("relevance_score", 0)
        if score < min_score:
            continue
        meta = item.get("metadata", {})
        results.append({
            "text": item["text"],
            "metadata": meta,
            "relevance_score": score,
            "source_citation": _format_source_citation(meta),
            "source_file": meta.get("source_file", ""),
            "source_path": meta.get("source_path", ""),
            "source_folder": meta.get("source_folder", ""),
        })

    # Sort by relevance descending
    results.sort(key=lambda x: x["relevance_score"], reverse=True)
    return results


def retrieve_by_file(file_name: str, query: str, n_results: int = TOP_K_RESULTS) -> list[dict]:
    """Retrieve only from a specific file."""
    return retrieve(query, n_results=n_results, filter_file=file_name)


def retrieve_by_folder(folder_name: str, query: str, n_results: int = TOP_K_RESULTS) -> list[dict]:
    """Retrieve only from a specific folder."""
    return retrieve(query, n_results=n_results, filter_folder=folder_name)


def format_context_for_llm(results: list[dict]) -> str:
    """Format retrieved chunks into a context block for the LLM prompt."""
    if not results:
        return "No relevant documents found."

    lines = []
    for i, r in enumerate(results, 1):
        lines.append(f"[Source {i}: {r['source_citation']}]")
        lines.append(r["text"])
        lines.append("")

    return "\n".join(lines)


def get_all_sources() -> list[dict]:
    """List every unique source file in the index."""
    return list_indexed_files()
