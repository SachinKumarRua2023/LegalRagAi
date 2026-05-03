# CompleteRagAI — US Legal Cases AI Agent

A fully local RAG (Retrieval-Augmented Generation) AI agent for US legal case research.

## Architecture

```
Your Files (PDF/DOCX/PPTX/XLSX/CSV/TXT)
        ↓
  Document Parser  ←── Extracts text + metadata (file, folder, page, section)
        ↓
   Text Chunker    ←── Splits into ~1000-char overlapping chunks
        ↓
 Embedding Engine  ←── sentence-transformers (free, local) OR Google text-embedding-004
        ↓
   ChromaDB        ←── Free local vector DB with full metadata storage
        ↓
  RAG Retriever    ←── Semantic search → top-K chunks with source citations
        ↓
  Gemini Flash     ←── Free LLM generates answer with [Source N] citations
        ↓
   AI Agent        ←── Natural language interface with file/folder filtering
```

## Free Stack (Zero Cost)

| Component | Tool | Cost |
|-----------|------|------|
| Vector DB | ChromaDB (local) | Free |
| Embeddings | sentence-transformers all-MiniLM-L6-v2 | Free |
| LLM | Google Gemini 1.5 Flash | Free (15 RPM, 1M tokens/day) |
| Data | CourtListener API + HuggingFace | Free |

## Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Set up API keys
```bash
copy .env.example .env
# Edit .env and add your GOOGLE_API_KEY
# Get free key at: https://aistudio.google.com/app/apikey
```

### 3. Download legal data (1-3 GB)
```bash
# Download US Supreme Court cases (~100MB, fast)
python ingest.py --download huggingface --dataset us_scotus --limit 3000

# Download from CourtListener API (free, no key needed for basic)
python ingest.py --download courtlistener --query "criminal law" --limit 500

# Download everything (1-2 GB)
python ingest.py --download all --limit 2000
```

### 4. Index your own files
```bash
# Drop your PDFs/DOCX/PPTX etc. in data/uploads/
# Then run:
python ingest.py --path ./data/uploads

# Or index any folder:
python ingest.py --path "C:/Users/YourName/Documents/LegalFiles"

# Or a single file:
python ingest.py --file ./my_case.pdf
```

### 5. Run the AI Agent
```bash
# Interactive mode (recommended)
python main.py

# Single query
python main.py --query "What are the key elements of a contract dispute?"

# Query within a specific file
python main.py --query "What was the ruling?" --file doe_v_roe.pdf

# Query within a folder
python main.py --query "Fourth amendment violations" --folder ./data/raw/criminal

# Search only in PDFs
python main.py --query "civil rights" --type pdf

# Show index status
python main.py --status
```

## Supported File Types

| Format | Extension | Notes |
|--------|-----------|-------|
| PDF | .pdf | Text + tables extracted per page |
| Word | .docx, .doc | Per heading/section + tables |
| PowerPoint | .pptx, .ppt | Per slide with title |
| Excel | .xlsx, .xls | Per sheet, batched rows |
| CSV | .csv | Batched rows as JSON |
| Text | .txt, .md, .rtf | Full document |
| HTML | .html, .htm | Text extraction |
| JSON | .json | Formatted output |

## Metadata Stored per Chunk

Every chunk in ChromaDB contains:
- `source_file` — filename
- `source_path` — full absolute path
- `source_folder` — parent folder path
- `file_type` — extension
- `file_hash` — SHA-256 (deduplication)
- `page_number` / `slide_number` / `sheet` — location in document
- `section` — heading or section name
- `chunk_index` — position in document
- `ingested_at` — timestamp
- `case_number`, `court`, `decision_date` — auto-extracted for legal docs

## Interactive Agent Commands

In interactive mode (`python main.py`):
```
/help                   — Show all commands
/status                 — Show database statistics
/files                  — List all indexed files
/index <path>           — Index a file or folder
/quit                   — Exit

# Natural language examples:
What are the elements of contract law?
In file smith_v_jones.pdf, what was the verdict?
In folder /data/raw, search for employment discrimination cases
Search in PDFs about criminal sentencing guidelines
What cases involve the Fourth Amendment?
Tell me about file roe_v_wade.txt
```

## Project Structure

```
CompleteRagAi/
├── config/settings.py              ← All configuration
├── src/
│   ├── data_ingestion/
│   │   ├── downloaders/            ← CourtListener + HuggingFace downloaders
│   │   ├── parsers/document_router.py  ← Universal document parser
│   │   └── chunkers/text_chunker.py    ← Smart text chunking
│   ├── vector_db/
│   │   ├── embeddings.py           ← Local/Google embedding engine
│   │   ├── chroma_client.py        ← ChromaDB CRUD operations
│   │   └── indexer.py              ← High-level indexing pipeline
│   ├── rag/
│   │   ├── retriever.py            ← Semantic search with source citation
│   │   ├── generator.py            ← Gemini/Claude LLM generation
│   │   └── pipeline.py             ← Full RAG pipeline
│   ├── agents/
│   │   ├── legal_agent.py          ← Interactive AI agent
│   │   └── tools.py                ← Agent tool registry
│   └── utils/
│       ├── metadata.py             ← Legal metadata extraction
│       └── file_utils.py           ← File utilities
├── data/
│   ├── raw/                        ← Downloaded legal data
│   └── uploads/                    ← Your own files (drop here)
├── chroma_db/                      ← ChromaDB persistent storage
├── ingest.py                       ← Data ingestion CLI
└── main.py                         ← Agent CLI
```

## Data Sources

### CourtListener (Free API)
- All US federal court opinions
- No API key required for basic access
- Register at courtlistener.com for higher rate limits

### HuggingFace Datasets (Free)
- `us_scotus` — US Supreme Court cases
- `legal_contracts` — US legal contracts
- `legal_case_reports` — General case reports

### Your Own Files
Drop any PDF, DOCX, PPTX, XLSX, CSV, or TXT files into `data/uploads/` and run `python ingest.py`.
