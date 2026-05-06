# Vector Database Deployment Strategy — CompleteRagAI

## Overview

This document explains exactly how the vector database works for **local development** vs **Render deployment**, and what you need to do to prepare data for your client demo.

---

## The Core Problem

**ChromaDB (your current setup) stores data in a local SQLite file.**

```
Local Machine:     chroma_db/chroma.sqlite3  (~15MB of legal cases)
Render Server:     Empty folder (no data)
```

When you deploy to Render, the server starts with **ZERO data** — it doesn't magically copy your local files.

---

## Architecture Comparison

### Option A: Local Development (What You Have Now)

```
┌─────────────────────────────────────────────────────────────┐
│                    YOUR LAPTOP                            │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    │
│  │  Frontend   │───▶│   Backend   │───▶│  ChromaDB   │    │
│  │  :3000      │    │   :8000     │    │  ./chroma_db│    │
│  └─────────────┘    └─────────────┘    │  (SQLite)   │    │
│                                         └─────────────┘    │
│                                               ↑            │
│                                          Data persists     │
│                                          on your disk      │
└─────────────────────────────────────────────────────────────┘
```

**Characteristics:**
- Data stored in `c:\Users\Sachin Kumar\CompleteRagAi\chroma_db\chroma.sqlite3`
- Survives between runs
- ~15MB of indexed legal cases
- **Perfect for client demo**

---

### Option B: Render Free Tier Deployment (What Happens If You Deploy Now)

```
┌─────────────────────────────────────────────────────────────┐
│                 RENDER FREE TIER SERVER                     │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    │
│  │   Vercel    │───▶│   Backend   │───▶│  ChromaDB   │    │
│  │  (Next.js)  │    │   (Python)  │    │  ./chroma_db│    │
│  └─────────────┘    └─────────────┘    │  (EMPTY!)   │    │
│                                         └─────────────┘    │
│                                               ↑            │
│                                     No data! Fresh server  │
│                                     Filesystem ephemeral   │
└─────────────────────────────────────────────────────────────┘
```

**Characteristics:**
- Server starts with empty `./chroma_db/` folder
- **No data** — RAG queries return "No context found"
- After 15 min idle: Server sleeps → **Data lost on wake**
- After manual restart: **Data lost**

---

## The Data Flow Problem

### Your Current State (Local)

```bash
# Check your local data
$ ls -lh chroma_db/
-rw-r---- 1 user user 15M May 6 17:00 chroma.sqlite3

# 15MB = ~5,000-10,000 chunks of legal cases
```

### What Render Sees

```bash
# When Render starts your backend
$ ls -lh chroma_db/
ls: cannot access 'chroma_db/': No such file or directory

# Empty! Nothing to query.
```

---

## Solution: Pre-Index Data on Render

### Step-by-Step: How to Get Data into Render

#### Step 1: Deploy Backend to Render (Empty DB)

```yaml
# render.yaml already configured
services:
  - type: web
    name: legal-rag-api
    runtime: python
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn backend.api:app --host 0.0.0.0 --port $PORT
```

**Deploy:**
1. Go to https://dashboard.render.com/
2. Click "New +" → "Web Service"
3. Connect GitHub repo: `LegalRagAi`
4. Render auto-detects `render.yaml`
5. Add environment variable:
   ```
   GROQ_API_KEY=gsk_xxxxx
   ```
6. Deploy

**Result:** Backend running at `https://legal-rag-api-xxx.onrender.com` with **EMPTY** vector DB.

---

#### Step 2: Upload & Index Your Legal Documents

**Method A: Via API (Recommended for Client Demo)**

```bash
# 1. Create a ZIP of your lawsuit files
$ cd data/lawsuit_2026_april/
$ zip -r lawsuit_files.zip .

# 2. Upload to Render via API
$ curl -X POST \
  https://legal-rag-api-xxx.onrender.com/api/upload \
  -F "file=@lawsuit_files.zip"

# Response:
# {"filename": "lawsuit_files.zip", "chunks_indexed": 245}
```

**What happens:**
1. ZIP uploaded to `/tmp/` on Render
2. Backend extracts files
3. Parses PDFs/DOCXs → extracts text
4. Chunks documents (1000 chars each, 200 overlap)
5. Embeds using `all-MiniLM-L6-v2` (384 dimensions)
6. Stores in `./chroma_db/chroma.sqlite3`

---

#### Step 3: Verify Data is Indexed

```bash
# Check index status
$ curl https://legal-rag-api-xxx.onrender.com/api/status

# Response:
# {
#   "collection": "legal_cases",
#   "total_chunks": 245,
#   "db_path": "./chroma_db",
#   "unique_files": 3
# }
```

---

#### Step 4: Test Query

```bash
# Send test query
$ curl -X POST \
  https://legal-rag-api-xxx.onrender.com/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the key legal arguments?", "top_k": 5}'

# Response includes answer + source citations
```

---

## The Critical Limitation: Render Free Tier

### What "Ephemeral Filesystem" Means

```
Timeline of Render Free Tier Server:

T+0:00   Deploy ──▶ chroma_db/chroma.sqlite3 created (245 chunks)
         ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
         
T+0:30   Query  ──▶ Works! Returns results from 245 chunks
         ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
         
T+15:00  Idle   ──▶ Server sleeps (free tier shuts down after 15 min)
         ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
         
T+15:01  Wake   ──▶ New server spins up
         ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
         
T+15:02  Query  ──▶ FAILS! "No context found"
                      chroma_db/ folder is EMPTY (fresh server)
                      
T+15:03  Re-upload ──▶ Must re-upload & re-index all files
```

**This is why Pinecone exists** — cloud vector DB persists independently.

---

## Comparison: ChromaDB vs Pinecone for Your Use Case

### Client Demo Scenarios

| Scenario | ChromaDB on Render | Pinecone | Local Demo |
|----------|-------------------|----------|------------|
| **30-min demo, no idle** | ✅ Works | ✅ Works | ✅ Best |
| **1-hour demo, idle breaks** | ❌ Data lost | ✅ Works | ✅ Best |
| **Multiple sessions** | ❌ Re-index each time | ✅ Works | ✅ Best |
| **Setup complexity** | Low | Medium | Lowest |
| **Cost** | Free | Free tier | Free |

---

## Recommendation for Your Client Demo

### Option 1: Local Demo (RECOMMENDED) ✅

**Why:** Full control, data persists, no server sleep issues.

**Steps:**
```bash
# Terminal 1: Start backend (data already indexed!)
$ python backend/api.py
# Runs on http://localhost:8000
# Uses your existing chroma_db/chroma.sqlite3 (15MB)

# Terminal 2: Start frontend
$ cd frontend
$ npm run dev
# Runs on http://localhost:3000

# Open browser: http://localhost:3000
# Ready to demo immediately!
```

**Pros:**
- ✅ Data already indexed (~15MB in chroma_db/)
- ✅ No upload needed
- ✅ No server sleep
- ✅ Full control

**Cons:**
- ❌ Must use your laptop (not "cloud" demo)
- ❌ Client sees `localhost:3000` in URL

---

### Option 2: Render Deploy (If Client Needs Live URL)

**Steps:**
```bash
# 1. Deploy to Render
# 2. Immediately upload your lawsuit files
$ curl -X POST \
  https://legal-rag-api-xxx.onrender.com/api/upload \
  -F "file=@lawsuit_files.zip"

# 3. Deploy Vercel frontend pointing to Render URL
# 4. Demo within 15 minutes (before sleep)
# 5. If server sleeps during demo → Re-upload files
```

**Pros:**
- ✅ Live URL (`https://your-app.vercel.app`)
- ✅ Looks professional

**Cons:**
- ❌ Must upload data after each deploy
- ❌ Must re-upload if server sleeps
- ❌ Risk of data loss mid-demo

---

## Technical Deep Dive: How Indexing Works

### The Pipeline

```
File Upload
    ↓
┌─────────────────────────────────────────────────────────────┐
│                    BACKEND API (Python)                      │
│                                                              │
│  1. Receive File ──▶ Save to /tmp/uploads/                   │
│                                                              │
│  2. Parse Document ──▶ Extract text                         │
│     - PDF: pdfplumber → text per page                        │
│     - DOCX: python-docx → paragraphs                        │
│     - PPTX: python-pptx → slides                            │
│                                                              │
│  3. Chunk Text ──▶ Split into 1000-char chunks                │
│     - Overlap: 200 characters                                 │
│     - Prefer sentence boundaries                              │
│     - Max: 500 chunks per document                            │
│                                                              │
│  4. Embed ──▶ Convert to vectors (384 dimensions)            │
│     - Model: sentence-transformers/all-MiniLM-L6-v2         │
│     - Local CPU inference (no API key needed)               │
│                                                              │
│  5. Store ──▶ Insert into ChromaDB                          │
│     - SQLite file: ./chroma_db/chroma.sqlite3                │
│     - Metadata: file_hash, chunk_index, page_number, etc.    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
    ↓
Query: "What are the damages?"
    ↓
Retrieve Top-K Chunks (cosine similarity)
    ↓
Send to Groq LLM with context
    ↓
Return answer with source citations
```

### Query Flow

```
User Question
    ↓
Embed Question (same model: all-MiniLM-L6-v2)
    ↓
384-dimensional vector: [0.12, -0.05, 0.89, ...]
    ↓
ChromaDB Query: SELECT * ORDER BY cosine_similarity(vector) LIMIT 5
    ↓
Top 5 relevant chunks returned
    ↓
Format with [Source 1], [Source 2] markers
    ↓
Groq LLM (llama-3.3-70b-versatile)
    ↓
"Based on [Source 1], the damages claimed are..."
```

---

## Exact Steps for Your Client Demo

### If Using Local Demo (Recommended)

```bash
# 1. Start backend (data already there!)
$ python backend/api.py

# 2. Start frontend
$ cd frontend
$ npm run dev

# 3. Open http://localhost:3000

# 4. Demo immediately — 15MB of legal cases ready
```

### If Using Render Deploy

```bash
# BEFORE DEMO (do this 10 minutes before client arrives):

# 1. Check if Render server is awake
$ curl https://legal-rag-api-xxx.onrender.com/api/status

# If returns 503/timeout → Server sleeping, will wake on first request

# 2. Upload your lawsuit files
$ curl -X POST \
  https://legal-rag-api-xxx.onrender.com/api/upload \
  -F "file=@data/lawsuit_2026_april/your_files.zip"

# 3. Verify indexing
$ curl https://legal-rag-api-xxx.onrender.com/api/status
# Should show: {"total_chunks": 245}

# 4. Test query
$ curl -X POST \
  https://legal-rag-api-xxx.onrender.com/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "test"}'

# 5. Open Vercel URL and demo
# ⚠️ Complete demo within 15 minutes!
```

---

## FAQ

### Q: Can I copy my local chroma.sqlite3 to Render?
**A:** No. Render free tier has no persistent disk. Each deploy gets a fresh filesystem.

### Q: Why not just commit chroma_db/ to Git?
**A:** SQLite files are binary, change constantly, and Git isn't designed for databases. Also, Render still won't persist it across restarts.

### Q: What if demo runs longer than 15 minutes?
**A:** Keep sending requests every 5 minutes to prevent sleep. Or use local demo.

### Q: Should I use Pinecone for the client demo?
**A:** If you have time (30 min) to:
1. Get Pinecone API key (free)
2. Create index
3. Re-index all data to Pinecone
4. Switch `VECTOR_DB_PROVIDER=pinecone`
5. Re-deploy

Then yes, Pinecone eliminates the sleep issue. Otherwise, local demo is safer.

---

## Summary

| What You Want | What to Do |
|---------------|-----------|
| **Safest client demo** | Local demo with `python backend/api.py` |
| **Live URL for client** | Render + upload files right before demo + keep server awake |
| **Permanent cloud solution** | Pinecone (requires setup time) |

**Your data is ready locally.** The 15MB in `chroma_db/chroma.sqlite3` is your asset. Use it!
