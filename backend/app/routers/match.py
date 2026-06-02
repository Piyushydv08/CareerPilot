import logging
import os
import numpy as np
from fastapi import APIRouter, Depends
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import google.generativeai as genai

from app.models.schemas import MatchAnalysisRequest, MatchAnalysisResponse
from app.core.database import get_database

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/match", tags=["matching"])

# Configure Gemini for Semantic Embeddings
genai.configure(api_key=os.environ.get("GEMINI_API_KEY", "mock-key-replace-in-production"))

def get_embedding(text: str) -> list[float]:
    """Fetch dense vector embeddings from Gemini text-embedding-004."""
    try:
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=text,
            task_type="retrieval_document"
        )
        return result['embedding']
    except Exception as e:
        logger.error(f"Embedding failed: {e}")
        # Return a zero vector for graceful fallback if offline
        return [0.0] * 768

def compute_cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    a = np.array(vec1)
    b = np.array(vec2)
    if np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
        return 0.0
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

@router.post("/analyze", response_model=MatchAnalysisResponse)
async def analyze_match_score(
    payload: MatchAnalysisRequest,
    db = Depends(get_database)
):
    """
    Dual-engine hybrid matching integrating scikit-learn TF-IDF keyword tracking 
    and Gemini text-embedding-004 semantic analysis.
    """
    logger.info("Executing Hybrid Engine Compatibility Match...")
    
    # Reconstruct resume text payload
    resume_text = ""
    if payload.resume:
        skill_names = " ".join([s.name for s in payload.resume.skills])
        exp_details = " ".join([e.details for e in payload.resume.experience])
        resume_text = f"{payload.resume.name} {skill_names} {exp_details}"
    
    job_text = payload.job_description.lower()
    
    if not resume_text:
        resume_text = "Empty Resume"

    # =========================================================================
    # PLANE 1: Strict Keyword Scoring (TF-IDF)
    # =========================================================================
    vectorizer = TfidfVectorizer(stop_words='english')
    # Fit transforming both texts to create a shared vocabulary matrix
    tfidf_matrix = vectorizer.fit_transform([resume_text, job_text])
    
    # Extract Vectors
    resume_vec = tfidf_matrix[0:1]
    job_vec = tfidf_matrix[1:2]
    
    # Compute Exact Token Cosine Similarity
    tfidf_score = float(cosine_similarity(resume_vec, job_vec)[0][0])
    
    # Compute Missing Terms based on Inverse Document Frequency logic
    job_arr = job_vec.toarray()[0]
    resume_arr = resume_vec.toarray()[0]
    feature_names = vectorizer.get_feature_names_out()
    
    missing_terms = []
    for i in range(len(feature_names)):
        # If term is prominent in Job but missing in Resume
        if job_arr[i] > 0.05 and resume_arr[i] == 0:
            missing_terms.append({
                "term": feature_names[i],
                "weight": float(job_arr[i]) * 100  # Percentage weight relative to job spec
            })
            
    # Sort gaps by critical weight
    missing_terms = sorted(missing_terms, key=lambda x: x["weight"], reverse=True)[:10]

    # =========================================================================
    # PLANE 2: Semantic Similarity (Gemini Embeddings)
    # =========================================================================
    resume_embedding = get_embedding(resume_text)
    job_embedding = get_embedding(job_text)
    
    semantic_score = compute_cosine_similarity(resume_embedding, job_embedding)
    
    # Generate MongoDB Atlas $vectorSearch aggregation pipeline as requested
    # This demonstrates how the semantic distance is natively computed inside Atlas.
    atlas_vector_search_pipeline = [
        {
            "$vectorSearch": {
                "index": "resume_vector_index",
                "path": "resume_embeddings",
                "queryVector": job_embedding,
                "numCandidates": 100,
                "limit": 10
            }
        },
        {
            "$project": {
                "name": 1,
                "semantic_score": {"$meta": "vectorSearchScore"}
            }
        }
    ]
    logger.info(f"Generated Atlas Pipeline: {atlas_vector_search_pipeline}")

    # =========================================================================
    # MATHEMATICAL BLENDING
    # =========================================================================
    alpha = 0.40
    beta = 0.60
    
    final_score = (alpha * tfidf_score) + (beta * semantic_score)
    smart_match_score = min(max(int(final_score * 100), 0), 100)

    # Optional DB telemetry
    if db is not None:
        try:
            log_entry = {
                "job_description_snippet": payload.job_description[:100],
                "tfidf_score": tfidf_score,
                "semantic_score": semantic_score,
                "computed_match_score": smart_match_score,
                "missing_terms": missing_terms
            }
            await db["match_logs"].insert_one(log_entry)
        except Exception as e:
            pass

    return {
        "match_score": smart_match_score,
        "tfidf_score": tfidf_score,
        "semantic_score": semantic_score,
        "missing_terms": missing_terms
    }
