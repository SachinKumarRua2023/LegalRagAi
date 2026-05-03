"""File utilities for the RAG system."""
from __future__ import annotations
import os
from pathlib import Path

from config.settings import SUPPORTED_EXTENSIONS, DATA_UPLOADS_PATH


def list_files_recursive(directory: str | Path, extensions: set[str] | None = None) -> list[Path]:
    """List all files in a directory tree, optionally filtered by extension."""
    directory = Path(directory)
    exts = extensions or SUPPORTED_EXTENSIONS
    return [p for p in directory.rglob("*") if p.is_file() and p.suffix.lower() in exts]


def get_file_info(path: str | Path) -> dict:
    """Return file metadata dict."""
    path = Path(path)
    stat = path.stat()
    return {
        "name": path.name,
        "path": str(path.absolute()),
        "folder": str(path.parent.absolute()),
        "extension": path.suffix.lower(),
        "size_bytes": stat.st_size,
        "size_kb": round(stat.st_size / 1024, 1),
        "size_mb": round(stat.st_size / (1024 * 1024), 2),
    }


def human_size(num_bytes: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if num_bytes < 1024:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} TB"


def scan_upload_folder() -> list[dict]:
    """Scan the uploads folder and return file info for all supported files."""
    files = list_files_recursive(DATA_UPLOADS_PATH)
    return [get_file_info(f) for f in files]
