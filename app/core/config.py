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
    
    # AI / LLM settings (Gemini for generate_content, BGE-M3 for embeddings)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL")
    EMBEDDING_MODEL_NAME: str = os.getenv("EMBEDDING_MODEL_NAME")
    HF_TOKEN: str = os.getenv("HF_TOKEN")
    
    # CORS settings
    ALLOWED_ORIGINS: List[str] = ["*"]
    
    # Milvus settings
    MILVUS_URL: str = os.getenv("MILVUS_URL", "")
    MILVUS_TOKEN: str = os.getenv("MILVUS_TOKEN", "")
    MILVUS_COLLECTION: str = os.getenv("MILVUS_COLLECTION", "chatbot_jobs_gemini")
    
    # Server settings
    PORT: int = int(os.getenv("PORT", ""))

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "")

settings = Settings()