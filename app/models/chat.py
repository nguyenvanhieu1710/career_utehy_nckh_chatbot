from pydantic import BaseModel, Field
from typing import Optional

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000, description="User message")

class ChatResponse(BaseModel):
    response: str
    intent: Optional[str] = None
    category: Optional[str] = None
    job_count: Optional[int] = None

class HealthResponse(BaseModel):
    status: str
    service: str
    version: str = "1.0.0"