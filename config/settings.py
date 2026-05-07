"""Central configuration for CompleteRagAI."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent.parent

# ── API Keys ────────────────────────────────────────────────
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
COURTLISTENER_TOKEN = os.getenv("COURTLISTENER_TOKEN", "")

# ── LLM ─────────────────────────────────────────────────────
# Options: "groq" | "gemini" | "claude" | "auto"
# "auto" picks the first available key in order: groq → gemini → claude
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "auto")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5-20251001")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# ── Embeddings ───────────────────────────────────────────────
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "local")
LOCAL_EMBEDDING_MODEL = "all-MiniLM-L6-v2"
GOOGLE_EMBEDDING_MODEL = "gemini-embedding-001"

# ── Vector DB ────────────────────────────────────────────────
# Options: "chromadb" (local) | "pinecone" (cloud - for serverless deployment)
VECTOR_DB_PROVIDER = os.getenv("VECTOR_DB_PROVIDER", "chromadb")

# ChromaDB (local - default)
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", str(BASE_DIR / "chroma_db"))
CHROMA_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "legal_cases")

# Pinecone (cloud - for Vercel/Render deployment)
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "legal-rag")
PINECONE_CLOUD = os.getenv("PINECONE_CLOUD", "aws")  # aws or gcp
PINECONE_REGION = os.getenv("PINECONE_REGION", "us-east-1")

# ── Data Paths ───────────────────────────────────────────────
DATA_RAW_PATH = Path(os.getenv("DATA_RAW_PATH", str(BASE_DIR / "data" / "raw")))
DATA_PROCESSED_PATH = Path(os.getenv("DATA_PROCESSED_PATH", str(BASE_DIR / "data" / "processed")))
DATA_UPLOADS_PATH = Path(os.getenv("DATA_UPLOADS_PATH", str(BASE_DIR / "data" / "uploads")))

for p in [DATA_RAW_PATH, DATA_PROCESSED_PATH, DATA_UPLOADS_PATH]:
    p.mkdir(parents=True, exist_ok=True)

# ── Chunking ─────────────────────────────────────────────────
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
MAX_CHUNKS_PER_DOC = 500

# ── Retrieval ────────────────────────────────────────────────
TOP_K_RESULTS = 8  # Retrieve more chunks for better context
SIMILARITY_THRESHOLD = 0.15  # Lower threshold to capture more content

# ── Download ─────────────────────────────────────────────────
MAX_DOWNLOAD_SIZE_GB = float(os.getenv("MAX_DOWNLOAD_SIZE_GB", "3"))
DOWNLOAD_BATCH_SIZE = int(os.getenv("DOWNLOAD_BATCH_SIZE", "100"))

# ── Odoo CRM ─────────────────────────────────────────────────
ODOO_URL = os.getenv("ODOO_URL", "")
ODOO_DB = os.getenv("ODOO_DB", "")
ODOO_USER = os.getenv("ODOO_USER", "")
ODOO_PASS = os.getenv("ODOO_PASS", "")

# ── VAPI Voice AI ─────────────────────────────────────────────
VAPI_API_KEY = os.getenv("VAPI_API_KEY", "")
VAPI_ASSISTANT_ID = os.getenv("VAPI_ASSISTANT_ID", "")
VAPI_PHONE_NUMBER_ID = os.getenv("VAPI_PHONE_NUMBER_ID", "")
HUMAN_TRANSFER_NUMBER = os.getenv("HUMAN_TRANSFER_NUMBER", "")

# ── Support Contact ───────────────────────────────────────────
SUPPORT_EMAIL = os.getenv("SUPPORT_EMAIL", "seekhowithrua@gmail.com")

# ── Supported File Types ─────────────────────────────────────
SUPPORTED_EXTENSIONS = {
    ".pdf", ".docx", ".doc", ".pptx", ".ppt",
    ".xlsx", ".xls", ".csv", ".txt", ".md",
    ".json", ".html", ".htm", ".rtf",
}
