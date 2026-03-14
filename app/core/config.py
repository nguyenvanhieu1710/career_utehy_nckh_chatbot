import os
from typing import List
from dotenv import load_dotenv
load_dotenv()

class Settings:
    # MongoDB settings
    MONGODB_URL: str = os.getenv("MONGODB_URL", "")
    MONGODB_DB_NAME: str = os.getenv("MONGODB_DB_NAME", "")
    
    # Ollama settings
    OLLAMA_URL: str = os.getenv("OLLAMA_URL", "")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "")
    OLLAMA_TIMEOUT: int = int(os.getenv("OLLAMA_TIMEOUT", ""))
    
    # CORS settings
    ALLOWED_ORIGINS: List[str] = ["*"]
    
    # Vector storage
    FAISS_INDEX_DIR: str = os.getenv("FAISS_INDEX_DIR", "")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "")

settings = Settings()