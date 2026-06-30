from typing import List, Set
from pydantic import BaseModel
from app.core.skill_engine.taxonomy_manager import TaxonomyManager

class ExpandedSkill(BaseModel):
    skill: str
    original_skill: str

class SkillExpander:
    """
    Expands a list of resume skills using the taxonomy hierarchy.
    Tracks which expanded skill corresponds to which original skill.
    """
    def __init__(self, taxonomy_manager: TaxonomyManager):
        self.taxonomy_manager = taxonomy_manager

    def expand_skills(self, normalized_skills: List[str]) -> List[ExpandedSkill]:
        expanded = []
        seen_skills: Set[str] = set()

        for skill in normalized_skills:
            # Add the original skill itself
            if skill not in seen_skills:
                expanded.append(ExpandedSkill(skill=skill, original_skill=skill))
                seen_skills.add(skill)
            
            # Add its taxonomy parents
            parents = self.taxonomy_manager.get_parents(skill)
            from app.core.skill_engine.skill_normalizer import SkillNormalizer
            
            for parent in parents:
                norm_parent = SkillNormalizer.normalize_skill(parent)
                if norm_parent and norm_parent not in seen_skills:
                    expanded.append(ExpandedSkill(skill=norm_parent, original_skill=skill))
                    seen_skills.add(norm_parent)
                    
        return expanded
