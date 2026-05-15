from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator
import logging

import time
from app.models.chat import ChatRequest, ChatResponse
from app.services.vector_service import (
    sync_to_milvus,
    get_milvus_stats
)
from app.services.search.orchestrator import search_jobs as hybrid_search
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
    4. Build prompt & stream câu trả lời từ llm
    """
    async def generate() -> AsyncGenerator[str, None]:
        start_time = time.time()
        try:
            # Bước 1: Validate câu hỏi
            is_valid, reason = is_question_in_scope(request.message)
            if not is_valid:
                yield get_rejection_message(reason)
                return

            # Bước 2: Classify intent
            intent, category = await classify_intent(request.message)

            # Bước 3: Lấy job data nếu cần
            job_context = None
            search_start = time.time()
            if intent == IntentType.JOB_SUGGESTION:
                job_context = await hybrid_search(
                    query=request.message,
                    top_k=3,
                    category=category,
                    enable_hybrid=True
                )
            search_duration = time.time() - search_start

            # Bước 4: Build prompt và stream câu trả lời
            prompt = build_optimized_prompt(
                user_message=request.message,
                intent=intent,
                job_context=job_context,
                category=category
            )

            ttft_measured = False
            async for chunk in stream_answer(prompt):
                if not ttft_measured:
                    ttft = time.time() - start_time
                    logger.info(f"[PERF] TTFT: {ttft:.3f}s | Search: {search_duration:.3f}s | Intent: {intent}")
                    ttft_measured = True
                yield chunk
            
            total_duration = time.time() - start_time
            logger.info(f"[PERF] Total E2E: {total_duration:.3f}s")

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