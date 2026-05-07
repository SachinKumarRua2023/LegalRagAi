"""High-level indexer: parse → chunk → embed → store."""
from __future__ import annotations
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.progress import track

from src.data_ingestion.parsers.document_router import parse_document, get_supported_extensions
from src.data_ingestion.chunkers.text_chunker import chunk_document
from src.vector_db.vector_client import add_chunks, collection_stats, list_indexed_files
from config.settings import DATA_RAW_PATH, DATA_UPLOADS_PATH, SUPPORTED_EXTENSIONS

console = Console()


def index_file(file_path: str | Path, extra_metadata: dict | None = None) -> dict[str, Any]:
    """Parse, chunk and index a single file. Returns a result summary."""
    path = Path(file_path)
    if not path.exists():
        return {"status": "error", "file": str(path), "error": "File not found"}

    ext = path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        return {"status": "skipped", "file": path.name, "reason": f"Unsupported extension: {ext}"}

    try:
        raw_chunks = parse_document(path)
        if extra_metadata:
            for c in raw_chunks:
                c["metadata"].update(extra_metadata)

        chunks = chunk_document(raw_chunks)
        if not chunks:
            return {"status": "empty", "file": path.name, "chunks": 0}

        added = add_chunks(chunks)
        return {
            "status": "ok",
            "file": path.name,
            "path": str(path),
            "chunks_added": added,
            "raw_sections": len(raw_chunks),
        }
    except Exception as e:
        return {"status": "error", "file": path.name, "error": str(e)}


def index_directory(
    directory: str | Path | None = None,
    recursive: bool = True,
    extra_metadata: dict | None = None,
) -> dict[str, Any]:
    """Index all supported files in a directory."""
    directory = Path(directory) if directory else DATA_RAW_PATH

    if not directory.exists():
        return {"status": "error", "error": f"Directory not found: {directory}"}

    pattern = "**/*" if recursive else "*"
    all_files = [
        p for p in directory.glob(pattern)
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    ]

    if not all_files:
        console.print(f"[yellow]No supported files found in {directory}[/yellow]")
        return {"status": "ok", "indexed": 0, "skipped": 0, "errors": 0, "files": []}

    results = []
    ok = skip = err = 0

    for fp in track(all_files, description="Indexing files..."):
        result = index_file(fp, extra_metadata)
        results.append(result)
        if result["status"] == "ok":
            ok += 1
            console.print(f"  [green]OK[/green] {result['file']} -> {result['chunks_added']} chunks")
        elif result["status"] == "skipped":
            skip += 1
        else:
            err += 1
            console.print(f"  [red]ERR[/red] {result['file']}: {result.get('error', result.get('reason', ''))}")

    stats = collection_stats()
    return {
        "status": "ok",
        "directory": str(directory),
        "indexed": ok,
        "skipped": skip,
        "errors": err,
        "total_files": len(all_files),
        "collection_total_chunks": stats["total_chunks"],
        "files": results,
    }


def index_uploaded_files() -> dict[str, Any]:
    """Index everything in the uploads folder."""
    return index_directory(DATA_UPLOADS_PATH)


def get_index_status() -> dict[str, Any]:
    """Fast stats-only check — does NOT list files (use /api/files for that)."""
    stats = collection_stats()
    return {**stats, "unique_files": stats.get("total_chunks", 0)}
