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

## 6. How 100 MB of Documents Became 2 MB in Pinecone

### Q: Was the full 100 MB uploaded to Pinecone?

**No.** The raw PDF/DOCX files are never sent to Pinecone. Only the math (numbers) gets stored there.

Here is exactly what happens step by step:

**Step 1 — Parse (runs locally on your machine)**
```
ARS_lawsuit_doc.pdf (2.5 MB)
    ↓ pdfplumber extracts text
"The defendant American Restoration Solutions failed to..."  (plain text, ~0.05 MB)
```
The images, fonts, formatting, and layout in the PDF are all thrown away. Only the raw text survives. A 2.5 MB PDF typically becomes ~50 KB of text — a 50x size reduction.

**Step 2 — Chunk (split into pieces)**
```
Full document text (~50 KB)
    ↓ split every 1000 characters, 200 overlap
Chunk 1: "The defendant American Restoration Solutions failed to..."
Chunk 2: "...complete the repairs by the agreed deadline. The contract..."
Chunk 3: "...signed on March 15, 2024. Exhibit A shows the original..."
...
~18 chunks per document
```
Each chunk is ~1000 characters = ~1 KB of plain text.

**Step 3 — Embed (convert text → numbers)**
```
Chunk 1: "The defendant American Restoration Solutions failed to..."
    ↓ Google gemini-embedding-001 API
[0.0231, -0.1847, 0.0923, 0.2341, -0.0567, ..., 0.1102]
   768 numbers (floats), each 4 bytes = 3,072 bytes per chunk
```
The text is gone. Pinecone only stores these 768 numbers + a tiny metadata dict (file name, path, page number). The actual sentence text is stored separately in Pinecone's metadata field — but only ~200 characters of it (the preview snippet), not the full chunk.

**Step 4 — What Pinecone actually stores per vector**
```json
{
  "id": "lawsuit_organized_deduped__ARS_001_complaint.pdf__chunk_0",
  "values": [0.0231, -0.1847, 0.0923, ...],   ← 768 floats = 3 KB
  "metadata": {
    "text": "The defendant American Restoration...",  ← full chunk text ~1 KB
    "source_file": "ARS_001_complaint.pdf",
    "source_path": "data/lawsuit_organized_deduped",
    "chunk_index": 0
  }
}
```
So each vector = ~4 KB total. 676 vectors × 4 KB = **~2.7 MB in Pinecone**.

### Q: So the original documents are completely gone from the system?

**Yes, for the cloud deployment.** The original PDFs only exist on your local machine in `data/lawsuit_organized_deduped/`. Render (the backend server) never has them. Pinecone only has the numbers.

This is intentional and is a feature:
- Pinecone free tier has a 2 GB vector storage limit — you could store 500,000+ chunks
- No large file hosting needed — no S3, no file server
- The text content of each chunk is preserved inside the metadata field, so answers still quote real sentences
- If you delete the local PDFs, the RAG system still works — the knowledge is already baked into the vectors

### Q: How does a vector (768 numbers) represent meaning?

The 768 numbers are coordinates in a 768-dimensional mathematical space. Sentences with similar meaning end up close together in that space (high cosine similarity score), even if they use different words.

```
"The contractor failed to fix the roof"       → [0.02, -0.18, 0.09, ...]
"ARS did not complete the repair work"        → [0.03, -0.17, 0.11, ...]
                                                ↑ very close → similarity ~0.92

"The cat sat on the mat"                      → [-0.31, 0.44, -0.22, ...]
                                                ↑ very far  → similarity ~0.04
```

So when you ask *"Did ARS finish the repairs?"*, your question gets embedded into the same space, and Pinecone finds the 8 chunks whose vectors are closest — those are the most relevant passages.

### Q: Full pipeline summary — 100 MB → 2 MB

```
48 lawsuit files (89 MB PDFs/DOCXs)
    │
    ▼ pdfplumber / python-docx extract text
~4 MB plain text  (images/formatting stripped)
    │
    ▼ split into 1000-char chunks with 200-char overlap
~676 text chunks  (~4 MB text total)
    │
    ▼ Google gemini-embedding-001 converts each chunk to 768 numbers
~676 vectors      (768 floats × 4 bytes = 3 KB/vector)
    │
    ▼ stored in Pinecone with metadata (chunk text + file info)
~2.7 MB in Pinecone  ← this is what "2 MB" refers to
```

The original files live only on your laptop. The cloud system only knows the math.

---

## 7. How the RAG Query Works (Step-by-Step)

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

## 8. Deployment Architecture

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

## 9. Full Journey — Every Hurdle We Hit and How We Solved It

> This section is the honest post-mortem. Every obstacle encountered, why it happened, and exactly what fixed it.

### Hurdle 1 — App crashed on startup (eager imports)
**What happened:** Deployed to Render. Server started, then immediately died before binding the port.
**Root cause:** `vector_client.py` imported both `chromadb` and `pinecone` at module load time. `import chromadb` triggers heavy SQLite initialization that blocked uvicorn's port binding.
**Fix:** Moved all vector DB imports inside `_get_client()` — lazy loading, only runs on first actual request.
**Lesson:** On Render free tier, startup must be ultra-lightweight. No heavy imports at module level.

---

### Hurdle 2 — Startup event blocked the async event loop
**What happened:** Server started but never became ready. Health checks timed out.
**Root cause:** The `@app.on_event("startup")` function called `get_index_status()` → `list_indexed_files()` → Pinecone query. A synchronous network call inside an async startup handler blocks the entire event loop.
**Fix:** Replaced startup body with a single print statement. Index status is fetched lazily on first `/api/status` request.
**Lesson:** FastAPI startup events must be near-instant. Never make network calls there.

---

### Hurdle 3 — Out of Memory (OOM) kill on Render
**What happened:** Render sent an OOM kill email. App died mid-query. Memory usage: ~480MB / 512MB limit.
**Root cause:** `sentence-transformers` + `torch` = ~300MB RAM just to load the embedding model. Each `/api/files` call ran a `top_k=10000` Pinecone scan and built 834 Python dicts → another ~150MB spike.
**Fix 1:** Removed torch + sentence-transformers entirely. Switched to Google `gemini-embedding-001` API (~130MB total RAM usage — a 350MB saving).
**Fix 2:** Added 5-minute in-memory cache on `list_indexed_files()`. Reduced Pinecone scan `top_k` from 10000 to 1000.
**Lesson:** On a 512MB server, every MB counts. API-based embeddings always beat local models for constrained environments.

---

### Hurdle 4 — App crash: TypeError `.filter is not a function`
**What happened:** Frontend crashed with `TypeError: data.filter is not a function` immediately on load.
**Root cause:** `files/route.ts` called `NextResponse.json(data)` without `{ status: res.status }`. When the backend returned HTTP 500 `{"detail":"..."}`, Next.js re-wrapped it as HTTP 200. `setFiles({"detail":"..."})` stored an object instead of an array. Then `files.filter(...)` crashed.
**Fix:** Added `{ status: res.status }` to all `NextResponse.json()` calls + `Array.isArray(data)` guard in `listFiles()`.
**Lesson:** Always propagate HTTP status codes through proxy routes. Never assume the shape of API responses.

---

### Hurdle 5 — Google embedding model not found / wrong dimensions
**What happened:** `models/text-embedding-004 not found`. Then: dimension mismatch when inserting into Pinecone.
**Root cause 1:** The old `google-generativeai` SDK was deprecated. The `text-embedding-004` model wasn't available on this API key. Migrated to new `google-genai` SDK.
**Root cause 2:** `gemini-embedding-001` returns 3072-dim vectors by default. Our Pinecone index was 384-dim. Vectors were rejected.
**Fix:** Used `output_dimensionality=768` parameter to truncate to 768-dim. Created new Pinecone index `legal-rag-768`. Re-indexed 676 vectors.
**Lesson:** When switching embedding providers, the Pinecone index dimension must match exactly. Always check output dimensions.

---

### Hurdle 6 — Google free tier rate limit (429) during indexing
**What happened:** Indexing stopped mid-way with `RESOURCE_EXHAUSTED`. Free tier allows 100 texts/minute — each text in a batch counts as 1 request.
**Fix:** Batched 20 texts per API call. Added 13-second sleep between batches (20 texts × 4.6 batches/min ≈ 92 texts/min, safely under 100 limit). Added retry with exponential backoff extracting the `retryDelay` hint from the error response.
**Lesson:** Free tiers count individual items, not API calls. Always throttle aggressively.

---

### Hurdle 7 — Gemini fallback LLM hitting limit: 0
**What happened:** Users got `429 RESOURCE_EXHAUSTED` from Gemini with `limit: 0` for `generate_content`.
**Root cause:** `LLM_PROVIDER` was not set in the Render dashboard (only in render.yaml, which dashboard vars override). Default `"auto"` tried Groq → Groq init failed → fell to Gemini. The Google API key was created for embeddings only — it had `limit: 0` for text generation.
**Fix:** Added `LLM_PROVIDER=groq` explicitly in Render dashboard. Added runtime error handling in pipeline so rate limit errors return a friendly user message instead of HTTP 500.
**Lesson:** render.yaml env vars are overridden by Render dashboard env vars. Always set critical vars in BOTH places.

---

### Hurdle 8 — ECHO MODE: Groq init failed silently
**What happened:** App showed `[ECHO MODE]` — LLM not running despite `GROQ_API_KEY` being set.
**Root cause:** `groq==0.12.0` passes a `proxies` argument to `httpx.Client.__init__()`. The latest `httpx` (0.28+) removed that parameter. `GroqGenerator.__init__()` threw `unexpected keyword argument 'proxies'`, `_try()` caught it silently, fell through to `EchoGenerator`.
**Fix:** Upgraded `groq>=0.13.0` (compatible with httpx 0.28+). Added diagnostic log line in `get_generator()` to print provider and API key presence on first query.
**Lesson:** Never pin SDKs to old patch versions. Transitive dependency upgrades (httpx) break older SDK versions silently.

---

## 10. Current Status — What Works, What Doesn't

| Feature | Status | Notes |
|---|---|---|
| Backend live on Render | WORKING | legalragai.onrender.com |
| Frontend live on Vercel | WORKING | legal-rag-ai.vercel.app |
| Google embeddings (768-dim) | WORKING | gemini-embedding-001, ~1-2s/query |
| Pinecone vector search | WORKING | legal-rag-768, 676 vectors |
| Groq LLM (Llama 3.3 70B) | WORKING | After groq>=0.13.0 fix deployed |
| File upload → auto-index | WORKING | Saves to temp, indexes to Pinecone |
| Sidebar file list | WORKING | 244 files, 676 chunks |
| Auto-retry on cold start | WORKING | 3 retries, 20s countdown |
| Conversation recording | NOT BUILT | Supabase integration pending |
| Response streaming | NOT BUILT | Full response sent at once |
| Auth / access control | NOT BUILT | Open API |
| UptimeRobot keep-alive | NOT SET UP | Cold starts still possible |

---

## 11. Road to Big Audience — Production Scaling Plan

### Stage 1: Still Free — Fix the Last Rough Edges (~1-2 days work)

These cost nothing and make the app noticeably better:

**11.1 UptimeRobot Keep-Alive (0 cost, eliminates cold starts)**
Sign up at uptimerobot.com. Add HTTP(S) monitor → `https://legalragai.onrender.com/api/health` → every 5 minutes.
Render free tier sleeps after 15 min inactivity. UptimeRobot pings it every 5 min → never sleeps.
Result: cold start drops from 60-120s → 0s for all users.

**11.2 Supabase Conversation Logging (0 cost, 500MB free)**
Every query + answer + sources saved to PostgreSQL. You can review what users are asking, spot gaps in your knowledge base, and build analytics.
```python
# After pipeline.query() in api.py:
supabase.table("conversations").insert({
    "question": req.question,
    "answer": result["answer"],
    "chunks_retrieved": result["chunks_retrieved"],
    "session_id": req.session_id,
}).execute()
```

**11.3 Response Streaming (0 cost, feels 5x faster)**
Groq supports token streaming. Instead of waiting 5s for a full answer, words appear as they're generated.
```python
@app.post("/api/query/stream")
async def query_stream(req: QueryRequest):
    async def generate():
        stream = groq_client.chat.completions.create(..., stream=True)
        for chunk in stream:
            token = chunk.choices[0].delta.content or ""
            yield f"data: {json.dumps({'token': token})}\n\n"
    return StreamingResponse(generate(), media_type="text/event-stream")
```

**11.4 Groq → Gemini Auto-Fallback on Rate Limit (0 cost, no downtime)**
When Groq hits 30 RPM, auto-switch to Gemini 2.0 Flash (15 RPM free). Combined: 45 RPM.
```python
# In generator.py generate():
try:
    return self._groq_generate(query, context)
except RateLimitError:
    return GeminiGenerator().generate(query, context)
```

---

### Stage 2: Small Budget — 10-100 Concurrent Users (~$15-30/month)

| Upgrade | Cost | What it fixes |
|---|---|---|
| Render Starter ($7/mo) | $7/mo | No cold starts, 1GB RAM, always-on |
| Groq paid tier | $0.05/1M tokens | 600 RPM instead of 30 RPM |
| Pinecone Starter ($0/mo → $70/mo) | Free up to 100k vectors | Already covered for current data |
| Upstash Redis ($0-10/mo) | ~$3/mo | Cross-worker query cache, session store |
| **Total** | **~$10-15/mo** | Handles 100+ concurrent users |

With $15/month this system handles 10-100 daily active users with sub-3s response times.

---

### Stage 3: Growth — 100-1000 Concurrent Users (~$100-300/month)

| Upgrade | Cost | What it fixes |
|---|---|---|
| Render Standard (2 workers) | $25/mo | 2 concurrent requests without queuing |
| OpenAI `text-embedding-3-small` | $0.02/1M tokens | Faster, cheaper than Google API |
| Pinecone Standard | $70/mo | 5M vectors, dedicated pod, faster queries |
| Redis (Upstash Pro) | $20/mo | Distributed cache across workers |
| Supabase Pro | $25/mo | Conversation analytics, user auth |
| CDN (Cloudflare free) | $0 | Cache static assets, DDoS protection |
| **Total** | **~$140/mo** | Handles 1000+ daily active users |

---

### Stage 4: Production Scale — 10,000+ Users (~$500-2000/month)

| Component | Technology | Cost | Reason |
|---|---|---|---|
| Backend | AWS ECS / Fly.io (auto-scale) | $100-400/mo | Scale to 10+ workers on demand |
| Embeddings | OpenAI or self-hosted `bge-m3` | $50-200/mo | Volume discounts |
| Vector DB | Pinecone Enterprise or Weaviate Cloud | $200-500/mo | Dedicated hardware, <10ms search |
| LLM | Groq + Claude Haiku fallback | $100-300/mo | Groq for speed, Claude for quality |
| Cache | Redis Enterprise | $50/mo | Sub-ms cache hits |
| Auth | Clerk.dev | $25/mo | User accounts, session management |
| Monitoring | Datadog / Grafana Cloud | $30/mo | Latency alerts, error tracking |
| **Total** | | **$500-1500/mo** | Enterprise-grade, <2s P99 latency |

---

### Stage 5: World-Class RAG System — What Separates Top Systems

These are the architectural differences between a demo and a system like Harvey AI (valued at $3B):

**A. Hybrid Search (BM25 + Vector)**
Pure vector search misses exact keyword matches (case numbers, names, dates). Top systems combine:
- Vector search: semantic meaning
- BM25 keyword search: exact terms
- Fusion ranking: merge both result lists
```python
# Pinecone supports hybrid search natively
results = index.query(vector=q_vec, sparse_vector=bm25_vec, top_k=20)
```

**B. Re-ranking (Cross-Encoder)**
After retrieving 20 candidates, re-rank with a cross-encoder model that scores query+document pairs directly. Accuracy jumps from ~70% to ~90% relevance.
```python
from sentence_transformers import CrossEncoder
reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
scores = reranker.predict([(query, chunk["text"]) for chunk in candidates])
```

**C. Legal-Aware Chunking**
Generic 1000-char chunking splits mid-sentence, mid-clause, mid-citation. Legal documents have structure:
- Split on section headers, numbered clauses, exhibit references
- Keep "WHEREAS ... NOW THEREFORE" clauses together
- Preserve citation context (case names, docket numbers, dates)

**D. Multi-Turn Conversation Memory**
Each query is currently independent. Top systems maintain context across turns:
- User: "What did the court decide?"
- System: finds answer
- User: "Why?" ← needs to know what "why" refers to
Store last 5 turns in session → append to prompt → coherent conversation.

**E. Document-Level Summarization**
Before chunking, generate a 1-paragraph summary of each document. Store it as a special "document overview" vector. When a query matches an overview, retrieve the full document for deeper analysis.

**F. Confidence Scoring**
Top systems tell users how confident they are. If top chunk score < 0.4, say "I found related information but it may not directly answer your question." If score < 0.15, say "I couldn't find relevant information."

**G. Streaming + Progressive Enhancement**
- Stream tokens as they generate (feels instant)
- Show source cards as they're retrieved (before LLM finishes)
- Allow follow-up questions while answer is streaming

---

## 12. Latency Breakdown — Where Time Is Spent Per Query

```
User hits Enter
    │
    ├─ Network: browser → Vercel → Render         ~100-300ms
    │
    ├─ Embedding: Google gemini-embedding-001      ~800-1200ms  ← biggest bottleneck
    │
    ├─ Pinecone search: top_k=8 cosine scan        ~50-150ms
    │
    ├─ LLM: Groq Llama 3.3 70B (2048 tokens)      ~1500-3000ms
    │
    └─ Response back to browser                    ~100-200ms

TOTAL current P50: ~3-5 seconds
TOTAL current P99: ~8-12 seconds (cold start + rate retry)
```

**How to get to <1 second P50:**

| Optimization | Latency saved | Cost |
|---|---|---|
| Stream LLM tokens | Perceived -3s (first token in 200ms) | Free |
| Cache repeated queries (Redis) | -4s for cache hits (~30% of traffic) | $3/mo |
| Precompute embeddings at upload time | 0 at query time | Free |
| Groq paid tier (higher speed) | -500ms | $0.05/1M tokens |
| Pinecone dedicated pod | -100ms on search | $70/mo |
| Move Render to same AWS region as Pinecone (us-east-1) | -50ms | $0 (config change) |
| Parallel embed + prefetch | -200ms (overlap network calls) | Free |

**Realistic targets:**
- Free tier: 3-5s P50, 8-12s P99
- $15/month: 2-3s P50, 5-8s P99
- $150/month: 1-2s P50, 3-5s P99
- $1500/month: <500ms P50, <2s P99 (streaming makes P50 feel ~100ms)

---

## 13. Common Commands

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

## 14. Critical Files — What NOT to Change Without Understanding

| File | Risk | Why |
|---|---|---|
| `src/vector_db/vector_client.py` | HIGH | Must use lazy imports — eager imports crash Render startup |
| `config/settings.py` | HIGH | All env var defaults live here |
| `backend/api.py` startup_event | HIGH | Must stay lightweight — no Pinecone calls at startup |
| `src/vector_db/pinecone_client.py` chunk IDs | MEDIUM | Changing ID format will duplicate vectors |
| `render.yaml` | MEDIUM | Controls Render deployment config |
| `frontend/lib/api.ts` apiFetch | MEDIUM | Error handling chain must be preserved |

---

## 15. Architecture Decision Log

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
