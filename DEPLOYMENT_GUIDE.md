# CompleteRagAI — Deployment Guide

## Overview

Deploy your Legal RAG AI Agent to production:
- **Frontend**: Vercel (Next.js) — Free tier
- **Backend**: Render (Docker) — Free tier
- **Total Cost**: $0

---

## Prerequisites

1. **GitHub Account**: https://github.com
2. **Vercel Account**: https://vercel.com (Sign up with GitHub)
3. **Render Account**: https://render.com (Sign up with GitHub)
4. **Groq API Key**: https://console.groq.com/keys

---

## Step 1: Push to GitHub

### 1.1 Initialize Git (if not already done)

```bash
# Navigate to project root
cd CompleteRagAi

# Initialize git (skip if already initialized)
git init

# Add all files
git add .

# First commit
git commit -m "Initial commit: Legal RAG AI with auto-install"
```

### 1.2 Create GitHub Repository

1. Go to https://github.com/new
2. Repository name: `legal-rag-ai` (or any name)
3. Make it **Public** (for free deployment)
4. Click **"Create repository"**

### 1.3 Push Code

```bash
# Add GitHub remote (replace with your repo URL)
git remote add origin https://github.com/YOUR_USERNAME/legal-rag-ai.git

# Push to main branch
git branch -M main
git push -u origin main
```

---

## Step 2: Deploy Backend on Render

### 2.1 Connect Repository

1. Go to https://dashboard.render.com
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub account
4. Select the `legal-rag-ai` repository
5. Click **"Connect"**

### 2.2 Configure Service

| Setting | Value |
|---------|-------|
| **Name** | `legal-rag-api` |
| **Environment** | `Docker` |
| **Region** | `Oregon (US West)` |
| **Branch** | `main` |
| **Root Directory** | `./` |
| **Dockerfile Path** | `./Dockerfile` |
| **Plan** | `Free` |

### 2.3 Environment Variables

Add these in Render Dashboard → Environment:

| Key | Value | Secret? |
|-----|-------|---------|
| `GROQ_API_KEY` | `gsk_...` | ✅ YES (toggle on) |
| `LLM_PROVIDER` | `groq` | ❌ No |
| `EMBEDDING_MODEL` | `local` | ❌ No |
| `CHROMA_DB_PATH` | `./chroma_db` | ❌ No |
| `CHROMA_COLLECTION_NAME` | `legal_cases` | ❌ No |
| `DATA_RAW_PATH` | `./data/raw` | ❌ No |
| `DATA_PROCESSED_PATH` | `./data/processed` | ❌ No |
| `DATA_UPLOADS_PATH` | `./data/uploads` | ❌ No |

> **Important**: Mark `GROQ_API_KEY` as secret! It won't be visible after saving.

### 2.4 Deploy

Click **"Create Web Service"**

Render will:
1. Build Docker image (~5 min)
2. Start container
3. Auto-download legal data on first start (~2-3 min)
4. Index to ChromaDB (~1 min)

**Your API URL**: `https://legal-rag-api.onrender.com` (example)

---

## Step 3: Deploy Frontend on Vercel

### 3.1 Connect Repository

1. Go to https://vercel.com/new
2. Import Git Repository → Select `legal-rag-ai`
3. Click **"Import"**

### 3.2 Configure Project

| Setting | Value |
|---------|-------|
| **Framework Preset** | `Next.js` |
| **Root Directory** | `frontend` |
| **Build Command** | `npm run build` |
| **Output Directory** | `.next` |
| **Install Command** | `npm install` |

### 3.3 Environment Variables

Add this in Vercel Dashboard → Settings → Environment Variables:

| Key | Value |
|-----|-------|
| `BACKEND_URL` | `https://legal-rag-api.onrender.com` (your Render URL) |

> Get your Render URL from Step 2.4 (ends with `.onrender.com`)

### 3.4 Deploy

Click **"Deploy"**

Vercel will:
1. Build Next.js app (~2 min)
2. Deploy to global CDN

**Your Frontend URL**: `https://legal-rag-ai.vercel.app` (example)

---

## Step 4: Verify Deployment

### 4.1 Test Backend API

Open in browser:
```
https://legal-rag-api.onrender.com/api/health
```

Expected response:
```json
{"status": "healthy"}
```

Check index status:
```
https://legal-rag-api.onrender.com/api/status
```

Expected:
```json
{
  "collection": "legal_cases",
  "total_chunks": 758,
  "unique_files": 26
}
```

### 4.2 Test Frontend

Open your Vercel URL:
```
https://legal-rag-ai.vercel.app
```

Try a query: "What cases involve prisoner rights?"

### 4.3 Full Integration Test

```bash
# Test query via API
curl -X POST https://legal-rag-api.onrender.com/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What was Haines v. Kerner about"}'
```

---

## Files Structure for Deployment

```
CompleteRagAI/
├── backend/
│   └── api.py              # FastAPI server
├── frontend/
│   ├── app/                # Next.js pages
│   ├── components/         # React components
│   ├── .env.local.example  # Environment template
│   ├── next.config.ts
│   ├── package.json
│   └── vercel.json         # Vercel config ✅
├── src/
│   ├── agents/             # Legal AI Agent
│   ├── rag/                # RAG pipeline
│   ├── vector_db/          # ChromaDB
│   └── data_ingestion/     # Parsers, downloaders
├── Dockerfile              # Render Docker config ✅
├── render.yaml             # Render service config ✅
├── requirements.txt        # Python deps
├── main.py                 # CLI entry
└── README.md
```

---

## Troubleshooting

### Backend: "Build failed"

**Check**: Dockerfile exists and is valid
```bash
docker build -t test-build .
```

**Fix**: Ensure `Dockerfile` is in root directory

### Backend: "No data found"

**Check**: Auto-install should run on first start. Check logs:
```
[Startup] Vector DB empty. Downloading 1-3GB sample legal data...
```

**Fix**: If auto-install fails, manually trigger:
```bash
curl -X POST https://your-api.onrender.com/api/ingest/download
```

### Frontend: "Cannot connect to backend"

**Check**: `BACKEND_URL` environment variable in Vercel

**Fix**: 
1. Vercel Dashboard → Project → Settings → Environment Variables
2. Update `BACKEND_URL` to your Render URL
3. Redeploy

### CORS Errors

**Check**: Backend CORS settings in `@backend/api.py:34-40`

Already configured:
```python
allow_origins=["*"],  # Allows all origins (Vercel, localhost, etc.)
```

### Groq API Errors

**Check**: `GROQ_API_KEY` set as secret in Render

**Fix**: 
1. Render Dashboard → Environment
2. Add `GROQ_API_KEY` with your key `gsk_...`
3. Mark as **Secret**
4. Redeploy

---

## Architecture (Deployed)

```
┌─────────────────────────────────────────────────────────────┐
│                        USER BROWSER                          │
│                   (https://your-app.vercel.app)              │
└───────────────────────┬─────────────────────────────────────┘
                        │ HTTPS
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                      VERCEL EDGE                            │
│                  (Next.js Static + API)                     │
│  • React UI                                               │
│  • Chat interface                                         │
│  • File upload                                            │
└───────────────────────┬─────────────────────────────────────┘
                        │ API Calls
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                     RENDER (Docker)                         │
│               (https://your-api.onrender.com)               │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              FastAPI Server                         │   │
│  │  • /api/query → RAG pipeline                      │   │
│  │  • /api/upload → File indexing                    │   │
│  │  • /api/status → DB stats                         │   │
│  └────────────────────┬────────────────────────────────┘   │
│                       │                                      │
│  ┌────────────────────┴────────────────────────────────┐   │
│  │           ChromaDB (Persistent)                     │   │
│  │  • Embeddings: 384-dim (MiniLM-L6-v2)              │   │
│  │  • 758 chunks indexed                              │   │
│  │  • HNSW cosine similarity                          │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Groq LLM                               │   │
│  │  • Model: llama-3.3-70b-versatile                  │   │
│  │  • Source citations with file paths                │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## Cost Breakdown

| Service | Tier | Cost | Limits |
|---------|------|------|--------|
| **Vercel** | Hobby | **$0** | 100GB bandwidth, 10k requests/day |
| **Render** | Free | **$0** | 512MB RAM, sleeps after 15min idle |
| **Groq** | Free | **$0** | 30 RPM, 14,400 requests/day |
| **ChromaDB** | Local | **$0** | Unlimited (runs in container) |
| **Embeddings** | Local | **$0** | CPU-based sentence-transformers |

**Total: $0/month** (for moderate usage)

> Note: Render free tier spins down after 15 min idle. First request after idle takes ~30s to wake up.

---

## Next Steps

### Custom Domain (Optional)

**Vercel**:
1. Dashboard → Project → Settings → Domains
2. Add your domain
3. Update DNS records

**Render**:
1. Dashboard → Service → Settings → Custom Domain
2. Add your API subdomain (e.g., `api.yourdomain.com`)

### SSL/HTTPS

✅ **Already enabled** on both Vercel and Render

### Monitoring

**Render**: Dashboard → Metrics (CPU, RAM, requests)
**Vercel**: Dashboard → Analytics (visitors, performance)

---

## Quick Reference

| Task | URL |
|------|-----|
| Vercel Dashboard | https://vercel.com/dashboard |
| Render Dashboard | https://dashboard.render.com |
| Groq Console | https://console.groq.com/keys |
| GitHub Repo | https://github.com/YOUR_USERNAME/legal-rag-ai |

---

**Your Legal RAG AI will be live at:**
- Frontend: `https://legal-rag-ai.vercel.app`
- Backend: `https://legal-rag-api.onrender.com`

Ready to deploy! 🚀
