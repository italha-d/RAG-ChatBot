import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
OLLAMA_CHAT_MODEL = os.getenv("OLLAMA_CHAT_MODEL", "llama3.2")

PROJECT_ROOT = Path(__file__).resolve().parent
CHROMA_PATH = Path(os.getenv("CHROMA_PATH", PROJECT_ROOT / "index"))
UPLOADS_DIR = Path(os.getenv("UPLOADS_DIR", PROJECT_ROOT / "uploads"))
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "rag_documents")

APP_HOST = os.getenv("APP_HOST", "127.0.0.1")
APP_PORT = int(os.getenv("APP_PORT", "7860"))

CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "800"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "120"))
TOP_K = int(os.getenv("TOP_K", "6"))

# Extensions treated as text; empty set means "any file that decodes as UTF-8".
TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".markdown",
    ".rst",
    ".csv",
    ".tsv",
    ".json",
    ".jsonl",
    ".yaml",
    ".yml",
    ".xml",
    ".html",
    ".htm",
    ".css",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".py",
    ".pyi",
    ".java",
    ".kt",
    ".go",
    ".rs",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
    ".cs",
    ".rb",
    ".php",
    ".swift",
    ".sql",
    ".sh",
    ".bash",
    ".ps1",
    ".bat",
    ".env",
    ".ini",
    ".cfg",
    ".conf",
    ".toml",
    ".log",
    ".tex",
    ".r",
    ".lua",
    ".scala",
    ".clj",
    ".vim",
    ".dockerfile",
    ".gitignore",
    ".editorconfig",
}

OFFICE_EXTENSIONS = {
    ".pdf",
    ".docx",
}

SKIP_DIR_NAMES = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    "index",
    "uploads",
    ".chroma",
    ".cursor",
}
