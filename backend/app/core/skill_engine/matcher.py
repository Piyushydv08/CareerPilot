from typing import List, Dict, Set, Optional
from app.core.skill_engine.skill_normalizer import SkillNormalizer
from app.core.skill_engine.taxonomy_manager import TaxonomyManager
from app.core.skill_engine.skill_expander import SkillExpander
from app.core.skill_engine.embedding_matcher import EmbeddingMatcher
from app.core.skill_engine.scorer import Scorer, SkillMatch, MatchResult

class SkillMatcher:
    """
    Orchestrator for the 5-step deterministic skill matching pipeline.
    """
    def __init__(self, taxonomy_path: Optional[str] = None, semantic_threshold: float = 0.70):
        self.normalizer = SkillNormalizer()
        self.taxonomy_manager = TaxonomyManager(taxonomy_path=taxonomy_path)
        self.expander = SkillExpander(self.taxonomy_manager)
        self.embedding_matcher = EmbeddingMatcher(threshold=semantic_threshold)
            
    def match_skills(self, resume_skills: List[str], jd_skills: List[str]) -> MatchResult:
        # Step 1: Normalization
        norm_resume = self.normalizer.normalize_list(resume_skills)
        norm_jd = self.normalizer.normalize_list(jd_skills)
        
        # Step 3: Expand resume skills
        expanded_resume = self.expander.expand_skills(norm_resume)
        
        all_matches: List[SkillMatch] = []
        matched_exact_taxonomy: List[SkillMatch] = []
        semantic_matches: List[SkillMatch] = []
        missing_skills: List[str] = []
        
        unmatched_jd = []
        
        # Build lookup dictionaries for exact and taxonomy
        original_resume_set = set(norm_resume)
        
        expanded_dict = {}
        for es in expanded_resume:
            if es.skill not in expanded_dict:
                expanded_dict[es.skill] = es.original_skill

        # Step 4: Exact and Taxonomy Match
        for jd_skill in norm_jd:
            if jd_skill in original_resume_set:
                # Exact match
                match = SkillMatch(
                    jd_skill=jd_skill,
                    resume_skill=jd_skill,
                    match_type="exact",
                    score=Scorer.get_weight("exact")
                )
                all_matches.append(match)
                matched_exact_taxonomy.append(match)
            elif jd_skill in expanded_dict:
                # Taxonomy match
                match = SkillMatch(
                    jd_skill=jd_skill,
                    resume_skill=expanded_dict[jd_skill],
                    match_type="taxonomy",
                    score=Scorer.get_weight("taxonomy")
                )
                all_matches.append(match)
                matched_exact_taxonomy.append(match)
            else:
                unmatched_jd.append(jd_skill)
                
        # Step 5: Embedding Match for unmatched
        if unmatched_jd:
            semantic_results = self.embedding_matcher.find_matches(unmatched_jd, expanded_resume)
            
            # Map semantic results
            semantic_jd_set = set()
            for sr in semantic_results:
                match = SkillMatch(
                    jd_skill=sr.jd_skill,
                    resume_skill=sr.resume_skill,
                    match_type="semantic",
                    score=Scorer.get_weight("semantic"),
                    similarity=sr.similarity
                )
                all_matches.append(match)
                semantic_matches.append(match)
                semantic_jd_set.add(sr.jd_skill)
                
            # Step 6: Missing Flagging
            for jd_skill in unmatched_jd:
                if jd_skill not in semantic_jd_set:
                    match = SkillMatch(
                        jd_skill=jd_skill,
                        match_type="missing",
                        score=Scorer.get_weight("missing")
                    )
                    all_matches.append(match)
                    missing_skills.append(jd_skill)

        # Calculate final score
        overall_score = Scorer.calculate_score(all_matches)
        
        return MatchResult(
            overall_score=overall_score,
            matched=matched_exact_taxonomy,
            semantic_matches=semantic_matches,
            missing_skills=missing_skills
        )
