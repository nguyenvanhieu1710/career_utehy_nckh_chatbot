"""
Optimized Vector Service
Tối ưu hóa tìm kiếm vector theo danh mục và intent
"""
import numpy as np
from sentence_transformers import SentenceTransformer
from app.core.mongodb import get_database
from app.services.intent_classifier import JobCategory, get_category_filter
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

# Load embedding model (offline)
embedding_model = SentenceTransformer(
    "sentence-transformers/all-MiniLM-L6-v2"
)


async def semantic_search_optimized(query: str, category: Optional[JobCategory] = None, top_k: int = 5) -> List[str]:
    """
    Tìm kiếm semantic được tối ưu theo danh mục
    """
    try:
        if category:
            # Targeted search theo category
            jobs = await fetch_jobs_by_category(category, limit=50)
            
            if not jobs:
                return []
            
            # Tạo embeddings cho jobs
            job_texts = []
            job_ids = []
            
            for job in jobs:
                text = f"{job['title']} {job['company']} {job['description']} {job['skills']} {job['location']} {job['requirements']}"
                job_texts.append(text.strip())
                job_ids.append(job["id"])
            
            # Generate embeddings
            job_embeddings = embedding_model.encode(job_texts, convert_to_numpy=True, show_progress_bar=False)
            query_embedding = embedding_model.encode([query])
            
            # Tính similarity
            similarities = np.dot(job_embeddings, query_embedding.T).flatten()
            top_indices = np.argsort(similarities)[::-1][:top_k]
            
            return [job_ids[idx] for idx in top_indices if idx < len(job_ids)]
        else:
            # Fallback về search toàn bộ
            from app.services.vector_service import semantic_search
            return semantic_search(query, top_k)
            
    except Exception as e:
        logger.error(f"Semantic search failed: {str(e)}")
        return []


async def fetch_jobs_by_category(category: JobCategory, limit: int = 20) -> List[dict]:
    """
    Lấy jobs theo danh mục cụ thể để giảm tải
    """
    try:
        db = get_database()
        companies_collection = db["companies"]
        filter_keywords = get_category_filter(category)
        
        companies = await companies_collection.find({}).to_list(length=None)
        job_list = []
        
        for company in companies:
            company_name = company.get("name", "Unknown Company")
            jobs = company.get("jobs", [])
            
            for job in jobs:
                if job.get("status") != "OPEN":
                    continue
                
                # Filter theo category
                if filter_keywords:
                    job_text = f"{job.get('title', '')} {job.get('description', '')} {' '.join(job.get('skills', []))}"
                    if not any(keyword in job_text.lower() for keyword in filter_keywords):
                        continue
                
                job_list.append({
                    "id": job.get("id", ""),
                    "title": job.get("title", ""),
                    "company": company_name,
                    "description": job.get("description", ""),
                    "skills": ", ".join(job.get("skills", [])) if isinstance(job.get("skills"), list) else str(job.get("skills", "")),
                    "location": job.get("location", ""),
                    "requirements": ", ".join(job.get("requirements", [])) if isinstance(job.get("requirements"), list) else str(job.get("requirements", "")),
                    "salary": job.get("salary", "Thỏa thuận")
                })
                
                if len(job_list) >= limit:
                    break
            
            if len(job_list) >= limit:
                break
        
        return job_list
        
    except Exception as e:
        logger.error(f"Failed to fetch jobs by category: {str(e)}")
        return []


async def get_jobs_optimized(job_ids: List[str], category: Optional[JobCategory] = None) -> List[dict]:
    """
    Lấy thông tin jobs được tối ưu
    """
    try:
        if not job_ids:
            return []
        
        db = get_database()
        companies_collection = db["companies"]
        companies = await companies_collection.find({}).to_list(length=None)
        
        job_results = []
        
        for company in companies:
            company_name = company.get("name", "Unknown Company")
            jobs = company.get("jobs", [])
            
            for job in jobs:
                if job.get("id") in job_ids:
                    description = job.get("description", "")
                    requirements = ", ".join(job.get("requirements", []))
                    
                    job_results.append({
                        "id": job.get("id", ""),
                        "title": job.get("title", ""),
                        "company": company_name,
                        "description": description[:200] + "..." if len(description) > 200 else description,
                        "skills": ", ".join(job.get("skills", [])) if isinstance(job.get("skills"), list) else str(job.get("skills", "")),
                        "location": job.get("location", ""),
                        "requirements": requirements[:150] + "..." if len(requirements) > 150 else requirements,
                        "salary": job.get("salary", "Thỏa thuận")
                    })
        
        # Sắp xếp theo thứ tự job_ids
        ordered_results = []
        for job_id in job_ids:
            for job in job_results:
                if job["id"] == job_id:
                    ordered_results.append(job)
                    break
        
        return ordered_results
        
    except Exception as e:
        logger.error(f"Failed to get optimized jobs: {str(e)}")
        return []