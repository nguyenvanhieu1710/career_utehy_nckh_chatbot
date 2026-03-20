"""
SQL Query Generator for MongoDB
Tạo MongoDB queries từ JobFilter
"""
import re
from typing import Dict, Any, Optional, List
from app.services.filter_detector import JobFilter
import logging

logger = logging.getLogger(__name__)


class SQLGenerator:
    """Generator MongoDB queries từ JobFilter"""
    
    def build_mongo_query(self, job_filter: JobFilter) -> Dict[str, Any]:
        """
        Xây dựng MongoDB query từ JobFilter
        
        Args:
            job_filter: Bộ lọc đã được phát hiện
            
        Returns:
            Dict[str, Any]: MongoDB query
        """
        if not job_filter.has_filters():
            return {}
        
        # Query for jobs array within companies
        job_conditions = {}
        
        # Add salary filter
        if job_filter.salary_min is not None or job_filter.salary_max is not None:
            salary_conditions = {}
            
            if job_filter.salary_min is not None:
                salary_conditions["$gte"] = job_filter.salary_min * 1000000  # Convert to VNĐ
                
            if job_filter.salary_max is not None:
                salary_conditions["$lte"] = job_filter.salary_max * 1000000  # Convert to VNĐ
            
            if salary_conditions:
                # Apply to jobs.salaryMin and jobs.salaryMax
                job_conditions["$or"] = [
                    {"jobs.salaryMin": salary_conditions},
                    {"jobs.salaryMax": salary_conditions}
                ]
        
        # Add location filter (job location)
        if job_filter.location:
            location_query = self._build_job_location_query(job_filter.location)
            if location_query:
                job_conditions.update(location_query)
        
        # Add company size filter (company level)
        if job_filter.company_size:
            company_query = self._build_company_size_query(job_filter.company_size)
            if company_query:
                job_conditions.update(company_query)
        
        # Add remote filter (workArrangement field)
        if job_filter.remote is not None:
            remote_query = self._build_remote_query(job_filter.remote)
            if remote_query:
                job_conditions.update(remote_query)
        
        # Add keywords filter (job level)
        if job_filter.keywords:
            keywords_query = self._build_keywords_query(job_filter.keywords)
            if keywords_query:
                job_conditions.update(keywords_query)
        
        # Add job status filter
        job_conditions["jobs.status"] = "OPEN"
        
        logger.info(f"Built MongoDB query: {job_conditions}")
        return job_conditions
    
    def _build_salary_query(self, salary_min: Optional[int], salary_max: Optional[int]) -> Optional[Dict[str, Any]]:
        """Xây dựng salary query"""
        salary_query = {}
        
        if salary_min is not None:
            salary_query["$gte"] = salary_min * 1000000  # Convert triệu to VNĐ
        
        if salary_max is not None:
            salary_query["$lte"] = salary_max * 1000000  # Convert triệu to VNĐ
        
        return salary_query if salary_query else None
    
    def _build_job_location_query(self, location: str) -> Optional[Dict[str, Any]]:
        """Xây dựng job location query (jobs.location field)"""
        if not location:
            return None
        
        # Map location names to search patterns
        location_mapping = {
            "hà nội": ["hà nội", "hn", "hanoi"],
            "hồ chí minh": ["hồ chí minh", "hcm", "saigon", "tp.hcm"],
            "đà nẵng": ["đà nẵng", "dn"],
            "hải phòng": ["hải phòng", "hp"],
            "cần thơ": ["cần thơ", "ct"],
            "quận 1": ["quận 1", "q1"],
            "quận 3": ["quận 3", "q3"],
            "quận 7": ["quận 7", "q7"],
            "thủ đức": ["thủ đức"],
            "bình thạnh": ["bình thạnh"],
            "cầu giấy": ["cầu giấy"],
            "đống đa": ["đống đa"],
            "hai bà trưng": ["hai bà trưng"],
            "hoàng mai": ["hoàng mai"],
            "long biên": ["long biên"],
            "tây hồ": ["tây hồ"],
            "ba đình": ["ba đình"]
        }
        
        search_terms = location_mapping.get(location.lower(), [location])
        
        # Build regex patterns for flexible matching
        patterns = []
        for term in search_terms:
            patterns.append(re.escape(term))
        
        if patterns:
            regex_pattern = "|".join(patterns)
            return {"jobs.location": {"$regex": regex_pattern, "$options": "i"}}
        
        return None
    
    def _build_company_size_query(self, company_size: str) -> Optional[Dict[str, Any]]:
        """Xây dựng company size query"""
        if not company_size:
            return None
        
        # Map company size to company description patterns
        size_mapping = {
            "startup": ["startup", "khởi nghiệp", "start up"],
            "công ty lớn": ["lớn", "enterprise", "tập đoàn", "big company", "large"],
            "công ty vừa": ["vừa", "medium", "mid-size", "mid size"],
            "công ty nhỏ": ["nhỏ", "small", "size nhỏ"]
        }
        
        search_terms = size_mapping.get(company_size.lower(), [company_size])
        
        # Search in company description or name
        patterns = []
        for term in search_terms:
            patterns.append(re.escape(term))
        
        if patterns:
            regex_pattern = "|".join(patterns)
            return {
                "$or": [
                    {"company": {"$regex": regex_pattern, "$options": "i"}},
                    {"description": {"$regex": regex_pattern, "$options": "i"}}
                ]
            }
        
        return None
    
    def _build_remote_query(self, remote: bool) -> Optional[Dict[str, Any]]:
        """Xây dựng remote work query (workArrangement field)"""
        if remote is None:
            return None
        
        if remote:
            # Use workArrangement field for remote work
            remote_values = ["remote", "hybrid", "wfh", "work from home", "từ xa"]
            patterns = [re.escape(value) for value in remote_values]
            regex_pattern = "|".join(patterns)
            
            return {
                "jobs.workArrangement": {"$regex": regex_pattern, "$options": "i"}
            }
        
        return None
    
    def _build_keywords_query(self, keywords: str) -> Optional[Dict[str, Any]]:
        """Xây dựng keywords search query (job fields)"""
        if not keywords or len(keywords.strip()) < 2:
            return None
        
        keywords_clean = keywords.strip()
        
        # Split into individual words for better matching
        words = [word.strip() for word in keywords_clean.split() if len(word.strip()) > 1]
        
        if not words:
            return None
        
        # Build search across job fields
        search_conditions = []
        
        for word in words:
            word_pattern = re.escape(word)
            search_conditions.extend([
                {"jobs.title": {"$regex": word_pattern, "$options": "i"}},
                {"jobs.description": {"$regex": word_pattern, "$options": "i"}},
                {"jobs.skills": {"$regex": word_pattern, "$options": "i"}},
                {"jobs.requirements": {"$regex": word_pattern, "$options": "i"}}
            ])
        
        if search_conditions:
            return {"$or": search_conditions}
        
        return None
    
    def build_aggregation_pipeline(self, job_filter: JobFilter, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Xây dựng MongoDB aggregation pipeline cho complex queries
        
        Args:
            job_filter: Bộ lọc công việc
            limit: Số lượng kết quả tối đa
            
        Returns:
            List[Dict[str, Any]]: Aggregation pipeline
        """
        pipeline = []
        
        # Match stage
        match_query = self.build_mongo_query(job_filter)
        if match_query:
            pipeline.append({"$match": match_query})
        
        # Add text score for relevance if keywords exist
        if job_filter.keywords:
            pipeline.append({
                "$addFields": {
                    "relevance_score": {
                        "$cond": {
                            "if": {"$regexMatch": {"input": "$title", "regex": job_filter.keywords, "options": "i"}},
                            "then": 10,
                            "else": {
                                "$cond": {
                                    "if": {"$regexMatch": {"input": "$description", "regex": job_filter.keywords, "options": "i"}},
                                    "then": 5,
                                    "else": 1
                                }
                            }
                        }
                    }
                }
            })
            
            pipeline.append({"$sort": {"relevance_score": -1}})
        
        # Limit results
        pipeline.append({"$limit": limit})
        
        return pipeline


# Singleton instance
sql_generator = SQLGenerator()


def build_mongo_query(job_filter: JobFilter) -> Dict[str, Any]:
    """
    Build MongoDB query from JobFilter (convenience function)
    
    Args:
        job_filter: Job filter object
        
    Returns:
        Dict[str, Any]: MongoDB query
    """
    return sql_generator.build_mongo_query(job_filter)


def build_aggregation_pipeline(job_filter: JobFilter, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Build MongoDB aggregation pipeline (convenience function)
    
    Args:
        job_filter: Job filter object
        limit: Maximum results
        
    Returns:
        List[Dict[str, Any]]: Aggregation pipeline
    """
    return sql_generator.build_aggregation_pipeline(job_filter, limit)
