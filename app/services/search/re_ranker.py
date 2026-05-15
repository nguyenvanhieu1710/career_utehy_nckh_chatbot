import logging
import re
from typing import List, Dict, Any, Optional
from app.services.filter_detector import JobFilter

logger = logging.getLogger(__name__)

class JobReRanker:
    """
    Chuyên trách việc tái xếp hạng (Re-ranking) các kết quả tìm kiếm.
    Sử dụng Flexible Scoring dựa trên các tiêu chí cụ thể (Lương, Vị trí, Quy mô công ty).
    """
    
    def __init__(self):
        # Mapping địa điểm lân cận
        self.location_groups = {
            "hà nội": ["ba đình", "long biên", "gò vấp", "thanh xuân", "cầu giấy", "đống đa", "hai bà trưng"],
            "hồ chí minh": ["quận 1", "quận 3", "quận 5", "quận 10", "bình thạnh", "phú nhuận", "tân bình"],
            "đà nẵng": ["thanh khê", "liên chiểu", "ngũ hành sơn", "sơn trà", "cam lệ"]
        }
        
        # Keywords quy mô công ty
        self.company_size_keywords = {
            "startup": ["startup", "khởi nghiệp", "đổi mới", "sáng tạo"],
            "lớn": ["tập đoàn", "tổng công ty", "multinational", "enterprise", "corporation"],
            "nhỏ": ["sme", "doanh nghiệp vừa và nhỏ"],
            "vừa": ["medium", "mid-size"]
        }
        
        # Remote patterns
        self.remote_patterns = [
            "remote", "wfh", "work from home", "hybrid", "flexible",
            "làm việc từ xa", "làm việc tại nhà", "online"
        ]

    def calculate_match_score(self, job: Dict[str, Any], query_filters: JobFilter) -> float:
        """Tính điểm match (0.0 - 1.0)"""
        score = 0.0
        weights = {
            "salary": 0.3,
            "location": 0.3,
            "company": 0.1,
            "remote": 0.1,
            "keywords": 0.2
        }
        
        # 1. Salary Score
        s_score = self._calculate_salary_score(job, query_filters)
        score += s_score * weights["salary"]
        
        # 2. Location Score
        l_score = self._calculate_location_score(job, query_filters)
        score += l_score * weights["location"]
        
        # 3. Company Score
        c_score = self._calculate_company_size_score(job, query_filters)
        score += c_score * weights["company"]
        
        # 4. Remote Score
        r_score = self._calculate_remote_score(job, query_filters)
        score += r_score * weights["remote"]
        
        # 5. Keywords Score
        k_score = self._calculate_keyword_score(job, query_filters)
        score += k_score * weights["keywords"]
        
        return min(score, 1.0)

    def _calculate_salary_score(self, job: Dict[str, Any], query_filters: JobFilter) -> float:
        if query_filters.salary_min is None: return 0.5 # Neutral if no preference
        
        # Note: mapping key salaryMin/salaryMax từ database mapping trong job_service
        # Trong job_service mình đã format salary thành string, 
        # nhưng để re-rank chuẩn ta nên dùng data thô nếu có.
        # Tuy nhiên ở đây ta tạm dùng logic cơ bản hoặc query filters.
        return 1.0 # Placeholder logic, thực tế sẽ lấy từ job dict

    def _calculate_location_score(self, job: Dict[str, Any], query_filters: JobFilter) -> float:
        if not query_filters.location: return 0.5
        job_loc = job.get("location", "").lower()
        req_loc = query_filters.location.lower()
        
        if req_loc in job_loc: return 1.0
        
        for main, nearby in self.location_groups.items():
            if req_loc == main and any(n in job_loc for n in nearby):
                return 0.7
        return 0.0

    def _calculate_company_size_score(self, job: Dict[str, Any], query_filters: JobFilter) -> float:
        if not query_filters.company_size: return 0.5
        text = (job.get("title", "") + " " + job.get("description", "")).lower()
        keywords = self.company_size_keywords.get(query_filters.company_size.lower(), [])
        return 1.0 if any(kw in text for kw in keywords) else 0.0

    def _calculate_remote_score(self, job: Dict[str, Any], query_filters: JobFilter) -> float:
        if query_filters.remote is None: return 0.5
        work_arr = job.get("work_arrangement", "").lower()
        return 1.0 if any(p in work_arr for p in self.remote_patterns) else 0.0

    def _calculate_keyword_score(self, job: Dict[str, Any], query_filters: JobFilter) -> float:
        if not query_filters.keywords: return 0.5
        text = (job.get("title", "") + " " + job.get("description", "") + " " + str(job.get("skills", ""))).lower()
        keywords = query_filters.keywords.lower().split()
        matches = sum(1 for kw in keywords if kw in text)
        return matches / len(keywords) if keywords else 0.0

    def rank_jobs(self, jobs: List[Dict[str, Any]], query_filters: JobFilter) -> List[Dict[str, Any]]:
        """Sắp xếp lại danh sách jobs dựa trên điểm số thực tế"""
        for job in jobs:
            job["match_score"] = self.calculate_match_score(job, query_filters)
        
        # Sort desc
        return sorted(jobs, key=lambda x: x.get("match_score", 0), reverse=True)

# Singleton
re_ranker = JobReRanker()

def rank_results(jobs: List[Dict[str, Any]], query_filters: JobFilter) -> List[Dict[str, Any]]:
    return re_ranker.rank_jobs(jobs, query_filters)
