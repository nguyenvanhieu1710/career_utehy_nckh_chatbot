import logging
from typing import Generator
from google import genai
from app.core.config import settings

logger = logging.getLogger(__name__)

_client = None

def get_client():
    """Get or create Gemini client (lazy-init để đọc key mới nhất từ .env)"""
    global _client
    if _client is None:
        key = settings.GEMINI_API_KEY
        model = settings.GEMINI_MODEL
        if not key:
            logger.warning("GEMINI_API_KEY is missing. Gemini API will fail.")
            return None
        # logger.info(f"Initializing Gemini client | model={model} | key={key[:8]}...{key[-4:]}")
        try:
            _client = genai.Client(api_key=key)
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {str(e)}")
            return None
    return _client


def generate_answer(prompt: str) -> str:
    """
    Generate answer from Gemini API using the modern SDK
    """
    c = get_client()
    if not c:
        return "Hệ thống AI chưa được cấu hình đúng. Vui lòng kiểm tra lại cấu hình."

    try:
        response = c.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt
        )
        if response.text:
            return response.text.strip()
        return "Xin lỗi, tôi không thể tạo câu trả lời cho nội dung này."
    except Exception as e:
        logger.error(f"Unexpected error with Gemini: {str(e)}", exc_info=True)
        return "Đã xảy ra lỗi không mong muốn. Vui lòng thử lại sau."

def stream_answer(prompt: str) -> Generator[str, None, None]:
    """
    Generate answer from Gemini API (streaming) using the modern SDK
    """
    c = get_client()
    if not c:
        yield "Hệ thống AI chưa được cấu hình đúng."
        return

    try:
        response = c.models.generate_content_stream(
            model=settings.GEMINI_MODEL,
            contents=prompt
        )
        for chunk in response:
            if chunk.text:
                yield chunk.text
    except Exception as e:
        logger.error(f"Streaming unexpected error with Gemini: {str(e)}", exc_info=True)
        yield "Đã xảy ra lỗi không mong muốn trong quá trình tạo luồng dữ liệu."