import os
import io
import json
import re
import logging
from datetime import datetime
from fastapi import APIRouter, File, UploadFile, Depends, HTTPException, status
from app.models.schemas import ResumeDataSchema, SkillSchema, ExperienceSchema, SkillGapSchema
from app.core.database import get_database
import pdfplumber
import google.generativeai as genai

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/resume", tags=["resume"])

# Initialize the Gemini SDK (Requires GEMINI_API_KEY in environment variables)
genai.configure(api_key=os.environ.get("GEMINI_API_KEY", "mock-key-replace-in-production"))

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

@router.post("/upload", response_model=ResumeDataSchema)
async def upload_resume(
    file: UploadFile = File(...),
    db = Depends(get_database)
):
    """Multipart parser uploading resume details asynchronously, extracting via pdfplumber and Gemini."""
    logger.info(f"Received resume upload task for file: {file.filename}")
    
    ext = os.path.splitext(file.filename)[1].lower()
    if ext != ".pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF documents are supported for advanced parser analysis."
        )

    file_bytes = await file.read()
    raw_text = ""
    
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    raw_text += page_text + "\n"
    except Exception as e:
        logger.error(f"Failed to parse PDF document cleanly: {e}")
        raise HTTPException(status_code=500, detail="Failed to parse PDF content stream.")

    if not raw_text.strip():
        raise HTTPException(status_code=400, detail="No readable text found in the PDF. Could be an image-only file.")

    # 3. Draft precise constraining system prompt
    system_instruction = (
        "You are an expert HR parser system. Extract the following strictly from the raw resume text into this exact JSON schema:\n"
        "{\n"
        '  "candidate_name": "string",\n'
        '  "contact_info": "string",\n'
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
        "  ]\n"
        "}\n"
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

    # 4. Execute a local heuristic rule-based processing step for ATS structural metric score
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

    parsed_data = {
        "name": gemini_json.get("candidate_name", "Unknown Candidate"),
        "email": gemini_json.get("contact_info", "No Contact Info Found"),
        "skills": flattened_skills[:10], # Limiting to top 10 for UI responsiveness
        "experience": extracted_experience,
        "gaps": [
            {"name": "System Architecture", "category": "Cloud Design", "impact": 15, "checked": False}
        ],
        "ats_score": ats_score
    }

    # Asynchronous metadata logging to MongoDB Atlas
    if db is not None:
        try:
            document_record = {
                "filename": file.filename,
                "content_type": file.content_type,
                "uploaded_at": datetime.utcnow(),
                "parsed_data": parsed_data,
                "raw_extracted_text": raw_text
            }
            result = await db["resumes"].insert_one(document_record)
            logger.info(f"Resume vector metadata inserted to Atlas under index: {result.inserted_id}")
        except Exception as e:
            logger.error(f"Failed to commit parsed resume data to MongoDB Atlas: {e}")

    return parsed_data
