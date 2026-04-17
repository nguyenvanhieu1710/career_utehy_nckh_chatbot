"""
Optimized Vector Service
Tối ưu hóa tìm kiếm vector theo danh mục và intent
"""
import numpy as np
from sqlalchemy import text
from app.core.database import SessionLocal
from app.services.intent_classifier import JobCategory, get_category_filter
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

from app.services.vector_service import embedding_model

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

async def semantic_search_optimized(query: str, category: Optional[JobCategory] = None, top_k: int = 5) -> List[dict]:
    """
    Tìm kiếm semantic được tối ưu theo danh mục, trả về danh sách job objects
    """
    try:
        if category:
            # Targeted search theo category
            jobs = await fetch_jobs_by_category(category, limit=100)
            
            if not jobs:
                return []
            
            # Tạo embeddings cho jobs
            job_texts = []
            for job in jobs:
                text = f"{job['title']} {job['company']} {job['description']} {job['skills']} {job['location']} {job['requirements']}"
                job_texts.append(text.strip())
            
            # Generate embeddings
            job_embeddings = embedding_model.encode(job_texts, convert_to_numpy=True, show_progress_bar=False)
            query_embedding = embedding_model.encode([query])
            
            # Tính similarity
            similarities = np.dot(job_embeddings, query_embedding.T).flatten()
            top_indices = np.argsort(similarities)[::-1][:top_k]
            
            results = []
            for idx in top_indices:
                if idx < len(jobs):
                    job = jobs[idx].copy()
                    job["similarity"] = float(similarities[idx])
                    results.append(job)
            return results
        else:
            # Fallback về search toàn bộ
            from app.services.vector_service import semantic_search
            job_ids = semantic_search(query, top_k)
            return await get_jobs_optimized(job_ids)
            
    except Exception as e:
        logger.error(f"Semantic search failed: {str(e)}", exc_info=True)
        return []

async def fetch_jobs_by_category(category: JobCategory, limit: int = 50) -> List[dict]:
    """
    Lấy jobs theo danh mục cụ thể từ PostgreSQL
    """
    try:
        filter_keywords = get_category_filter(category)
        if not filter_keywords:
            return []
            
        keyword_patterns = [f"%{kw}%" for kw in filter_keywords]
        
        async with SessionLocal() as db:
            # Simple keyword matching in DB for category filtering
            conditions = []
            params = {"limit": limit}
            
            for i, kw in enumerate(keyword_patterns):
                key = f"kw_{i}"
                conditions.append(f"(j.title ILIKE :{key} OR j.description ILIKE :{key})")
                params[key] = kw
                
            where_clause = " OR ".join(conditions)
            
            query = text(f"""
                SELECT 
                    j.id, j.title, c.name as company, j.description, 
                    j.skills, j.location, j.requirements,j.salary_display,
                    j.salary_min, j.salary_max, j.work_arrangement
                FROM jobs j
                JOIN companies c ON j.company_id = c.id
                WHERE j.status = 'approved' AND j.action_status = 'active'
                AND ({where_clause})
                LIMIT :limit
            """)
            
            result = await db.execute(query, params)
            rows = result.fetchall()
            
            return [
                {
                    "id": str(r.id),
                    "title": r.title,
                    "company": r.company,
                    "description": r.description or "",
                    "skills": r.skills or "",
                    "location": r.location or "",
                    "requirements": r.requirements or "",
                    "salary_display": r.salary_display or "",
                    "salary_min": r.salary_min,
                    "salary_max": r.salary_max,
                    "salary": _format_salary(r.salary_display, r.salary_min, r.salary_max),
                    "work_arrangement": r.work_arrangement
                } for r in rows
            ]
            
    except Exception as e:
        logger.error(f"Failed to fetch jobs by category: {str(e)}", exc_info=True)
        return []

async def get_jobs_optimized(job_ids: List[str], category: Optional[JobCategory] = None) -> List[dict]:
    """
    Lấy thông tin chi tiết jobs từ danh sách IDs
    """
    try:
        if not job_ids:
            return []
            
        async with SessionLocal() as db:
            query = text("""
                SELECT 
                    j.id, j.title, c.name as company, j.description, 
                    j.skills, j.location, j.requirements, j.salary_display,
                    j.salary_min, j.salary_max, j.work_arrangement
                FROM jobs j
                JOIN companies c ON j.company_id = c.id
                WHERE j.id = ANY(CAST(:job_ids AS uuid[]))
            """)
            
            result = await db.execute(query, {"job_ids": list(job_ids)})
            rows = result.fetchall()
            
            job_map = {
                str(r.id): {
                    "id": str(r.id),
                    "title": r.title,
                    "company": r.company,
                    "description": r.description or "",
                    "skills": r.skills or "",
                    "location": r.location or "",
                    "requirements": r.requirements or "",
                    "salary_display": r.salary_display or "",
                    "salary_min": r.salary_min,
                    "salary_max": r.salary_max,
                    "salary": _format_salary(r.salary_display, r.salary_min, r.salary_max),
                    "work_arrangement": r.work_arrangement
                } for r in rows
            }
            
            # Maintain original order
            return [job_map[jid] for jid in job_ids if jid in job_map]
            
    except Exception as e:
        logger.error(f"Failed to get optimized jobs: {str(e)}", exc_info=True)
        return []
