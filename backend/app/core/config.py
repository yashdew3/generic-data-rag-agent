# backend/app/core/config.py
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Generic Data RAG Agent"
    UPLOAD_DIR: Path = Path("uploads")
    META_FILE: Path = UPLOAD_DIR / "uploads.json"
    FRONTEND_ORIGIN: str | None = None  
    
    # Gemini API configuration
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_MAX_CONTEXT_CHARS: int = 4000
    RETRIEVER_TOP_K: int = 5

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"  

# instantiate once for import across the app
settings = Settings()
