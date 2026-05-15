"""
Intent Classification Service
Phân loại ý định của người dùng để tối ưu hóa prompt
"""
import re
from typing import Tuple, Optional, List
from enum import Enum


class IntentType(Enum):
    """Loại ý định của người dùng"""
    CONSULTATION = "consultation"  # Tư vấn chung
    JOB_SUGGESTION = "job_suggestion"  # Gợi ý công việc cụ thể
    UNKNOWN = "unknown"  # Không xác định


class JobCategory(Enum):
    """Danh mục công việc"""
    IT = "it"
    EDUCATION = "education"
    FINANCE = "finance"
    HEALTHCARE = "healthcare"
    MARKETING = "marketing"
    SALES = "sales"
    HR = "hr"
    ENGINEERING = "engineering"
    DESIGN = "design"
    OTHER = "other"


# Keywords cho từng loại ý định
CONSULTATION_KEYWORDS = {
    # Tư vấn chung về nghề nghiệp
    "tư vấn", "hướng dẫn", "định hướng", "lời khuyên", "gợi ý nghề nghiệp",
    "nên học", "nên chọn", "phù hợp", "sinh viên năm", "mới ra trường",
    "chuyển nghề", "phát triển sự nghiệp", "kỹ năng cần có", "chuẩn bị",
    "học thêm", "chứng chỉ", "kinh nghiệm", "thăng tiến", "tương lai",
    "xu hướng", "triển vọng", "cơ hội", "thách thức", "khó khăn",
    "làm thế nào", "bắt đầu", "cần gì", "yêu cầu", "điều kiện"
}

JOB_SUGGESTION_KEYWORDS = {
    # Yêu cầu gợi ý công việc cụ thể
    "tìm việc", "việc làm", "công việc", "tuyển dụng", "ứng tuyển",
    "job", "work", "position", "vị trí", "chức vụ", "tuyển",
    "hiring", "recruitment", "apply", "ứng viên", "candidate"
}
# Keywords cho từng lĩnh vực
CATEGORY_KEYWORDS = {
    JobCategory.IT: {
        "lập trình", "developer", "programmer", "software", "phần mềm",
        "web", "mobile", "app", "website", "code", "coding", "python",
        "java", "javascript", "react", "nodejs", "php", "c++", "c#",
        "database", "sql", "mysql", "mongodb", "api", "backend", "frontend",
        "fullstack", "devops", "system admin", "network", "security",
        "cybersecurity", "data science", "machine learning", "ai", "blockchain",
        "game", "unity", "android", "ios", "flutter", "react native"
    },
    
    JobCategory.EDUCATION: {
        "giáo dục", "giáo viên", "giảng viên", "thầy cô", "dạy học",
        "gia sư", "teacher", "education", "training", "đào tạo",
        "học sinh", "sinh viên", "trường học", "đại học", "cao đẳng",
        "mầm non", "tiểu học", "trung học", "phổ thông", "chuyên môn",
        "sư phạm", "pedagogy", "curriculum", "giáo trình"
    },
    
    JobCategory.FINANCE: {
        "tài chính", "ngân hàng", "kế toán", "finance", "banking",
        "accounting", "accountant", "audit", "kiểm toán", "thuế",
        "tax", "investment", "đầu tư", "bảo hiểm", "insurance",
        "credit", "tín dụng", "loan", "vay", "financial", "money"
    },
    
    JobCategory.HEALTHCARE: {
        "y tế", "bác sĩ", "y sĩ", "điều dưỡng", "dược sĩ", "healthcare",
        "medical", "doctor", "nurse", "pharmacy", "hospital", "bệnh viện",
        "phòng khám", "clinic", "health", "sức khỏe", "chăm sóc"
    },
    
    JobCategory.MARKETING: {
        "marketing", "quảng cáo", "advertising", "brand", "thương hiệu",
        "digital marketing", "social media", "content", "seo", "sem",
        "facebook ads", "google ads", "email marketing", "pr",
        "public relations", "truyền thông", "media", "campaign"
    },
    
    JobCategory.SALES: {
        "bán hàng", "sales", "kinh doanh", "business", "telesales",
        "account", "customer", "khách hàng", "tư vấn bán hàng",
        "sale executive", "business development", "retail", "wholesale"
    },
    
    JobCategory.HR: {
        "nhân sự", "hr", "human resources", "tuyển dụng", "recruitment",
        "recruiter", "talent", "payroll", "lương", "benefits", "training",
        "employee", "nhân viên", "quản lý nhân sự", "hrm", "hris"
    },
    
    JobCategory.ENGINEERING: {
        "kỹ sư", "engineer", "engineering", "xây dựng", "construction",
        "cơ khí", "mechanical", "điện", "electrical", "điện tử", "electronic",
        "hóa học", "chemical", "môi trường", "environmental", "civil",
        "dân dụng", "công nghiệp", "industrial", "automation", "tự động hóa"
    },
    
    JobCategory.DESIGN: {
        "thiết kế", "design", "designer", "graphic", "ui", "ux",
        "photoshop", "illustrator", "figma", "sketch", "creative",
        "sáng tạo", "nghệ thuật", "art", "visual", "layout", "branding"
    }
}


async def classify_intent(message: str) -> Tuple[IntentType, Optional[JobCategory]]:
    """
    Phân loại ý định của người dùng bằng LLM (ưu tiên) hoặc Regex (fallback)
    """
    message_lower = message.lower().strip()
    
    # 1. Thử phân loại bằng LLM để có độ chính xác cao nhất
    from app.services.llm_service import generate_answer
    import json
    
    system_prompt = f"""Bạn là một trợ lý phân loại ý định người dùng. 
Dựa trên câu hỏi, hãy phân loại vào một trong hai nhóm:
- CONSULTATION: Tư vấn nghề nghiệp, định hướng, lời khuyên, kỹ năng, xu hướng thị trường.
- JOB_SUGGESTION: Tìm kiếm công việc cụ thể, gợi ý vị trí tuyển dụng.

Cũng hãy xác định lĩnh vực (category) từ các giá trị: {", ".join([c.value for c in JobCategory])}.

Chỉ trả về JSON theo định dạng: {{"intent": "CONSULTATION"|"JOB_SUGGESTION", "category": "value"}}.
Câu hỏi: "{message}"
"""
    try:
        response_text = await generate_answer(system_prompt)
        # Làm sạch response để lấy JSON
        json_match = re.search(r'\{.*\}', response_text.replace('\n', ''), re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            intent_str = data.get("intent", "").lower()
            category_str = data.get("category", "").lower()
            
            intent = IntentType.CONSULTATION
            if "job" in intent_str: intent = IntentType.JOB_SUGGESTION
            
            category = None
            for c in JobCategory:
                if c.value == category_str:
                    category = c
                    break
            return intent, category
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"LLM Intent Classification failed, falling back to Regex: {e}")

    # 2. Fallback sang Regex logic (như cũ)
    # Kiểm tra keywords tư vấn
    has_consultation_keyword = any(
        keyword in message_lower for keyword in CONSULTATION_KEYWORDS
    )
    
    # Kiểm tra keywords gợi ý công việc
    has_job_suggestion_keyword = any(
        keyword in message_lower for keyword in JOB_SUGGESTION_KEYWORDS
    )
    
    detected_category = None
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in message_lower for keyword in keywords):
            detected_category = category
            break
    
    if has_job_suggestion_keyword and detected_category:
        return IntentType.JOB_SUGGESTION, detected_category
    elif has_consultation_keyword:
        return IntentType.CONSULTATION, detected_category
    elif detected_category and not has_consultation_keyword:
        return IntentType.JOB_SUGGESTION, detected_category
    else:
        return IntentType.CONSULTATION, None


def get_category_filter(category: JobCategory) -> List[str]:
    """
    Lấy danh sách từ khóa để filter jobs theo danh mục
    
    Args:
        category: Danh mục công việc
        
    Returns:
        List[str]: Danh sách từ khóa để tìm kiếm
    """
    if category in CATEGORY_KEYWORDS:
        return list(CATEGORY_KEYWORDS[category])
    return []


def should_include_job_data(intent: IntentType) -> bool:
    """
    Xác định có nên include job data vào prompt không
    Luôn trả về True để tăng tính thực tế của lời tư vấn
    """
    return intent in [IntentType.JOB_SUGGESTION, IntentType.CONSULTATION]


def get_optimized_prompt_instruction(intent: IntentType, category: Optional[JobCategory]) -> str:
    """
    Lấy instruction tối ưu cho prompt dựa trên intent
    
    Args:
        intent: Loại ý định
        category: Danh mục công việc (nếu có)
        
    Returns:
        str: Instruction cho prompt
    """
    if intent == IntentType.CONSULTATION:
        category_name = category.value if category else "các lĩnh vực liên quan"
        return f"""
===== HƯỚNG DẪN TƯ VẤN (Chuyên gia hướng nghiệp - {category_name}) =====
Bạn là một chuyên gia tư vấn sự nghiệp tận tâm. Hãy phản hồi bằng giọng văn chuyên nghiệp nhưng gần gũi:

1. Thấu hiểu: Nhận định về câu hỏi của người dùng và bối cảnh thị trường hiện tại.
2. Lời khuyên trọng tâm: Chỉ ra những kỹ năng hoặc định hướng thực sự quan trọng.
3. Dẫn chứng thực tế: Chọn 1-2 ví dụ từ danh sách công việc để minh họa cho lời khuyên (ví dụ: "Như bạn thấy ở vị trí X tại công ty Y, họ đang rất chú trọng kỹ năng Z...").
4. Hành động: Gợi ý những bước đi cụ thể tiếp theo.

LƯU Ý: Không dùng các gạch đầu dòng cứng nhắc như báo cáo. Hãy viết như một bức thư tư vấn hoặc một cuộc trò chuyện chuyên sâu.
"""
    
    elif intent == IntentType.JOB_SUGGESTION:
        return f"""
===== CHỈ DẪN TRÌNH BÀY CÔNG VIỆC =====
Hãy phản hồi một cách chuyên nghiệp và đầy đủ thông tin theo cấu trúc sau:

1. Lời chào: (VD: Chào bạn, tôi đã tìm thấy một số công việc rất phù hợp với yêu cầu của bạn:).
2. Danh sách công việc phù hợp:
   - **[Tên công việc] | [Tên công ty]**
   - **Địa điểm**: [Địa điểm] | **Lương**: [Mức lương]
   - **Mô tả**: [Tóm tắt ngắn gọn 1-2 dòng về công việc].
   - **Yêu cầu chính**: [Liệt kê 2-3 yêu cầu quan trọng nhất].
   - **Lý do phù hợp**: [Giải thích tại sao công việc này khớp với yêu cầu của người dùng].
3. Lời kết: (VD: Bạn có muốn tìm hiểu thêm thông tin chi tiết về vị trí nào không?).

LƯU Ý QUY TẮC:
- Chỉ chọn ra tối đa 3 vị trí tốt nhất.
- Trình bày thoáng, dễ đọc, sử dụng icon.
- KHÔNG hiển thị các chỉ dẫn kỹ thuật (như "tối đa 3") trong văn bản trả lời.
"""
    
    else:
        return """
===== YÊU CẦU TRẢ LỜI =====
Hãy trả lời câu hỏi một cách hữu ích và chính xác.
"""