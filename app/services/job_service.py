import logging
from typing import List, Dict, Any, Optional
from sqlalchemy import text
from app.core.database import SessionLocal

logger = logging.getLogger(__name__)

def _format_salary(salary_display: Optional[str], salary_min: Optional[float], salary_max: Optional[float]) -> str:
    """Helper to format salary strings nicely (Source of truth)"""
    sd = (salary_display or "").strip()
    if sd and sd not in {"0", "0-0", "0-0tr", "0-0 tr", "thỏa thuận", "negotiable"}:
        return sd

    sm = salary_min or 0
    sx = salary_max or 0
    if sm > 0 and sx > 0:
        return f"{sm/1000000:.0f}-{sx/1000000:.0f}tr"
    if sm > 0:
        return f"{sm/1000000:.0f}tr+"
    return "Thỏa thuận"

async def get_job_details_by_ids(job_ids: List[str]) -> List[Dict[str, Any]]:
    """
    Truy vấn thông tin chi tiết công việc từ PostgreSQL dựa trên danh sách IDs.
    Đảm bảo giữ nguyên thứ tự của job_ids truyền vào (quan trọng cho relevance của Milvus).
    """
    if not job_ids:
        return []

    try:
        async with SessionLocal() as db:
            query = text("""
                SELECT 
                    j.id, j.title, c.name as company, j.description, 
                    j.skills, j.location, j.requirements, j.salary_display,
                    j.salary_min, j.salary_max, j.work_arrangement
                FROM jobs j JOIN companies c ON j.company_id = c.id
                WHERE j.id = ANY(CAST(:ids AS uuid[]))
            """)
            
            result = await db.execute(query, {"ids": job_ids})
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
                    "salary": _format_salary(r.salary_display, r.salary_min, r.salary_max),
                    "work_arrangement": r.work_arrangement or ""
                } for r in rows
            }
            
            # Trả về kết quả theo đúng thứ tự IDs truyền vào ban đầu
            return [job_map[jid] for jid in job_ids if jid in job_map]

    except Exception as e:
        logger.error(f"Error fetching job details: {str(e)}")
        return []

async def search_jobs_by_filter(where_clause: str, params: Dict[str, Any], limit: int = 5) -> List[Dict[str, Any]]:
    """
    Truy vấn danh sách công việc dựa trên WHERE clause và params từ SQLGenerator.
    """
    try:
        async with SessionLocal() as db:
            sql = text(f"""
                SELECT 
                    j.id, j.title, c.name as company, j.description, 
                    j.skills, j.location, j.requirements, j.salary_display,
                    j.salary_min, j.salary_max, j.work_arrangement
                FROM jobs j JOIN companies c ON j.company_id = c.id
                WHERE {where_clause}
                LIMIT :limit
            """)
            params["limit"] = limit
            
            result = await db.execute(sql, params)
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
                    "salary": _format_salary(r.salary_display, r.salary_min, r.salary_max),
                    "work_arrangement": r.work_arrangement or ""
                } for r in rows
            ]
    except Exception as e:
        logger.error(f"Error searching jobs by filter: {str(e)}")
        return []
