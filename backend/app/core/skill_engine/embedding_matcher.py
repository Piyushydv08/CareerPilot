import numpy as np
from typing import List
from pydantic import BaseModel
from sklearn.metrics.pairwise import cosine_distances
from app.core.vector_store import ef  # Reuse the fast initialized embedding function
from app.core.skill_engine.skill_expander import ExpandedSkill

class SemanticMatchResult(BaseModel):
    jd_skill: str
    resume_skill: str  # The original resume skill
    matched_term: str  # The specific term it matched (could be expanded)
    similarity: float

class EmbeddingMatcher:
    """
    Handles semantic similarity matching using Sentence Transformers.
    """
    def __init__(self, threshold: float = 0.75):
        self.threshold = threshold

    def find_matches(self, unmatched_jd_skills: List[str], expanded_resume_skills: List[ExpandedSkill]) -> List[SemanticMatchResult]:
        if not unmatched_jd_skills or not expanded_resume_skills:
            return []

        # Extract just the skill strings for embedding
        resume_skill_strings = [es.skill for es in expanded_resume_skills]

        try:
            jd_embeddings = ef(unmatched_jd_skills)
            resume_embeddings = ef(resume_skill_strings)
            
            # Returns a matrix of distances
            distances = cosine_distances(resume_embeddings, jd_embeddings)  # type: ignore
            
            matches = []
            
            for j, jd_skill in enumerate(unmatched_jd_skills):
                best_match_idx = distances[:, j].argmin()
                best_distance = distances[best_match_idx, j]
                similarity = 1.0 - best_distance
                
                if similarity >= self.threshold:
                    best_expanded_skill = expanded_resume_skills[best_match_idx]
                    matches.append(SemanticMatchResult(
                        jd_skill=jd_skill,
                        resume_skill=best_expanded_skill.original_skill,
                        matched_term=best_expanded_skill.skill,
                        similarity=float(similarity)
                    ))
                    
            return matches
        except Exception as e:
            print(f"Error during semantic matching: {e}")
            return []
