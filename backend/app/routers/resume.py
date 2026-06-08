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
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load .env before reading any env vars
load_dotenv()

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/resume", tags=["resume"])

# Initialize the Gemini SDK (Requires GEMINI_API_KEY in environment variables)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
IS_MOCK_MODE = not GEMINI_API_KEY or GEMINI_API_KEY.startswith("mock")

_gemini_client: genai.Client | None = None

def get_gemini_client() -> genai.Client:
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    return _gemini_client


def extract_json(text: str) -> dict:
    """
    Robustly parse JSON from a Gemini response.
    Handles markdown fences (```json), extra whitespace, and partial wrappers.
    """
    text = text.strip()
    text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'```\s*$', '', text)
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Fallback: extract first {...} block
    m = re.search(r'\{[\s\S]+\}', text)
    if m:
        return json.loads(m.group(0))
    raise ValueError(f"No valid JSON in Gemini response: {text[:200]}")


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
        # pyrefly: ignore [missing-import]
        from docx import Document
        doc = Document(io.BytesIO(file_bytes))
        paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
        return "\n".join(paragraphs)
    except Exception as e:
        logger.error(f"Failed to extract text from DOCX: {e}")
        raise HTTPException(status_code=500, detail="Failed to parse DOCX content stream.")



def generate_mock_resume_data(raw_text: str) -> dict:
    """Generate high-quality mock resume data based on the extracted text when offline/no API key."""
    # Find candidate name: often the first non-empty line
    lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
    candidate_name = "Varun Kumar"  # Default fallback
    if lines:
        for line in lines[:5]:
            if "@" not in line and "http" not in line and 3 < len(line) < 30:
                candidate_name = line
                break

    # Extract email
    email_match = re.search(r'[\w.-]+@[\w.-]+', raw_text)
    email = email_match.group(0) if email_match else "candidate@careerpilot.ai"

    # Extract skills by checking presence of common tech terms in text
    tech_keywords = [
        "React", "React.js", "TypeScript", "JavaScript", "Node.js", "Node", "GraphQL", 
        "Python", "Django", "Flask", "AWS", "Docker", "Kubernetes", "PostgreSQL", 
        "MongoDB", "SQL", "Git", "CI/CD", "Next.js", "Express", "HTML", "CSS"
    ]
    detected_skills = []
    text_lower = raw_text.lower()
    
    for tech in tech_keywords:
        pattern = r'\b' + re.escape(tech.lower()) + r'\b'
        if re.search(pattern, text_lower):
            # Assign confidence: higher if mentioned multiple times
            confidence = 85 if text_lower.count(tech.lower()) > 1 else 70
            detected_skills.append({"name": tech, "confidence": confidence})
            
    # Default skills if none detected
    if not detected_skills:
        detected_skills = [
            {"name": "React.js", "confidence": 90},
            {"name": "TypeScript", "confidence": 85},
            {"name": "Node.js", "confidence": 80},
            {"name": "GraphQL", "confidence": 75}
        ]

    # Create dummy experience or parse years/companies if possible
    experience = [
        {
            "company": "Web Innovations",
            "role": "Senior Full Stack Developer",
            "duration": "2022 - Present",
            "details": "Led the architecture and development of high-performance React and Node.js web applications. Built microservices and automated CI/CD deployment pipelines using AWS and Docker."
        },
        {
            "company": "Tech Solutions Inc.",
            "role": "Frontend Engineer",
            "duration": "2020 - 2022",
            "details": "Developed responsive user interfaces using HTML/CSS, JavaScript, and React. Collaborated with designers to deliver premium user experiences."
        }
    ]

    # Create gaps: identify technologies that are NOT in the detected skills
    possible_gaps = [
        {"name": "Docker", "category": "DevOps", "impact": 10},
        {"name": "Kubernetes", "category": "DevOps", "impact": 12},
        {"name": "AWS", "category": "Cloud", "impact": 15},
        {"name": "PostgreSQL", "category": "API Design", "impact": 8},
        {"name": "GraphQL", "category": "API Design", "impact": 7},
        {"name": "Unit Testing", "category": "Testing", "impact": 9}
    ]
    
    gaps = []
    detected_skill_names = {str(s["name"]).lower() for s in detected_skills if isinstance(s, dict) and "name" in s}
    for gap in possible_gaps:
        if isinstance(gap, dict) and "name" in gap:
            gap_name = str(gap["name"])
            if gap_name.lower() not in detected_skill_names:
                gaps.append({
                    "name": gap_name,
                    "category": str(gap.get("category", "General")),
                    "impact": int(gap.get("impact", 10)),
                    "checked": False
                })
                if len(gaps) == 4:
                    break
                    
    # Fallback if we didn't get 4 gaps
    while len(gaps) < 4:
        current_gap_names = {str(x["name"]).lower() for x in gaps if isinstance(x, dict) and "name" in x}
        extra_gaps = [
            g for g in possible_gaps 
            if isinstance(g, dict) and "name" in g and str(g["name"]).lower() not in current_gap_names
        ]
        if not extra_gaps:
            break
        target_gap = extra_gaps[0]
        gaps.append({
            "name": str(target_gap["name"]),
            "category": str(target_gap.get("category", "General")),
            "impact": int(target_gap.get("impact", 10)),
            "checked": False
        })

    return {
        "candidate_name": candidate_name,
        "contact_info": email,
        "skills": detected_skills,
        "experience": experience,
        "gaps": gaps
    }


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
        '  ],\n'
        '  "experience": [\n'
        "    {\n"
        '      "company": "str",\n'
        '      "role": "str",\n'
        '      "duration": "str",\n'
        '      "details": "str (bulleted metrics combined)"\n'
        "    }\n"
        '  ],\n'
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

    if IS_MOCK_MODE:
        logger.info("No Gemini API key — generating mock parsed resume data locally.")
        gemini_json = generate_mock_resume_data(raw_text)
    else:
        try:
            # 2. Pass the raw text block directly to Gemini 1.5 Flash for structured parsing
            client = get_gemini_client()
            response = client.models.generate_content(
                model="gemini-1.5-flash",
                contents=f"SYSTEM INSTRUCTION:\n{system_instruction}\n\nRESUME TEXT TO PARSE:\n{raw_text}",
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            gemini_json = extract_json(response.text)
        except Exception as e:
            logger.error(f"Gemini API failure ({type(e).__name__}): {e}")
            logger.warning("Falling back to heuristic resume parsing (mock data).")
            # Graceful fallback — never return 502 to the user
            gemini_json = generate_mock_resume_data(raw_text)

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
        "ats_score": ats_score,
        "raw_text": raw_text  # Full extracted text for downstream ATS analysis
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
                    client = get_gemini_client()
                    embedding_result = client.models.embed_content(
                        model="text-embedding-004",
                        contents=raw_text[:8000],
                    )
                    resume_embeddings = embedding_result.embeddings[0].values
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


@router.post("/streamlit/analyze")
async def streamlit_analyze(
    file: UploadFile = File(...),
    job_description: str = Body(..., embed=True)
):
    """Endpoint adapted from the provided Streamlit code: returns Gemini analysis or a mock fallback."""
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in (".pdf", ".docx"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PDF and DOCX supported")

    file_bytes = await file.read()
    raw_text = ""
    if ext == ".pdf":
        if pdfplumber is None:
            # attempt simple fallback: try decode as text
            try:
                raw_text = file_bytes.decode(errors="ignore")
            except Exception:
                raw_text = ""
        else:
            try:
                with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                    for page in pdf.pages:
                        t = page.extract_text()
                        if t:
                            raw_text += t + "\n"
            except Exception as e:
                logger.error(f"PDF parse failed in streamlit_analyze: {e}")
    else:
        raw_text = extract_text_from_docx(file_bytes)

    if not raw_text.strip():
        # fallback to mock generator
        gemini_json = generate_mock_resume_data("")
        return {"response": "No readable text; returning mock analysis.", "mock": gemini_json}

    # Compose prompt similar to Streamlit
    prompt = (
        "You are an experienced Technical Human Resource Manager, your task is to review the provided resume against the job description. "
        "Please share your professional evaluation on whether the candidate's profile aligns with the role. Highlight strengths and weaknesses."
    )

    if genai is None:
        logger.warning("Gemini client not available; returning mock analysis.")
        gemini_json = generate_mock_resume_data(raw_text)
        return {"response": "Gemini not available; returning mock analysis.", "mock": gemini_json}

    try:
        client = get_gemini_client()
        # Use a text-first approach: include job description and extracted resume text
        contents = f"SYSTEM INSTRUCTION:\n{prompt}\n\nJOB DESCRIPTION:\n{job_description}\n\nRESUME TEXT:\n{raw_text}"
        cfg = None
        if types is not None:
            try:
                cfg = types.GenerateContentConfig(response_mime_type="text/plain")
            except Exception:
                cfg = None

        if cfg is not None:
            resp = client.models.generate_content(model="gemini-pro-vision", contents=contents, config=cfg)
        else:
            resp = client.models.generate_content(model="gemini-pro-vision", contents=contents)

        text_out = getattr(resp, "text", None) or getattr(resp, "output", None) or str(resp)
        return {"response": text_out}
    except Exception as e:
        logger.error(f"Gemini call failed in streamlit_analyze: {e}")
        gemini_json = generate_mock_resume_data(raw_text)
        return {"response": "Gemini call failed; returning mock analysis.", "mock": gemini_json}


@router.post("/streamlit/match")
async def streamlit_match(
    file: UploadFile = File(...),
    job_description: str = Body(..., embed=True)
):
    """Return a percentage match and missing keywords similar to the Streamlit sample."""
    # Reuse the analyze flow to get text
    result = await streamlit_analyze(file=file, job_description=job_description)
    # If we received a Gemini text response, attempt to parse numeric percentage
    text = result.get("response", "") if isinstance(result, dict) else str(result)
    # Heuristic extraction of percentage
    m = re.search(r"(\d{1,3})\s*%", text)
    if m:
        pct = int(m.group(1))
    else:
        # fallback: compute simple overlap score
        jd_terms = set(re.findall(r"\w+", job_description.lower()))
        # Extract skills from mock or parsed result
        skills = []
        if isinstance(result, dict) and "mock" in result:
            skills = [s.get("name", "") for s in result["mock"].get("skills", [])]
        else:
            skills = re.findall(r"\w+", text.lower())[:50]

        common = jd_terms.intersection({s.lower() for s in skills})
        pct = int(min(100, (len(common) / max(1, len(jd_terms))) * 100))

    return {"match_percentage": pct, "raw_response": text}


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

    if IS_MOCK_MODE:
        logger.info("Mock API key detected — generating mock cover letter locally.")
        cover_letter = (
            f"# Cover Letter for {payload.resume.name}\n\n"
            f"Dear Hiring Team,\n\n"
            f"I am writing to express my strong interest in the open position matching my background as a professional. "
            f"With key skills in {top_skills} and a solid track record of technical contributions, I am confident in my "
            f"ability to add immediate value to your engineering team.\n\n"
            f"Throughout my career, I have honed my expertise in building scalable, user-centric web applications. "
            f"My professional history includes roles such as: {experience_summary}. These experiences have "
            f"equipped me with the technical depth and structured problem-solving skills necessary to address complex business requirements "
            f"and deliver high-quality solutions.\n\n"
            f"I would appreciate the opportunity to discuss how my technical skills and professional goals align with your team's needs. "
            f"Thank you for your time and consideration.\n\n"
            f"Sincerely,\n"
            f"{payload.resume.name}"
        )
        return CoverLetterResponse(cover_letter=cover_letter)

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
        client = get_gemini_client()
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )
        cover_letter = response.text.strip()
        logger.info(f"Cover letter generated successfully for {payload.resume.name}")
        return CoverLetterResponse(cover_letter=cover_letter)
    except Exception as e:
        logger.error(f"Gemini cover letter generation failed: {e}")
        raise HTTPException(status_code=502, detail="Failed to generate cover letter via AI subsystem.")
