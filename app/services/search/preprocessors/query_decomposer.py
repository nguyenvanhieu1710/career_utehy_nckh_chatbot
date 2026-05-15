import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from app.services.filter_detector import detect_job_filters, JobFilter

logger = logging.getLogger(__name__)

@dataclass
class SearchStrategy:
    """Chiến lược tìm kiếm cho complex queries"""
    type: str  # exact, partial, location_only, etc.
    filters: JobFilter
    weight: float  # Độ ưu tiên của strategy
    description: str  # Mô tả strategy

class QueryDecomposer:
    """
    Phân tích complex queries thành sub-strategies.
    Dùng cho các câu hỏi đa điều kiện mà search thông thường có thể không trả về kết quả.
    """
    
    def __init__(self):
        self.specific_locations = [
            "quận 1", "quận 3", "quận 7", "quận 10",
            "cầu giấy", "bình thạnh", "thủ đức", "tây hồ",
            "long biên", "ba đình", "gò vấp"
        ]
    
    def decompose_query(self, query: str) -> List[SearchStrategy]:
        """Phân tích query thành multiple search strategies"""
        strategies = []
        detected_filters = detect_job_filters(query)
        
        # Strategy 1: Exact Match (Weight: 1.0)
        if detected_filters.has_filters():
            strategies.append(SearchStrategy(
                type="exact",
                filters=detected_filters,
                weight=1.0,
                description="Match chính xác tất cả filters"
            ))
        
        # Strategy 2: Keywords only (Fallback)
        if detected_filters.keywords:
            strategies.append(SearchStrategy(
                type="keywords_only",
                filters=JobFilter(keywords=detected_filters.keywords),
                weight=0.6,
                description="Tìm kiếm theo keywords chung"
            ))
        
        # Sort by weight
        strategies.sort(key=lambda x: x.weight, reverse=True)
        return strategies

# Singleton
query_decomposer = QueryDecomposer()

def decompose(query: str) -> List[SearchStrategy]:
    return query_decomposer.decompose_query(query)
