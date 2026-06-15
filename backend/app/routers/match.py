# app/routers/match.py

import json
import logging
import os
import re
import httpx
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

from app.models.schemas import (
    MatchAnalysisRequest,
    MatchAnalysisResponse,
    ATSCategoryScores,
    MissingTerm,
    SimulateScoreRequest,
    SimulateScoreResponse,
)
from app.core.database import get_database
from app.core.normalization import (
    normalize_technical_skill, normalize_soft_skill, normalize_keyword, 
    normalize_certification, normalize_project_domain, normalize_education_degree, 
    normalize_education_field, normalize_job_title, deduplicate_normalized_list
)
from app.core.scoring import calculate_comprehensive_ats_score

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/match", tags=["matching"])

# ── Gemini (kept for detailed ATS analysis) ───────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
IS_GEMINI_MOCK = not GEMINI_API_KEY or GEMINI_API_KEY.startswith("mock")

_gemini_client: genai.Client | None = None

def get_gemini_client() -> genai.Client:
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    return _gemini_client

# ── Groq / Llama (for JD skill extraction) ───────────────────────────────────
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_BASE_URL = "https://api.groq.com/openai/v1/chat/completions"
IS_GROQ_MOCK = not bool(GROQ_API_KEY)


async def call_llama(system_prompt: str, user_content: str) -> str:  # Groq llama-3.3-70b inference
    msgs = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}]
    payload = {"model": "llama-3.3-70b-versatile", "messages": msgs, "temperature": 0.1, "max_tokens": 2048}
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    client = httpx.AsyncClient(timeout=30.0)
    response = await client.post(GROQ_BASE_URL, headers=headers, json=payload)
    await client.aclose()
    data = response.json()
    return str(data["choices"][0]["message"]["content"]).strip()


# ── JD skill-extraction prompt (per ATS redesign spec) ───────────────────────
JD_SKILL_EXTRACTION_PROMPT = """You are an Expert ATS Job Description Parser.

Analyze the provided Job Description and extract ALL hiring requirements mentioned.

Your goal is to identify:

1. Technical Skills
   * Programming languages
   * Frameworks
   * Libraries
   * Databases
   * Cloud platforms
   * Tools
   * Software
   * Technologies
   * Certifications
   * Technical methodologies

2. Soft Skills
   * Communication
   * Leadership
   * Analytical Thinking
   * Problem Solving
   * Critical Thinking
   * Presentation Skills
   * Teamwork
   * Collaboration
   * Adaptability
   * Stakeholder Management
   * Time Management
   * Any behavioral or interpersonal skill explicitly mentioned

3. Experience Requirements
   * Minimum years of experience
   * Maximum years of experience
   * Experience domains
   * Required industry experience
   * Preferred industry experience

4. Education Requirements
   * Degrees
   * Branches / Majors
   * Required education
   * Preferred education

5. Certification Requirements
   * Required certifications
   * Preferred certifications

6. Project Requirements
   * Types of projects expected
   * Domain-specific projects
   * Hands-on experience requirements

7. Responsibilities
   * Major job responsibilities
   * Key duties

8. Role Metadata
   * Job title
   * Department
   * Seniority level

IMPORTANT RULES
* Extract ONLY information explicitly mentioned.
* Do NOT invent requirements.
* Do NOT infer missing information.
* Remove duplicates.
* Standardize skill names whenever possible.
* Return ONLY valid JSON.
* No markdown.
* No explanations.
* No comments.

OUTPUT FORMAT
{
"job_title": "",
"department": "",
"seniority_level": "",
"technical_skills": [],
"soft_skills": [],
"experience_requirements": {
"minimum_years": 0,
"maximum_years": 0,
"required_domains": [],
"preferred_domains": []
},
"education_requirements": {
"required_degrees": [],
"preferred_degrees": [],
"required_fields_of_study": [],
"preferred_fields_of_study": []
},
"certification_requirements": {
"required_certifications": [],
"preferred_certifications": []
},
"project_requirements": [],
"responsibilities": [],
"preferred_skills": [],
"keywords": []
}

Return ONLY the JSON object.
No markdown fences.
No explanations.
No extra text."""


def extract_json(text: str) -> dict:
    """Robustly extract JSON from a model response (handles markdown fences)."""
    text = text.strip()
    text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'```\s*$', '', text)
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'[\[{][\s\S]+[\]}]', text)
        if match:
            return json.loads(match.group(0))
        raise ValueError(f"No valid JSON: {text[:200]}")


def get_personalized_recommendation(technical_skills: list[str], soft_skills: list[str]) -> str:
    if IS_GEMINI_MOCK:
        return ""
    
    prompt = f"""You are an experienced Career Coach, Data Science Mentor, and Technical Interview Expert.

Analyze the candidate's gap skills and provide personalized recommendations.

Technical Skills:
{", ".join(technical_skills)}

Soft Skills:
{", ".join(soft_skills)}

Instructions
3. Provide recommendations in the following sections:

### Technical Skill Recommendations
For each technical skill:
- Explain its importance in industry.
- Mention whether the candidate should:
  - Maintain it
  - Improve it
  - Learn advanced concepts
- Suggest specific topics to study next.

### Soft Skill Recommendations
For each soft skill:
- Explain why it matters.
- Mention practical ways to improve it.
- Suggest real-world activities to develop it.

### Career-Oriented Recommendations
Based on the overall skill profile:
- Recommend suitable career paths.
- Mention the top skills that should be prioritized.
- Mention skills that are most important for placements and interviews.

### Learning Roadmap
Create:
- Immediate Focus (next 10 days)

Ensure recommendations are practical, actionable, and tailored to the provided skills.
Do not generate generic advice."""

    try:
        client = get_gemini_client()
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.7)
        )
        return response.text or ""
    except Exception as e:
        logger.error(f"Error generating recommendation: {e}")
        return ""



# ----------------------------------------------------------------------
# New detailed ATS prompt (supports both JD-present and JD-missing cases)
# ----------------------------------------------------------------------
DETAILED_ATS_PROMPT = """You are an expert Resume Parser, ATS Evaluator, and Technical Recruiter.

Your task is to analyze the provided resume and optionally compare it against a job description.

IMPORTANT RULES:
1. Return ONLY valid JSON.
2. Do not include markdown, explanations, comments, or code fences.
3. Do not invent information not present in the resume.
4. If a field is unavailable, return null, an empty string, or an empty array.
5. Extract all possible information from the resume.
6. If a job description is provided, perform ATS matching.
7. If no job description is provided, perform a general ATS readiness evaluation.
8. ATS score must always be between 0 and 100.

RESUME:
{resume_text}

JOB DESCRIPTION (may be empty):
{job_description}

TASKS:

STEP 1: RESUME PARSING
Extract:
- name
- email
- phone
- location
- linkedin
- github
- portfolio
- summary
- total_experience_years (numeric, estimate if needed)
- technical_skills (list of strings)
- soft_skills (list of strings)
- education (list of objects with degree, institution, year)
- experience (list of objects with company, designation, duration, description)
- projects (list of objects with name, description, technologies)
- certifications (list of strings)
- achievements (list of strings)
- languages (list of strings)
- keywords (list of important terms extracted from resume)

STEP 2: ATS ANALYSIS

IF JOB DESCRIPTION IS PROVIDED:
- Calculate ATS Match Score using the weighting:
  Skills Match = 40%, Experience Relevance = 30%, Projects Relevance = 15%,
  Education Relevance = 10%, Certifications = 5%.
- Provide matching_skills, missing_skills, matching_keywords, missing_keywords.
- Provide percentage matches for each category.
- Provide strengths, weaknesses, resume_improvements, hiring_recommendation.

IF JOB DESCRIPTION IS NOT PROVIDED:
- Provide a General ATS Readiness Score (0-100) based on:
  Contact Information Quality, Skills Section Quality, Experience Quality,
  Project Quality, Education Quality, Certification Quality,
  Keyword Richness, ATS Friendliness, Quantified Achievements, Resume Completeness.
- Still provide the resume_data section with all extracted information.
- Omit category-specific match percentages (set to 0) and set job_description_provided = false.

FINAL OUTPUT FORMAT (exactly as shown, return only this JSON):
{
  "resume_data": {
    "name": "",
    "email": "",
    "phone": "",
    "location": "",
    "linkedin": "",
    "github": "",
    "portfolio": "",
    "summary": "",
    "total_experience_years": 0,
    "technical_skills": [],
    "soft_skills": [],
    "education": [
      {"degree": "", "institution": "", "year": ""}
    ],
    "experience": [
      {"company": "", "designation": "", "duration": "", "description": ""}
    ],
    "projects": [
      {"name": "", "description": "", "technologies": []}
    ],
    "certifications": [],
    "achievements": [],
    "languages": [],
    "keywords": []
  },
  "ats_analysis": {
    "job_description_provided": true,
    "ats_score": 0,
    "overall_rating": "",
    "matching_keywords": [],
    "missing_keywords": [],
    "matched_skills": [],
    "missing_skills": [],
    "experience_match_percentage": 0,
    "education_match_percentage": 0,
    "project_match_percentage": 0,
    "certification_match_percentage": 0,
    "contact_score": 0,
    "skills_score": 0,
    "experience_score": 0,
    "projects_score": 0,
    "education_score": 0,
    "certification_score": 0,
    "keyword_score": 0,
    "formatting_score": 0,
    "strengths": [],
    "weaknesses": [],
    "missing_sections": [],
    "recommendations": [],
    "resume_summary": "",
    "hiring_recommendation": "",
    "ats_ready": true
  }
}"""

def run_detailed_ats_analysis(resume_text: str, job_description: str) -> dict:
    """Call Gemini with the detailed prompt and return the parsed JSON."""
    client = get_gemini_client()
    prompt = DETAILED_ATS_PROMPT.format(
        resume_text=resume_text[:7000],
        job_description=job_description[:5000] if job_description else "Not provided."
    )
    response = client.models.generate_content(
        model="gemini-1.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.2,
        ),
    )
    return extract_json(response.text or "")

# ----------------------------------------------------------------------
# Heuristic fallback (simplified version to match new schema)
# ----------------------------------------------------------------------
def fallback_detailed_analysis(resume_text: str, job_description: str, resume_data=None) -> dict:
    """When Gemini fails, return a basic but valid structure using simple heuristics."""
    # Basic extraction from resume_text (very naive)
    lines = [l.strip() for l in resume_text.split('\n') if l.strip()]
    name = lines[0] if lines else "Unknown"
    email_match = re.search(r'[\w.-]+@[\w.-]+', resume_text)
    email = email_match.group(0) if email_match else ""

    # Determine if JD is provided
    jd_provided = bool(job_description and len(job_description) > 50)

    if jd_provided:
        # Dummy scoring
        ats_score = 65
        overall_rating = "Average"
        matched_skills = ["Python", "JavaScript"]  # just examples
        missing_skills = ["AWS", "Docker"]
        strengths = ["Clear work history"]
        weaknesses = ["Missing cloud skills"]
        recommendations = ["Add more quantifiable achievements"]
        hiring_recommendation = "Consider with training"
    else:
        ats_score = 70
        overall_rating = "Good"
        matched_skills = []
        missing_skills = []
        strengths = ["Good contact info", "Relevant experience"]
        weaknesses = ["No project section"]
        recommendations = ["Add a projects section"]
        hiring_recommendation = ""

    return {
        "resume_data": {
            "name": name,
            "email": email,
            "phone": "",
            "location": "",
            "linkedin": "",
            "github": "",
            "portfolio": "",
            "summary": "",
            "total_experience_years": 3,
            "technical_skills": ["Python", "JavaScript", "React"] if jd_provided else ["Python"],
            "soft_skills": ["Communication", "Teamwork"],
            "education": [{"degree": "B.Sc. Computer Science", "institution": "University", "year": "2020"}],
            "experience": [
                {"company": "Tech Corp", "designation": "Developer", "duration": "2021-2023", "description": "Built web apps"}
            ],
            "projects": [],
            "certifications": [],
            "achievements": [],
            "languages": ["English"],
            "keywords": ["Python", "React"]
        },
        "ats_analysis": {
            "job_description_provided": jd_provided,
            "ats_score": ats_score,
            "overall_rating": overall_rating,
            "matching_keywords": ["Python", "JavaScript"] if jd_provided else [],
            "missing_keywords": ["AWS"] if jd_provided else [],
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "experience_match_percentage": 60 if jd_provided else 0,
            "education_match_percentage": 50 if jd_provided else 0,
            "project_match_percentage": 40 if jd_provided else 0,
            "certification_match_percentage": 30 if jd_provided else 0,
            "contact_score": 70,
            "skills_score": 65,
            "experience_score": 60,
            "projects_score": 40,
            "education_score": 70,
            "certification_score": 30,
            "keyword_score": 55,
            "formatting_score": 70,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "missing_sections": ["Projects", "Certifications"],
            "recommendations": recommendations,
            "resume_summary": "Candidate has relevant technical skills but lacks cloud experience.",
            "hiring_recommendation": hiring_recommendation,
            "ats_ready": ats_score >= 60
        }
    }

# ----------------------------------------------------------------------
# Helper: build a default ATSCategoryScores from an ats_analysis dict
# ----------------------------------------------------------------------
def _build_category_scores(ats: dict) -> ATSCategoryScores:
    return ATSCategoryScores(
        skills_match=int(ats.get("skills_score", 50)),
        experience_relevance=int(ats.get("experience_score", 50)),
        keyword_density=int(ats.get("keyword_score", 50)),
        education_certifications=int(max(ats.get("education_score", 50), ats.get("certification_score", 50))),
        formatting_completeness=int(ats.get("formatting_score", 50)),
    )

# ----------------------------------------------------------------------
# Updated endpoint
# ----------------------------------------------------------------------
@router.post("/analyze", response_model=MatchAnalysisResponse)
async def analyze_match_score(
    payload: MatchAnalysisRequest,
    db=Depends(get_database),
):
    """
    Enhanced ATS analysis that returns both the new detailed schema and
    the legacy fields required by the current frontend.
    Also runs Llama-based JD skill extraction to produce gap_skills.
    """
    # Build resume text from payload
    resume_text = (payload.resume_raw_text or "").strip()
    if not resume_text and payload.resume:
        parts = []
        if payload.resume.name:
            parts.append(f"Name: {payload.resume.name}")
        if payload.resume.email:
            parts.append(f"Email: {payload.resume.email}")
        parts.append("\nSKILLS:")
        for s in payload.resume.skills:
            parts.append(f"  - {s.name}")
        parts.append("\nEXPERIENCE:")
        for e in payload.resume.experience:
            parts.append(f"  {e.role} at {e.company} ({e.duration})\n    {e.details}")
        resume_text = "\n".join(parts)

    job_description = payload.job_description.strip()

    # ── Run detailed ATS analysis (Gemini or fallback) ────────────────────────
    try:
        if not IS_GEMINI_MOCK:
            detailed_result = run_detailed_ats_analysis(resume_text, job_description)
        else:
            detailed_result = fallback_detailed_analysis(resume_text, job_description, payload.resume)
    except Exception as e:
        logger.error(f"Detailed ATS analysis failed: {e}")
        detailed_result = fallback_detailed_analysis(resume_text, job_description, payload.resume)

    # Extract core fields from the detailed result
    ats = detailed_result.get("ats_analysis", {})
    resume_data_parsed = detailed_result.get("resume_data", {})

    # ── ATS Score Safety Rule: no JD → resume-only readiness response ─────────
    if not job_description:
        readiness_score = int(ats.get("ats_score", 0))
        readiness_category_scores = _build_category_scores(ats)
        resume_skills_only = [
            s for s in resume_data_parsed.get("technical_skills", []) if isinstance(s, str)
        ]
        if not resume_skills_only and payload.resume:
            resume_skills_only = [s.name for s in payload.resume.skills]
        return MatchAnalysisResponse(
            match_score=readiness_score,
            category_scores=readiness_category_scores,
            matched_keywords=[],
            missing_keywords=[],
            suggestions=ats.get("recommendations", [])[:5],
            missing_terms=[],
            is_ai_powered=not IS_GEMINI_MOCK,
            resume_skills=deduplicate_normalized_list(resume_skills_only),
            jd_skills=[],
            matched_skills=[],
            missing_skills=[],
            gap_skills=[],
        )

    # ── Call B: JD skill extraction via Llama ─────────────────────────────────
    jd_skills: list[str] = []
    jd_soft_skills: list[str] = []
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
            jd_soft_skills = normalized_jd_soft
            logger.info(f"Llama extracted {len(jd_skills)} JD skills and {len(jd_soft_skills)} JD soft skills.")
            
            # Save for debugging
            with open("jd_full_parse.json", "w", encoding="utf-8") as f:
                json.dump(parsed_jd_final, f, indent=4)
        except Exception as e:
            logger.error(f"Llama JD skill extraction failed: {e}")
            jd_skills = deduplicate_normalized_list([normalize_technical_skill(str(k)) for k in ats.get("missing_skills", []) + ats.get("missing_keywords", [])])
    else:
        jd_skills = deduplicate_normalized_list([normalize_technical_skill(str(k)) for k in ats.get("missing_skills", []) + ats.get("missing_keywords", [])])

    # ── Resume skills: prefer Gemini's technical_skills, fall back to payload skills ──
    raw_resume_skills: list[str] = []
    raw_resume_soft_skills: list[str] = []
    
    if "normalized" in resume_data_parsed and isinstance(resume_data_parsed["normalized"], dict):
        raw_resume_skills = resume_data_parsed["normalized"].get("technical_skills", [])
        raw_resume_soft_skills = resume_data_parsed["normalized"].get("soft_skills", [])
    else:
        parsed_tech = resume_data_parsed.get("technical_skills", [])
        if isinstance(parsed_tech, list) and parsed_tech:
            raw_resume_skills = [s for s in parsed_tech if isinstance(s, str)]
            
        parsed_soft = resume_data_parsed.get("soft_skills", [])
        if isinstance(parsed_soft, list) and parsed_soft:
            raw_resume_soft_skills = [s for s in parsed_soft if isinstance(s, str)]

    # ALWAYS merge the skills from the initial resume parse payload to ensure no skills are dropped during re-parse
    if payload.resume and payload.resume.skills:
        payload_skills = [s.name for s in payload.resume.skills if s.name]
        raw_resume_skills.extend(payload_skills)
            
    resume_skills = deduplicate_normalized_list([normalize_technical_skill(s) for s in raw_resume_skills])
    resume_soft_skills = deduplicate_normalized_list([normalize_soft_skill(s) for s in raw_resume_soft_skills])

    # Inject normalized skills back into resume_data_parsed so the mathematical ATS formula sees everything
    if "normalized" not in resume_data_parsed or not isinstance(resume_data_parsed["normalized"], dict):
        resume_data_parsed["normalized"] = {}
    resume_data_parsed["normalized"]["technical_skills"] = resume_skills
    resume_data_parsed["normalized"]["soft_skills"] = resume_soft_skills

    # Wrap the root fields into a "raw" dictionary to match the schema expected by calculate_comprehensive_ats_score
    if "raw" not in resume_data_parsed:
        resume_data_parsed["raw"] = {k: v for k, v in resume_data_parsed.items() if k not in ("normalized", "raw")}

    # ── Set-difference gap computation ───────────────────────────────────────
    resume_set = {s.lower() for s in resume_skills}
    jd_lower_map = {s.lower(): s for s in jd_skills}  # lowercase → canonical
    missing_skills = [jd_lower_map[k] for k in jd_lower_map if k not in resume_set]
    matched_skills = [jd_lower_map[k] for k in jd_lower_map if k in resume_set]
    
    resume_soft_set = {s.lower() for s in resume_soft_skills}
    jd_soft_lower_map = {s.lower(): s for s in jd_soft_skills}
    missing_soft_skills = [jd_soft_lower_map[k] for k in jd_soft_lower_map if k not in resume_soft_set]

    # ── Build response structure (using deterministic scoring) ────────────────
    is_ai_powered = not IS_GEMINI_MOCK

    if parsed_jd_final:
        deterministic_ats = calculate_comprehensive_ats_score(resume_data_parsed, parsed_jd_final)
        match_score = deterministic_ats.get("ats_score", 0)
        category_scores_dict = deterministic_ats.get("breakdown", {})
        category_scores = ATSCategoryScores(
            skills_match=category_scores_dict.get("skills_match", 0),
            experience_relevance=category_scores_dict.get("experience_relevance", 0),
            keyword_density=category_scores_dict.get("keyword_density", 0),
            education_certifications=category_scores_dict.get("education_certifications", 0),
            formatting_completeness=category_scores_dict.get("formatting_completeness", 0)
        )
    else:
        # Fallback to AI-generated or mock score if no JD
        match_score = int(ats.get("ats_score", 0))
        category_scores = _build_category_scores(ats)

    # Use ONLY the set-difference computed matched_skills/missing_skills for keyword lists.
    # This guarantees the displayed keywords are strictly JD ∩ Resume and JD − Resume,
    # never generic AI-recommended skills from Gemini's analysis.
    if jd_skills:
        # JD skills were extracted — use the set-diff results exclusively
        matched_keywords = deduplicate_normalized_list(matched_skills)
        missing_keywords = deduplicate_normalized_list(missing_skills)
    elif ats.get("job_description_provided"):
        # Fallback to Gemini analysis fields when Groq JD extraction was unavailable
        matched_keywords = deduplicate_normalized_list(ats.get("matched_skills", []) + ats.get("matching_keywords", []))
        missing_keywords = deduplicate_normalized_list(ats.get("missing_skills", []) + ats.get("missing_keywords", []))
    else:
        matched_keywords = deduplicate_normalized_list(ats.get("matching_keywords", []))
        missing_keywords = deduplicate_normalized_list(ats.get("missing_keywords", []))

    suggestions = ats.get("recommendations", [])
    recommendation_markdown = None

    if missing_skills or missing_soft_skills:
        # Call Gemini for a personalized recommendation based on the gaps
        import asyncio
        recommendation_markdown = await asyncio.to_thread(
            get_personalized_recommendation, 
            missing_skills, 
            missing_soft_skills
        )

    # ── Deduplicate all skill lists before returning ──────────────────────────
    resume_skills = deduplicate_normalized_list(resume_skills)
    jd_skills = deduplicate_normalized_list(jd_skills)
    matched_skills = deduplicate_normalized_list(matched_skills)
    missing_skills = deduplicate_normalized_list(missing_skills)
    matched_keywords = deduplicate_normalized_list(matched_keywords)
    missing_keywords = deduplicate_normalized_list(missing_keywords)

    # ── Debug logging to verify the ATS calculation pipeline ─────────────────
    logger.debug("RESUME SKILLS: %s", resume_skills)
    logger.debug("JD SKILLS: %s", jd_skills)
    logger.debug("MATCHED SKILLS: %s", matched_skills)
    logger.debug("MISSING SKILLS: %s", missing_skills)

    # ── Persist the detailed result in DB ─────────────────────────────────────
    if db is not None:
        try:
            await db["detailed_ats_logs"].insert_one({
                "timestamp": datetime.now(timezone.utc),
                "job_description_snippet": job_description[:200],
                "detailed_result": detailed_result,
                "is_ai_powered": is_ai_powered,
                "jd_skills": jd_skills,
                "missing_skills": missing_skills,
            })
        except Exception as e:
            logger.warning(f"Failed to store detailed ATS log: {e}")

    return MatchAnalysisResponse(
        match_score=match_score,
        category_scores=category_scores,
        matched_keywords=matched_keywords[:15],
        missing_keywords=missing_keywords[:15],
        suggestions=suggestions[:5],
        recommendation_markdown=recommendation_markdown,
        missing_terms=[],
        is_ai_powered=is_ai_powered,
        resume_skills=resume_skills,
        jd_skills=jd_skills,
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        gap_skills=missing_skills,  # backward compat alias
        parsed_resume=resume_data_parsed,
        parsed_jd=parsed_jd_final or {},
    )

@router.post("/simulate_score", response_model=SimulateScoreResponse)
async def simulate_score(payload: SimulateScoreRequest):
    """
    Lightweight endpoint to instantly recalculate the ATS score
    when the frontend simulator injects temporary skills.
    """
    import copy
    
    # Deep copy to avoid mutating the original
    simulated_resume = copy.deepcopy(payload.parsed_resume)
    
    # Inject simulated skills into the normalized technical skills array
    if "normalized" not in simulated_resume or not isinstance(simulated_resume["normalized"], dict):
        simulated_resume["normalized"] = {}
    
    existing_tech = simulated_resume["normalized"].get("technical_skills", [])
    if not existing_tech:
        existing_tech = simulated_resume.get("technical_skills", [])
        if not existing_tech:
            existing_tech = simulated_resume.get("raw", {}).get("technical_skills", [])

    simulated_resume["normalized"]["technical_skills"] = existing_tech + payload.simulated_technical_skills
    
    # Run the exact mathematical engine
    deterministic_ats = calculate_comprehensive_ats_score(simulated_resume, payload.parsed_jd)
    
    category_scores_dict = deterministic_ats.get("breakdown", {})
    category_scores = ATSCategoryScores(
        skills_match=category_scores_dict.get("skills_match", 0),
        experience_relevance=category_scores_dict.get("experience_relevance", 0),
        keyword_density=category_scores_dict.get("keyword_density", 0),
        education_certifications=category_scores_dict.get("education_certifications", 0),
        formatting_completeness=category_scores_dict.get("formatting_completeness", 0)
    )
    
    return SimulateScoreResponse(
        match_score=deterministic_ats.get("ats_score", 0),
        category_scores=category_scores
    )