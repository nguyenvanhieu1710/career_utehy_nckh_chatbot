import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from app.core.database import SessionLocal
from sqlalchemy import text
from app.core.config import settings
import logging
import os
import pickle
from datetime import datetime

logger = logging.getLogger(__name__)

# Load embedding model (offline)
embedding_model = SentenceTransformer(
    "sentence-transformers/all-MiniLM-L6-v2"
)

dimension = 384
index = faiss.IndexFlatL2(dimension)

job_ids = []
job_texts = []

# Storage paths
FAISS_INDEX_FILE = os.path.join(settings.FAISS_INDEX_DIR, "jobs.index")
FAISS_METADATA_FILE = os.path.join(settings.FAISS_INDEX_DIR, "metadata.pkl")

# Ensure storage directory exists
os.makedirs(settings.FAISS_INDEX_DIR, exist_ok=True)

async def fetch_all_jobs_for_indexing():
    """
    Fetch all jobs from PostgreSQL for FAISS indexing
    """
    try:
        async with SessionLocal() as db:
            query = text("""
                SELECT 
                    j.id, 
                    j.title, 
                    c.name as company_name, 
                    j.description, 
                    j.skills, 
                    j.location, 
                    j.requirements 
                FROM jobs j
                JOIN companies c ON j.company_id = c.id
                WHERE j.status = 'approved' AND j.action_status = 'active'
            """)
            
            result = await db.execute(query)
            rows = result.fetchall()
            
            job_list = []
            for row in rows:
                # row is a tuple, or potentially a Row object with keys
                job_list.append({
                    "id": str(row.id),
                    "title": row.title,
                    "company": row.company_name,
                    "description": row.description or "",
                    "skills": str(row.skills) if row.skills else "",
                    "location": row.location or "",
                    "requirements": row.requirements or ""
                })
            
            return job_list
            
    except Exception as e:
        logger.error(f"Failed to fetch jobs from PostgreSQL: {str(e)}", exc_info=True)
        return []


async def build_faiss_index():
    """
    Build FAISS index from all approved jobs
    Call this on startup and when jobs are updated
    """
    global job_ids, job_texts, index
    
    try:
        jobs = await fetch_all_jobs_for_indexing()
        
        if not jobs:
            logger.warning("No jobs found for FAISS indexing")
            return
        
        job_ids.clear()
        job_texts.clear()
        
        for job in jobs:
            # Combine all job fields for better semantic search
            text = f"""
            {job['title']}
            {job['company']}
            {job['description']}
            {job['skills']}
            {job['location']}
            {job['requirements']}
            """
            job_ids.append(job["id"])
            job_texts.append(text.strip())
        
        # Generate embeddings
        embeddings = embedding_model.encode(
            job_texts,
            convert_to_numpy=True,
            show_progress_bar=False
        )
        
        # Build FAISS index
        index.reset()
        index.add(embeddings)
        
        # Save to disk
        save_faiss_index()
        
        logger.info(f"Built FAISS index with {len(job_ids)} jobs")
        
    except Exception as e:
        logger.error(f"Failed to build FAISS index: {str(e)}", exc_info=True)


def save_faiss_index():
    """
    Save FAISS index and metadata to disk
    """
    try:
        # Save FAISS index
        faiss.write_index(index, FAISS_INDEX_FILE)
        
        # Save metadata (job_ids, job_texts, timestamp)
        metadata = {
            "job_ids": job_ids,
            "job_texts": job_texts,
            "timestamp": datetime.now().isoformat(),
            "total_vectors": len(job_ids)
        }
        
        with open(FAISS_METADATA_FILE, "wb") as f:
            pickle.dump(metadata, f)
        
        logger.info("FAISS index saved to disk")
        
    except Exception as e:
        logger.error(f"Failed to save FAISS index: {str(e)}", exc_info=True)


def load_faiss_index():
    """
    Load FAISS index from disk (faster than rebuilding)
    Returns True if loaded successfully, False otherwise
    """
    global job_ids, job_texts, index
    
    try:
        if not os.path.exists(FAISS_INDEX_FILE) or not os.path.exists(FAISS_METADATA_FILE):
            return False
        
        # Load FAISS index
        index = faiss.read_index(FAISS_INDEX_FILE)
        
        # Load metadata
        with open(FAISS_METADATA_FILE, "rb") as f:
            metadata = pickle.load(f)
        
        job_ids = metadata["job_ids"]
        job_texts = metadata["job_texts"]
        
        logger.info(f"Loaded FAISS index with {len(job_ids)} jobs from disk")
        return True
        
    except Exception as e:
        logger.error(f"Failed to load FAISS index: {str(e)}", exc_info=True)
        return False


def get_faiss_stats():
    """
    Get statistics about current FAISS index
    """
    try:
        stats = {
            "total_vectors": len(job_ids),
            "dimension": dimension,
            "index_type": "IndexFlatL2",
            "memory_usage_mb": (len(job_ids) * dimension * 4) / (1024 * 1024),
            "job_ids": job_ids[:10] if len(job_ids) > 10 else job_ids,  # First 10
            "total_job_ids": len(job_ids)
        }
        
        # Check if saved files exist
        if os.path.exists(FAISS_INDEX_FILE):
            stats["disk_index_size_mb"] = os.path.getsize(FAISS_INDEX_FILE) / (1024 * 1024)
        
        if os.path.exists(FAISS_METADATA_FILE):
            stats["disk_metadata_size_mb"] = os.path.getsize(FAISS_METADATA_FILE) / (1024 * 1024)
            
            with open(FAISS_METADATA_FILE, "rb") as f:
                metadata = pickle.load(f)
                stats["last_saved"] = metadata.get("timestamp")
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get FAISS stats: {str(e)}", exc_info=True)
        return {"error": str(e)}


def semantic_search(query: str, top_k: int = 5):
    """
    Semantic search using FAISS
    Returns list of job IDs ranked by relevance
    """
    try:
        if not job_ids:
            logger.warning("FAISS index is empty, returning empty results")
            return []
        
        # Generate query embedding
        query_embedding = embedding_model.encode([query])
        
        # Search in FAISS
        distances, indices = index.search(
            np.array(query_embedding),
            min(top_k, len(job_ids))  # Don't search for more than available
        )
        
        # Return job IDs
        results = []
        for idx in indices[0]:
            if idx < len(job_ids):
                results.append(job_ids[idx])
        
        return results
        
    except Exception as e:
        logger.error(f"Semantic search failed: {str(e)}", exc_info=True)
        return []