
import os
from datetime import date
from pathlib import Path
from dotenv import load_dotenv

# Project root
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables
load_dotenv(BASE_DIR / ".env", override=True)

# Original assessment folder
ASSESSMENT_DIR = (
    Path.home()
    / "Downloads"
    / "veltrix_assessment"
    / "veltrix_assessment"
)

# Original assessment documents and manifest
DATA_DIR = ASSESSMENT_DIR / "corpus"
CORPUS_DIR = DATA_DIR
MANIFEST_PATH = ASSESSMENT_DIR / "manifest.json"

# Local project index
INDEX_DIR = BASE_DIR / os.getenv("INDEX_DIR", "index")

# Original assessment database
DATABASE_PATH = Path(
    os.getenv(
        "DATABASE_PATH",
        str(ASSESSMENT_DIR / "veltrix.db")
    )
)

# Gemini configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL", "gemini-2.5-flash"
).strip()

# Groq configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv(
    "GROQ_MODEL", "openai/gpt-oss-120b"
).strip()

# RAG configuration
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "150"))
TOP_K = int(os.getenv("TOP_K", "5"))
MAX_CORPUS_TOKENS = int(
    os.getenv("MAX_CORPUS_TOKENS", "3000")
)

APP_TODAY = date.fromisoformat(
    os.getenv("APP_TODAY", "2026-11-02")
)

# Create only the local index folder
INDEX_DIR.mkdir(parents=True, exist_ok=True)

# Validate assessment files
if not DATA_DIR.exists():
    raise FileNotFoundError(
        f"Assessment corpus not found: {DATA_DIR}"
    )

if not MANIFEST_PATH.exists():
    raise FileNotFoundError(
        f"Assessment manifest not found: {MANIFEST_PATH}"
    )

if not DATABASE_PATH.exists():
    raise FileNotFoundError(
        f"Assessment database not found: {DATABASE_PATH}"
    )
