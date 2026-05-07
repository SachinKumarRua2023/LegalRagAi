# CompleteRagAI — Full Project Documentation
> Last updated: 2026-05-07 (session 2) | For AI assistants: read this entire file before making any changes.

---

## 1. What This Project Is

A **production-deployed RAG (Retrieval-Augmented Generation) system** for US legal case research.

- Users ask natural language questions about legal cases
- The system finds relevant document chunks from a vector DB (semantic search)
- An LLM generates an answer grounded in those chunks, with inline citations
- Built for a real legal client case: American Restoration Solutions lawsuit documents

**Live URLs:**
- Frontend: `https://legal-rag-ai.vercel.app` (Next.js on Vercel)
- Backend API: `https://legalragai.onrender.com` (FastAPI on Render free tier)
- Pinecone index: `legal-rag-768` (aws / us-east-1, 768-dim cosine)
- GitHub: `https://github.com/SachinKumarRua2023/LegalRagAi`

---

## 2. Tech Stack

| Layer | Technology | Notes |
|---|---|---|
| Frontend | Next.js 14, React, TypeScript | Deployed on Vercel |
| Backend | FastAPI, Uvicorn, Python 3.11 | Deployed on Render free tier |
| LLM (primary) | Groq — Llama 3.3 70B | Free tier: 30 RPM, 14,400 req/day |
| LLM (fallback) | Google Gemini 1.5 Flash | Free tier: 15 RPM, 1M tokens/day |
| LLM (fallback) | Anthropic Claude Haiku | Paid |
| Embeddings | Google gemini-embedding-001 | API, 768-dim, FREE (1M tokens/day), no torch needed |
| Vector DB | Pinecone (cloud) | Free tier: 2GB, 100k vectors |
| Vector DB (local dev) | ChromaDB | Local SQLite, not used in prod |
| Document parsing | pdfplumber, python-docx, python-pptx, openpyxl | 14+ file formats |
| Styling | Tailwind CSS, Lucide icons | Navy + gold legal theme |

---

## 3. Project Structure

```
CompleteRagAi/
├── backend/api.py              # FastAPI server — all REST endpoints
├── config/settings.py          # All env-var config (single source of truth)
├── ingest.py                   # CLI: index files into vector DB
├── main.py                     # CLI: interactive legal agent REPL
├── render.yaml                 # Render deployment config (auto-read by Render)
├── requirements.txt            # 39 Python packages
├── .env                        # SECRET — never committed (gitignored)
├── .env.example                # Template showing all required vars
│
├── src/
│   ├── rag/
│   │   ├── pipeline.py         # Main RAG orchestrator: query → retrieve → generate → cite
│   │   ├── retriever.py        # Semantic search with metadata filters
│   │   └── generator.py        # Multi-LLM factory (Groq/Gemini/Claude/Echo)
│   │
│   ├── vector_db/
│   │   ├── vector_client.py    # Unified abstraction — routes to chroma or pinecone
│   │   ├── pinecone_client.py  # Pinecone cloud client (USED IN PROD)
│   │   ├── chroma_client.py    # ChromaDB local client (local dev only)
│   │   ├── embeddings.py       # Local (sentence-transformers) or Google embeddings
│   │   └── indexer.py          # High-level: parse → chunk → embed → store
│   │
│   ├── data_ingestion/
│   │   ├── parsers/document_router.py  # Routes files to per-format parsers
│   │   ├── chunkers/text_chunker.py    # Recursive character splitter
│   │   └── downloaders/
│   │       ├── auto_downloader.py      # Oyez.org + HuggingFace CaseHOLD
│   │       ├── courtlistener_downloader.py
│   │       └── huggingface_downloader.py
│   │
│   ├── agents/
│   │   ├── legal_agent.py      # Interactive REPL with intent detection
│   │   └── tools.py            # 9 registered tools for the agent
│   │
│   └── utils/
│       ├── file_utils.py
│       └── metadata.py
│
├── frontend/
│   ├── app/
│   │   ├── page.tsx            # Main page: layout, theme, backend keep-alive ping
│   │   ├── layout.tsx          # Root layout with metadata + icon
│   │   ├── icon.svg            # Scales of justice favicon (navy + gold)
│   │   ├── globals.css         # Tailwind base + custom scrollbar + legal colors
│   │   └── api/                # Next.js proxy routes (server-side, hide BACKEND_URL)
│   │       ├── chat/route.ts   # POST → /api/query on backend
│   │       ├── status/route.ts # GET → /api/status on backend
│   │       ├── files/route.ts  # GET → /api/files on backend
│   │       ├── upload/route.ts # POST → /api/upload on backend
│   │       └── download/route.ts # POST → /api/ingest/download on backend
│   │
│   ├── components/
│   │   ├── ChatWindow.tsx      # Query input, message list, file type filter chips
│   │   ├── Message.tsx         # Renders user/assistant messages with markdown
│   │   ├── SourceCard.tsx      # Shows source file, relevance score, page/slide info
│   │   ├── Sidebar.tsx         # File list grouped by folder, upload zone, download button
│   │   └── UploadZone.tsx      # Drag-and-drop file upload with progress feedback
│   │
│   ├── lib/
│   │   ├── api.ts              # All fetch calls — browser → /api/* → BACKEND_URL
│   │   └── types.ts            # TypeScript: Source, QueryResponse, IndexedFile, Message
│   │
│   ├── next.config.mjs         # Next.js config with BACKEND_URL env var passthrough
│   └── vercel.json             # Vercel deployment config (no secrets, plain env vars)
│
└── data/                       # GITIGNORED — large files
    ├── raw/mixed/              # 206 files, 0.37 MB (scotus + casehold txt, already indexed)
    ├── lawsuit_2026_april/     # 52 files, 101 MB (original lawsuit docs)
    └── lawsuit_organized_deduped/ # 48 files, 89 MB (clean/deduped version)
```

---

## 4. Environment Variables

### Backend (.env / Render dashboard)
```
LLM_PROVIDER=groq                         # "groq" | "gemini" | "claude" | "auto"
GROQ_API_KEY=gsk_...                      # SECRET
GROQ_MODEL=llama-3.3-70b-versatile

EMBEDDING_MODEL=google                    # "local" | "google"
                                          # google = gemini-embedding-001, 768-dim, FREE (needs GOOGLE_API_KEY)
                                          # local = sentence-transformers, 384-dim (NOT used in prod — OOM risk)
GOOGLE_API_KEY=...                        # SECRET — required for google embeddings

VECTOR_DB_PROVIDER=pinecone               # "pinecone" | "chromadb"
PINECONE_API_KEY=pcsk_...                 # SECRET
PINECONE_INDEX_NAME=legal-rag-768         # 768-dim index (matches Google embeddings)
PINECONE_CLOUD=aws
PINECONE_REGION=us-east-1

DATA_RAW_PATH=./data/raw
DATA_PROCESSED_PATH=./data/processed
DATA_UPLOADS_PATH=./data/uploads
PORT=8000

# Optional:
GOOGLE_API_KEY=...
ANTHROPIC_API_KEY=...
COURTLISTENER_TOKEN=...
```

### Frontend (Vercel dashboard)
```
BACKEND_URL=https://legalragai.onrender.com
```

---

## 5. Data Currently in Pinecone

**Index:** `legal-rag-768` | **Dimension:** 768 | **Metric:** cosine | **Provider:** aws us-east-1

| Source | Files | Chunks |
|---|---|---|
| data/lawsuit_organized_deduped | ~38 | ~676 |
| **Total** | **~38** | **~676 unique vectors** |

**Storage:** well under 2 GB limit (plenty of headroom)

**Key lawsuit documents indexed:**
- ARS court filings, motions, affirmations (NYSCEF)
- Correspondence letters (AmTrust, Country Cove, Kimberly Reese)
- Inventory/damage documents (Country Cove, unsalvageable items)
- Lease documents (partial — some PDFs were corrupted/empty)
- SCOTUS cases + CaseHOLD legal holdings

---

## 6. How the RAG Query Works (Step-by-Step)

```
1. User types question in ChatWindow
2. POST /api/chat (Next.js route) → POST https://legalragai.onrender.com/api/query
3. FastAPI receives QueryRequest { question, top_k=5, filter_file?, filter_folder?, filter_file_type? }
4. pipeline.query() runs:
   a. RETRIEVE: embeddings.embed_query(question) → 768-dim vector (Google gemini-embedding-001)
               pinecone_client.query_collection(vector, top_k=8) → top chunks
               Each chunk has: text, source_file, source_path, relevance_score
   b. FILTER: chunks with score < 0.15 are discarded
   c. GENERATE: groq_client.chat.completions.create(
                  model="llama-3.3-70b-versatile",
                  messages=[system_prompt, context_chunks, user_question],
                  max_tokens=2048, temperature=0.1
                )
   d. CITE: deduplicate sources by source_path, build sources list
5. Response: { answer, sources[], query, chunks_retrieved }
6. Frontend renders answer as Markdown + SourceCards
```

**Chunking config:** 1000 chars, 200 overlap, max 500 chunks/doc
**Retrieval config:** top_k=8 chunks, similarity threshold=0.15
**Generation config:** max_tokens=2048, temperature=0.1

---

## 7. Deployment Architecture

```
User Browser
    │
    ▼
Vercel (legal-rag-ai.vercel.app)
  Next.js App Router
  - Serves React UI
  - /api/* routes proxy to backend (hides BACKEND_URL from browser)
    │
    │  HTTPS POST /api/query
    ▼
Render Free Tier (legalragai.onrender.com)
  FastAPI + Uvicorn (single worker, WEB_CONCURRENCY=1)
  - Calls Google embedding API on each query (no local model load)
  - Connects to Pinecone on each query
  - Calls Groq API for generation
    │
    ├──▶ Pinecone (aws us-east-1) — vector search
    └──▶ Groq API — LLM generation
```

**Important Render free tier constraints:**
- Sleeps after 15 minutes of inactivity (cold start = 60-120 seconds)
- 512 MB RAM (Google embeddings use ~130 MB — torch removed)
- Single CPU, single worker
- No persistent disk (data must be in Pinecone, not ChromaDB)

**Cold start mitigation already in place:**
- `page.tsx` pings `/api/status` on page load to wake backend
- Keep-alive ping every 10 minutes while page is open
- Yellow "Backend warming up" banner when 503 is detected
- All API routes handle HTML responses gracefully (not a JSON crash)

---

## 8. What Was Built & Fixed (Session History — 2026-05-07)

### Session 1 — Initial Build & Deployment Fixes
- Indexed 834 unique vectors into Pinecone (384-dim `legal-rag` index)
- Fixed Windows encoding bug in `indexer.py` (replaced ✓/✗ with OK/ERR for cp1252 compatibility)
- Added `GROQ_MODEL` to `.env` and `render.yaml`
- **Root cause 1:** `vector_client.py` eager imports crashed Render startup → fixed to lazy imports
- **Root cause 2:** Startup event blocked async event loop with Pinecone query → replaced with print
- Fixed `next.config.ts` → `next.config.mjs` (Vercel doesn't support .ts config)
- Removed `@backend-url` secret reference from `vercel.json`
- All 4 frontend API routes handle HTML cold-start responses without crashing
- Added backend status indicator + warming-up banner in header
- Added scales-of-justice SVG favicon (`app/icon.svg`)

### Session 2 — OOM Fix, Google Embeddings, Re-index (2026-05-07)

**Problem:** Render 512MB OOM — torch + sentence-transformers used ~300MB, triggered OOM kill.

**Solution:** Switched entirely to Google `gemini-embedding-001` (no torch, ~130MB usage).

**Changes:**
- `requirements.txt`: Removed `torch`, `sentence-transformers`. Added `google-genai>=1.0.0`.
- `src/vector_db/embeddings.py`: Rewrote `GoogleEmbeddingEngine` using new `google.genai` SDK.
  - Uses `gemini-embedding-001` with `output_dimensionality=768`
  - Batches 20 texts/call, 13s sleep between batches (stays under 100 texts/min free tier)
  - Retry with backoff on 429 errors (extracts `retryDelay` from error message)
- `src/vector_db/pinecone_client.py`:
  - `_embedding_dimension()` now reads from active engine (dynamic, not hardcoded 384)
  - `list_indexed_files()` caches results 5 min to prevent repeated 10k-vector scans (OOM fix)
  - Reduced `top_k` from 10000 to 1000 for file listing
- `src/rag/generator.py`: Updated `GeminiGenerator` to use new `google.genai` SDK
- `config/settings.py`: `GOOGLE_EMBEDDING_MODEL = "gemini-embedding-001"`
- `.env`: `EMBEDDING_MODEL=google`, `PINECONE_INDEX_NAME=legal-rag-768`
- `render.yaml`: `EMBEDDING_MODEL: google`, `PINECONE_INDEX_NAME: legal-rag-768`

**New Pinecone index:** `legal-rag-768` (768-dim, cosine, aws us-east-1) — re-indexed 676 vectors.

**Frontend bug fixes:**
- `files/route.ts` + `status/route.ts`: Added `{ status: res.status }` to `NextResponse.json()` — missing this caused backend 500 errors to appear as 200, crashing the app with `TypeError: .filter is not a function`
- `lib/api.ts`: `apiFetch` now handles FastAPI `{"detail":"..."}` error format + `Array.isArray` guard on `listFiles()`
- `ChatWindow.tsx`: Auto-retry with 20s countdown on backend warmup errors (up to 3 retries)
- `Message.tsx`: Shows `msg.content` as loading text during retry countdown

---

## 9. Known Issues & Limitations

| Issue | Severity | Root Cause |
|---|---|---|
| 60-120s cold start on first daily use | Medium | Render free tier sleep policy |
| Groq free tier: 30 RPM rate limit | Medium | Multiple users hit quota quickly |
| Single worker (WEB_CONCURRENCY=1) | Medium | Concurrent requests queue |
| Google embedding latency ~1-2s/query | Low | API call vs local model — acceptable tradeoff for no OOM |
| No response streaming | Low | Groq called with full response, not streamed |
| Corrupted PDFs not indexed (5 files) | Low | Empty/password-protected PDFs |
| `.xls` files not indexed (5 files) | Low | Old Excel format, needs xlrd integration fix |
| CORS restricted to Vercel + localhost | Low | Fixed — was `allow_origins=["*"]` |
| No authentication | Low | Open API, anyone with URL can query |

---

## 10. Future Improvements (Priority Order)

### HIGH PRIORITY — Performance & Multi-User

#### 10.1 Add UptimeRobot Keep-Alive (Free, 5 minutes)
Eliminates cold starts completely. Sign up at uptimerobot.com, add HTTP monitor for `https://legalragai.onrender.com/api/health`, interval 5 minutes.

#### 10.2 Preload Embedding Model at Startup
Currently `all-MiniLM-L6-v2` loads on the **first query** (adds ~3-5 sec to first response). Fix: load it at server startup.
```python
# In backend/api.py startup event:
@app.on_event("startup")
async def startup_event():
    import asyncio
    asyncio.get_event_loop().run_in_executor(None, get_embedding_engine)
    print("[Startup] LegalRagAI ready. Preloading embedding model...")
```

#### 10.3 Add Response Streaming (SSE)
Currently the LLM generates the full answer before sending. With streaming, tokens appear as they're generated (perceived latency drops from ~5s to near-instant).
```python
# In backend/api.py
from fastapi.responses import StreamingResponse
@app.post("/api/query/stream")
async def query_stream(req: QueryRequest):
    async def generate():
        # Groq supports streaming
        stream = groq_client.chat.completions.create(..., stream=True)
        for chunk in stream:
            yield f"data: {chunk.choices[0].delta.content}\n\n"
    return StreamingResponse(generate(), media_type="text/event-stream")
```

#### 10.4 Semantic Query Caching
Cache embeddings + responses for similar queries. Prevents re-querying Pinecone + Groq for the same question.
```python
# Simple in-memory cache (upgrade to Redis for multi-worker):
from functools import lru_cache
QUERY_CACHE = {}  # {question_hash: response}
CACHE_THRESHOLD = 0.95  # cosine similarity

def cached_query(question: str):
    q_vec = embed_query(question)
    for cached_q_vec, response in QUERY_CACHE.values():
        if cosine_sim(q_vec, cached_q_vec) > CACHE_THRESHOLD:
            return response
    result = pipeline.query(question)
    QUERY_CACHE[hash(question)] = (q_vec, result)
    return result
```

#### 10.5 Groq Rate Limit Handling with Fallback
When Groq hits 30 RPM, automatically fall back to Gemini. Currently fallback exists but isn't triggered by rate limits.
```python
# In generator.py, wrap Groq with rate limit detection:
try:
    return groq_generate(...)
except groq.RateLimitError:
    return gemini_generate(...)  # auto-fallback
```

#### 10.6 Async RAG Pipeline
The current pipeline is synchronous. For multiple concurrent users, each request blocks a thread. Make retrieval and generation async.
```python
# In pipeline.py:
async def query_async(question: str, ...):
    chunks = await asyncio.to_thread(query_collection, question, n_results)
    answer = await asyncio.to_thread(generate, question, chunks)
    return format_response(answer, chunks)
```

### MEDIUM PRIORITY — Features

#### 10.7 Conversation Memory / Multi-Turn
Currently each query is independent. Add conversation history so follow-up questions have context.
```python
# In QueryRequest:
class QueryRequest(BaseModel):
    question: str
    history: list[dict] = []  # [{"role": "user", "content": "..."}, ...]
```

#### 10.8 Better Chunking for Legal Documents
Legal documents have specific structure (sections, clauses, exhibits). A legal-aware chunker would:
- Split on "WHEREAS", "NOW THEREFORE", numbered sections
- Keep exhibit references together
- Preserve paragraph structure

#### 10.9 Re-ranking with Cross-Encoder
After Pinecone retrieves top-k by cosine similarity, re-rank with a cross-encoder (more accurate relevance scoring). Use `cross-encoder/ms-marco-MiniLM-L-6-v2` (free).

#### 10.10 Document Summarization Endpoint
`GET /api/summarize?file=ARS_044_...pdf` — summarize a specific document using the LLM.

#### 10.11 Fix Old .xls Files
5 old-format Excel files failed. Fix: add xlrd fallback in `document_router.py`:
```python
# In parse_xlsx():
try:
    wb = openpyxl.load_workbook(path, read_only=True)
except InvalidFileException:
    import xlrd
    wb = xlrd.open_workbook(path)
```

### LOW PRIORITY — Production Hardening

#### 10.12 Add Authentication
Add API key middleware to prevent unauthorized access:
```python
# Simple: check X-API-Key header
# Better: Clerk.dev or Auth.js for the frontend
```

#### 10.13 Restrict CORS
Change `allow_origins=["*"]` to `allow_origins=["https://legal-rag-ai.vercel.app"]` in `backend/api.py`.

#### 10.14 Add Request Rate Limiting
Use `slowapi` to limit requests per IP:
```python
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)
@app.post("/api/query")
@limiter.limit("10/minute")
def query_endpoint(req: QueryRequest): ...
```

#### 10.15 Upgrade to Render Paid ($7/month)
- No cold starts
- 512MB → 1GB RAM
- Multiple workers possible
- Persistent disk

#### 10.16 ~~Switch to Google Embeddings~~ ✅ DONE
Google embeddings (`gemini-embedding-001`) are now the default. torch + sentence-transformers have been removed. OOM issue resolved.

---

## 11. Common Commands

### Local Development
```bash
# Activate venv (Windows)
.venv\Scripts\activate

# Run backend locally
uvicorn backend.api:app --reload --port 8000

# Run frontend locally
cd frontend && npm run dev

# Index files
python ingest.py --path ./data/lawsuit_organized_deduped
python ingest.py --status

# Run interactive agent
python main.py
```

### Deployment
```bash
# Push to GitHub (triggers Render + Vercel auto-deploy)
git push origin main

# Check Render logs
# → Render dashboard → LegalRagAI → Events

# Test backend health
curl https://legalragai.onrender.com/api/health

# Test query
curl -X POST https://legalragai.onrender.com/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the lawsuit about?", "top_k": 5}'
```

### Ingestion (Run Locally, Pushes to Pinecone)
```bash
# Index specific folder
python ingest.py --path ./data/lawsuit_organized_deduped

# Index single file
python ingest.py --file ./data/lawsuit_2026_april/filedbydanit.docx

# Check Pinecone status
python ingest.py --status

# Download + index public legal cases
python ingest.py --download auto --limit 200
```

---

## 12. Critical Files — What NOT to Change Without Understanding

| File | Risk | Why |
|---|---|---|
| `src/vector_db/vector_client.py` | HIGH | Must use lazy imports — eager imports crash Render startup |
| `config/settings.py` | HIGH | All env var defaults live here |
| `backend/api.py` startup_event | HIGH | Must stay lightweight — no Pinecone calls at startup |
| `src/vector_db/pinecone_client.py` chunk IDs | MEDIUM | Changing ID format will duplicate vectors |
| `render.yaml` | MEDIUM | Controls Render deployment config |
| `frontend/lib/api.ts` apiFetch | MEDIUM | Error handling chain must be preserved |

---

## 13. Architecture Decision Log

| Decision | Reason |
|---|---|
| Pinecone over ChromaDB for prod | ChromaDB requires persistent disk (not available on Render free) |
| Google embeddings (gemini-embedding-001) | No torch/OOM risk, free 1M tokens/day, 768-dim better than 384 |
| Groq primary LLM | Fastest free tier, 30 RPM sufficient for demo |
| Lazy import of vector DB clients | Eager chromadb import blocked uvicorn port binding |
| Next.js API route proxy | Hides BACKEND_URL from browser, enables server-side env vars |
| Sidebar always mounted (CSS hide) | Prevents remount → repeated API call spam |
| Lightweight startup event | Heavy startup (Pinecone query) blocked async event loop |
| `next.config.mjs` not `.ts` | Vercel doesn't support TypeScript Next.js config |
| PYTHONUTF8=1 for local ingestion | Windows cp1252 can't encode ✓/✗ Unicode chars |
