import os
import io
import json
import re
import logging
from datetime import datetime
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


def calculate_ats_score(experience_list: list) -> int:
    """Local heuristic rule-based processing step to calculate an ATS score out of 100."""
    score = 40  # Base starting score
    active_verbs = {"led", "developed", "engineered", "built", "managed", "created", "designed", "architected", "optimized", "increased", "decreased", "improved", "spearheaded", "orchestrated"}

    # Regex to find metrics like numbers, percentages, or dollar values
    metrics_pattern = re.compile(r'(\d+%|\$\d+|\b\d+\s*(?:million|billion|k|m)\b)', re.IGNORECASE)

    for exp in experience_list:
        details = exp.get("details", "").lower()

        # Heavily reward explicit quantitative metrics
        if metrics_pattern.search(details):
            score += 15
        elif re.search(r'\d+', details):
            score += 5

        # Reward active action verbs
        words = set(details.split())
        if words.intersection(active_verbs):
            score += 10

    # Cap maximum structural score at 100
    return min(score, 100)


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

    ext = os.path.splitext(file.filename)[1].lower()
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
        "You are an expert HR parser system. Extract the following strictly from the raw resume text into this exact JSON schema:\n"
        "{\n"
        '  "candidate_name": "string",\n'
        '  "contact_info": "string (email or phone)",\n'
        '  "skills": {\n'
        '    "languages": ["str"],\n'
        '    "frameworks": ["str"],\n'
        '    "developer_tools": ["str"],\n'
        '    "methodologies": ["str"]\n'
        '  },\n'
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
    ats_score = calculate_ats_score(extracted_experience)

    # Flatten skills to align with the ResumeDataSchema
    flattened_skills = []
    raw_skills = gemini_json.get("skills", {})
    for category, items in raw_skills.items():
        if isinstance(items, list):
            for item in items:
                # Simulated match score for frontend display logic
                flattened_skills.append({"name": str(item), "match": min(80 + len(str(item)), 100)})

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
        "skills": flattened_skills[:10],  # Limiting to top 10 for UI responsiveness
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
                "uploaded_at": datetime.utcnow(),
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
