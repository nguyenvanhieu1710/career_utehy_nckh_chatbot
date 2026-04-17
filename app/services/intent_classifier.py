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


def classify_intent(message: str) -> Tuple[IntentType, Optional[JobCategory]]:
    """
    Phân loại ý định của người dùng
    
    Args:
        message: Tin nhắn từ người dùng
        
    Returns:
        Tuple[IntentType, Optional[JobCategory]]: (loại ý định, danh mục công việc nếu có)
    """
    message_lower = message.lower().strip()
    
    # Kiểm tra keywords tư vấn
    has_consultation_keyword = any(
        keyword in message_lower for keyword in CONSULTATION_KEYWORDS
    )
    
    # Kiểm tra keywords gợi ý công việc
    has_job_suggestion_keyword = any(
        keyword in message_lower for keyword in JOB_SUGGESTION_KEYWORDS
    )
    
    # Xác định danh mục công việc
    detected_category = None
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in message_lower for keyword in keywords):
            detected_category = category
            break
    
    # Logic phân loại
    if has_job_suggestion_keyword and detected_category:
        # Có từ khóa "tìm việc" + lĩnh vực cụ thể → Gợi ý công việc
        return IntentType.JOB_SUGGESTION, detected_category
    
    elif has_consultation_keyword:
        # Có từ khóa tư vấn → Tư vấn chung
        return IntentType.CONSULTATION, detected_category
    
    elif detected_category and not has_consultation_keyword:
        # Chỉ có lĩnh vực, không có từ khóa tư vấn → Có thể là gợi ý công việc
        return IntentType.JOB_SUGGESTION, detected_category
    
    else:
        # Không xác định được → Mặc định là tư vấn
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
===== YÊU CẦU TRẢ LỜI (Tư vấn nghề nghiệp - {category_name}) =====
Hãy đưa ra lời tư vấn chuyên sâu dựa trên dữ liệu thực tế:

1. Phân tích câu hỏi: Đưa ra nhận định dựa trên xu hướng thị trường (1-2 câu).
2. Lời khuyên cụ thể: Các kỹ năng và lộ trình cần tập trung.
3. MINH HỌA THỰC TẾ: Sử dụng thông tin từ danh sách công việc được cung cấp để đưa ra các ví dụ cụ thể về yêu cầu thực tế của nhà tuyển dụng.
4. Hướng dẫn bước tiếp theo.

LƯU Ý: Tuyệt đối không trả lời chung chung. Hãy dùng các job thực tế làm dẫn chứng cho lời khuyên.
"""
    
    elif intent == IntentType.JOB_SUGGESTION:
        category_name = category.value if category else "tất cả lĩnh vực"
        return f"""
===== YÊU CẦU TRẢ LỜI (Gợi ý công việc - {category_name}) =====
Hãy gợi ý công việc phù hợp:

1. Giải thích tìm kiếm (1-2 câu)
2. Danh sách công việc phù hợp (top 3):
   - Tên công việc tại Công ty
   - Địa điểm, mức lương
   - Kỹ năng yêu cầu
   - Lý do phù hợp
3. Lời khuyên ứng tuyển (2-3 gợi ý)

LƯU Ý: Giải thích rõ TẠI SAO đề xuất mỗi công việc.
"""
    
    else:
        return """
===== YÊU CẦU TRẢ LỜI =====
Hãy trả lời câu hỏi một cách hữu ích và chính xác.
"""