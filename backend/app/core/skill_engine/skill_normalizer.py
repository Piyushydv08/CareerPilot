import re
from typing import List
from app.core.normalization import TECHNICAL_SKILL_MAP

class SkillNormalizer:
    """
    Normalizes skills by lowercasing, trimming whitespace, and standardizing aliases.
    Uses the existing TECHNICAL_SKILL_MAP for alias resolution.
    """
    
    @staticmethod
    def normalize_skill(skill: str) -> str:
        if not isinstance(skill, str) or not skill:
            return ""
        # Lowercase and trim excess whitespace
        clean_skill = " ".join(skill.strip().split()).lower()
        # Resolve alias if present in the map
        return TECHNICAL_SKILL_MAP.get(clean_skill, clean_skill)

    @staticmethod
    def normalize_list(skills: List[str]) -> List[str]:
        """
        Normalizes a list of skills and removes duplicates while preserving order.
        """
        normalized = []
        seen = set()
        for s in skills:
            norm = SkillNormalizer.normalize_skill(s)
            if norm and norm not in seen:
                seen.add(norm)
                normalized.append(norm)
        return normalized
