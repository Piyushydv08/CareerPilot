import os
import io
import json
import re
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, File, UploadFile, Depends, HTTPException, status, Body
from app.models.schemas import ResumeDataSchema, SkillSchema, ExperienceSchema, SkillGapSchema, CoverLetterRequest, CoverLetterResponse
from app.core.database import get_database
import pdfplumber
import google.generativeai as genai

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/resume", tags=["resume"])

# Initialize the Gemini SDK (Requires GEMINI_API_KEY in environment variables)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "mock-key-replace-in-production")
genai.configure(api_key=GEMINI_API_KEY)

# Flag: skip real API calls in offline/dev mode
IS_MOCK_MODE = GEMINI_API_KEY == "mock-key-replace-in-production"


def calculate_ats_score(gemini_json: dict) -> int:
    """
    Multi-dimensional ATS score (0-100) across five weighted pillars:
      1. Contact Information Completeness  — up to 10 pts
      2. Skills Breadth and Depth          — up to 25 pts
      3. Experience Quality                — up to 35 pts
      4. Resume Sections Completeness      — up to 15 pts
      5. Experience Diversity              — up to 15 pts
    """
    total = 0

    # ── 1. Contact Information Completeness (10 pts) ──────────────────────────
    contact = gemini_json.get("contact_info", "")
    has_email = bool(re.search(r'[\w.-]+@[\w.-]+', contact))
    has_phone = bool(re.search(r'\+?[\d\s\-()]{7,}', contact))
    if has_email and has_phone:
        total += 10
    elif has_email or has_phone:
        total += 5

    # ── 2. Skills Breadth and Depth (25 pts) ──────────────────────────────────
    raw_skills = gemini_json.get("skills", [])
    if isinstance(raw_skills, list):
        # New flat schema: [{name, confidence}, ...]
        unique_skills = len({s["name"] for s in raw_skills if isinstance(s, dict) and s.get("name")})
    elif isinstance(raw_skills, dict):
        # Legacy nested schema fallback
        all_skill_names: set = set()
        for items in raw_skills.values():
            if isinstance(items, list):
                all_skill_names.update(str(i) for i in items)
        unique_skills = len(all_skill_names)
    else:
        unique_skills = 0

    if unique_skills >= 16:
        total += 25
    elif unique_skills >= 11:
        total += 20
    elif unique_skills >= 7:
        total += 15
    elif unique_skills >= 4:
        total += 10
    elif unique_skills >= 1:
        total += 5

    # ── 3. Experience Quality (35 pts) ────────────────────────────────────────
    experience_list = gemini_json.get("experience", [])
    active_verbs = {
        "led", "developed", "engineered", "built", "managed", "created", "designed",
        "architected", "optimized", "increased", "decreased", "improved", "spearheaded",
        "orchestrated", "deployed", "launched", "migrated", "automated", "reduced",
        "scaled", "integrated", "implemented", "delivered", "established", "streamlined"
    }
    metrics_pattern = re.compile(
        r'(\d+%|\$\d+|\d+\s*(?:million|billion|k|m)\b|\d+\s*(?:users|clients|requests|services|ms|seconds))',
        re.IGNORECASE
    )

    metrics_pts = 0
    verb_pts = 0
    bonus_pts = 0

    for exp in experience_list:
        details = exp.get("details", "").lower()
        words = set(details.split())
        has_metrics = bool(metrics_pattern.search(details))
        has_verb = bool(words.intersection(active_verbs))

        if has_metrics and metrics_pts < 18:
            metrics_pts = min(metrics_pts + 6, 18)
        if has_verb and verb_pts < 12:
            verb_pts = min(verb_pts + 4, 12)
        if has_metrics and has_verb and bonus_pts < 5:
            bonus_pts = min(bonus_pts + 2, 5)

    total += metrics_pts + verb_pts + bonus_pts

    # ── 4. Resume Sections Completeness (15 pts) ──────────────────────────────
    if len(experience_list) >= 1:
        total += 5
    if unique_skills >= 4:
        total += 5
    if gemini_json.get("candidate_name", "Unknown Candidate") != "Unknown Candidate":
        total += 5

    # ── 5. Experience Diversity (15 pts) ──────────────────────────────────────
    distinct_companies = len({exp.get("company", "") for exp in experience_list if exp.get("company", "")})
    if distinct_companies >= 3:
        total += 15
    elif distinct_companies == 2:
        total += 10
    elif distinct_companies == 1:
        total += 5

    return max(0, min(total, 100))



def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract plain text from a .docx file using python-docx."""
    try:
        from docx import Document
        doc = Document(io.BytesIO(file_bytes))
        paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
        return "\n".join(paragraphs)
    except Exception as e:
        logger.error(f"Failed to extract text from DOCX: {e}")
        raise HTTPException(status_code=500, detail="Failed to parse DOCX content stream.")


@router.post("/upload", response_model=ResumeDataSchema)
async def upload_resume(
    file: UploadFile = File(...),
    db = Depends(get_database)
):
    """Multipart parser uploading resume details asynchronously, extracting via pdfplumber/python-docx and Gemini."""
    logger.info(f"Received resume upload task for file: {file.filename}")

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in (".pdf", ".docx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF and DOCX documents are supported for advanced parser analysis."
        )

    file_bytes = await file.read()
    raw_text = ""

    # 1. Extract raw text from file based on extension
    if ext == ".pdf":
        try:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        raw_text += page_text + "\n"
        except Exception as e:
            logger.error(f"Failed to parse PDF document cleanly: {e}")
            raise HTTPException(status_code=500, detail="Failed to parse PDF content stream.")
    elif ext == ".docx":
        raw_text = extract_text_from_docx(file_bytes)

    if not raw_text.strip():
        raise HTTPException(status_code=400, detail="No readable text found in the file. Could be an image-only file.")

    # 1. Draft precise constraining system prompt including skill gaps extraction
    system_instruction = (
        "You are an expert HR parser and skills extraction system. Extract the following strictly from the raw resume text into this exact JSON schema:\n"
        "{\n"
        '  "candidate_name": "string",\n'
        '  "contact_info": "string (email or phone)",\n'
        '  "skills": [\n'
        "    {\n"
        '      "name": "str (clean skill name, e.g. Node.js, REST API Design, JWT Authentication)",\n'
        '      "confidence": <integer 1-100>\n'
        "    }\n"
        "  ],\n"
        '  "experience": [\n'
        "    {\n"
        '      "company": "str",\n'
        '      "role": "str",\n'
        '      "duration": "str",\n'
        '      "details": "str (bulleted metrics combined)"\n'
        "    }\n"
        "  ],\n"
        '  "gaps": [\n'
        "    {\n"
        '      "name": "str (skill gap name)",\n'
        '      "category": "str (e.g. Cloud, DevOps, API Design, Testing)",\n'
        '      "impact": <integer between 5 and 15>,\n'
        '      "checked": false\n'
        "    }\n"
        "  ]\n"
        "}\n"
        "\n"
        "SKILLS EXTRACTION RULES — follow all of these precisely:\n"
        "1. SCAN ALL SECTIONS: Education, Projects, Technical Skills, Work Experience, Achievements, and Certifications for any technology or tool mention.\n"
        "2. INCLUDE IMPLICIT SKILLS: If the candidate built something using a technology, that technology is a skill — even if it is not listed in a 'Skills' section. "
        "   Examples: 'built a backend with Node.js and Express.js' → Node.js, Express.js, REST API Design; "
        "   'implemented JWT-based auth' → JWT Authentication; 'used Socket.IO for real-time messaging' → Socket.IO, Real-Time Systems; "
        "   'deployed with Docker on AWS' → Docker, AWS; 'styled with Tailwind CSS' → Tailwind CSS.\n"
        "3. INFER FROM VERBS AND TOOL COMBINATIONS: 'implemented', 'built', 'designed', 'deployed', 'integrated', 'configured' all imply hands-on skill. "
        "   Infer logical companion skills (e.g., Express.js implies Node.js; Redux implies React.js).\n"
        "4. DEDUPLICATE: Treat near-duplicates as one skill with the highest applicable confidence "
        "   (e.g., React and React.js → React.js; Mongo and MongoDB → MongoDB).\n"
        "5. ASSIGN CONFIDENCE scores as follows:\n"
        "   - 90-100: Core technology used across multiple projects or central to work experience (e.g., main language, primary framework).\n"
        "   - 70-89: Used in at least one project or work experience entry with clear evidence.\n"
        "   - 50-69: Only listed in a skills section without supporting project/experience evidence.\n"
        "   - 30-49: Tangentially implied or inferred from a related tool — no direct mention.\n"
        "6. CLEAN NAMES: Use canonical, industry-standard names (e.g., 'Node.js' not 'nodejs', 'REST API Design' not 'restful apis').\n"
        "7. BE COMPREHENSIVE: Extract every technology that has any evidence of use. Do not limit the list.\n"
        "\n"
        "For the 'gaps' array: identify the top 4 most impactful skill gaps based on what is missing or weak compared to modern industry standards for the candidate's apparent role level. "
        "Each gap must have a unique name, a category, and an impact integer between 5 and 15 (higher = more critical). "
        "Return ONLY the raw JSON output without any markdown formatting or surrounding text."
    )

    try:
        # 2. Pass the raw text block directly to the Gemini API utilizing structured outputs
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(
            f"SYSTEM INSTRUCTION:\n{system_instruction}\n\nRESUME TEXT TO PARSE:\n{raw_text}",
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json"
            )
        )
        gemini_json = json.loads(response.text)
    except Exception as e:
        logger.error(f"Gemini API structural extraction failure: {e}")
        raise HTTPException(status_code=502, detail="Failed to structurally parse resume via AI subsystem.")

    # 3. Execute a local heuristic rule-based processing step for ATS structural metric score
    extracted_experience = gemini_json.get("experience", [])
    ats_score = calculate_ats_score(gemini_json)

    # Build skills list from the flat array returned by Gemini, using real confidence scores
    flattened_skills = []
    raw_skills = gemini_json.get("skills", [])
    if isinstance(raw_skills, list):
        for item in raw_skills:
            if isinstance(item, dict) and item.get("name"):
                confidence = max(1, min(100, int(item.get("confidence", 50))))
                flattened_skills.append({"name": str(item["name"]), "match": confidence})

    # 4. Extract Gemini-generated gaps (top 4, validated)
    raw_gaps = gemini_json.get("gaps", [])
    parsed_gaps = []
    for gap in raw_gaps[:4]:
        parsed_gaps.append({
            "name": str(gap.get("name", "Unknown Gap")),
            "category": str(gap.get("category", "General")),
            "impact": max(5, min(15, int(gap.get("impact", 8)))),
            "checked": False
        })

    parsed_data = {
        "name": gemini_json.get("candidate_name", "Unknown Candidate"),
        "email": gemini_json.get("contact_info", "No Contact Info Found"),
        "skills": flattened_skills,  # Full deduplicated skill list with Gemini-assigned confidence scores
        "experience": extracted_experience,
        "gaps": parsed_gaps,
        "ats_score": ats_score
    }

    # 5. Asynchronous metadata logging to MongoDB Atlas with embeddings
    if db is not None:
        try:
            document_record = {
                "filename": file.filename,
                "content_type": file.content_type,
                "uploaded_at": datetime.now(timezone.utc),
                "parsed_data": parsed_data,
                "raw_extracted_text": raw_text,
                "resume_embeddings": []
            }
            result = await db["resumes"].insert_one(document_record)
            mongo_id = result.inserted_id
            logger.info(f"Resume metadata inserted to Atlas under index: {mongo_id}")

            # Generate and store vector embeddings asynchronously
            if not IS_MOCK_MODE:
                try:
                    embedding_result = genai.embed_content(
                        model="models/text-embedding-004",
                        content=raw_text[:8000],  # Truncate to avoid token limits
                        task_type="retrieval_document"
                    )
                    resume_embeddings = embedding_result['embedding']
                    await db["resumes"].update_one(
                        {"_id": mongo_id},
                        {"$set": {"resume_embeddings": resume_embeddings}}
                    )
                    logger.info(f"Resume embeddings ({len(resume_embeddings)} dims) stored for document {mongo_id}")
                except Exception as e:
                    logger.error(f"Failed to generate/store resume embeddings: {e}")
        except Exception as e:
            logger.error(f"Failed to commit parsed resume data to MongoDB Atlas: {e}")

    return parsed_data


@router.post("/cover_letter", response_model=CoverLetterResponse)
async def generate_cover_letter(payload: CoverLetterRequest):
    """Generate a professional Markdown cover letter using Gemini 1.5 Flash."""
    logger.info(f"Generating cover letter for: {payload.resume.name}")

    # Build experience summary from resume data
    experience_summary = "; ".join([
        f"{exp.role} at {exp.company} ({exp.duration}): {exp.details[:100]}"
        for exp in payload.resume.experience
    ]) or "Not specified"

    top_skills = ", ".join([s.name for s in payload.resume.skills[:6]]) or "Not specified"

    prompt = (
        f"Write a professional cover letter for {payload.resume.name} applying to this role:\n"
        f"{payload.job_description}\n\n"
        f"Their experience: {experience_summary}\n"
        f"Their top skills: {top_skills}\n\n"
        "Format in Markdown. Write exactly 3 paragraphs. "
        "Do not use cliches like 'I am writing to express' or 'I am passionate about'. "
        "Do not use generic openers. Be specific, confident, and data-driven. "
        "Start with a compelling hook that references a specific achievement or skill. "
        "Return ONLY the Markdown cover letter text, nothing else."
    )

    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        cover_letter = response.text.strip()
        logger.info(f"Cover letter generated successfully for {payload.resume.name}")
        return CoverLetterResponse(cover_letter=cover_letter)
    except Exception as e:
        logger.error(f"Gemini cover letter generation failed: {e}")
        raise HTTPException(status_code=502, detail="Failed to generate cover letter via AI subsystem.")
