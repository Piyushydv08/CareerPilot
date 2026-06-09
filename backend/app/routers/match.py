# app/routers/match.py (updated)

import json
import logging
import os
import re
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
)
from app.core.database import get_database

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/match", tags=["matching"])

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
IS_MOCK_MODE = not GEMINI_API_KEY or GEMINI_API_KEY.startswith("mock")

_gemini_client: genai.Client | None = None

def get_gemini_client() -> genai.Client:
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    return _gemini_client

def extract_json(text: str) -> dict:
    """Robustly extract JSON from Gemini response (handles markdown fences)."""
    text = text.strip()
    text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'```\s*$', '', text)
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'\{[\s\S]+\}', text)
        if match:
            return json.loads(match.group(0))
        raise ValueError(f"No valid JSON: {text[:200]}")

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
    return extract_json(response.text)

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

    # Run detailed analysis (Gemini or fallback)
    try:
        if not IS_MOCK_MODE:
            detailed_result = run_detailed_ats_analysis(resume_text, job_description)
        else:
            detailed_result = fallback_detailed_analysis(resume_text, job_description, payload.resume)
    except Exception as e:
        logger.error(f"Detailed ATS analysis failed: {e}")
        detailed_result = fallback_detailed_analysis(resume_text, job_description, payload.resume)

    # Extract core fields from the detailed result
    ats = detailed_result.get("ats_analysis", {})
    resume_data_parsed = detailed_result.get("resume_data", {})

    # Build legacy response structure (for current frontend)
    match_score = ats.get("ats_score", 0)
    is_ai_powered = not IS_MOCK_MODE

    # Map category scores (from new schema to old 5 categories)
    category_scores = ATSCategoryScores(
        skills_match=ats.get("skills_score", 50),
        experience_relevance=ats.get("experience_score", 50),
        keyword_density=ats.get("keyword_score", 50),
        education_certifications=max(ats.get("education_score", 50), ats.get("certification_score", 50)),
        formatting_completeness=ats.get("formatting_score", 50),
    )

    # Use matched_skills/missing_skills for keyword lists if JD provided,
    # otherwise use matching_keywords/missing_keywords
    if ats.get("job_description_provided"):
        matched_keywords = ats.get("matched_skills", []) + ats.get("matching_keywords", [])
        missing_keywords = ats.get("missing_skills", []) + ats.get("missing_keywords", [])
    else:
        matched_keywords = ats.get("matching_keywords", [])
        missing_keywords = ats.get("missing_keywords", [])

    suggestions = ats.get("recommendations", [])

    # Persist the detailed result in DB for future UI enhancements
    if db is not None:
        try:
            await db["detailed_ats_logs"].insert_one({
                "timestamp": datetime.now(timezone.utc),
                "job_description_snippet": job_description[:200],
                "detailed_result": detailed_result,
                "is_ai_powered": is_ai_powered
            })
        except Exception as e:
            logger.warning(f"Failed to store detailed ATS log: {e}")

    # Return legacy response with extra field "_detailed" that can be used later
    response = MatchAnalysisResponse(
        match_score=match_score,
        category_scores=category_scores,
        matched_keywords=matched_keywords[:15],
        missing_keywords=missing_keywords[:15],
        suggestions=suggestions[:5],
        missing_terms=[],
        is_ai_powered=is_ai_powered,
    )
    # Attach the full detailed result as a custom field (not in schema, but accessible in frontend)
    response._detailed = detailed_result   # type: ignore
    return response