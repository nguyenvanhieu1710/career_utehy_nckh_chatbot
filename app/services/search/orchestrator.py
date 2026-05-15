import asyncio
import time
import logging
from typing import List, Dict, Any, Optional

from app.services.search.strategies.hybrid import HybridSearchStrategy
from app.services.search.strategies.sql import SQLSearchStrategy
from app.services.search.strategies.vector import VectorSearchStrategy

logger = logging.getLogger(__name__)

# Cấu hình timeout
SEARCH_TIMEOUT = 5.0

class SearchOrchestrator:
    """
    Search Orchestrator — Điều phối các chiến thuật tìm kiếm.
    
    Pipeline:
    1. Thử HybridSearchStrategy (Primary)
    2. Nếu Hybrid timeout hoặc không có kết quả -> Fallback sang SQLSearchStrategy
    """

    def __init__(self):
        self.hybrid_strategy = HybridSearchStrategy()
        self.sql_strategy = SQLSearchStrategy()
        self.vector_strategy = VectorSearchStrategy()
        
        # Thống kê hiệu suất (giống logic cũ nhưng tách biệt ở tầng Orchestrator)
        self.performance_stats = {
            "total_requests": 0,
            "hybrid_hits": 0,
            "sql_fallbacks": 0,
            "timeouts": 0,
            "avg_latency": 0.0
        }

    async def search(
        self, 
        query: str, 
        top_k: int = 5, 
        category: Optional[Any] = None,
        enable_hybrid: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Entry point chính cho việc tìm kiếm job.
        """
        start_time = time.time()
        self.performance_stats["total_requests"] += 1
        
        # Normalize category
        cat_str = category.value if hasattr(category, 'value') else str(category) if category else None

        try:
            # === BƯỚC 1: Thử Hybrid Search với Timeout ===
            if enable_hybrid:
                try:
                    results = await asyncio.wait_for(
                        self.hybrid_strategy.search(query, top_k=top_k, category=cat_str),
                        timeout=SEARCH_TIMEOUT
                    )
                    if results:
                        self.performance_stats["hybrid_hits"] += 1
                        self._update_latency(time.time() - start_time)
                        return results
                except asyncio.TimeoutError:
                    logger.warning(f"Hybrid search timed out after {SEARCH_TIMEOUT}s, falling back to SQL")
                    self.performance_stats["timeouts"] += 1
            
            # === BƯỚC 2: Fallback sang SQL Search ===
            logger.info("Using SQL fallback search...")
            self.performance_stats["sql_fallbacks"] += 1
            results = await self.sql_strategy.search(query, top_k=top_k)
            
            self._update_latency(time.time() - start_time)
            return results

        except Exception as e:
            logger.error(f"Search Orchestrator failed: {str(e)}", exc_info=True)
            # Safe fallback cuối cùng: Vector search thuần túy
            return await self.vector_strategy.search(query, top_k=top_k, category=cat_str)

    def _update_latency(self, elapsed: float):
        total = self.performance_stats["total_requests"]
        curr_avg = self.performance_stats["avg_latency"]
        self.performance_stats["avg_latency"] = (curr_avg * (total - 1) + elapsed) / total

    def get_stats(self) -> Dict[str, Any]:
        return self.performance_stats.copy()

# Singleton instance
search_orchestrator = SearchOrchestrator()

# Public API (để thay thế hoàn toàn hybrid_search_service.py)
async def search_jobs(
    query: str, 
    top_k: int = 5, 
    category: Optional[Any] = None,
    enable_hybrid: bool = True
) -> List[Dict[str, Any]]:
    return await search_orchestrator.search(query, top_k, category, enable_hybrid)

def get_search_stats() -> Dict[str, Any]:
    return search_orchestrator.get_stats()
