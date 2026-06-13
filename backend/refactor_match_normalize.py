import re
import os

filepath = "app/routers/match.py"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add import
import_pattern = r'from app\.core\.database import get_database'
new_import = '''from app.core.database import get_database
from app.core.normalization import (
    normalize_technical_skill, normalize_soft_skill, normalize_keyword, 
    normalize_certification, normalize_project_domain, normalize_education_degree, 
    normalize_education_field, normalize_job_title, deduplicate_normalized_list
)'''
content = content.replace(import_pattern, new_import)

# 2. Delete old SKILL_NORM_MAP and normalize_skill and deduplicate_skills
delete_pattern = r'# ── Skill normalization map \(canonical names\) ─────────────────────────────────.*?def extract_json'
new_extract_json = 'def extract_json'
content = re.sub(delete_pattern, new_extract_json, content, flags=re.DOTALL)

# 3. Refactor Call B inside analyze endpoint
jd_logic_pattern = r'# ── Call B: JD skill extraction via Llama ─────────────────────────────────\n    jd_skills: list\[str\] = \[\]\n    if not IS_GROQ_MOCK:.*?else:\n        jd_skills = \[normalize_skill\(str\(k\)\) for k in ats\.get\("missing_skills", \[\]\) \+ ats\.get\("missing_keywords", \[\]\)\]'

new_jd_logic = '''# ── Call B: JD skill extraction via Llama ─────────────────────────────────
    jd_skills: list[str] = []
    parsed_jd_final = None
    if not IS_GROQ_MOCK:
        try:
            raw_jd_response = await call_llama(JD_SKILL_EXTRACTION_PROMPT, job_description[:5000])
            raw_jd_parsed = extract_json(raw_jd_response)
            
            # Apply Normalization Layer for JD
            normalized_jd_tech = deduplicate_normalized_list([normalize_technical_skill(s) for s in raw_jd_parsed.get("technical_skills", [])])
            normalized_jd_soft = deduplicate_normalized_list([normalize_soft_skill(s) for s in raw_jd_parsed.get("soft_skills", [])])
            normalized_jd_keywords = deduplicate_normalized_list([normalize_keyword(s) for s in raw_jd_parsed.get("keywords", [])])
            
            parsed_jd_final = {
                "raw": raw_jd_parsed,
                "normalized": {
                    "technical_skills": normalized_jd_tech,
                    "soft_skills": normalized_jd_soft,
                    "keywords": normalized_jd_keywords,
                }
            }
            
            jd_skills = normalized_jd_tech
            logger.info(f"Llama extracted {len(jd_skills)} JD skills.")
            
            # Save for debugging
            with open("jd_full_parse.json", "w", encoding="utf-8") as f:
                json.dump(parsed_jd_final, f, indent=4)
        except Exception as e:
            logger.error(f"Llama JD skill extraction failed: {e}")
            jd_skills = deduplicate_normalized_list([normalize_technical_skill(str(k)) for k in ats.get("missing_skills", []) + ats.get("missing_keywords", [])])
    else:
        jd_skills = deduplicate_normalized_list([normalize_technical_skill(str(k)) for k in ats.get("missing_skills", []) + ats.get("missing_keywords", [])])'''

content = re.sub(jd_logic_pattern, new_jd_logic, content, flags=re.DOTALL)


# 4. Refactor resume skill processing inside analyze endpoint
resume_skill_pattern = r'# ── Resume skills: prefer Gemini\'s technical_skills, fall back to payload skills ──.*?resume_skills = \[normalize_skill\(s\) for s in raw_resume_skills\]'

new_resume_skill_logic = '''# ── Resume skills: prefer Gemini's technical_skills, fall back to payload skills ──
    raw_resume_skills: list[str] = []
    
    # Check if we have the new nested normalized schema
    if "normalized" in resume_data_parsed and isinstance(resume_data_parsed["normalized"], dict):
        raw_resume_skills = resume_data_parsed["normalized"].get("technical_skills", [])
    else:
        parsed_tech = resume_data_parsed.get("technical_skills", [])
        if isinstance(parsed_tech, list) and parsed_tech:
            raw_resume_skills = [s for s in parsed_tech if isinstance(s, str)]
        elif payload.resume and payload.resume.skills:
            raw_resume_skills = [s.name for s in payload.resume.skills]
            
    resume_skills = deduplicate_normalized_list([normalize_technical_skill(s) for s in raw_resume_skills])'''

content = re.sub(resume_skill_pattern, new_resume_skill_logic, content, flags=re.DOTALL)


# 5. Fix deduplicate_skills calls inside legacy response structure
dedup_calls_pattern = r'deduplicate_skills'
content = content.replace(dedup_calls_pattern, 'deduplicate_normalized_list')


with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
print("Applied modifications to match.py successfully.")
