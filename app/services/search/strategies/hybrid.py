import logging
import asyncio
from typing import List, Dict, Any, Optional

from app.services.search.base import BaseSearchStrategy
from app.services.search.strategies.vector import VectorSearchStrategy
from app.services.search.strategies.sql import SQLSearchStrategy
from app.services.filter_detector import detect_job_filters
from app.services.sql_generator import build_postgres_query
from app.services.job_service import search_jobs_by_filter

from app.services.search.re_ranker import rank_results

logger = logging.getLogger(__name__)

class HybridSearchStrategy(BaseSearchStrategy):
    """
    Chiến thuật tìm kiếm Hybrid: 
    Kết hợp Vector Search (ngữ nghĩa) + SQL Filtering (bộ lọc chính xác).
    Có cơ chế bổ sung (supplement) từ SQL nếu kết quả vector bị lọc quá nhiều.
    """
    
    def __init__(self):
        self.vector_strategy = VectorSearchStrategy()
        self.sql_strategy = SQLSearchStrategy()

    async def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        top_k = kwargs.get("top_k", 5)
        category = kwargs.get("category")
        
        # 1. Detect filters
        job_filter = detect_job_filters(query)
        
        # Biến chứa kết quả thô
        raw_results = []

        # Nếu không có bộ lọc nào, chạy Vector Search cho nhanh
        if not job_filter.has_filters():
            logger.info(f"[{self.get_name()}] No filters detected, using pure vector search")
            raw_results = await self.vector_strategy.search(query, top_k=top_k, category=category)
            # 2. Bước 1: Lấy ứng viên từ Vector Search
            candidate_k = min(top_k * 10, 100)
            from app.services.vector_service import get_milvus_client, get_embedding
            from app.core.config import settings
            
            client = get_milvus_client()
            job_ids = []
            if client:
                query_vec = get_embedding(query)
                res = client.search(
                    collection_name=settings.MILVUS_COLLECTION,
                    data=[query_vec],
                    filter=f'category == "{category}"' if category else "",
                    limit=candidate_k,
                    output_fields=["job_id"]
                )
                job_ids = [hit["entity"]["job_id"] for hit in res[0]]
            
            if not job_ids:
                raw_results = await self.sql_strategy.search(query, top_k=top_k)
            else:
                # 3. Bước 2: Lọc ứng viên bằng SQL
                where_clause, params = build_postgres_query(job_filter)
                hybrid_where = f"j.id = ANY(CAST(:ids AS uuid[])) AND ({where_clause})"
                params["ids"] = job_ids
                
                raw_results = await search_jobs_by_filter(hybrid_where, params, limit=top_k)
                
                # 4. Bước 3: Bổ sung từ SQL nếu thiếu
                if len(raw_results) < top_k:
                    supplement = await self.sql_strategy.search(query, top_k=top_k)
                    existing_ids = {r["id"] for r in raw_results}
                    for job in supplement:
                        if job["id"] not in existing_ids and len(raw_results) < top_k:
                            raw_results.append(job)
        
        # 5. BƯỚC CUỐI: RE-RANKING
        # Sau khi có kết quả thô, dùng Re-ranker để sắp xếp lại theo độ phù hợp thực tế
        final_results = rank_results(raw_results, job_filter)
        
        logger.info(f"[{self.get_name()}] Hybrid search & re-ranking completed")
        return final_results
