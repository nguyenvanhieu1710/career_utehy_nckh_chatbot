import logging
from typing import List, Dict, Any, Optional

from app.services.search.base import BaseSearchStrategy
from app.services.vector_service import get_milvus_client, get_embedding
from app.services.job_service import get_job_details_by_ids
from app.core.config import settings

logger = logging.getLogger(__name__)

class VectorSearchStrategy(BaseSearchStrategy):
    """
    Chiến thuật tìm kiếm ngữ nghĩa (Semantic Search) sử dụng Milvus.
    """
    
    async def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        top_k = kwargs.get("top_k", 5)
        category = kwargs.get("category")
        
        # 1. Gọi hạ tầng Milvus để lấy danh sách IDs phù hợp nhất
        client = get_milvus_client()
        if client is None:
            return []

        try:
            query_vec = get_embedding(query)
            filter_expr = f'category == "{category}"' if category else ""
            
            res = client.search(
                collection_name=settings.MILVUS_COLLECTION,
                data=[query_vec],
                filter=filter_expr,
                limit=top_k,
                output_fields=["job_id"]
            )
            job_ids = [hit["entity"]["job_id"] for hit in res[0]]
        except Exception as e:
            logger.error(f"Milvus search failed in VectorSearchStrategy: {e}")
            job_ids = []
        
        if not job_ids:
            logger.info(f"[{self.get_name()}] No results found in Milvus for query: {query}")
            return []
            
        # 2. Lấy thông tin chi tiết từ PostgreSQL thông qua Repository chung
        results = await get_job_details_by_ids(job_ids)
        
        logger.info(f"[{self.get_name()}] Found {len(results)} results for query: {query}")
        return results
