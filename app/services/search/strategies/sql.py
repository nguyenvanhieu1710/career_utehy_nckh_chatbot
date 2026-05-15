import logging
from typing import List, Dict, Any, Optional

from app.services.search.base import BaseSearchStrategy
from app.services.filter_detector import detect_job_filters
from app.services.sql_generator import build_postgres_query
from app.services.job_service import search_jobs_by_filter

logger = logging.getLogger(__name__)

class SQLSearchStrategy(BaseSearchStrategy):
    """
    Chiến thuật tìm kiếm thuần SQL trên PostgreSQL.
    Dùng làm fallback khi Vector search không khả dụng hoặc khi có filters rõ ràng.
    """
    
    async def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        top_k = kwargs.get("top_k", 5)
        
        # 1. Detect filters từ ngôn ngữ tự nhiên
        job_filter = detect_job_filters(query)
        
        # 2. Build WHERE clause
        where_clause, params = build_postgres_query(job_filter)
        
        # 3. Thực thi truy vấn thông qua job_service
        results = await search_jobs_by_filter(where_clause, params, limit=top_k)
        
        logger.info(f"[{self.get_name()}] Found {len(results)} results using SQL search")
        return results
