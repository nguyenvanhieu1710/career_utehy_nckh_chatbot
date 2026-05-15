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
        top_k = kwargs.get("top_k", 3)
        category = kwargs.get("category")
        
        # 1. Detect filters
        job_filter = detect_job_filters(query)
        job_filter.category = category # Gán category từ Intent Classifier
        raw_results = []

        # 2. Bước 1: Lấy ứng viên tiềm năng từ Vector Search
        candidate_k = min(top_k * 20, 200) 
        from app.services.vector_service import get_milvus_client, get_embedding
        from app.core.config import settings
        
        client = get_milvus_client()
        job_ids = []
        
        if client:
            try:
                search_text = job_filter.keywords if job_filter.keywords else query
                query_vec = get_embedding(search_text)
                
                res = client.search(
                    collection_name=settings.MILVUS_COLLECTION,
                    data=[query_vec],
                    anns_field="vector",
                    limit=candidate_k,
                    output_fields=["job_id"]
                )
                
                # Xử lý kết quả linh hoạt (SearchResult object vs List)
                hits = []
                if isinstance(res, list) and len(res) > 0:
                    hits = res[0]
                elif hasattr(res, 'data') and res.data:
                    hits = res.data[0]
                
                if hits:
                    for hit in hits:
                        if isinstance(hit, dict):
                            id_val = hit.get("id") or hit.get("entity", {}).get("job_id")
                        else:
                            id_val = getattr(hit, "id", None) or hit.entity.get("job_id")
                        if id_val: job_ids.append(str(id_val))
                    
                    logger.info(f"[{self.get_name()}] Milvus found {len(job_ids)} candidate IDs")

            except Exception as e:
                logger.error(f"Milvus search error: {e}")

        # 3. Bước 2: Kết hợp lọc SQL (Ưu tiên gắt gao)
        if job_ids:
            where_clause, params = build_postgres_query(job_filter)
            hybrid_where = f"j.id = ANY(CAST(:ids AS uuid[]))"
            
            if where_clause:
                # Thử tìm khớp tất cả (Strict)
                strict_where = f"{hybrid_where} AND ({where_clause})"
                params["ids"] = job_ids
                raw_results = await search_jobs_by_filter(strict_where, params, limit=top_k)
                
                # NẾU RỖNG: Nới lỏng (Bỏ qua lương, chỉ giữ Location)
                if not raw_results and job_filter.location:
                    from app.services.filter_detector import JobFilter
                    relaxed_filter = JobFilter(location=job_filter.location, category=category)
                    relaxed_where, r_params = build_postgres_query(relaxed_filter)
                    if relaxed_where:
                        # MERGE THAM SỐ SQL
                        r_params["ids"] = job_ids
                        raw_results = await search_jobs_by_filter(f"{hybrid_where} AND ({relaxed_where})", r_params, limit=top_k)
                        if raw_results:
                            logger.info(f"[{self.get_name()}] Found {len(raw_results)} results after relaxing filters")

        # 4. Bước 3: Cứu cánh cuối cùng - Lấy Top Vector nếu vẫn rỗng
        if not raw_results and job_ids:
            logger.info(f"[{self.get_name()}] Falling back to top vector matches (Ignoring filters)")
            raw_results = await search_jobs_by_filter(f"j.id = ANY(CAST(:ids AS uuid[]))", {"ids": job_ids[:top_k]}, limit=top_k)

        # 5. Nếu Milvus không có gì, dùng SQL keyword search
        if not raw_results:
            raw_results = await self.sql_strategy.search(query, top_k=top_k)
        
        # 6. RE-RANKING
        final_results = rank_results(raw_results, job_filter)
        return final_results
