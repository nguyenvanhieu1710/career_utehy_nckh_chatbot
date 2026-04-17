"""
PostgreSQL Query Generator for Job Search
Tạo các đoạn truy vấn SQL từ JobFilter để sử dụng với PostgreSQL
"""
import re
from typing import Dict, Any, Optional, List, Tuple
from app.services.filter_detector import JobFilter
import logging

logger = logging.getLogger(__name__)


class SQLGenerator:
    """Generator PostgreSQL queries từ JobFilter"""
    
    def build_postgres_query(self, job_filter: JobFilter) -> Tuple[str, Dict[str, Any]]:
        """
        Xây dựng câu truy vấn SQL WHERE và params từ JobFilter
        """
        conditions = ["j.status = 'approved'", "j.action_status = 'active'"]
        params = {}
        
        # Salary filter
        if job_filter.salary_min is not None:
            conditions.append("j.salary_min >= :salary_min")
            params["salary_min"] = job_filter.salary_min * 1000000
            
        if job_filter.salary_max is not None:
            conditions.append("j.salary_max <= :salary_max")
            params["salary_max"] = job_filter.salary_max * 1000000
            
        # Location filter
        if job_filter.location:
            location_mapping = {
                "hà nội": ["hà nội", "hn", "hanoi"],
                "hồ chí minh": ["hồ chí minh", "hcm", "saigon", "tp.hcm"],
                "đà nẵng": ["đà nẵng", "dn"],
                "hải phòng": ["hải phòng", "hp"]
            }
            search_terms = location_mapping.get(job_filter.location.lower(), [job_filter.location])
            loc_conds = []
            for i, term in enumerate(search_terms):
                key = f"loc_{i}"
                loc_conds.append(f"j.location ILIKE :{key}")
                params[key] = f"%{term}%"
            if loc_conds:
                conditions.append(f"({' OR '.join(loc_conds)})")
                
        # Remote/Work Arrangement
        if job_filter.remote is not None:
            if job_filter.remote:
                conditions.append("j.work_arrangement ILIKE '%remote%'")
            else:
                conditions.append("j.work_arrangement NOT ILIKE '%remote%'")
                
        # Keywords
        if job_filter.keywords:
            words = [w.strip() for w in job_filter.keywords.split() if len(w.strip()) > 1]
            if words:
                keyword_conds = []
                for i, word in enumerate(words):
                    key = f"kw_{i}"
                    keyword_conds.append(
                        f"(j.title ILIKE :{key} OR j.description ILIKE :{key} OR CAST(j.skills AS text) ILIKE :{key})"
                    )
                    params[key] = f"%{word}%"
                if keyword_conds:
                    conditions.append(f"({' OR '.join(keyword_conds)})")
            
        return " AND ".join(conditions), params


# Singleton instance
sql_generator = SQLGenerator()

def build_postgres_query(job_filter: JobFilter) -> Tuple[str, Dict[str, Any]]:
    return sql_generator.build_postgres_query(job_filter)
