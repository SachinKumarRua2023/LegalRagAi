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

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Depends, Request, Form
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
from src.integrations.odoo_client import log_to_odoo
from config.settings import VAPI_API_KEY, HUMAN_TRANSFER_NUMBER, SUPPORT_EMAIL

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
def query_endpoint(
    req: QueryRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
):
    """Run a RAG query against the vector database."""
    try:
        result = rag_query(
            question=req.question,
            n_results=req.top_k,
            filter_file=req.filter_file,
            filter_folder=req.filter_folder,
            filter_file_type=req.filter_file_type,
        )
        # Log to Odoo CRM in background (never slows the response)
        background_tasks.add_task(
            log_to_odoo,
            username=user["username"],
            question=req.question,
            answer=result["answer"],
            sources=result["sources"],
            chunks_retrieved=result["chunks_retrieved"],
            channel="web",
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


# ── Make / n8n / Zapier automation endpoint (no JWT, uses shared secret) ──────

AUTOMATION_SECRET = os.getenv("AUTOMATION_SECRET", "legalrag-automation-2026")

@app.post("/api/automate/query")
def automation_query(req: AutomationQueryRequest, background_tasks: BackgroundTasks):
    """
    Public endpoint for Make / n8n / Zapier.
    Protected by AUTOMATION_SECRET env var instead of JWT.
    Accepts a question + sender info, returns AI answer.
    """
    if req.secret != AUTOMATION_SECRET:
        raise HTTPException(status_code=403, detail="Invalid automation secret.")
    try:
        result = rag_query(question=req.question, n_results=5)
        background_tasks.add_task(
            log_to_odoo,
            username=req.from_email,
            question=req.question,
            answer=result["answer"],
            sources=result["sources"],
            chunks_retrieved=result["chunks_retrieved"],
            channel="email",
        )
        return {
            "answer": result["answer"],
            "sources_count": len(result["sources"]),
            "top_source": result["sources"][0]["source_file"] if result["sources"] else "",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/automate/query/form")
async def automation_query_form(
    background_tasks: BackgroundTasks,
    question: str = Form(...),
    from_email: str = Form("automation@system"),
    from_name: str = Form("Automation"),
    secret: str = Form(""),
):
    """
    Form-data version for Make.com — avoids JSON escaping issues with special characters.
    Use Body content type: application/x-www-form-urlencoded in Make HTTP module.
    """
    if secret != AUTOMATION_SECRET:
        raise HTTPException(status_code=403, detail="Invalid automation secret.")
    try:
        result = rag_query(question=question, n_results=5)
        background_tasks.add_task(
            log_to_odoo,
            username=from_email,
            question=question,
            answer=result["answer"],
            sources=result["sources"],
            chunks_retrieved=result["chunks_retrieved"],
            channel="email",
        )
        return {
            "answer": result["answer"],
            "sources_count": len(result["sources"]),
            "top_source": result["sources"][0]["source_file"] if result["sources"] else "",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── VAPI Voice AI webhook ─────────────────────────────────────────────────────

@app.post("/api/vapi/webhook")
async def vapi_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    VAPI calls this when a user asks a question over the phone.
    VAPI sends the transcribed question → we run RAG → return answer as text → VAPI speaks it.
    """
    try:
        body = await request.json()
        message = body.get("message", {})
        msg_type = message.get("type", "")

        # Function/tool call from VAPI assistant
        if msg_type == "function-call":
            func = message.get("functionCall", {})
            params = func.get("parameters", {})
            if isinstance(params, str):
                import json as _json
                params = _json.loads(params)
            question = params.get("question", params.get("query", ""))
            if not question:
                return {"result": "I didn't catch your question. Could you please repeat it?"}

            result = rag_query(question=question, n_results=5)
            # Keep answer concise for voice (strip markdown)
            answer = result["answer"].replace("**", "").replace("##", "").replace("#", "")
            answer = answer[:1500]  # Voice responses should be shorter

            background_tasks.add_task(
                log_to_odoo,
                username="voice_caller",
                question=question,
                answer=answer,
                sources=result["sources"],
                chunks_retrieved=result["chunks_retrieved"],
                channel="voice",
            )
            return {"result": answer}

        # Call ended — log summary
        if msg_type == "end-of-call-report":
            print(f"[VAPI] Call ended: {body.get('endedReason', 'unknown')}")
            return {"status": "logged"}

        return {"status": "ok"}
    except Exception as e:
        print(f"[VAPI] Webhook error: {e}")
        return {"result": "I'm having technical difficulties. Please try again or call our support team."}


# ── Support ticket endpoint ───────────────────────────────────────────────────

class AutomationQueryRequest(BaseModel):
    question: str
    from_email: str = "automation@system"
    from_name: str = "Automation"
    secret: str = ""  # simple shared secret to prevent abuse


class LegalDraftRequest(BaseModel):
    question: str
    from_email: str = "automation@system"
    from_name: str = "Client"
    secret: str = ""
    attachment_text: str = ""  # extracted text from email attachment (optional)


@app.post("/api/automate/query/legal")
async def legal_draft_endpoint(req: LegalDraftRequest, background_tasks: BackgroundTasks):
    """
    Full legal AI pipeline:
    1. RAG query → Pinecone case documents
    2. Tavily internet search → relevant legal cases, statutes, precedents
    3. Claude drafts a professional formal legal letter using all context
    Returns a citation-rich, court-ready legal email reply.
    """
    if req.secret != AUTOMATION_SECRET:
        raise HTTPException(status_code=403, detail="Invalid automation secret.")
    try:
        # Step 1: RAG against Pinecone
        rag_result = rag_query(question=req.question, n_results=8)

        # Step 2: Internet legal research via Tavily
        from src.integrations.web_search import search_legal_evidence
        web_results = search_legal_evidence(req.question, max_results=5)

        # Step 3: Claude drafts professional legal letter
        from src.integrations.legal_drafter import draft_legal_email
        professional_reply = draft_legal_email(
            question=req.question,
            rag_answer=rag_result["answer"],
            rag_sources=rag_result["sources"],
            web_results=web_results,
            attachment_text=req.attachment_text,
            from_name=req.from_name,
        )

        background_tasks.add_task(
            log_to_odoo,
            username=req.from_email,
            question=req.question,
            answer=professional_reply,
            sources=rag_result["sources"],
            chunks_retrieved=rag_result["chunks_retrieved"],
            channel="email_legal",
        )

        drafted = professional_reply
        return {
            "professional_reply": drafted["body"],
            "email_subject": drafted["subject"],
            "rag_answer": rag_result["answer"],
            "web_sources_found": len(web_results),
            "chunks_retrieved": rag_result["chunks_retrieved"],
            "source_files": [s["source_file"] for s in rag_result["sources"][:3]],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/automate/query/legal/form")
async def legal_draft_form(
    background_tasks: BackgroundTasks,
    question: str = Form(...),
    from_email: str = Form("automation@system"),
    from_name: str = Form("Client"),
    secret: str = Form(""),
    attachment_text: str = Form(""),
    attachment_base64: str = Form(""),
    attachment_filename: str = Form(""),
):
    """
    Form-data version for Make.com.
    Returns: professional_reply (HTML body) + email_subject (professional subject line).
    Accepts attachment as base64 string — no multipart upload needed from Make.com.
    """
    if secret != AUTOMATION_SECRET:
        raise HTTPException(status_code=403, detail="Invalid automation secret.")

    # Decode base64 attachment and extract text if no attachment_text already provided
    if attachment_base64.strip() and attachment_filename.strip() and not attachment_text.strip():
        try:
            import base64 as _base64
            b64 = attachment_base64.strip().replace('-', '+').replace('_', '/')
            b64 += '=' * (4 - len(b64) % 4)
            file_bytes = _base64.b64decode(b64)
            ext = Path(attachment_filename).suffix.lower()
            if ext in SUPPORTED_EXTENSIONS:
                with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                    tmp.write(file_bytes)
                    tmp_path = Path(tmp.name)
                try:
                    from src.data_ingestion.parsers.document_router import parse_document
                    extracted = parse_document(tmp_path)
                    if extracted and extracted.strip():
                        attachment_text = extracted[:3000]
                        print(f"[AutomateLegal] Extracted {len(attachment_text)} chars from attachment: {attachment_filename}")
                    try:
                        index_file(tmp_path, extra_metadata={"source": "email_attachment", "filename": attachment_filename})
                        print(f"[AutomateLegal] Indexed attachment to Pinecone: {attachment_filename}")
                    except Exception as idx_e:
                        print(f"[AutomateLegal] Pinecone indexing failed (non-fatal): {idx_e}")
                finally:
                    tmp_path.unlink(missing_ok=True)
        except Exception as e:
            print(f"[AutomateLegal] Base64 attachment processing failed (non-fatal): {e}")

    # Each step is individually resilient — always returns HTTP 200 with a reply
    try:
        rag_result = rag_query(question=question, n_results=8)
    except Exception as e:
        print(f"[AutomateLegal] RAG query failed (non-fatal): {e}")
        rag_result = {"answer": "Unable to retrieve case documents at this time.", "sources": [], "chunks_retrieved": 0}

    try:
        from src.integrations.web_search import search_legal_evidence
        web_results = search_legal_evidence(question, max_results=5)
    except Exception as e:
        print(f"[AutomateLegal] Web search failed (non-fatal): {e}")
        web_results = []

    try:
        from src.integrations.legal_drafter import draft_legal_email
        drafted = draft_legal_email(
            question=question,
            rag_answer=rag_result["answer"],
            rag_sources=rag_result["sources"],
            web_results=web_results,
            attachment_text=attachment_text,
            from_name=from_name,
        )
    except Exception as e:
        print(f"[AutomateLegal] Drafting failed (non-fatal): {e}")
        from datetime import date
        today = date.today().strftime("%B %d, %Y")
        drafted = {
            "subject": f"Legal Response: {question[:70]}",
            "body": f'<div style="font-family:Georgia,serif;max-width:700px;color:#1a1a1a;line-height:1.8;"><p style="color:#555;">{today}</p><p>Dear {from_name},</p><p>Thank you for your inquiry. Our team has received your message and will respond shortly with a detailed legal analysis.</p><p>Respectfully submitted,<br><strong>Legal AI Research Assistant</strong></p></div>',
        }

    try:
        background_tasks.add_task(
            log_to_odoo,
            username=from_email,
            question=question,
            answer=drafted["body"],
            sources=rag_result["sources"],
            chunks_retrieved=rag_result["chunks_retrieved"],
            channel="email_legal",
        )
    except Exception:
        pass

    return {
        "professional_reply": drafted["body"],
        "email_subject": drafted["subject"],
        "web_sources_found": len(web_results),
        "chunks_retrieved": rag_result["chunks_retrieved"],
        "source_files": [s["source_file"] for s in rag_result["sources"][:3]],
    }


# ── Automation file upload → auto-index to Pinecone ──────────────────────────

@app.post("/api/automate/upload")
async def automation_upload(
    file: UploadFile = File(...),
    secret: str = Form(""),
):
    """
    Secret-protected file upload for Make.com automation.
    Accepts email attachment → parses text → indexes to Pinecone → returns extracted text.
    Make.com: use multipart/form-data, pass file + secret fields.
    """
    if secret != AUTOMATION_SECRET:
        raise HTTPException(status_code=403, detail="Invalid automation secret.")

    ext = Path(file.filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Supported: {sorted(SUPPORTED_EXTENSIONS)}",
        )

    # Save to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)

    try:
        # Index to Pinecone (parse + chunk + embed + store)
        result = index_file(tmp_path, extra_metadata={"source": "email_attachment", "filename": file.filename})

        # Extract text for immediate use in the reply
        from src.data_ingestion.parsers.document_router import parse_document
        extracted_text = parse_document(tmp_path)
        preview = extracted_text[:3000] if extracted_text else ""

        return {
            "status": "indexed",
            "filename": file.filename,
            "extracted_text": preview,
            "chunks_indexed": result.get("chunks_added", 0),
        }
    finally:
        tmp_path.unlink(missing_ok=True)


class SupportTicketRequest(BaseModel):
    name: str
    email: str
    subject: str
    description: str


@app.post("/api/support/ticket")
def create_support_ticket(req: SupportTicketRequest):
    """Create a support ticket in Odoo CRM."""
    try:
        from src.integrations.odoo_client import get_odoo_client
        client = get_odoo_client()
        if client:
            ticket_id = client.create_support_ticket(
                req.name, req.email, req.subject, req.description
            )
            return {"status": "created", "ticket_id": ticket_id}
        return {"status": "queued", "message": f"Report sent to {SUPPORT_EMAIL}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/support/info")
def support_info():
    """Returns support contact details for the frontend."""
    return {
        "email": SUPPORT_EMAIL,
        "phone": HUMAN_TRANSFER_NUMBER,
        "vapi_enabled": bool(VAPI_API_KEY),
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("backend.api:app", host="0.0.0.0", port=port, reload=False)
