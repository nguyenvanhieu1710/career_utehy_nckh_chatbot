import logging
import asyncio
from typing import Generator
from google import genai
from groq import AsyncGroq
from app.core.config import settings

logger = logging.getLogger(__name__)

_gemini_client = None
_groq_client = None

def get_gemini_client():
    global _gemini_client
    if _gemini_client is None:
        key = settings.GEMINI_API_KEY
        if not key: return None
        try:
            _gemini_client = genai.Client(api_key=key)
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
    return _gemini_client

def get_groq_client():
    global _groq_client
    if _groq_client is None:
        key = settings.GROQ_API_KEY
        if not key: return None
        try:
            _groq_client = AsyncGroq(api_key=key)
        except Exception as e:
            logger.error(f"Failed to initialize Groq: {e}")
    return _groq_client


async def generate_answer(prompt: str) -> str:
    """Thử Groq trước (tốc độ cao), nếu lỗi fallback sang Gemini"""
    # 1. Thử Groq
    c_groq = get_groq_client()
    if c_groq:
        try:
            response = await c_groq.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"Groq failed, trying Gemini fallback: {e}")

    # 2. Fallback sang Gemini
    c_gemini = get_gemini_client()
    if c_gemini:
        try:
            response = c_gemini.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt
            )
            if response.text: return response.text.strip()
        except Exception as e:
            logger.error(f"Both LLMs failed: {e}")
    
    return "Xin lỗi, hiện tại tôi đang gặp khó khăn khi kết nối với các mô hình ngôn ngữ. Vui lòng thử lại sau."

async def stream_answer(prompt: str) -> Generator[str, None, None]:
    """Stream answer với Groq là Primary và Gemini là Fallback"""
    # 1. Thử Groq Stream
    c_groq = get_groq_client()
    success = False
    if c_groq:
        try:
            response = await c_groq.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                stream=True
            )
            async for chunk in response:
                content = chunk.choices[0].delta.content
                if content:
                    yield content
            success = True
        except Exception as e:
            logger.warning(f"Groq stream failed, switching to Gemini: {e}")

    if success: return

    # 2. Fallback sang Gemini Stream
    c_gemini = get_gemini_client()
    if c_gemini:
        try:
            response = c_gemini.models.generate_content_stream(
                model=settings.GEMINI_MODEL,
                contents=prompt
            )
            for chunk in response:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            logger.error(f"Fallback Gemini stream also failed: {e}")
            yield "Đã xảy ra lỗi kết nối với toàn bộ hệ thống AI."