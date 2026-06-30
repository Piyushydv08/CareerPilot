from app.core.skill_engine.matcher import SkillMatcher
import json

def test_matcher():
    resume_skills = ["PyTorch", "Matplotlib", "FastAPI", "PostgreSQL"]
    jd_skills = ["Deep Learning", "Data Visualization", "Backend Development", "SQL", "Neural Networks", "Docker"]
    
    matcher = SkillMatcher(semantic_threshold=0.65)
    result = matcher.match_skills(resume_skills, jd_skills)
    
    print("Match Score:", result.overall_score)
    print("\n--- MATCHED ---")
    for m in result.matched:
        print(f"{m.jd_skill} <- {m.resume_skill} ({m.match_type}, score: {m.score})")
        
    print("\n--- SEMANTIC MATCHES ---")
    for m in result.semantic_matches:
        print(f"{m.jd_skill} <- {m.resume_skill} ({m.match_type}, sim: {m.similarity}, score: {m.score})")
        
    print("\n--- MISSING ---")
    print(result.missing_skills)

if __name__ == "__main__":
    test_matcher()
