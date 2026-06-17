import os
import uuid
import chromadb
from chromadb.utils import embedding_functions
from sklearn.metrics.pairwise import cosine_distances
import numpy as np

# Set up a local persistent directory for ChromaDB
CHROMA_DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "chroma_data")

# We use the fast and lightweight all-MiniLM-L6-v2 model for skill embedding
ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")

# Initialize persistent client
chroma_client = chromadb.PersistentClient(path=CHROMA_DATA_PATH)

def get_or_create_skills_collection():
    """
    Returns the persistent collection for skills, creating it if it doesn't exist.
    We use cosine similarity space since we filter by cosine distance <= 0.30 (similarity >= 0.70).
    """
    collection = chroma_client.get_or_create_collection(
        name="resume_jd_skills",
        embedding_function=ef,  # type: ignore
        metadata={"hnsw:space": "cosine"}
    )
    return collection

def store_skills_in_db(source: str, session_id: str, technical_skills: list[str], soft_skills: list[str]):
    """
    Stores skills in ChromaDB, tagged with their source (e.g., 'resume' or 'jd') and session_id.
    """
    collection = get_or_create_skills_collection()
    
    docs = []
    ids = []
    metadatas = []
    
    # Process Technical Skills
    for skill in technical_skills:
        docs.append(skill)
        ids.append(f"{session_id}_{source}_tech_{uuid.uuid4().hex[:8]}")
        metadatas.append({"source": source, "session_id": session_id, "type": "technical"})
        
    # Process Soft Skills
    for skill in soft_skills:
        docs.append(skill)
        ids.append(f"{session_id}_{source}_soft_{uuid.uuid4().hex[:8]}")
        metadatas.append({"source": source, "session_id": session_id, "type": "soft"})
        
    if docs:
        collection.add(
            documents=docs,
            ids=ids,
            metadatas=metadatas
        )

def get_semantic_matches(resume_unmatched_skills: list[str], jd_skills: list[str]) -> list[tuple[str, str]]:
    """
    Performs fast in-memory semantic matching to find resume skills that match JD skills with >= 0.70 similarity
    (i.e., cosine distance <= 0.30).
    Returns a list of tuples (resume_skill, matched_jd_skill).
    """
    if not resume_unmatched_skills or not jd_skills:
        return []
        
    try:
        # Generate embeddings in memory directly instead of writing to DB
        jd_embeddings = ef(jd_skills)
        resume_embeddings = ef(resume_unmatched_skills)
        
        # Calculate pairwise cosine distances (returns a matrix of distances)
        distances = cosine_distances(resume_embeddings, jd_embeddings)  # type: ignore
        
        semantic_matches = []
        # Find the best resume skill match for each missing JD skill
        for j, jd_skill in enumerate(jd_skills):
            best_match_idx = distances[:, j].argmin()
            best_distance = distances[best_match_idx, j]
            
            if best_distance <= 0.30: # <= 0.30 distance is >= 0.70 similarity
                matched_resume_skill = resume_unmatched_skills[best_match_idx]
                semantic_matches.append((matched_resume_skill, jd_skill))
                
        return semantic_matches
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Error computing in-memory semantic matches: {e}")
        return []
