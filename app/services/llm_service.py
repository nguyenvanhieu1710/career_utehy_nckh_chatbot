import json
import logging
from typing import Generator
import google.generativeai as genai
from app.core.config import settings

logger = logging.getLogger(__name__)

# Configure Gemini
if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)
else:
    logger.warning("GEMINI_API_KEY is missing. Gemini API will fail.")

MODEL_NAME = "gemini-2.5-flash"
try:
    model = genai.GenerativeModel(MODEL_NAME)
except Exception as e:
    logger.error(f"Failed to initialize Gemini model: {str(e)}")
    model = None

def generate_answer(prompt: str) -> str:
    """
    Generate answer from Gemini API
    
    Args:
        prompt: User question/prompt
        
    Returns:
        Generated answer or error message
    """
    if not model:
        return "Hệ thống AI chưa được cấu hình đúng. Vui lòng kiểm tra lại cấu hình."
        
    try:
        response = model.generate_content(prompt)
        # Check if response was blocked or has no text
        if response.text:
            return response.text.strip()
        return "Xin lỗi, tôi không thể tạo câu trả lời cho nội dung này."
    except Exception as e:
        logger.error(f"Unexpected error with Gemini: {str(e)}", exc_info=True)
        return "Đã xảy ra lỗi không mong muốn. Vui lòng thử lại sau."

def stream_answer(prompt: str) -> Generator[str, None, None]:
    """
    Generate answer from Gemini API (streaming)
    Yields partial text chunks
    """
    if not model:
        yield "Hệ thống AI chưa được cấu hình đúng."
        return

    try:
        response = model.generate_content(prompt, stream=True)
        for chunk in response:
            if chunk.text:
                yield chunk.text
    except Exception as e:
        logger.error(f"Streaming unexpected error with Gemini: {str(e)}", exc_info=True)
        yield "Đã xảy ra lỗi không mong muốn trong quá trình tạo luồng dữ liệu."