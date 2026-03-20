"""
QUERY DECOMPOSITION - Phase 3 Step 1
Phân tích complex queries thành multiple search strategies
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from app.services.filter_detector import detect_job_filters, JobFilter

@dataclass
class SearchStrategy:
    """Chiến lược tìm kiếm cho complex queries"""
    type: str  # exact, partial, location_only, etc.
    filters: JobFilter
    weight: float  # Độ ưu tiên của strategy
    description: str  # Mô tả strategy

class QueryDecomposer:
    """Phân tích complex queries thành sub-strategies"""
    
    def __init__(self):
        self.specific_locations = [
            "quận 1", "quận 3", "quận 7", "quận 10",
            "cầu giấy", "bình thạnh", "thủ đức", "tây hồ",
            "long biên", "ba đình", "gò vấp"
        ]
        
        self.high_salary_thresholds = {
            "cao": 20,  # triệu
            "khá": 15,
            "tốt": 12
        }
    
    def decompose_query(self, query: str) -> List[SearchStrategy]:
        """
        Phân tích query thành multiple search strategies
        
        Args:
            query: Complex query từ người dùng
            
        Returns:
            List[SearchStrategy]: Các chiến lược tìm kiếm
        """
        strategies = []
        
        # Detect tất cả filters
        detected_filters = detect_job_filters(query)
        
        # Strategy 1: Exact Match (Weight: 1.0)
        if detected_filters.has_filters():
            strategies.append(SearchStrategy(
                type="exact",
                filters=detected_filters,
                weight=1.0,
                description="Match chính xác tất cả filters"
            ))
        
        # Strategy 2: Relaxed Salary (Weight: 0.8)
        if detected_filters.salary_max is not None:
            relaxed_filters = JobFilter(
                salary_min=detected_filters.salary_min,
                salary_max=None,  # Bỏ max salary
                location=detected_filters.location,
                company_size=detected_filters.company_size,
                remote=detected_filters.remote,
                keywords=detected_filters.keywords
            )
            strategies.append(SearchStrategy(
                type="relaxed_salary",
                filters=relaxed_filters,
                weight=0.8,
                description="Lỏ bỏ salary max, chỉ giữ min"
            ))
        
        # Strategy 3: Location Priority (Weight: 0.9)
        if detected_filters.location and self._is_specific_location(detected_filters.location):
            location_priority_filters = JobFilter(
                location=detected_filters.location,
                company_size=detected_filters.company_size,
                remote=detected_filters.remote,
                # Bỏ salary để ưu tiên location
                salary_min=None,
                salary_max=None
            )
            strategies.append(SearchStrategy(
                type="location_priority",
                filters=location_priority_filters,
                weight=0.9,
                description="Ưu tiên location cụ thể"
            ))
        
        # Strategy 4: Company Size Priority (Weight: 0.7)
        if detected_filters.company_size:
            size_priority_filters = JobFilter(
                company_size=detected_filters.company_size,
                location=detected_filters.location,
                remote=detected_filters.remote,
                # Giữ salary min nếu có
                salary_min=detected_filters.salary_min,
                salary_max=None
            )
            strategies.append(SearchStrategy(
                type="company_size_priority",
                filters=size_priority_filters,
                weight=0.7,
                description="Ưu tiên quy mô công ty"
            ))
        
        # Strategy 5: Remote Priority (Weight: 0.8)
        if detected_filters.remote:
            remote_priority_filters = JobFilter(
                remote=True,
                company_size=detected_filters.company_size,
                location=detected_filters.location,
                # Giữ salary cho remote jobs
                salary_min=detected_filters.salary_min,
                salary_max=None
            )
            strategies.append(SearchStrategy(
                type="remote_priority",
                filters=remote_priority_filters,
                weight=0.8,
                description="Ưu tiên việc làm từ xa"
            ))
        
        # Strategy 6: General Keywords (Weight: 0.6)
        if detected_filters.keywords:
            keyword_filters = JobFilter(
                keywords=detected_filters.keywords
            )
            strategies.append(SearchStrategy(
                type="keywords_only",
                filters=keyword_filters,
                weight=0.6,
                description="Tìm kiếm theo keywords chung"
            ))
        
        # Strategy 7: Fallback - Minimal Filters (Weight: 0.5)
        if detected_filters.has_filters():
            minimal_filters = JobFilter(
                # Chỉ giữ filter quan trọng nhất
                salary_min=detected_filters.salary_min,
                location=detected_filters.location if self._is_specific_location(detected_filters.location) else None,
                company_size=detected_filters.company_size,
                remote=None,
                keywords=None
            )
            strategies.append(SearchStrategy(
                type="minimal_filters",
                filters=minimal_filters,
                weight=0.5,
                description="Chỉ giữ filters quan trọng nhất"
            ))
        
        # Sort by weight (cao nhất trước)
        strategies.sort(key=lambda x: x.weight, reverse=True)
        
        return strategies
    
    def _is_specific_location(self, location: Optional[str]) -> bool:
        """Kiểm tra có phải location cụ thể không"""
        if not location:
            return False
        
        location_lower = location.lower()
        return any(specific_loc in location_lower for specific_loc in self.specific_locations)
    
    def get_strategy_summary(self, strategies: List[SearchStrategy]) -> str:
        """Tóm tắt các strategies được tạo"""
        summary = f"Đã tạo {len(strategies)} chiến lược:\n"
        
        for i, strategy in enumerate(strategies, 1):
            summary += f"{i}. {strategy.description} (weight: {strategy.weight})\n"
        
        return summary
    
    def analyze_query_complexity(self, query: str) -> Dict[str, Any]:
        """Phân tích độ phức tạp của query"""
        filters = detect_job_filters(query)
        
        complexity_score = 0
        complexity_factors = []
        
        # Count filters
        filter_count = sum([
            1 for _ in [filters.salary_min, filters.salary_max, 
                        filters.location, filters.company_size, 
                        filters.remote, filters.keywords]
            if _ is not None
        ])
        
        if filter_count >= 3:
            complexity_score += 3
            complexity_factors.append("Nhiều filters (3+)")
        elif filter_count >= 2:
            complexity_score += 2
            complexity_factors.append("Multiple filters (2)")
        elif filter_count >= 1:
            complexity_score += 1
            complexity_factors.append("Single filter")
        
        # Specific location bonus
        if filters.location and self._is_specific_location(filters.location):
            complexity_score += 1
            complexity_factors.append("Location cụ thể")
        
        # Salary range bonus
        if filters.salary_min is not None and filters.salary_max is not None:
            complexity_score += 1
            complexity_factors.append("Salary range")
        
        # High salary bonus
        if filters.salary_min and filters.salary_min >= 15:
            complexity_score += 1
            complexity_factors.append("High salary requirement")
        
        # Determine complexity level
        if complexity_score >= 5:
            complexity_level = "Rất phức tạp"
        elif complexity_score >= 3:
            complexity_level = "Phức tạp"
        elif complexity_score >= 2:
            complexity_level = "Trung bình"
        else:
            complexity_level = "Đơn giản"
        
        return {
            "query": query,
            "complexity_score": complexity_score,
            "complexity_level": complexity_level,
            "factors": complexity_factors,
            "filter_count": filter_count,
            "strategies_needed": min(filter_count + 2, 7)  # Max 7 strategies
        }

# Singleton instance
query_decomposer = QueryDecomposer()

def decompose_query(query: str) -> List[SearchStrategy]:
    """
    Public function để decompose query
    """
    return query_decomposer.decompose_query(query)

def analyze_query_complexity(query: str) -> Dict[str, Any]:
    """
    Public function để analyze query complexity
    """
    return query_decomposer.analyze_query_complexity(query)

# Test function
def test_query_decomposition():
    """Test query decomposition với các complex queries"""
    test_queries = [
        "startup ở Hồ Chí Minh lương cao",
        "công ty lớn ở Quận 1 remote lương trên 20 triệu",
        "việc làm từ xa cho công ty nhỏ",
        "Python developer ở Đà Nẵng lương từ 15 triệu",
        "fresh graduate việc IT",
        "marketing manager remote lương 15-25 triệu",
        "khởi nghiệp công nghệ Hà Nội",
        "doanh nghiệp lớn Quận 3 hybrid working"
    ]
    
    print("=== QUERY DECOMPOSITION TEST ===\n")
    
    for query in test_queries:
        print(f"Query: {query}")
        
        # Analyze complexity
        complexity = analyze_query_complexity(query)
        print(f"Độ phức tạp: {complexity['complexity_level']} (score: {complexity['complexity_score']})")
        print(f"Yếu tố: {', '.join(complexity['factors'])}")
        
        # Decompose strategies
        strategies = decompose_query(query)
        print(f"Số strategies: {len(strategies)}")
        
        # Show strategy summary
        summary = query_decomposer.get_strategy_summary(strategies)
        print(summary)
        
        print("=" * 60)

if __name__ == "__main__":
    test_query_decomposition()
