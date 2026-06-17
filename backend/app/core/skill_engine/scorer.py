from typing import List, Optional
from pydantic import BaseModel

class SkillMatch(BaseModel):
    jd_skill: str
    resume_skill: Optional[str] = None
    match_type: str  # "exact", "alias", "taxonomy", "semantic", "missing"
    score: float
    similarity: Optional[float] = None

class MatchResult(BaseModel):
    overall_score: float
    matched: List[SkillMatch]
    semantic_matches: List[SkillMatch]
    missing_skills: List[str]

class Scorer:
    """
    Calculates weighted match scores based on the MatchType.
    """
    WEIGHTS = {
        "exact": 1.00,
        "alias": 0.95,
        "taxonomy": 0.90,
        "semantic": 0.70,
        "missing": 0.00
    }

    @staticmethod
    def calculate_score(matches: List[SkillMatch]) -> float:
        """
        Calculates the final percentage score.
        """
        if not matches:
            return 0.0
            
        total_score = sum(Scorer.WEIGHTS.get(m.match_type, 0.0) for m in matches)
        return round((total_score / len(matches)) * 100.0, 2)

    @staticmethod
    def get_weight(match_type: str) -> float:
        return Scorer.WEIGHTS.get(match_type, 0.0)
