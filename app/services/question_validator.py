"""
Question Validator Service
Validates if user questions are within scope (job/career related)
"""
import re
from typing import Tuple


# Blacklist keywords - out of scope topics
BLACKLIST_KEYWORDS = {
    # Medical
    "y tế", "bệnh", "thuốc", "chữa", "đau", "sức khỏe", "bác sĩ", "khám", "điều trị",
    "vaccine", "covid", "cảm cúm", "đau đầu", "đau bụng", "sốt", "ho",
    
    # Legal
    "pháp luật", "luật", "kiện", "tòa án", "hợp đồng", "vi phạm", "tội", "phạt",
    "ly hôn", "thừa kế", "tranh chấp", "bồi thường",
    
    # Financial advice
    "đầu tư", "chứng khoán", "cổ phiếu", "forex", "crypto", "bitcoin", "coin",
    "vay tiền", "vay vốn", "lãi suất", "ngân hàng", "tín dụng", "nợ",
    
    # Politics
    "chính trị", "bầu cử", "đảng", "chính phủ", "tổng thống", "thủ tướng",
    
    # Religion
    "tôn giáo", "phật", "chúa", "allah", "cầu nguyện", "nhà thờ", "chùa",
    
    # Inappropriate
    "sex", "tình dục", "khiêu dâm", "porn", "xxx",
    
    # Personal advice (non-career)
    "tình yêu", "chia tay", "hẹn hò", "bạn gái", "bạn trai", "crush",
}

# Whitelist keywords - job/career related
WHITELIST_KEYWORDS = {
    "việc làm", "công việc", "tuyển dụng", "ứng tuyển", "cv", "resume",
    "phỏng vấn", "interview", "lương", "salary", "nghề nghiệp", "career",
    "kỹ năng", "skill", "kinh nghiệm", "experience", "học vấn", "bằng cấp",
    "công ty", "doanh nghiệp", "tổ chức", "startup", "intern", "thực tập",
    "full-time", "part-time", "remote", "freelance", "lập trình", "developer",
    "kỹ sư", "engineer", "designer", "marketing", "sales", "giáo dục",
    "giáo viên", "giảng viên", "gia sư", "tư vấn nghề nghiệp",
}


def is_question_in_scope(question: str) -> Tuple[bool, str]:
    """
    Check if question is within scope (job/career related)
    
    Args:
        question: User's question
        
    Returns:
        Tuple[bool, str]: (is_valid, reason)
            - is_valid: True if question is in scope
            - reason: Explanation message
    """
    question_lower = question.lower().strip()
    
    # Empty question
    if not question_lower or len(question_lower) < 3:
        return False, "Câu hỏi quá ngắn. Vui lòng mô tả rõ hơn."
    
    # Check blacklist (out of scope)
    for keyword in BLACKLIST_KEYWORDS:
        if re.search(r'\b' + re.escape(keyword) + r'\b', question_lower):
            return False, (
                f"Xin lỗi, tôi chỉ tư vấn về việc làm và nghề nghiệp. "
                f"Tôi không thể trả lời câu hỏi về {keyword}. "
                f"Bạn có thể hỏi về tìm việc, kỹ năng, hoặc lời khuyên nghề nghiệp."
            )
    
    # Check whitelist (in scope)
    has_job_keyword = False
    for keyword in WHITELIST_KEYWORDS:
        if keyword in question_lower:
            has_job_keyword = True
            break
    
    # If has job keyword, definitely in scope
    if has_job_keyword:
        return True, "Valid job-related question"
    
    # Ambiguous - allow but with lower confidence
    # Let LLM handle it with strict instructions
    if len(question_lower) > 10:
        return True, "Ambiguous but allowed"
    
    return False, (
        "Tôi không chắc câu hỏi của bạn liên quan đến việc làm. "
        "Bạn có thể hỏi rõ hơn về công việc, kỹ năng, hoặc nghề nghiệp không?"
    )


def get_rejection_message(reason: str) -> str:
    """
    Get friendly rejection message for out-of-scope questions
    
    Args:
        reason: Reason for rejection
        
    Returns:
        Formatted rejection message
    """
    return f"""🚫 {reason}

💡 Tôi có thể giúp bạn:
- Tìm việc làm phù hợp
- Tư vấn kỹ năng cần có
- Gợi ý nghề nghiệp
- Chuẩn bị phỏng vấn
- Định hướng sự nghiệp

Hãy thử hỏi: "Tìm việc lập trình Python" hoặc "Kỹ năng cần có cho marketing"
"""