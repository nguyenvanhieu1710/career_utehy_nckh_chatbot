"""
Hybrid Search Service
Kết hợp Vector Search (FAISS) + SQL filtering (PostgreSQL) cho kết quả tối ưu
"""
import asyncio
import time
from typing import List, Dict, Any, Optional
import logging
from sqlalchemy import text

from app.services.filter_detector import detect_job_filters, JobFilter
from app.services.sql_generator import build_postgres_query
from app.services.vector_service import semantic_search
from app.services.optimized_vector_service import semantic_search_optimized, get_jobs_optimized
from app.core.database import SessionLocal
from app.services.intent_classifier import JobCategory

logger = logging.getLogger(__name__)


def _format_salary(salary_display: Optional[str], salary_min: Optional[float], salary_max: Optional[float]) -> str:
    sd = (salary_display or "").strip()
    if sd and sd not in {"0", "0-0", "0-0tr", "0-0 tr"}:
        return sd

    sm = salary_min or 0
    sx = salary_max or 0
    if sm > 0 and sx > 0:
        return f"{sm/1000000:.0f}-{sx/1000000:.0f}tr"
    if sm > 0:
        return f"{sm/1000000:.0f}tr+"
    return "Thỏa thuận"


class HybridSearchService:
    """Service kết hợp vector search và SQL filtering"""
    
    def __init__(self):
        self.performance_stats = {
            "total_searches": 0,
            "vector_only_fallbacks": 0,
            "sql_only_fallbacks": 0,
            "hybrid_successes": 0,
            "avg_response_time": 0
        }
    
    async def hybrid_search(
        self, 
        query: str, 
        top_k: int = 5,
        category: Optional[JobCategory] = None,
        enable_hybrid: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search kết hợp vector + SQL
        """
        start_time = time.time()
        self.performance_stats["total_searches"] += 1
        
        try:
            if not enable_hybrid:
                return await self._vector_search_fallback(query, top_k, category)
            
            # Step 1: Detect filters
            job_filter = detect_job_filters(query)
            
            # Step 2: Choose search strategy
            if job_filter.has_filters():
                results = await self._hybrid_search_with_filters(query, job_filter, top_k, category)
                self.performance_stats["hybrid_successes"] += 1
            else:
                results = await self._vector_search_fallback(query, top_k, category)
            
            # Update performance stats
            response_time = time.time() - start_time
            self._update_performance_stats(response_time)
            
            return results
            
        except Exception as e:
            logger.error(f"Hybrid search failed: {str(e)}", exc_info=True)
            return await self._vector_search_fallback(query, top_k, category)
    
    async def _hybrid_search_with_filters(
        self,
        query: str,
        job_filter: JobFilter,
        top_k: int,
        category: Optional[JobCategory] = None
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search với filters - Vector-first approach
        """
        try:
            candidate_k = min(top_k * 4, 50)
            candidate_job_ids = await semantic_search_optimized(query, category, top_k=candidate_k)
            
            if not candidate_job_ids:
                return await self._sql_search_fallback(query, job_filter, top_k)
            
            filtered_jobs = await self._filter_candidates_by_sql(candidate_job_ids, job_filter, top_k * 2)
            
            if not filtered_jobs:
                return await self._sql_search_fallback(query, job_filter, top_k)
            
            final_results = await self._rerank_by_relevance(query, filtered_jobs, top_k)
            return final_results[:top_k]
            
        except Exception as e:
            logger.error(f"Hybrid search with filters failed: {str(e)}")
            return await self._sql_search_fallback(query, job_filter, top_k)
    
    async def _filter_candidates_by_sql(
        self,
        candidate_job_ids: List[str],
        job_filter: JobFilter,
        limit: int
    ) -> List[Dict[str, Any]]:
        """
        Filter candidates bằng SQL query từ PostgreSQL
        """
        try:
            where_clause, params = build_postgres_query(job_filter)
            params["job_ids"] = tuple(candidate_job_ids)
            
            async with SessionLocal() as db:
                query = text(f"""
                    SELECT 
                        j.id, j.title, c.name as company, j.description, 
                        j.skills, j.location, j.requirements, j.salary_display,
                        j.salary_min, j.salary_max, j.work_arrangement
                    FROM jobs j
                    JOIN companies c ON j.company_id = c.id
                    WHERE j.id = ANY(CAST(:job_ids AS uuid[])) AND {where_clause}
                    LIMIT :limit
                """)
                params["limit"] = limit * 2
                
                result = await db.execute(query, params)
                rows = result.fetchall()
                
                return [
                    {
                        "id": str(r.id),
                        "title": r.title,
                        "company": r.company,
                        "description": r.description,
                        "skills": r.skills,
                        "location": r.location,
                        "requirements": r.requirements,
                        "salary": _format_salary(r.salary_display, r.salary_min, r.salary_max),
                        "salaryMin": r.salary_min,
                        "salaryMax": r.salary_max
                    } for r in rows
                ]
        except Exception as e:
            logger.error(f"SQL filtering failed: {str(e)}")
            return []

    async def _rerank_by_relevance(self, query: str, jobs: List[Dict[str, Any]], top_k: int) -> List[Dict[str, Any]]:
        from app.services.vector_service import embedding_model
        import numpy as np
        
        job_texts = [f"{j['title']} {j['company']} {j['description']} {j['skills']}" for j in jobs]
        job_embeddings = embedding_model.encode(job_texts, convert_to_numpy=True)
        query_embedding = embedding_model.encode([query])
        similarities = np.dot(job_embeddings, query_embedding.T).flatten()
        
        for i, job in enumerate(jobs):
            job["relevance_score"] = float(similarities[i])
            
        jobs.sort(key=lambda x: x["relevance_score"], reverse=True)
        return jobs[:top_k]

    async def _vector_search_fallback(self, query: str, top_k: int, category: Optional[JobCategory] = None) -> List[Dict[str, Any]]:
        self.performance_stats["vector_only_fallbacks"] += 1
        job_ids = await semantic_search_optimized(query, category, top_k)
        return await get_jobs_optimized(job_ids, category)

    async def _sql_search_fallback(self, query: str, job_filter: JobFilter, top_k: int) -> List[Dict[str, Any]]:
        self.performance_stats["sql_only_fallbacks"] += 1
        where_clause, params = build_postgres_query(job_filter)
        
        async with SessionLocal() as db:
            sql = text(f"""
                SELECT j.id, j.title, c.name as company, j.description, j.location
                FROM jobs j JOIN companies c ON j.company_id = c.id
                WHERE {where_clause} LIMIT :limit
            """)
            params["limit"] = top_k
            result = await db.execute(sql, params)
            rows = result.fetchall()
            return [{"id": str(r.id), "title": r.title, "company": r.company, "location": r.location} for r in rows]

    def _update_performance_stats(self, response_time: float):
        total = self.performance_stats["total_searches"]
        current_avg = self.performance_stats["avg_response_time"]
        self.performance_stats["avg_response_time"] = ((current_avg * (total - 1)) + response_time) / total

    def get_performance_stats(self) -> Dict[str, Any]:
        return self.performance_stats.copy()

    def reset_performance_stats(self):
        self.performance_stats = {k: 0 for k in self.performance_stats}


# Singleton instance
hybrid_search_service = HybridSearchService()

from app.services.parallel_hybrid_search import parallel_hybrid_search

async def hybrid_search(query: str, top_k: int = 5, category: Optional[str] = None, enable_hybrid: bool = True) -> List[Dict[str, Any]]:
    # Sử dụng parallel implementation để tối ưu hiệu năng
    return await parallel_hybrid_search(query, top_k, category, enable_hybrid)

def get_hybrid_performance_stats() -> Dict[str, Any]:
    return hybrid_search_service.get_performance_stats()

def reset_hybrid_performance_stats():
    hybrid_search_service.reset_performance_stats()
