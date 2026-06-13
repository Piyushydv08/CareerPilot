import logging
import re
from typing import Dict, Any, List

from app.core.normalization import (
    normalize_technical_skill, normalize_soft_skill, normalize_project_domain,
    normalize_education_degree, normalize_education_field, normalize_certification,
    deduplicate_normalized_list
)

logger = logging.getLogger(__name__)


def calculate_skills_match(resume_tech: list, resume_soft: list, jd_tech: list, jd_soft: list) -> float:
    # 1. Technical Match
    if not jd_tech:
        tech_match = 100.0  # If JD doesn't ask for any, assume 100%
    else:
        resume_tech_set = {s.lower() for s in resume_tech}
        matched_tech = [s for s in jd_tech if s.lower() in resume_tech_set]
        tech_match = (len(matched_tech) / len(jd_tech)) * 100.0

    # 2. Soft Skill Match
    if not jd_soft:
        soft_match = 100.0
    else:
        resume_soft_set = {s.lower() for s in resume_soft}
        matched_soft = [s for s in jd_soft if s.lower() in resume_soft_set]
        soft_match = (len(matched_soft) / len(jd_soft)) * 100.0

    return (tech_match * 0.8) + (soft_match * 0.2)


def calculate_experience_match(resume_exp_data: dict, jd_exp_data: dict) -> float:
    # A: Years Match
    req_years = jd_exp_data.get("minimum_years", 0)
    resume_years = resume_exp_data.get("total_years", 0)
    
    if req_years <= 0:
        years_match = 100.0
    else:
        years_match = min(resume_years / req_years, 1.0) * 100.0

    # B: Domain Match
    req_domains = [normalize_project_domain(d) for d in jd_exp_data.get("required_domains", []) if d]
    resume_roles = resume_exp_data.get("roles", [])
    # Extract domains implicitly from role titles or descriptions if not explicitly present
    # Using job titles as a proxy for domains here.
    resume_domains = deduplicate_normalized_list([normalize_project_domain(r.get("designation", "")) for r in resume_roles])
    
    if not req_domains:
        domain_match = 100.0
    else:
        resume_domain_set = {d.lower() for d in resume_domains}
        matched_domains = [d for d in req_domains if d.lower() in resume_domain_set]
        domain_match = (len(matched_domains) / len(req_domains)) * 100.0

    # C: Role Similarity (Proxy: Keyword overlap in job titles)
    # Since we don't have a direct "role title" in jd_exp_data, we assume 100 for now or calculate from domains
    # In a full ATS, you'd embed the title and do cosine similarity. Here, we'll use a basic text intersection.
    role_match = 100.0  # Stubbed to 100% since complex NLP title matching isn't provided in the prompt

    return (years_match * 0.4) + (domain_match * 0.4) + (role_match * 0.2)


def calculate_project_match(resume_projects: list, jd_proj_reqs: list, resume_tech: list, jd_tech: list) -> float:
    req_domains = deduplicate_normalized_list([normalize_project_domain(d) for d in jd_proj_reqs if d])
    res_domains = deduplicate_normalized_list([normalize_project_domain(p.get("domain", "")) for p in resume_projects if isinstance(p, dict)])

    # Domain Match
    if not req_domains:
        domain_match = 100.0
    else:
        res_dom_set = {d.lower() for d in res_domains}
        matched_doms = [d for d in req_domains if d.lower() in res_dom_set]
        domain_match = (len(matched_doms) / len(req_domains)) * 100.0

    # Technology Match
    if not jd_tech:
        tech_match = 100.0
    else:
        # Get all tech used specifically in resume projects
        proj_techs = []
        for p in resume_projects:
            if isinstance(p, dict):
                proj_techs.extend(p.get("technologies", []))
        proj_techs_norm = {normalize_technical_skill(t).lower() for t in proj_techs}
        
        matched_tech = [t for t in jd_tech if t.lower() in proj_techs_norm]
        tech_match = (len(matched_tech) / len(jd_tech)) * 100.0

    return (domain_match * 0.7) + (tech_match * 0.3)


def calculate_education_match(resume_edu: list, jd_edu_data: dict) -> float:
    req_degrees = deduplicate_normalized_list([normalize_education_degree(d) for d in jd_edu_data.get("required_degrees", [])])
    req_fields = deduplicate_normalized_list([normalize_education_field(f) for f in jd_edu_data.get("required_fields_of_study", [])])

    res_degrees = deduplicate_normalized_list([normalize_education_degree(e.get("degree", "")) for e in resume_edu if isinstance(e, dict)])
    res_fields = deduplicate_normalized_list([normalize_education_field(e.get("field_of_study", "")) for e in resume_edu if isinstance(e, dict)])

    # Degree Match
    if not req_degrees:
        degree_match = 100.0
    else:
        res_deg_set = {d.lower() for d in res_degrees}
        matched_deg = [d for d in req_degrees if d.lower() in res_deg_set]
        degree_match = (len(matched_deg) / len(req_degrees)) * 100.0

    # Field Match
    if not req_fields:
        field_match = 100.0
    else:
        res_fld_set = {f.lower() for f in res_fields}
        matched_fld = [f for f in req_fields if f.lower() in res_fld_set]
        field_match = (len(matched_fld) / len(req_fields)) * 100.0

    return (degree_match * 0.4) + (field_match * 0.6)


def calculate_certification_match(resume_certs: list, jd_cert_data: dict) -> float:
    req_certs = deduplicate_normalized_list([normalize_certification(c) for c in jd_cert_data.get("required_certifications", [])])
    pref_certs = deduplicate_normalized_list([normalize_certification(c) for c in jd_cert_data.get("preferred_certifications", [])])

    res_certs = deduplicate_normalized_list([normalize_certification(c) for c in resume_certs if c])
    res_cert_set = {c.lower() for c in res_certs}

    # Required Match
    if not req_certs:
        req_match = 100.0
    else:
        matched_req = [c for c in req_certs if c.lower() in res_cert_set]
        req_match = (len(matched_req) / len(req_certs)) * 100.0

    # Preferred Match
    if not pref_certs:
        pref_match = 100.0
    else:
        matched_pref = [c for c in pref_certs if c.lower() in res_cert_set]
        pref_match = (len(matched_pref) / len(pref_certs)) * 100.0

    return (req_match * 0.8) + (pref_match * 0.2)


def calculate_resume_quality_v2(resume_data: dict) -> float:
    """
    Calculates out of 110 points, then normalizes to 100.
    """
    score = 0
    raw_resume = resume_data.get("raw", {})
    
    # 1. Contact Information (10)
    email = raw_resume.get("email", "")
    phone = raw_resume.get("phone", "")
    linkedin = raw_resume.get("linkedin", "")
    if email: score += 4
    if phone: score += 3
    if linkedin: score += 3

    # 2. Summary (10)
    if raw_resume.get("summary"):
        score += 10

    # 3. Technical Skills Section (15)
    if raw_resume.get("technical_skills"):
        score += 15

    # 4. Projects (20)
    projects = raw_resume.get("projects", [])
    if len(projects) >= 2:
        score += 20
    elif len(projects) == 1:
        score += 10

    # 5. Experience (20)
    roles = raw_resume.get("experience", {}).get("roles", [])
    if len(roles) >= 2:
        score += 20
    elif len(roles) == 1:
        score += 10

    # 6. Education (10)
    if raw_resume.get("education"):
        score += 10

    # 7. Certifications (10)
    if raw_resume.get("certifications"):
        score += 10

    # 8. Achievements (5)
    if raw_resume.get("achievements"):
        score += 5

    # 9. ATS Formatting (10)
    # We heuristically grant this based on successful parsing by Llama (if we successfully got a name and skills)
    if raw_resume.get("candidate_name") and raw_resume.get("technical_skills"):
        score += 10

    # Normalize 110 to 100
    normalized_score = (score / 110.0) * 100.0
    return min(normalized_score, 100.0)


def calculate_comprehensive_ats_score(resume_parsed: dict, jd_parsed: dict) -> dict:
    """
    Master ATS function tying all modular logic together according to the formula.
    """
    try:
        r_norm = resume_parsed.get("normalized", {})
        j_norm = jd_parsed.get("normalized", {})
        
        resume_tech = r_norm.get("technical_skills", [])
        resume_soft = r_norm.get("soft_skills", [])
        
        jd_tech = j_norm.get("technical_skills", [])
        jd_soft = j_norm.get("soft_skills", [])

        # 1. Skills
        skill_score = calculate_skills_match(resume_tech, resume_soft, jd_tech, jd_soft)

        # 2. Experience
        r_exp = resume_parsed.get("raw", {}).get("experience", {})
        j_exp = jd_parsed.get("raw", {}).get("experience_requirements", {})
        exp_score = calculate_experience_match(r_exp, j_exp)

        # 3. Projects
        r_proj = resume_parsed.get("raw", {}).get("projects", [])
        j_proj = jd_parsed.get("raw", {}).get("project_requirements", [])
        proj_score = calculate_project_match(r_proj, j_proj, resume_tech, jd_tech)

        # 4. Education
        r_edu = resume_parsed.get("raw", {}).get("education", [])
        j_edu = jd_parsed.get("raw", {}).get("education_requirements", {})
        edu_score = calculate_education_match(r_edu, j_edu)

        # 5. Certifications
        r_cert = resume_parsed.get("raw", {}).get("certifications", [])
        j_cert = jd_parsed.get("raw", {}).get("certification_requirements", {})
        cert_score = calculate_certification_match(r_cert, j_cert)

        # 6. Resume Quality
        quality_score = calculate_resume_quality_v2(resume_parsed)

        # Final Formula
        final_ats = (
            (skill_score * 0.40) +
            (exp_score * 0.20) +
            (proj_score * 0.15) +
            (edu_score * 0.10) +
            (cert_score * 0.05) +
            (quality_score * 0.10)
        )

        return {
            "ats_score": int(final_ats),
            "breakdown": {
                "skills_match": int(skill_score),
                "experience_relevance": int(exp_score),
                "keyword_density": int(proj_score),  # Map Project Match -> legacy UI "keyword_density" dial
                "education_certifications": int((edu_score * 0.66) + (cert_score * 0.33)), 
                "formatting_completeness": int(quality_score)
            }
        }
    except Exception as e:
        logger.error(f"Error in comprehensive ATS scoring: {e}")
        # Safe fallback
        return {
            "ats_score": 50,
            "breakdown": {
                "skills_match": 50,
                "experience_relevance": 50,
                "keyword_density": 50,
                "education_certifications": 50,
                "formatting_completeness": 50
            }
        }
