"""Full RAG pipeline: query → retrieve → generate → respond with sources."""
from __future__ import annotations
from typing import Any

from src.rag.retriever import retrieve, format_context_for_llm
from src.rag.generator import get_generator
from config.settings import TOP_K_RESULTS, SIMILARITY_THRESHOLD


def query(
    question: str,
    n_results: int = TOP_K_RESULTS,
    min_score: float = SIMILARITY_THRESHOLD,
    filter_file: str | None = None,
    filter_folder: str | None = None,
    filter_file_type: str | None = None,
    verbose: bool = False,
) -> dict[str, Any]:
    """
    Full RAG pipeline.

    Returns:
        {
          "answer": str,           # LLM answer with inline source citations
          "sources": [...],        # List of source metadata dicts
          "query": str,
          "chunks_retrieved": int,
        }
    """
    # 1. Retrieve relevant chunks
    results = retrieve(
        query=question,
        n_results=n_results,
        min_score=min_score,
        filter_file=filter_file,
        filter_folder=filter_folder,
        filter_file_type=filter_file_type,
    )

    if verbose:
        print(f"\n[Pipeline] Retrieved {len(results)} chunks for: '{question}'")
        for i, r in enumerate(results, 1):
            print(f"  [{i}] score={r['relevance_score']:.3f} | {r['source_citation']}")

    # 2. Build context block
    context = format_context_for_llm(results)

    # 3. Generate answer
    generator = get_generator()
    answer = generator.generate(question, context)

    # 4. Build source list (deduplicated)
    seen_paths: set[str] = set()
    unique_sources = []
    for r in results:
        path = r.get("source_path") or r.get("source_file", "")
        if path not in seen_paths:
            seen_paths.add(path)
            unique_sources.append({
                "source_file": r["source_file"],
                "source_path": r["source_path"],
                "source_folder": r["source_folder"],
                "source_citation": r["source_citation"],
                "relevance_score": r["relevance_score"],
            })

    return {
        "answer": answer,
        "sources": unique_sources,
        "query": question,
        "chunks_retrieved": len(results),
    }


def query_file(file_name: str, question: str) -> dict[str, Any]:
    """Query specifically within one file."""
    return query(question, filter_file=file_name, n_results=8)


def query_folder(folder_name: str, question: str) -> dict[str, Any]:
    """Query specifically within one folder."""
    return query(question, filter_folder=folder_name, n_results=8)


def format_response(result: dict[str, Any]) -> str:
    """Pretty-print a query result for CLI output."""
    lines = []
    lines.append("\n" + "=" * 70)
    lines.append(f"QUERY: {result['query']}")
    lines.append("=" * 70)
    lines.append(result["answer"])
    lines.append("\n" + "-" * 70)
    lines.append(f"SOURCES RETRIEVED ({result['chunks_retrieved']} chunks, {len(result['sources'])} unique files):")
    for i, src in enumerate(result["sources"], 1):
        lines.append(f"  [{i}] {src['source_citation']} (score: {src['relevance_score']})")
    lines.append("=" * 70)
    return "\n".join(lines)
