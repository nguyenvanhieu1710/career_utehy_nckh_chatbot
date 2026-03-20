"""
ENHANCED MATCHING - Phase 3 Step 2
Cải thiện job-filter matching logic với flexible scoring
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from app.services.filter_detector import JobFilter

logger = logging.getLogger(__name__)

class EnhancedMatcher:
    """Enhanced job matching với flexible scoring"""
    
    def __init__(self):
        # Location mapping cho nearby detection
        self.location_groups = {
            "hà nội": ["ba đình", "long biên", "gò vấp", "thanh xuân", "cầu giấy", "đống đa", "hai bà trưng"],
            "hồ chí minh": ["quận 1", "quận 3", "quận 5", "quận 10", "bình thạnh", "phú nhuận", "tân bình"],
            "đà nẵng": ["thanh khê", "liên chiểu", "ngũ hành sơn", "sơn trà", "cam lệ"],
            "quận 1": ["bến thành", "gò vấp"],
            "quận 3": ["phú nhuận"],
            "cầu giấy": ["đống đa"],
            "bình thạnh": ["quận 2"]
        }
        
        # Company size mapping
        self.company_size_keywords = {
            "startup": ["startup", "khởi nghiệp", "đổi mới", "sáng tạo", "innovation", "tech"],
            "lớn": ["tập đoàn", "tổng công ty", "multinational", "quốc tế", "enterprise", "corporation"],
            "nhỏ": ["sme", "doanh nghiệp vừa và nhỏ", "family", "gia đình"],
            "vừa": ["medium", "mid-size", "trung bình"]
        }
        
        # Remote work patterns
        self.remote_patterns = [
            "remote", "wfh", "work from home", "hybrid", "flexible",
            "làm việc từ xa", "làm việc tại nhà", "online", "trực tuyến"
        ]
    
    def calculate_match_score(self, job: Dict[str, Any], query_filters: JobFilter) -> float:
        """
        Tính điểm match linh hoạt hơn
        
        Args:
            job: Job data từ database
            query_filters: Filters từ query decomposition
            
        Returns:
            float: Match score (0.0 - 1.0+)
        """
        score = 0.0
        
        # 1. Salary Matching (Flexible)
        salary_score = self._calculate_salary_score(job, query_filters)
        score += salary_score
        
        # 2. Location Matching (Exact + Nearby)
        location_score = self._calculate_location_score(job, query_filters)
        score += location_score
        
        # 3. Company Size Matching (Keyword-based)
        company_score = self._calculate_company_size_score(job, query_filters)
        score += company_score
        
        # 4. Remote Work Matching
        remote_score = self._calculate_remote_score(job, query_filters)
        score += remote_score
        
        # 5. Keywords Matching
        keyword_score = self._calculate_keyword_score(job, query_filters)
        score += keyword_score
        
        # Bonus points cho perfect matches
        if salary_score >= 0.8 and location_score >= 0.8:
            score += 0.2  # Bonus cho salary + location match
        
        if score > 1.0:
            score = 1.0
        
        return score
    
    def _calculate_salary_score(self, job: Dict[str, Any], query_filters: JobFilter) -> float:
        """Flexible salary matching"""
        if query_filters.salary_min is None:
            return 0.0
        
        job_salary_min = job.get("salaryMin", 0)
        job_salary_max = job.get("salaryMax", float('inf'))
        required_min = query_filters.salary_min
        
        # Exact match
        if job_salary_min >= required_min:
            if query_filters.salary_max is not None:
                required_max = query_filters.salary_max
                if job_salary_min <= required_max and job_salary_max >= required_min:
                    return 1.0  # Perfect range match
                elif job_salary_min <= required_max * 1.2:
                    return 0.8  # Close range match
                else:
                    return 0.5  # Partial match
            else:
                # Only min salary required
                if job_salary_min <= required_min * 1.2:
                    return 0.9  # Very close
                elif job_salary_min <= required_min * 1.5:
                    return 0.7  # Close
                elif job_salary_min <= required_min * 2.0:
                    return 0.5  # Acceptable
                else:
                    return 0.3  # Higher than required
        
        return 0.0
    
    def _calculate_location_score(self, job: Dict[str, Any], query_filters: JobFilter) -> float:
        """Location matching với nearby detection"""
        if query_filters.location is None:
            return 0.0
        
        job_location = job.get("location", "").lower()
        required_location = query_filters.location.lower()
        
        # Exact match
        if required_location in job_location:
            return 1.0
        
        # Nearby location check
        for main_location, nearby_areas in self.location_groups.items():
            if required_location == main_location:
                for nearby in nearby_areas:
                    if nearby in job_location:
                        return 0.7  # Nearby location
        
        # Partial match
        if any(word in job_location for word in required_location.split()):
            return 0.5
        
        return 0.0
    
    def _calculate_company_size_score(self, job: Dict[str, Any], query_filters: JobFilter) -> float:
        """Company size matching keyword-based"""
        if query_filters.company_size is None:
            return 0.0
        
        job_description = (
            job.get("title", "") + " " + 
            job.get("description", "") + " " + 
            job.get("company", "")
        ).lower()
        
        required_size = query_filters.company_size.lower()
        
        # Direct keyword match
        size_keywords = self.company_size_keywords.get(required_size, [])
        for keyword in size_keywords:
            if keyword in job_description:
                return 1.0
        
        # Similar size detection
        if required_size == "startup" and any(kw in job_description for kw in ["startup", "khởi nghiệp", "đổi mới"]):
            return 0.8
        elif required_size == "lớn" and any(kw in job_description for kw in ["tập đoàn", "quốc tế", "multinational"]):
            return 0.8
        elif required_size == "nhỏ" and any(kw in job_description for kw in ["sme", "doanh nghiệp vừa"]):
            return 0.8
        
        return 0.0
    
    def _calculate_remote_score(self, job: Dict[str, Any], query_filters: JobFilter) -> float:
        """Remote work matching"""
        if query_filters.remote is None:
            return 0.0
        
        job_work_arrangement = job.get("workArrangement", "").lower()
        
        # Direct remote patterns
        for pattern in self.remote_patterns:
            if pattern in job_work_arrangement:
                return 1.0
        
        # Hybrid/ flexible patterns
        if any(word in job_work_arrangement for word in ["hybrid", "flexible", "linh hoạt"]):
            return 0.8
        
        return 0.0
    
    def _calculate_keyword_score(self, job: Dict[str, Any], query_filters: JobFilter) -> float:
        """Keywords matching trong title, description, skills"""
        if query_filters.keywords is None:
            return 0.0
        
        keywords = query_filters.keywords.lower().split()
        if not keywords or len(keywords) == 0:
            return 0.0
        
        job_text = (
            job.get("title", "") + " " + 
            job.get("description", "") + " " + 
            " ".join(job.get("skills", [])) + " " +
            " ".join(job.get("requirements", []))
        ).lower()
        
        # Count keyword matches
        matched_keywords = 0
        for keyword in keywords:
            if len(keyword) > 2 and keyword in job_text:
                matched_keywords += 1
        
        # Calculate score based on match ratio
        match_ratio = matched_keywords / len(keywords)
        
        if match_ratio >= 0.8:
            return 1.0
        elif match_ratio >= 0.6:
            return 0.8
        elif match_ratio >= 0.4:
            return 0.6
        elif match_ratio >= 0.2:
            return 0.4
        else:
            return 0.0
    
    def rank_jobs_by_match_score(self, jobs: List[Dict[str, Any]], query_filters: JobFilter) -> List[Dict[str, Any]]:
        """
        Rank jobs theo match score và similarity
        """
        scored_jobs = []
        
        for job in jobs:
            # Calculate match score
            match_score = self.calculate_match_score(job, query_filters)
            
            # Combine với existing similarity score
            existing_similarity = job.get("similarity", 0.0)
            
            # Final score: weighted combination
            final_score = (
                match_score * 0.7 +  # 70% match score
                existing_similarity * 0.3  # 30% similarity
            )
            
            scored_job = job.copy()
            scored_job["match_score"] = match_score
            scored_job["final_score"] = final_score
            scored_jobs.append(scored_job)
        
        # Sort by final score (descending)
        scored_jobs.sort(key=lambda x: x["final_score"], reverse=True)
        
        return scored_jobs

# Singleton instance
enhanced_matcher = EnhancedMatcher()

def calculate_match_score(job: Dict[str, Any], query_filters: JobFilter) -> float:
    """
    Public function để calculate match score
    """
    return enhanced_matcher.calculate_match_score(job, query_filters)

def rank_jobs_by_match_score(jobs: List[Dict[str, Any]], query_filters: JobFilter) -> List[Dict[str, Any]]:
    """
    Public function để rank jobs
    """
    return enhanced_matcher.rank_jobs_by_match_score(jobs, query_filters)

# Test function
def test_enhanced_matching():
    """Test enhanced matching với sample jobs"""
    print("=== ENHANCED MATCHING TEST ===\n")
    
    # Sample jobs
    sample_jobs = [
        {
            "id": "1",
            "title": "Senior Python Developer",
            "company": "Tech Startup Vietnam",
            "location": "Hồ Chí Minh, Quận 1",
            "salaryMin": 18,
            "salaryMax": 25,
            "workArrangement": "Hybrid working",
            "description": "We are looking for experienced Python developers",
            "skills": ["Python", "Django", "React"],
            "requirements": ["3+ years experience"],
            "similarity": 0.85
        },
        {
            "id": "2", 
            "title": "Marketing Manager",
            "company": "Tập đoàn ABC",
            "location": "Hà Nội, Ba Đình",
            "salaryMin": 25,
            "salaryMax": 35,
            "workArrangement": "Remote",
            "description": "Large corporation seeking marketing professionals",
            "skills": ["Marketing", "Management"],
            "requirements": ["5+ years experience"],
            "similarity": 0.75
        },
        {
            "id": "3",
            "title": "Junior Developer",
            "company": "SME Company",
            "location": "Đà Nẵng",
            "salaryMin": 8,
            "salaryMax": 12,
            "workArrangement": "Office only",
            "description": "Small company looking for junior developers",
            "skills": ["JavaScript", "HTML", "CSS"],
            "requirements": ["1+ year experience"],
            "similarity": 0.90
        }
    ]
    
    # Test queries
    test_queries = [
        {
            "query": "startup ở HCM lương cao",
            "filters": JobFilter(company_size="startup", location="hồ chí minh", salary_min=20)
        },
        {
            "query": "công ty lớn Hà Nội remote",
            "filters": JobFilter(company_size="lớn", location="hà nội", remote=True)
        },
        {
            "query": "Python developer lương 15-25 triệu",
            "filters": JobFilter(salary_min=15, salary_max=25, keywords="Python developer")
        }
    ]
    
    for test_case in test_queries:
        query = test_case["query"]
        filters = test_case["filters"]
        
        print(f"Query: {query}")
        print(f"Filters: {filters.to_dict()}")
        
        # Rank jobs
        ranked_jobs = rank_jobs_by_match_score(sample_jobs, filters)
        
        print("Top 3 matched jobs:")
        for i, job in enumerate(ranked_jobs[:3], 1):
            print(f"  {i}. {job['title']} at {job['company']}")
            print(f"     Location: {job['location']}")
            print(f"     Salary: {job.get('salaryMin', 'N/A')} - {job.get('salaryMax', 'N/A')} triệu")
            print(f"     Match Score: {job['match_score']:.2f}")
            print(f"     Final Score: {job['final_score']:.2f}")
            print()
        
        print("=" * 60)

if __name__ == "__main__":
    test_enhanced_matching()
