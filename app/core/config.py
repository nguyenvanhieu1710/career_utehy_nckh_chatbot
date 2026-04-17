import os
from typing import List
from dotenv import load_dotenv
load_dotenv()

class Settings:
    # MongoDB settings
    MONGODB_URL: str = os.getenv("MONGODB_URL", "")
    MONGODB_DB_NAME: str = os.getenv("MONGODB_DB_NAME", "")
    
    # PostgreSQL settings
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    
    # Gemini settings
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # CORS settings
    ALLOWED_ORIGINS: List[str] = ["*"]
    
    # Vector storage
    FAISS_INDEX_DIR: str = os.getenv("FAISS_INDEX_DIR", "")
    
    # Server settings
    PORT: int = int(os.getenv("PORT", ""))

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "")

settings = Settings()