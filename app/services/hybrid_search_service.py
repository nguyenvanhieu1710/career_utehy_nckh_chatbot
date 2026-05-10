"""
Hybrid Search Service - Milvus Cloud Edition
Kết hợp Semantic Search (Milvus) + Metadata Filtering (PostgreSQL)
"""
import asyncio
import time
from typing import List, Dict, Any, Optional
import logging
from sqlalchemy import text

from app.services.filter_detector import detect_job_filters, JobFilter
from app.services.sql_generator import build_postgres_query
from app.services.vector_service import (
    semantic_search,
    get_job_details,
    _format_salary
)
from app.core.database import SessionLocal
from app.services.intent_classifier import JobCategory

logger = logging.getLogger(__name__)

# Timeout cho Milvus Cloud vector search (giây)
VECTOR_SEARCH_TIMEOUT = 5.0


class HybridSearchService:
    """
    Service kết hợp vector search (Milvus) + SQL filtering (PostgreSQL).
    Chạy vector search với timeout để tránh block, tự động fallback sang SQL nếu timeout.
    """

    def __init__(self):
        self.performance_stats = {
            "total_searches": 0,
            "vector_only": 0,
            "hybrid_successes": 0,
            "sql_only_fallbacks": 0,
            "timeout_fallbacks": 0,
            "avg_response_time": 0.0
        }

    async def hybrid_search(
        self,
        query: str,
        top_k: int = 5,
        category: Optional[Any] = None,
        enable_hybrid: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search kết hợp vector + SQL với parallel execution và timeout.

        Flow:
        1. Detect filters từ query (nhanh, sync)
        2. Chạy vector search (Milvus) với timeout
        3. Nếu có filters → SQL filter trên kết quả vector
        4. Fallback sang pure SQL nếu vector timeout hoặc rỗng
        """
        start_time = time.time()
        self.performance_stats["total_searches"] += 1

        # Normalize category enum → string
        cat_str = category.value if hasattr(category, 'value') else str(category) if category else None

        try:
            # Bước 1: Detect filters (sync, fast)
            job_filter = detect_job_filters(query)

            # Bước 2: Vector search với timeout
            candidate_k = min(top_k * 10, 100) if (enable_hybrid and job_filter.has_filters()) else top_k

            try:
                vector_task = asyncio.create_task(
                    semantic_search(query, category=cat_str, top_k=candidate_k)
                )
                job_ids = await asyncio.wait_for(vector_task, timeout=VECTOR_SEARCH_TIMEOUT)
            except asyncio.TimeoutError:
                logger.warning(f"Vector search timed out after {VECTOR_SEARCH_TIMEOUT}s, falling back to SQL")
                self.performance_stats["timeout_fallbacks"] += 1
                return await self._sql_search_fallback(job_filter, top_k)

            # Bước 3: Routing dựa trên kết quả vector + filters
            if not job_ids:
                logger.info("Vector search returned empty, falling back to SQL")
                self.performance_stats["sql_only_fallbacks"] += 1
                return await self._sql_search_fallback(job_filter, top_k)

            if enable_hybrid and job_filter.has_filters():
                results = await self._filter_candidates_by_sql(job_ids, job_filter, top_k)
                logger.info(f"[Hybrid] Vector({len(job_ids)}) → SQL filter → {len(results)} results")

                # Bổ sung từ SQL nếu Hybrid trả về quá ít
                if len(results) < top_k:
                    supplement = await self._sql_search_fallback(job_filter, top_k - len(results))
                    existing_ids = {r["id"] for r in results}
                    for job in supplement:
                        if job["id"] not in existing_ids:
                            results.append(job)
                    logger.info(f"[Hybrid] Supplemented with SQL fallback → total {len(results)} results")

                self.performance_stats["hybrid_successes"] += 1
            else:
                results = await get_job_details(job_ids[:top_k])
                logger.info(f"[Vector-only] Returned {len(results)} results")
                self.performance_stats["vector_only"] += 1

            elapsed = time.time() - start_time
            self._update_avg_response_time(elapsed)
            logger.info(f"Search completed in {elapsed:.3f}s | path={'hybrid' if job_filter.has_filters() else 'vector'} | results={len(results)}")
            return results

        except Exception as e:
            logger.error(f"Hybrid search failed: {str(e)}", exc_info=True)
            # Safe fallback: thuần vector, không filter
            job_ids = await semantic_search(query, category=cat_str, top_k=top_k)
            return await get_job_details(job_ids)

    async def _filter_candidates_by_sql(
        self,
        candidate_job_ids: List[str],
        job_filter: JobFilter,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Filter Milvus candidates bằng SQL (fast vì đã có IDs)"""
        try:
            where_clause, params = build_postgres_query(job_filter)

            async with SessionLocal() as db:
                sql = text(f"""
                    SELECT
                        j.id, j.title, c.name as company, j.description,
                        j.skills, j.location, j.requirements, j.salary_display,
                        j.salary_min, j.salary_max, j.work_arrangement
                    FROM jobs j JOIN companies c ON j.company_id = c.id
                    WHERE j.id = ANY(CAST(:ids AS uuid[])) AND ({where_clause})
                    LIMIT :limit
                """)
                params["ids"] = candidate_job_ids
                params["limit"] = limit

                rows = (await db.execute(sql, params)).fetchall()

                # Giữ thứ tự relevance từ Milvus
                job_map = {
                    str(r.id): {
                        "id": str(r.id),
                        "title": r.title,
                        "company": r.company,
                        "description": r.description or "",
                        "skills": r.skills or "",
                        "location": r.location or "",
                        "requirements": r.requirements or "",
                        "salary": _format_salary(r.salary_display, r.salary_min, r.salary_max),
                        "work_arrangement": r.work_arrangement
                    } for r in rows
                }
                return [job_map[jid] for jid in candidate_job_ids if jid in job_map]

        except Exception as e:
            logger.error(f"SQL filtering failed: {e}")
            return await get_job_details(candidate_job_ids[:limit])

    async def _sql_search_fallback(self, job_filter: JobFilter, top_k: int) -> List[Dict[str, Any]]:
        """Pure SQL search — dùng khi vector search không available"""
        try:
            where_clause, params = build_postgres_query(job_filter)
            async with SessionLocal() as db:
                sql = text(f"""
                    SELECT j.id, j.title, c.name as company, j.location,
                           j.salary_display, j.salary_min, j.salary_max,
                           j.work_arrangement, j.description, j.skills, j.requirements
                    FROM jobs j JOIN companies c ON j.company_id = c.id
                    WHERE {where_clause} LIMIT :limit
                """)
                params["limit"] = top_k
                rows = (await db.execute(sql, params)).fetchall()
                return [
                    {
                        "id": str(r.id),
                        "title": r.title,
                        "company": r.company,
                        "location": r.location or "",
                        "salary": _format_salary(r.salary_display, r.salary_min, r.salary_max),
                        "work_arrangement": r.work_arrangement or "",
                        "description": r.description or "",
                        "skills": r.skills or "",
                        "requirements": r.requirements or ""
                    }
                    for r in rows
                ]
        except Exception as e:
            logger.error(f"SQL fallback failed: {e}")
            return []

    def _update_avg_response_time(self, response_time: float):
        total = self.performance_stats["total_searches"]
        current_avg = self.performance_stats["avg_response_time"]
        self.performance_stats["avg_response_time"] = (
            (current_avg * (total - 1) + response_time) / total
        )

    def get_performance_stats(self) -> Dict[str, Any]:
        return self.performance_stats.copy()


# Singleton instance
hybrid_search_service = HybridSearchService()


# Public API — dùng trực tiếp trong chat.py
async def hybrid_search(
    query: str,
    top_k: int = 5,
    category: Optional[Any] = None,
    enable_hybrid: bool = True
) -> List[Dict[str, Any]]:
    return await hybrid_search_service.hybrid_search(query, top_k, category, enable_hybrid)


def get_hybrid_performance_stats() -> Dict[str, Any]:
    return hybrid_search_service.get_performance_stats()
