from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import logging

from app.models.chat import ChatRequest, ChatResponse
from app.services.vector_service import build_faiss_index, get_faiss_stats
from app.services.llm_service import stream_answer
from app.services.question_validator import is_question_in_scope, get_rejection_message
from app.services.intent_classifier import classify_intent, should_include_job_data
from app.services.optimized_vector_service import semantic_search_optimized, get_jobs_optimized
from app.prompt_engine.prompt_builder import build_optimized_prompt

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """
    Chat with streaming response - Optimized with Intent Classification
    """
    try:
        user_message = request.message
        
        # Step 1: Validate question scope
        is_valid, reason = is_question_in_scope(user_message)
        if not is_valid:
            async def rejection_stream():
                yield get_rejection_message(reason)
            
            return StreamingResponse(
                rejection_stream(),
                media_type="text/plain; charset=utf-8"
            )
        
        # Step 2: Classify intent
        intent, category = classify_intent(user_message)
        logger.info(f"Intent: {intent.value}, Category: {category.value if category else None}")
        
        # Step 3: Conditional job search
        job_context = []
        if should_include_job_data(intent):
            job_ids = await semantic_search_optimized(user_message, category, top_k=3)
            job_context = await get_jobs_optimized(job_ids, category)
            logger.info(f"Retrieved {len(job_context)} jobs for category {category.value if category else None}")
        else:
            logger.info("Skipping job search for consultation")
        
        # Step 4: Build optimized prompt
        prompt = build_optimized_prompt(user_message, intent, job_context, category)
        
        # Step 5: Stream LLM response
        return StreamingResponse(
            stream_answer(prompt),
            media_type="text/plain; charset=utf-8"
        )
        
    except Exception as e:
        logger.error(f"Chat stream error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/faiss-stats")
async def get_vector_stats():
    """Get FAISS index statistics"""
    try:
        return get_faiss_stats()
    except Exception as e:
        logger.error(f"Failed to get FAISS stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get vector statistics")

@router.post("/rebuild-index")
async def rebuild_index():
    """Rebuild FAISS index from database"""
    try:
        await build_faiss_index()
        stats = get_faiss_stats()
        return {
            "message": "FAISS index rebuilt successfully",
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Failed to rebuild index: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to rebuild index")