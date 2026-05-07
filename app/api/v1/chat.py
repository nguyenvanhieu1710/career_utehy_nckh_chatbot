from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator
import logging

from app.models.chat import ChatRequest, ChatResponse
from app.services.vector_service import (
    sync_to_milvus,
    get_milvus_stats
)
from app.services.hybrid_search_service import hybrid_search
from app.services.intent_classifier import classify_intent, IntentType
from app.services.question_validator import is_question_in_scope, get_rejection_message
from app.services.llm_service import stream_answer
from app.prompt_engine.prompt_builder import build_optimized_prompt

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """
    Chat Streaming endpoint:
    1. Validate câu hỏi
    2. Classify intent (tư vấn vs tìm việc)
    3. Hybrid Search nếu cần job data
    4. Build prompt & stream câu trả lời từ Gemini
    """
    async def generate() -> AsyncGenerator[str, None]:
        try:
            # Bước 1: Validate câu hỏi có liên quan nghề nghiệp không
            is_valid, reason = is_question_in_scope(request.message)
            if not is_valid:
                yield get_rejection_message(reason)
                return

            # Bước 2: Classify intent
            intent, category = classify_intent(request.message)

            # Bước 3: Lấy job data nếu cần
            job_context = None
            if intent == IntentType.JOB_SUGGESTION:
                job_context = await hybrid_search(
                    query=request.message,
                    top_k=request.top_k if hasattr(request, 'top_k') else 5,
                    category=category,
                    enable_hybrid=True
                )

            # Bước 4: Build prompt và stream câu trả lời
            prompt = build_optimized_prompt(
                user_message=request.message,
                intent=intent,
                job_context=job_context,
                category=category
            )

            for chunk in stream_answer(prompt):
                yield chunk

        except Exception as e:
            logger.error(f"Chat stream error: {str(e)}", exc_info=True)
            yield "Đã xảy ra lỗi. Vui lòng thử lại sau."

    return StreamingResponse(generate(), media_type="text/plain")


@router.get("/milvus-stats")
async def get_vector_stats():
    """Get statistics from Milvus Cloud collection"""
    stats = get_milvus_stats()
    if stats:
        return stats
    raise HTTPException(status_code=500, detail="Failed to get Milvus stats")


@router.post("/sync-milvus")
async def sync_milvus_endpoint():
    """
    Trigger synchronization of PostgreSQL jobs to Milvus Cloud.
    """
    success = await sync_to_milvus()
    if success:
        return {"message": "Data synchronized to Milvus Cloud successfully"}
    raise HTTPException(status_code=500, detail="Failed to sync data to Milvus")