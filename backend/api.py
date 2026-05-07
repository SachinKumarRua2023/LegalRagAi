"""
FastAPI backend server for CompleteRagAI.
Deploy on Railway (free) or Render (free), then point frontend to its URL.

Run locally: uvicorn backend.api:app --reload --port 8000
"""
from __future__ import annotations
import os
import sys
import shutil
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Make root importable when running from backend/
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag.pipeline import query as rag_query
from src.vector_db.indexer import index_file, index_directory, get_index_status
from src.vector_db.vector_client import list_indexed_files
from config.settings import DATA_UPLOADS_PATH, SUPPORTED_EXTENSIONS
from backend.auth import authenticate, get_current_user

app = FastAPI(
    title="CompleteRagAI — Legal Research API",
    description="RAG API for US legal case research. ChromaDB + Groq/Gemini/Claude.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://legal-rag-ai.vercel.app",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Startup: Auto-install sample data if vector DB is empty ────────────────────

@app.on_event("startup")
async def startup_event():
    print("[Startup] LegalRagAI ready. Embeddings: Google | Vector DB: Pinecone | LLM: Groq")


# ── Request / Response models ─────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


class QueryRequest(BaseModel):
    question: str
    top_k: int = 5
    filter_file: Optional[str] = None
    filter_folder: Optional[str] = None
    filter_file_type: Optional[str] = None


class QueryResponse(BaseModel):
    answer: str
    sources: list[dict]
    query: str
    chunks_retrieved: int


# ── Routes ───────────────────────────────────���─────────────────────────���──────

@app.get("/")
def root():
    return {"status": "ok", "service": "CompleteRagAI", "docs": "/docs"}


@app.get("/api/health")
def health():
    return {"status": "healthy"}


@app.post("/api/login")
def login(req: LoginRequest):
    """Authenticate and return a JWT token."""
    return authenticate(req.username, req.password)


@app.post("/api/query", response_model=QueryResponse)
def query_endpoint(req: QueryRequest, user: dict = Depends(get_current_user)):
    """Run a RAG query against the vector database."""
    try:
        result = rag_query(
            question=req.question,
            n_results=req.top_k,
            filter_file=req.filter_file,
            filter_folder=req.filter_folder,
            filter_file_type=req.filter_file_type,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/files")
def list_files(user: dict = Depends(get_current_user)):
    """List all files currently indexed in the vector DB."""
    try:
        return list_indexed_files()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/status")
def index_status():
    """Get vector database statistics (public — used for keep-alive ping)."""
    try:
        return get_index_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/upload")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    """Upload a file and index it into the vector DB, tagged with the uploader."""
    ext = Path(file.filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Supported: {sorted(SUPPORTED_EXTENSIONS)}",
        )

    dest = DATA_UPLOADS_PATH / file.filename
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    result = index_file(dest, extra_metadata={"uploaded_by": user["username"]})
    return {"status": "indexed", "file": file.filename, "uploaded_by": user["username"], "result": result}


@app.post("/api/ingest/download")
def trigger_download(background_tasks: BackgroundTasks, cases_per_topic: int = 20):
    """Trigger a background download of mixed legal case data."""
    def _download():
        from src.data_ingestion.downloaders.auto_downloader import download_mixed_legal_data
        from src.vector_db.indexer import index_directory
        from config.settings import DATA_RAW_PATH
        result = download_mixed_legal_data(cases_per_topic=cases_per_topic)
        index_directory(DATA_RAW_PATH / "mixed")

    background_tasks.add_task(_download)
    return {"status": "started", "message": f"Downloading {cases_per_topic} cases per topic in background"}


@app.post("/api/ingest/folder")
def ingest_folder(folder_path: str):
    """Index all supported files in a given folder path."""
    p = Path(folder_path)
    if not p.exists():
        raise HTTPException(status_code=404, detail=f"Folder not found: {folder_path}")
    result = index_directory(p)
    return result


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("backend.api:app", host="0.0.0.0", port=port, reload=False)
