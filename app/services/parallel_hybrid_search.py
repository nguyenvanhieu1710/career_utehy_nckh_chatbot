"""
PARALLEL HYBRID SEARCH - Performance Optimization
Chạy vector search và SQL processing song song để giảm response time từ 7.11s xuống <2s
"""
import asyncio
import time
import logging
from typing import List, Dict, Any, Optional, Tuple

from app.services.filter_detector import detect_job_filters
from app.services.optimized_vector_service import semantic_search_optimized
from app.core.database import SessionLocal
from sqlalchemy import text
import re

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

async def parallel_hybrid_search(
    query: str, 
    top_k: int = 5, 
    category: Optional[str] = None, 
    enable_hybrid: bool = True
) -> List[Dict[str, Any]]:
    """
    PARALLEL HYBRID SEARCH - Performance Optimization for PostgreSQL
    """
    
    start_time = time.time()
    
    try:
        # Step 1: Detect filters (Synchronous)
        job_filter = detect_job_filters(query)
        logger.info(f"Detected filters: {job_filter.to_dict()}")
        
        # Step 2: Vector search (Parallel task)
        vector_task = asyncio.create_task(
            semantic_search_optimized(query, category, top_k=top_k*3)
        )
        
        # Step 3: Wait for tasks with timeout 2.0s
        try:
            done, pending = await asyncio.wait(
                [vector_task],
                timeout=2.0
            )
            
            if vector_task in done:
                vector_results = vector_task.result()
                # Apply SQL filter in-memory (fast)
                filtered_results = apply_sql_filter_fast(vector_results, job_filter, top_k)
                
                if filtered_results:
                    return filtered_results
            
            # If vector search failed or filtered out everything, use SQL fallback
            return await sql_search_fallback(job_filter, top_k)
                    
        except asyncio.TimeoutError:
            logger.warning("Parallel processing timeout, using vector-only fallback")
            return await semantic_search_optimized(query, category, top_k=top_k)
            
    except Exception as e:
        logger.error(f"Parallel hybrid search failed: {str(e)}")
        return []

def apply_sql_filter_fast(vector_results: List[Dict], job_filter: Any, top_k: int) -> List[Dict]:
    """Apply SQL filter in-memory on vector results"""
    if not vector_results:
        return []
    
    filtered_results = []
    
    for job in vector_results:
        # Salary check
        if job_filter.salary_min is not None and job.get("salary_min", 0) < job_filter.salary_min * 1000000:
            continue
        if job_filter.salary_max is not None and job.get("salary_max", float('inf')) > job_filter.salary_max * 1000000:
            continue
        
        # Location check
        if job_filter.location and job.get("location"):
            if job_filter.location.lower() not in job.get("location").lower():
                continue
        
        # Remote check
        if job_filter.remote is not None:
            is_remote = "remote" in job.get("work_arrangement", "").lower()
            if job_filter.remote != is_remote:
                continue
                
        filtered_results.append(job)
        if len(filtered_results) >= top_k:
            break
            
    return filtered_results

async def sql_search_fallback(job_filter: Any, top_k: int) -> List[Dict]:
    """PostgreSQL-only search fallback"""
    try:
        from app.services.sql_generator import build_postgres_query
        where_clause, params = build_postgres_query(job_filter)
        
        async with SessionLocal() as db:
            query = text(f"""
                SELECT 
                    j.id, j.title, c.name as company, j.location, 
                    j.salary_min, j.salary_max, j.work_arrangement,
                    j.description, j.skills, j.requirements, j.salary_display
                FROM jobs j
                JOIN companies c ON j.company_id = c.id
                WHERE {where_clause}
                LIMIT :limit
            """)
            params["limit"] = top_k
            
            result = await db.execute(query, params)
            rows = result.fetchall()
            
            formatted_results = []
            for row in rows:
                formatted_results.append({
                    "id": str(row.id),
                    "title": row.title,
                    "company": row.company,
                    "location": row.location,
                    "description": row.description or "",
                    "skills": row.skills or "",
                    "requirements": row.requirements or "",
                    "salary_display": row.salary_display or "",
                    "salary_min": row.salary_min or 0,
                    "salary_max": row.salary_max or 0,
                    "salary": _format_salary(row.salary_display, row.salary_min, row.salary_max),
                    "work_arrangement": row.work_arrangement or "",
                    "similarity": 1.0,
                    "sql_score": 1.0
                })
            
            return formatted_results
            
    except Exception as e:
        logger.error(f"PostgreSQL fallback failed: {str(e)}", exc_info=True)
        return []
