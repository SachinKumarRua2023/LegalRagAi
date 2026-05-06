"""Tool definitions for the legal AI agent."""
from __future__ import annotations
from typing import Any

from src.rag.pipeline import query, query_file, query_folder
from src.vector_db.indexer import index_file, index_directory, get_index_status
from src.vector_db.vector_client import list_indexed_files
from src.utils.file_utils import scan_upload_folder, list_files_recursive, get_file_info
from config.settings import DATA_RAW_PATH, DATA_UPLOADS_PATH


# ── Tool functions ────────────────────────────────────────────────────────────

def tool_search(question: str, top_k: int = 5) -> dict[str, Any]:
    """Semantic search across all indexed documents."""
    return query(question, n_results=top_k)


def tool_search_in_file(file_name: str, question: str) -> dict[str, Any]:
    """Search within a specific file by name."""
    return query_file(file_name, question)


def tool_search_in_folder(folder_path: str, question: str) -> dict[str, Any]:
    """Search within all files in a specific folder."""
    return query_folder(folder_path, question)


def tool_list_indexed_files() -> list[dict]:
    """List all files currently indexed in the vector database."""
    return list_indexed_files()


def tool_index_file(file_path: str) -> dict[str, Any]:
    """Index a single file into the vector database."""
    return index_file(file_path)


def tool_index_folder(folder_path: str) -> dict[str, Any]:
    """Index all supported files in a folder."""
    return index_directory(folder_path)


def tool_get_index_status() -> dict[str, Any]:
    """Get statistics about the current vector database index."""
    return get_index_status()


def tool_scan_uploads() -> list[dict]:
    """Scan the uploads folder for available files."""
    return scan_upload_folder()


def tool_search_by_type(file_type: str, question: str, top_k: int = 5) -> dict[str, Any]:
    """Search only in documents of a specific type (pdf, docx, pptx, etc.)."""
    return query(question, n_results=top_k, filter_file_type=file_type)


# ── Tool registry ─────────────────────────────────────────────────────────────

TOOLS = {
    "search": tool_search,
    "search_in_file": tool_search_in_file,
    "search_in_folder": tool_search_in_folder,
    "list_files": tool_list_indexed_files,
    "index_file": tool_index_file,
    "index_folder": tool_index_folder,
    "index_status": tool_get_index_status,
    "scan_uploads": tool_scan_uploads,
    "search_by_type": tool_search_by_type,
}

TOOL_DESCRIPTIONS = {
    "search": "Search all documents with a question. Usage: search('<question>')",
    "search_in_file": "Search within a specific file. Usage: search_in_file('<filename>', '<question>')",
    "search_in_folder": "Search within a folder. Usage: search_in_folder('<folder_path>', '<question>')",
    "list_files": "List all indexed files in the database.",
    "index_file": "Index a single file. Usage: index_file('<path>')",
    "index_folder": "Index all files in a folder. Usage: index_folder('<path>')",
    "index_status": "Show database statistics.",
    "scan_uploads": "Show files in the uploads folder.",
    "search_by_type": "Search only in a specific file type. Usage: search_by_type('pdf', '<question>')",
}
