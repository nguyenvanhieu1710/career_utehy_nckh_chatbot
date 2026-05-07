import logging
import os
from typing import List, Dict, Any, Optional
from datetime import datetime

from pymilvus import MilvusClient, DataType
from sqlalchemy import text
from app.core.database import SessionLocal
from app.core.config import settings

logger = logging.getLogger(__name__)

# BGE-M3 Embedding Model — Singleton (load một lần, dùng mãi)
# Dim: 1024, chạy local, không cần API key, không quota
_embedding_model = None

def get_embedding_model():
    """Lazy-load BGE-M3 model (download ~600MB lần đầu từ HuggingFace)"""
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        model_name = getattr(settings, 'EMBEDDING_MODEL_NAME', 'BAAI/bge-m3')
        logger.info(f"Loading embedding model: {model_name} (first load may take a few minutes)")
        _embedding_model = SentenceTransformer(model_name)
        logger.info("Embedding model loaded successfully")
    return _embedding_model

# Milvus Client Instance
_milvus_client = None

def get_milvus_client():
    global _milvus_client
    if _milvus_client is None:
        try:
            _milvus_client = MilvusClient(
                uri=settings.MILVUS_URL,
                token=settings.MILVUS_TOKEN
            )
            logger.info(f"Connected to Milvus Cloud: {settings.MILVUS_URL}")
        except Exception as e:
            logger.error(f"Failed to connect to Milvus Cloud: {str(e)}")
    return _milvus_client

# --- Utility Helpers from optimized_vector_service ---

def _format_salary(salary_display: Optional[str], salary_min: Optional[float], salary_max: Optional[float]) -> str:
    """Helper to format salary strings nicely"""
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

# --- Embedding Logic (BGE-M3) ---

EMBEDDING_DIM = 1024  # BGE-M3 output dimension

def get_embedding(text_content: str) -> List[float]:
    """
    Generate embedding using BGE-M3 (local SentenceTransformer).
    Model: BAAI/bge-m3 — 1024 dimensions, multilingual, no API quota.
    """
    try:
        model = get_embedding_model()
        # Truncate to ~300-400 words for speed (matches matching service)
        truncated = text_content[:1500]
        vector = model.encode(truncated, normalize_embeddings=True)
        return vector.tolist()
    except Exception as e:
        logger.error(f"BGE-M3 Embedding failed: {str(e)}")
        return [0.0] * EMBEDDING_DIM

# --- Milvus Schema & Sync ---

def ensure_collection_exists():
    """
    Ensures Milvus collection exists with correct schema.
    Tự động drop & recreate nếu dim không khớp (ví dụ: migrate từ Gemini 768 sang BGE-M3 1024)
    """
    client = get_milvus_client()
    if client is None: return False

    try:
        if client.has_collection(collection_name=settings.MILVUS_COLLECTION):
            # Kiểm tra dim có khớp không
            try:
                col_info = client.describe_collection(settings.MILVUS_COLLECTION)
                for field in col_info.get("fields", []):
                    if field["name"] == "vector":
                        stored_dim = field.get("params", {}).get("dim", 0)
                        if stored_dim != EMBEDDING_DIM:
                            logger.warning(
                                f"Dim mismatch: stored={stored_dim}, expected={EMBEDDING_DIM}. "
                                f"Dropping collection to recreate with correct dim..."
                            )
                            client.drop_collection(settings.MILVUS_COLLECTION)
                            break
                else:
                    return True  # dim đúng, giữ nguyên
            except Exception:
                return True  # Không đọc được info, giữ nguyên

        logger.info(f"Initializing collection: {settings.MILVUS_COLLECTION} (dim={EMBEDDING_DIM})")
        schema = client.create_schema(auto_id=False, enable_dynamic_field=True)

        schema.add_field(field_name="job_id", datatype=DataType.VARCHAR, max_length=100, is_primary=True)
        schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=EMBEDDING_DIM)
        schema.add_field(field_name="category", datatype=DataType.VARCHAR, max_length=100)  # For filtering

        index_params = client.prepare_index_params()
        index_params.add_index(field_name="vector", index_type="AUTOINDEX", metric_type="COSINE")

        client.create_collection(
            collection_name=settings.MILVUS_COLLECTION,
            schema=schema,
            index_params=index_params
        )
        logger.info(f"Collection {settings.MILVUS_COLLECTION} created with dim={EMBEDDING_DIM}")
        return True
    except Exception as e:
        logger.error(f"Milvus collection init failed: {e}")
        return False

async def sync_to_milvus():
    """Syncs PG data to Milvus with job_type as category tag"""
    if not ensure_collection_exists(): return False
    client = get_milvus_client()
    
    try:
        async with SessionLocal() as db:
            query = text("""
                SELECT j.id, j.title, c.name as company, j.description, j.skills, 
                       j.location, j.requirements, j.job_type
                FROM jobs j JOIN companies c ON j.company_id = c.id
            """)
            rows = (await db.execute(query)).fetchall()
            
            if not rows: return False
            
            logger.info(f"Syncing {len(rows)} jobs to Milvus...")
            batch = []
            for r in rows:
                content = f"{r.title} {r.company} {r.description or ''} {r.skills or ''} {r.location or ''} {r.requirements or ''}"
                vector = get_embedding(content)
                batch.append({
                    "job_id": str(r.id),
                    "vector": vector,
                    "category": r.job_type or "OTHER"
                })
                
                if len(batch) >= 50:
                    client.upsert(collection_name=settings.MILVUS_COLLECTION, data=batch)
                    batch = []
            
            if batch:
                client.upsert(collection_name=settings.MILVUS_COLLECTION, data=batch)
            logger.info(f"Sync complete: {len(rows)} jobs indexed to Milvus.")
            return True
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        return False

# --- Search & Detail Mapping ---

async def semantic_search(query: str, category: Optional[str] = None, top_k: int = 5) -> List[str]:
    """
    Core semantic search. Supports optional category filtering.
    """
    client = get_milvus_client()
    if client is None: return []
    
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
        return [hit["entity"]["job_id"] for hit in res[0]]
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return []

async def get_job_details(job_ids: List[str]) -> List[dict]:
    """
    Fetches rich job data from PG for the given IDs. 
    Maintains original order from Milvus.
    """
    if not job_ids: return []
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
            rows = (await db.execute(query, {"ids": job_ids})).fetchall()
            
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
            return [job_map[jid] for jid in job_ids if jid in job_map]
    except Exception as e:
        logger.error(f"Fetch details failed: {e}")
        return []

def get_milvus_stats():
    """Returns basic stats about the Milvus collection"""
    try:
        client = get_milvus_client()
        if not ensure_collection_exists():
            return {"status": "error", "message": "Collection does not exist"}
        
        res = client.describe_collection(collection_name=settings.MILVUS_COLLECTION)
        # Get count (approximate or via query depending on version, here we use describe)
        stats = client.get_collection_stats(collection_name=settings.MILVUS_COLLECTION)
        
        return {
            "collection_name": settings.MILVUS_COLLECTION,
            "total_entities": stats.get("row_count", 0),
            "status": "active"
        }
    except Exception as e:
        logger.error(f"Failed to get Milvus stats: {e}")
        return None