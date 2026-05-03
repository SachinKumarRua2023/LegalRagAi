# CompleteRagAI — Full Technical Documentation

## Overview

**CompleteRagAI** is a production-ready **Retrieval-Augmented Generation (RAG) system** designed specifically for US legal case research. It combines semantic search capabilities with AI-powered question answering, enabling users to query across legal documents (PDFs, DOCX, PPTX, XLSX, CSV, TXT, JSON) and receive cited, contextual responses.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Technology Stack Deep Dive](#technology-stack-deep-dive)
3. [Data Flow Pipeline](#data-flow-pipeline)
4. [Auto-Install Data Issue Analysis](#auto-install-data-issue-analysis)
5. [Deployment Guide](#deployment-guide)
6. [API Reference](#api-reference)
7. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER INTERFACES                                │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────────────┐  │
│  │  CLI Tool   │    │  Web API    │    │   Interactive Legal Agent       │  │
│  │  main.py    │    │  backend/   │    │   (REPL with intent detection)  │  │
│  └──────┬──────┘    └──────┬──────┘    └──────────────┬──────────────────┘  │
└─────────┼──────────────────┼─────────────────────────┼──────────────────────┘
          │                  │                         │
          └──────────────────┼─────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           RAG PIPELINE LAYER                                │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────────┐  │
│  │   Retriever     │───▶│ Context Builder │───▶│      LLM Generator      │  │
│  │  (Semantic)     │    │  (Format LLM    │    │  (Groq/Gemini/Claude)   │  │
│  │                 │    │   context)      │    │                         │  │
│  └─────────────────┘    └─────────────────┘    └─────────────────────────┘  │
│           ▲                                                        │        │
│           │                                                        ▼        │
│           │                                               ┌────────────────┐ │
│           │                                               │  Cited Answer  │ │
│           │                                               │  with Sources  │ │
│           │                                               └────────────────┘ │
└───────────┼──────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         VECTOR DATABASE LAYER                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      ChromaDB (Persistent)                          │   │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────┐  │   │
│  │  │ Collection  │    │ Embeddings  │    │  Metadata + Document    │  │   │
│  │  │ (legal_     │◄───│  (384-dim   │◄───│  Storage (HNSW Index)   │  │   │
│  │  │  cases)     │    │  vectors)   │    │                         │  │   │
│  │  └─────────────┘    └─────────────┘    └─────────────────────────┘  │   │
│  │         ▲                                                          │   │
│  │         │              Cosine Similarity Search                     │   │
│  └─────────┼──────────────────────────────────────────────────────────┘   │
└────────────┼────────────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        EMBEDDING ENGINE LAYER                               │
│  ┌─────────────────────────┐        ┌─────────────────────────────────────┐   │
│  │  Local (Default)        │        │  Google (Optional)                  │   │
│  │  ├─ sentence-transformers│        │  ├─ text-embedding-004              │   │
│  │  ├─ all-MiniLM-L6-v2    │        │  ├─ 768-dim vectors                 │   │
│  │  ├─ 384-dim vectors     │        │  ├─ Requires GOOGLE_API_KEY        │   │
│  │  ├─ 100% Free/Local     │        │  ├─ Better quality                  │   │
│  │  └─ No API key needed   │        │  └─ Free tier available             │   │
│  └─────────────────────────┘        └─────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      DATA INGESTION LAYER                                   │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────────┐  │
│  │  File Parsers   │    │  Text Chunker   │    │  Auto-Downloader        │  │
│  │  ├─ PDF         │    │  (Recursive     │    │  ├─ Oyez.org (SCOTUS)   │  │
│  │  ├─ DOCX/DOC    │    │   overlap)      │    │  ├─ HuggingFace         │  │
│  │  ├─ PPTX/PPT    │    │                 │    │     (CaseHOLD)          │  │
│  │  ├─ XLSX/XLS    │    │  Config:        │    │                         │  │
│  │  ├─ CSV         │    │  chunk_size=1000│    │  Saves: TXT/JSON/       │  │
│  │  ├─ TXT/MD/RTF  │    │  overlap=200    │    │  DOCX/PPTX/XLSX/CSV     │  │
│  │  └─ JSON        │    │                 │    │                         │  │
│  └─────────────────┘    └─────────────────┘    └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Technology Stack Deep Dive

### 1. **Vector Database: ChromaDB**

**File:** `src/vector_db/chroma_client.py`

**What it does:**
ChromaDB is an open-source, AI-native embedding database that stores and queries vector embeddings. Unlike cloud-based vector DBs (Pinecone, Weaviate, Qdrant Cloud), ChromaDB runs **100% locally** with zero external dependencies.

**Key Features:**
- **Persistent storage**: Data survives between sessions (`chromadb.PersistentClient`)
- **HNSW indexing**: Hierarchical Navigable Small World algorithm for fast approximate nearest neighbor (ANN) search
- **Cosine similarity**: Configured with `"hnsw:space": "cosine"` for semantic search
- **Metadata filtering**: Filter by file name, folder path, file type using Chroma's `where` clause

**Implementation Details:**
```python
# @src/vector_db/chroma_client.py:28-32
collection = client.get_or_create_collection(
    name=name,
    metadata={"hnsw:space": "cosine"},  # Cosine similarity for semantic search
)
```

**Why ChromaDB?**
- Free forever (no usage limits)
- No API keys required
- Embeddable in any Python application
- Supports metadata-based filtering

---

### 2. **Embedding Engine: Dual Backend System**

**File:** `src/vector_db/embeddings.py`

**What it does:**
Converts text into high-dimensional vector representations that capture semantic meaning. The system supports two backends:

#### **A. Local Embedding Engine (Default)**
**Model:** `sentence-transformers/all-MiniLM-L6-v2`

**Specifications:**
- **Dimensions:** 384
- **Size:** ~80MB
- **Speed:** ~1000 docs/sec on CPU
- **Cost:** $0 (runs on your hardware)
- **Quality:** Excellent for semantic similarity

**Implementation:**
```python
# @src/vector_db/embeddings.py:17-32
class LocalEmbeddingEngine:
    def __init__(self, model_name: str = LOCAL_EMBEDDING_MODEL):
        from sentence_transformers import SentenceTransformer
        self._model = SentenceTransformer(model_name)
        
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vecs = self._model.encode(texts, normalize_embeddings=True)
        return vecs.tolist()
```

#### **B. Google Embedding Engine (Optional)**
**Model:** `models/text-embedding-004`

**Specifications:**
- **Dimensions:** 768
- **Quality:** State-of-the-art
- **Free tier:** 1 million tokens/day at no cost
- **Cost:** Requires `GOOGLE_API_KEY`

**Why Dual Backends?**
- **Local** for privacy-sensitive deployments and zero cost
- **Google** for higher quality when API access is available

---

### 3. **Document Parsing System**

**File:** `src/data_ingestion/parsers/document_router.py`

**What it does:**
Routes files to specialized parsers based on extension. Each parser extracts text while preserving structural information (pages, sections, tables).

#### **PDF Parser (`_parse_pdf`)**
- **Library:** `pdfplumber`
- **Capabilities:** 
  - Text extraction per page
  - Table extraction with row/column preservation
  - Page-level metadata tracking
- **Output:** Chunks with `page_number`, `section`, `total_pages`

#### **DOCX Parser (`_parse_docx`)**
- **Library:** `python-docx`
- **Capabilities:**
  - Heading detection (paragraph style analysis)
  - Section-based chunking
  - Table extraction
- **Output:** Chunks with `section` (heading context)

#### **PPTX Parser (`_parse_pptx`)**
- **Library:** `python-pptx`
- **Capabilities:**
  - Slide-by-slide extraction
  - Title detection (shape type 13)
  - Text box content extraction
- **Output:** Chunks with `slide_number`, `total_slides`

#### **Excel Parser (`_parse_excel`)**
- **Library:** `openpyxl`
- **Capabilities:**
  - Multi-sheet support
  - Row-batch chunking (50 rows per chunk to avoid memory issues)
  - JSON serialization of row data
- **Output:** Chunks with `sheet` name

#### **CSV Parser (`_parse_csv`)**
- **Standard library:** `csv.DictReader`
- **Capabilities:**
  - Header-aware parsing
  - Batch chunking (50 rows per chunk)
- **Output:** JSON-serialized row batches

#### **Text/Markdown/JSON/HTML/RTF (`_parse_text`)**
- Simple text file reading with UTF-8 encoding
- Full document as single chunk

---

### 4. **Text Chunking System**

**File:** `src/data_ingestion/chunkers/text_chunker.py`

**What it does:**
Splits large documents into smaller, semantically coherent chunks that fit within embedding model context limits while preserving context through overlap.

**Algorithm: Recursive Character Text Splitting**

```python
# @config/settings.py:42-44
CHUNK_SIZE = 1000        # Maximum tokens per chunk
CHUNK_OVERLAP = 200      # Overlapping tokens between chunks
MAX_CHUNKS_PER_DOC = 500 # Safety limit
```

**Why Chunking Matters:**
- Embedding models have token limits
- Smaller chunks improve retrieval precision
- Overlap preserves context across chunk boundaries
- Legal documents often have multi-page arguments that need continuity

---

### 5. **RAG Pipeline**

**File:** `src/rag/pipeline.py`

**What it does:**
Orchestrates the full retrieval → context building → generation workflow.

**Flow:**
1. **Query Embedding**: User question → vector embedding
2. **Semantic Search**: ChromaDB ANN search with cosine similarity
3. **Filtering**: Apply file/folder/type filters via ChromaDB `where` clause
4. **Context Assembly**: Format retrieved chunks with source markers
5. **LLM Generation**: Send context + question to LLM
6. **Source Deduplication**: Return unique source list with relevance scores

**Source Citation Format:**
```
[Source 1: File: doe_v_roe.pdf | Folder: /data/raw | Page 3]
Case text here...

[Source 2: File: smith_v_jones.docx | Folder: /data/raw/contracts | Section: Facts]
Another case text...
```

---

### 6. **LLM Generator System**

**File:** `src/rag/generator.py`

**What it does:**
Generates natural language answers from retrieved context, with automatic fallback between providers.

**Priority Order (Auto Mode):**
1. **Groq** (llama-3.3-70b-versatile) — Fastest free tier, 30 RPM
2. **Gemini** (gemini-1.5-flash) — 15 RPM, 1M tokens/day
3. **Claude** (claude-haiku-4-5-20251001) — Requires API key
4. **Echo Mode** (fallback) — Returns context preview when no keys available

**System Prompt Engineering:**
```python
# @src/rag/generator.py:16-29
SYSTEM_PROMPT = """You are an expert AI legal research assistant...
1. Answer using ONLY the provided document context
2. ALWAYS cite sources using [Source N: ...] markers
3. Include "Sources Used" section at end
4. If context insufficient, say so clearly — never make up facts
"""
```

---

### 7. **Legal AI Agent**

**File:** `src/agents/legal_agent.py`

**What it does:**
Provides a conversational interface with intent detection for natural language legal research queries.

**Intent Detection:**
- `/help`, `/status`, `/quit` — Commands
- `/index <path>` — Trigger indexing
- `in file X.pdf, what is...` — File-scoped search
- `in folder /path, search for...` — Folder-scoped search  
- `search in PDFs about...` — File type filtering
- General queries — Full collection search

**Response Rendering:**
- Rich Markdown formatting
- Source table with file, folder, relevance score
- Color-coded console output

---

### 8. **Auto-Downloader System**

**File:** `src/data_ingestion/downloaders/auto_downloader.py`

**What it does:**
Automatically downloads US legal case data from free public sources and converts to multiple file formats.

**Data Sources:**

#### **A. Oyez.org API** (Supreme Court cases)
- **URL:** `https://api.oyez.org/cases`
- **Data:** SCOTUS case name, term, docket, facts, question, conclusion
- **No API key required**
- **Rate limit handling:** Built-in 0.2s delays between requests

#### **B. HuggingFace CaseHOLD Dataset**
- **Dataset:** `casehold/casehold`
- **Data:** Legal case holdings, citing context
- **Format:** Parquet files streamed
- **No authentication required** for this public dataset

**Output Formats Created:**
1. **TXT** — One file per case, plain text with headers
2. **JSON** — Structured data with metadata
3. **DOCX** — Word documents with formatted headings
4. **PPTX** — PowerPoint presentations (20 slides max)
5. **XLSX** — Excel workbook with all cases
6. **CSV** — Comma-separated values for data analysis

---

### 9. **Backend API**

**File:** `backend/api.py`

**What it does:**
FastAPI-based REST API for programmatic access.

**Endpoints:**
- `POST /api/query` — RAG query with optional filters
- `POST /api/upload` — File upload + automatic indexing
- `POST /api/ingest/download` — Trigger background data download
- `POST /api/ingest/folder` — Index a folder path
- `GET /api/status` — Collection statistics
- `GET /api/files` — List indexed files
- `GET /api/health` — Health check

**CORS Configuration:**
- Allows frontend requests from any origin (development)
- Supports credentials and all HTTP methods

---

### 10. **Frontend**

**Folder:** `frontend/`

**What it does:**
Modern React-based web interface for non-technical users.

**Technology:**
- React 18 with hooks
- Tailwind CSS for styling
- Lucide React for icons
- Fetch API for backend communication

**Features:**
- Chat interface with message history
- File upload with drag-and-drop
- Source citation display
- Typing indicators
- Error handling

---

## Data Flow Pipeline

### Ingestion Flow

```
User File / Auto-Download
         │
         ▼
┌─────────────────┐
│ Document Router │───► Determines parser by extension
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  File Parser    │───► Extracts text + structure (pages/slides/sheets)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Metadata Builder│───► Adds file_hash, source_path, timestamps
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Text Chunker    │───► Splits into 1000-token chunks with 200 overlap
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Embedding Engine│───► 384-dim vectors (MiniLM-L6-v2)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  ChromaDB Store │───► Upsert with unique IDs, metadata, vectors
└─────────────────┘
```

### Query Flow

```
User Query
    │
    ▼
┌─────────────────┐
│  Intent Parse   │───► LegalAgent detects file/folder/type filters
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Query Embedder  │───► Convert question to 384-dim vector
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ ChromaDB Query  │───► ANN search with cosine similarity
│  (with filters) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Result Filter   │───► Apply min_score threshold (default 0.3)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Context Builder │───► Format with [Source N] markers
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  LLM Generator  │───► Groq/Gemini/Claude generates answer
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Source Deduplic │───► Remove duplicate file sources
└────────┬────────┘
         │
         ▼
    ┌────────┐
    │ Answer │───► With citations + Sources Used section
    │+Sources│
    └────────┘
```

---

## Auto-Install Data Issue Analysis

### ❌ **THE PROBLEM**

The data is **NOT automatically installed** on first run. The user must manually trigger downloads.

### 🔍 **Root Cause Analysis**

**1. No Auto-Trigger on Import/Init**

Looking at the code flow:

```python
# @main.py:60-63 — Interactive mode entry point
def main():
    # ... argument parsing ...
    from src.agents.legal_agent import LegalAgent
    agent = LegalAgent()
    agent.run_interactive()  # Just starts the REPL, no data check
```

**The `LegalAgent.__init__()` does NOT check if data exists or trigger downloads.**

**2. Manual Trigger Required**

Downloads only happen when explicitly requested:

```python
# @ingest.py:46-56 — Only runs with --download auto flag
if args.download == "auto":
    from src.data_ingestion.downloaders.auto_downloader import download_mixed_legal_data
    result = download_mixed_legal_data(cases_per_topic=args.limit // 10 or 30)
```

**3. API Also Requires Explicit Call**

```python
# @backend/api.py:125-136
@app.post("/api/ingest/download")
def trigger_download(background_tasks: BackgroundTasks, cases_per_topic: int = 20):
    """Trigger a background download..."""
    def _download():
        result = download_mixed_legal_data(cases_per_topic=cases_per_topic)
        index_directory(DATA_RAW_PATH / "mixed")
    background_tasks.add_task(_download)
```

This endpoint requires a POST request — it's not called automatically.

### 🛠️ **The Fix: Auto-Install on Startup**

To enable automatic data download when the vector database is empty, add this initialization check:

#### **Option A: Add to `main.py`**

```python
# @main.py — Add after imports
def ensure_data_available():
    """Auto-download sample data if vector DB is empty."""
    from src.vector_db.indexer import get_index_status
    from src.data_ingestion.downloaders.auto_downloader import download_mixed_legal_data
    from src.vector_db.indexer import index_directory
    from config.settings import DATA_RAW_PATH
    
    status = get_index_status()
    if status.get("total_chunks", 0) == 0:
        print("[Init] No data found. Auto-downloading legal cases...")
        result = download_mixed_legal_data(cases_per_topic=50)
        index_directory(DATA_RAW_PATH / "mixed")
        print(f"[Init] Auto-indexed {result['total_cases']} cases")

# Call in main() before starting interactive mode:
def main():
    # ... existing code ...
    ensure_data_available()  # Add this line
    agent = LegalAgent()
    agent.run_interactive()
```

#### **Option B: Add to `LegalAgent.__init__`**

```python
# @src/agents/legal_agent.py:33-40
class LegalAgent:
    def __init__(self):
        # ... existing init code ...
        self._ensure_data()
    
    def _ensure_data(self):
        """Auto-populate with sample data if empty."""
        status = get_index_status()
        if status.get("total_chunks", 0) == 0:
            console.print("[yellow]No indexed data found. Downloading sample legal cases...[/yellow]")
            from src.data_ingestion.downloaders.auto_downloader import download_mixed_legal_data
            from src.vector_db.indexer import index_directory
            from config.settings import DATA_RAW_PATH
            result = download_mixed_legal_data(cases_per_topic=50)
            index_directory(DATA_RAW_PATH / "mixed")
            console.print(f"[green]✓ Auto-downloaded {result['total_cases']} cases[/green]")
```

#### **Option C: Add to Backend Startup**

```python
# @backend/api.py — Add after app creation
@app.on_event("startup")
async def startup_event():
    """Auto-download data on server start if DB is empty."""
    from src.vector_db.indexer import get_index_status
    from src.data_ingestion.downloaders.auto_downloader import download_mixed_legal_data
    from src.vector_db.indexer import index_directory
    from config.settings import DATA_RAW_PATH
    
    status = get_index_status()
    if status.get("total_chunks", 0) == 0:
        print("[Startup] Vector DB empty. Downloading sample data...")
        result = download_mixed_legal_data(cases_per_topic=50)
        index_directory(DATA_RAW_PATH / "mixed")
        print(f"[Startup] Indexed {result['total_cases']} cases")
```

### ✅ **Recommended Implementation**

Add the startup check to `backend/api.py` for the API server and to `main.py` for CLI usage. This provides:
- **Zero-config first run**: Works immediately without manual steps
- **Non-destructive**: Only downloads if DB is empty
- **Configurable**: Can be disabled via environment variable

---

## Deployment Guide

### Local Development

```bash
# 1. Clone repository
git clone <repo-url>
cd CompleteRagAi

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment (optional but recommended)
cp .env.example .env
# Edit .env with your API keys

# 5. Run data ingestion (manual - THE ISSUE!)
python ingest.py --download auto --limit 500

# 6. Start interactive agent
python main.py

# 7. Or start API server
python backend/api.py
```

### Production Deployment

#### Docker

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create data directories
RUN mkdir -p data/raw data/processed data/uploads chroma_db

# Auto-download on container start (if implementing fix)
# RUN python -c "from src.data_ingestion.downloaders.auto_downloader import download_mixed_legal_data; download_mixed_legal_data(50)"

EXPOSE 8000
CMD ["uvicorn", "backend.api:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Render.com (Cloud)

```yaml
# render.yaml
services:
  - type: web
    name: complete-rag-ai
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn backend.api:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.0
      - key: GROQ_API_KEY
        sync: false
      - key: GOOGLE_API_KEY
        sync: false
```

---

## API Reference

### Query Endpoint

```bash
POST /api/query
Content-Type: application/json

{
  "question": "What are the key facts in Miranda v. Arizona?",
  "top_k": 5,
  "filter_file": null,
  "filter_folder": null,
  "filter_file_type": null
}
```

**Response:**
```json
{
  "answer": "According to [Source 1: File: miranda_cases.txt...], the key facts were...",
  "sources": [
    {
      "source_file": "miranda_cases.txt",
      "source_path": "/app/data/raw/mixed/scotus/miranda_cases.txt",
      "source_folder": "/app/data/raw/mixed/scotus",
      "source_citation": "File: miranda_cases.txt | Folder: ... | Page 1",
      "relevance_score": 0.89
    }
  ],
  "query": "What are the key facts in Miranda v. Arizona?",
  "chunks_retrieved": 3
}
```

---

## Troubleshooting

### Issue: "No data found" / Empty results

**Cause:** Data not downloaded/indexed.

**Fix:**
```bash
python ingest.py --download auto --limit 500
python ingest.py  # Index the downloaded files
```

### Issue: "No API key found — running in echo mode"

**Cause:** No LLM provider configured.

**Fix:** Add API key to `.env`:
```bash
GROQ_API_KEY=gsk_xxxxx
# or
GOOGLE_API_KEY=AIxxxxx
```

### Issue: ChromaDB permission errors

**Cause:** Directory not writable.

**Fix:**
```bash
chmod -R 755 chroma_db/
# Or change CHROMA_DB_PATH in .env
```

### Issue: Sentence transformers download fails

**Cause:** First-time model download requires internet.

**Fix:** The model downloads automatically on first use (~80MB). If blocked:
```bash
# Pre-download
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
```

---

## File Structure Summary

```
CompleteRagAi/
├── config/settings.py              # Central configuration
├── src/
│   ├── vector_db/
│   │   ├── chroma_client.py      # ChromaDB CRUD operations
│   │   ├── embeddings.py         # Local + Google embedding engines
│   │   └── indexer.py            # High-level indexing orchestrator
│   ├── data_ingestion/
│   │   ├── parsers/
│   │   │   └── document_router.py # Multi-format file parser
│   │   ├── chunkers/
│   │   │   └── text_chunker.py   # Recursive text splitting
│   │   └── downloaders/
│   │       └── auto_downloader.py # Oyez + HuggingFace download
│   ├── rag/
│   │   ├── pipeline.py           # Full RAG orchestration
│   │   ├── retriever.py          # Semantic search + filtering
│   │   └── generator.py          # LLM response generation
│   └── agents/
│       ├── legal_agent.py        # Conversational AI interface
│       └── tools.py              # Agent tool definitions
├── backend/
│   └── api.py                    # FastAPI REST endpoints
├── frontend/                     # React web interface
├── main.py                       # CLI entry point
├── ingest.py                     # Data ingestion CLI
└── requirements.txt              # Python dependencies
```

---

## Summary

**CompleteRagAI** is a fully-featured legal RAG system with:
- **Free vector database** (ChromaDB) with persistent local storage
- **Dual embedding backends** (local MiniLM-L6-v2 or Google text-embedding-004)
- **Multi-format document parsing** (PDF, DOCX, PPTX, XLSX, CSV, TXT, JSON)
- **Semantic search** with file/folder/type filtering
- **Multi-provider LLM generation** (Groq, Gemini, Claude) with auto-fallback
- **Conversational AI agent** with natural language intent detection
- **REST API** for programmatic access
- **Modern React frontend**

**The main issue** is that sample legal data is not auto-installed on first run. The fix requires adding a startup check to `main.py`, `LegalAgent.__init__`, or `backend/api.py` that triggers `download_mixed_legal_data()` when the vector database is empty.

---

*Documentation generated for CompleteRagAI — US Legal RAG System*
