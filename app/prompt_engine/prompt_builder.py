"""
Optimized Prompt Builder
Xây dựng prompt tối ưu dựa trên intent classification
"""
from app.prompt_engine.system_prompt import SYSTEM_PROMPT
from app.services.intent_classifier import IntentType, JobCategory, get_optimized_prompt_instruction
from typing import List, Optional


def build_optimized_prompt(
    user_message: str, 
    intent: IntentType, 
    job_context: Optional[List[dict]] = None,
    category: Optional[JobCategory] = None
) -> str:
    """
    Xây dựng prompt tối ưu dựa trên intent
    """
    if intent == IntentType.CONSULTATION:
        # Tư vấn chung - không cần job data
        category_context = ""
        if category:
            category_context = f"\n\nLƯU Ý: Câu hỏi liên quan đến lĩnh vực {category.value}. Hãy tập trung tư vấn về lĩnh vực này."
        
        instruction = get_optimized_prompt_instruction(IntentType.CONSULTATION, category)
        
        return f"""{SYSTEM_PROMPT}{category_context}

===== CÂU HỎI TƯ VẤN =====
{user_message}

{instruction}

Hãy đưa ra lời tư vấn hữu ích, cụ thể và thiết thực."""
    
    else:
        # Gợi ý công việc - có job data
        job_data = job_context or []
        
        if job_data:
            formatted_jobs = "\n\n".join([
                f"🔹 Công việc {idx}: {job['title']}\n"
                f"   • Công ty: {job['company']}\n"
                f"   • Địa điểm: {job['location']}\n"
                f"   • Lương: {job['salary']}\n"
                f"   • Kỹ năng: {job['skills']}\n"
                f"   • Mô tả: {job['description']}\n"
                f"   • Yêu cầu: {job['requirements']}"
                for idx, job in enumerate(job_data, 1)
            ])
            
            job_data_section = f"Tìm thấy {len(job_data)} công việc phù hợp trong lĩnh vực {category.value if category else 'được yêu cầu'}:\n\n{formatted_jobs}"
        else:
            job_data_section = f"Không tìm thấy công việc phù hợp trong lĩnh vực {category.value if category else 'được yêu cầu'}."
        
        instruction = get_optimized_prompt_instruction(IntentType.JOB_SUGGESTION, category)
        
        return f"""{SYSTEM_PROMPT}

===== DỮ LIỆU CÔNG VIỆC =====
{job_data_section}

===== CÂU HỎI =====
{user_message}

{instruction}"""


def get_prompt_stats(prompt: str) -> dict:
    """Lấy thống kê về prompt để monitor performance"""
    return {
        "total_chars": len(prompt),
        "total_words": len(prompt.split()),
        "estimated_tokens": len(prompt) // 4,
        "lines": len(prompt.split('\n'))
    }