import re
import os

filepath = "app/routers/resume.py"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add normalization import
import_pattern = r'from typing import Any'
new_import = '''from app.core.normalization import (
    normalize_technical_skill, normalize_soft_skill, normalize_keyword, 
    normalize_certification, normalize_project_domain, normalize_education_degree, 
    normalize_education_field, normalize_job_title, deduplicate_normalized_list
)
from typing import Any'''
content = content.replace(import_pattern, new_import)

# 2. Update logic block
logic_pattern = r'# ── Call A: Comprehensive Structured Resume Parse via Llama ─────────\n        try:.*?# Attach skills for quality scoring\n        parsed_data_json\["skills"\] = resume_technical_skills'

new_logic = '''# ── Call A: Comprehensive Structured Resume Parse via Llama ─────────
        try:
            raw_llama_response = await call_llama(
                system_prompt=COMPREHENSIVE_RESUME_PROMPT,
                user_content=raw_text[:6000],
            )
            raw_parsed = extract_json(raw_llama_response)
            
            # Apply Normalization Layer
            normalized_tech = deduplicate_normalized_list([normalize_technical_skill(s) for s in raw_parsed.get("technical_skills", [])])
            normalized_soft = deduplicate_normalized_list([normalize_soft_skill(s) for s in raw_parsed.get("soft_skills", [])])
            normalized_keywords = deduplicate_normalized_list([normalize_keyword(s) for s in raw_parsed.get("keywords", [])])
            normalized_certs = deduplicate_normalized_list([normalize_certification(s) for s in raw_parsed.get("certifications", [])])
            normalized_projects = deduplicate_normalized_list([normalize_project_domain(p.get("domain", "")) for p in raw_parsed.get("projects", []) if isinstance(p, dict)])
            normalized_degrees = deduplicate_normalized_list([normalize_education_degree(e.get("degree", "")) for e in raw_parsed.get("education", []) if isinstance(e, dict)])
            normalized_fields = deduplicate_normalized_list([normalize_education_field(e.get("field_of_study", "")) for e in raw_parsed.get("education", []) if isinstance(e, dict)])
            normalized_titles = deduplicate_normalized_list([normalize_job_title(r.get("designation", "")) for r in raw_parsed.get("experience", {}).get("roles", []) if isinstance(r, dict)])
            
            # Construct Final Resume Parser Output
            parsed_data_json = {
                "raw": raw_parsed,
                "normalized": {
                    "technical_skills": normalized_tech,
                    "soft_skills": normalized_soft,
                    "keywords": normalized_keywords,
                    "certifications": normalized_certs,
                    "project_domains": normalized_projects,
                    "education_degrees": normalized_degrees,
                    "education_fields": normalized_fields,
                    "job_titles": normalized_titles,
                    "experience_domains": []
                }
            }

            resume_technical_skills = normalized_tech
            resume_soft_skills = normalized_soft
            
            # Rank representative skills from the extracted technical skills
            resume_representative_skills = rank_representative_skills(resume_technical_skills, [], max_count=8)

            # Write debug output
            with open("resume_full_parse.json", "w", encoding="utf-8") as f:
                import json
                json.dump(parsed_data_json, f, indent=4)
            logger.info("Groq extracted comprehensive structured profile with normalization.")
        except Exception as e:
            logger.error(f"Groq comprehensive parse failed: {e}. Using text-scan fallback.")
            raw_parsed = generate_mock_resume_data(raw_text)
            parsed_data_json = {
                "raw": raw_parsed,
                "normalized": {
                    "technical_skills": raw_parsed.get("skills", []),
                    "soft_skills": [],
                    "keywords": [],
                    "certifications": [],
                    "project_domains": [],
                    "education_degrees": [],
                    "education_fields": [],
                    "job_titles": [],
                    "experience_domains": []
                }
            }
            resume_technical_skills = parsed_data_json["normalized"]["technical_skills"]
            resume_representative_skills = resume_technical_skills[:8]

        # ── Compatibility Mapping for Frontend & Legacy Functions ──
        # Inject standard fallback keys into the ROOT of parsed_data_json so calculate_resume_quality_score doesn't break
        raw_exp = parsed_data_json["raw"].get("experience", {})
        if isinstance(raw_exp, dict):
            mapped_experience = []
            for role in raw_exp.get("roles", []):
                if isinstance(role, dict):
                    mapped_experience.append({
                        "company": role.get("company", ""),
                        "role": role.get("designation", ""),
                        "duration": role.get("duration", ""),
                        "details": role.get("description", "")
                    })
            parsed_data_json["experience"] = mapped_experience
        elif isinstance(raw_exp, list):
            parsed_data_json["experience"] = raw_exp
        else:
            parsed_data_json["experience"] = []

        parsed_data_json["gaps"] = []
        
        parsed_data_json["name"] = parsed_data_json["raw"].get("candidate_name", "Unknown Candidate")
        
        emails = parsed_data_json["raw"].get("email", "")
        phones = parsed_data_json["raw"].get("phone", "")
        linkedin = parsed_data_json["raw"].get("linkedin", "")
        parsed_data_json["contact_info"] = ", ".join(filter(None, [emails, phones, linkedin]))

        parsed_data_json["skills"] = resume_technical_skills'''

content = re.sub(logic_pattern, new_logic, content, flags=re.DOTALL)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
print("Applied modifications to resume.py successfully.")
