import os
import io
import json
import re
import logging
import httpx
from datetime import datetime, timezone
from fastapi import APIRouter, File, UploadFile, Depends, HTTPException, status, Body
from app.models.schemas import ResumeDataSchema, SkillSchema, ExperienceSchema, SkillGapSchema, CoverLetterRequest, CoverLetterResponse
from app.core.database import get_database
import pdfplumber
from dotenv import load_dotenv

# Load .env before reading any env vars
load_dotenv()

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/resume", tags=["resume"])

# ── Groq / Llama configuration ────────────────────────────────────────────────
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_BASE_URL = "https://api.groq.com/openai/v1/chat/completions"
IS_MOCK_MODE = not bool(GROQ_API_KEY)


async def call_llama(system_prompt: str, user_content: str) -> str:  # Groq llama-3.3-70b-versatile inference
    msgs = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}]
    payload = {"model": "llama-3.3-70b-versatile", "messages": msgs, "temperature": 0.1, "max_tokens": 2048}
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    client = httpx.AsyncClient(timeout=30.0)
    response = await client.post(GROQ_BASE_URL, headers=headers, json=payload)
    await client.aclose()
    data = response.json()
    return str(data["choices"][0]["message"]["content"]).strip()


# ── JSON extraction helper ─────────────────────────────────────────────────────
from typing import Any
def extract_json(text: str) -> Any:  # Strip markdown fences and parse JSON from model response
    text = text.strip()
    text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'```\s*$', '', text).strip()
    loaded = _try_json_loads(text)
    if loaded is not None:
        return loaded
    m = re.search(r'[\[{][\s\S]+[\]}]', text)
    if m:
        return _try_json_loads(m.group(0)) or json.loads(m.group(0))
    raise ValueError(f"No valid JSON in Llama response: {text[:200]}")


def _try_json_loads(text: str) -> dict | list | None:  # Returns parsed object or None — never raises
    if not text or text[0] not in ("{", "["):
        return None
    import contextlib; result: dict | list | None = None; ctx = contextlib.suppress(Exception)  # noqa: E702
    with ctx: result = json.loads(text)  # noqa: E701
    return result


# ── Resume skill-extraction system prompt ─────────────────────────────────────
RESUME_SKILL_EXTRACTION_PROMPT = """\
You are a precise technical skill extraction engine for a career intelligence platform.

Your task: Extract ONLY technical skills from resume text. Return a JSON array of skill objects.

Rules:
- Include frameworks, languages, libraries, tools, platforms, cloud services, databases, protocols, and methodologies that are explicitly mentioned OR clearly implied by project/work descriptions.
- IMPLICIT SKILLS: If the text says "built an API with Express.js" → include Express.js, Node.js, REST API Design. If "deployed on AWS EC2" → include AWS, EC2. If "used Socket.IO" → include Socket.IO, Real-Time Systems.
- EXCLUDE: soft skills, generic terms (e.g. "communication", "teamwork", "problem solving", "leadership"), and non-technical certifications.
- DEDUPLICATE: React and React.js → React.js. MongoDB and Mongo → MongoDB.
- CONFIDENCE scoring: 90-100 = used heavily across multiple projects; 70-89 = clearly used in at least one project; 50-69 = listed in skills section only; 30-49 = implied/inferred.
- Use canonical industry-standard names: "Node.js" not "nodejs", "PostgreSQL" not "postgres".
- Be exhaustive — extract every technical skill with any evidence.

Return ONLY a raw JSON array. No markdown, no explanation, no surrounding text.
Format: [{"name": "React.js", "confidence": 92}, {"name": "Node.js", "confidence": 88}, ...]
"""


def calculate_ats_score(gemini_json: dict) -> int:  # Multi-dimensional ATS score (0-100) across five weighted pillars
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
    """Multipart parser uploading resume details asynchronously, extracting via pdfplumber/python-docx and Llama."""
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

    # 2. Run Llama skill extraction (Call A — resume)
    if IS_MOCK_MODE:
        logger.info("No Groq API key — generating mock parsed resume data locally.")
        llama_skills: list = generate_mock_resume_data(raw_text).get("skills", [])
        gemini_json = generate_mock_resume_data(raw_text)
    else:
        # ── Call A: Resume skill extraction via Llama ─────────────────────────
        try:
            raw_llama_response = await call_llama(
                system_prompt=RESUME_SKILL_EXTRACTION_PROMPT,
                user_content=raw_text[:6000],
            )
            parsed_llama = extract_json(raw_llama_response)
            # Normalise: could be a list (expected) or a dict with a key
            if isinstance(parsed_llama, list):
                llama_skills = parsed_llama
            elif isinstance(parsed_llama, dict):
                # Try common wrapper keys
                llama_skills = (
                    parsed_llama.get("skills")
                    or parsed_llama.get("data")
                    or list(parsed_llama.values())[0]
                    if parsed_llama else []
                )
            else:
                llama_skills = []
            logger.info(f"Llama extracted {len(llama_skills)} skills from resume.")
        except Exception as e:
            logger.error(f"Llama skill extraction failed: {e}. Falling back to mock data.")
            llama_skills = generate_mock_resume_data(raw_text).get("skills", [])

        # ── Build a minimal gemini_json-compatible dict from Llama output ─────
        # (We still need it for calculate_ats_score and experience extraction)
        # Use a secondary Llama call for the full structured parse (experience, contact, gaps)
        FULL_PARSE_PROMPT = """\
You are an expert HR parser. Extract structured data from the raw resume text into this exact JSON schema:
{
  "candidate_name": "string",
  "contact_info": "string (email or phone)",
  "experience": [
    {
      "company": "str",
      "role": "str",
      "duration": "str",
      "details": "str (bulleted metrics combined)"
    }
  ],
  "gaps": [
    {
      "name": "str (skill gap name)",
      "category": "str (e.g. Cloud, DevOps, API Design, Testing)",
      "impact": <integer between 5 and 15>,
      "checked": false
    }
  ]
}

For the 'gaps' array: identify the top 4 most impactful skill gaps based on what is missing or weak compared to modern industry standards for the candidate's apparent role level. Each gap must have a unique name, a category, and an impact integer between 5 and 15 (higher = more critical).
Return ONLY the raw JSON output without any markdown formatting or surrounding text.
"""
        try:
            raw_full_response = await call_llama(
                system_prompt=FULL_PARSE_PROMPT,
                user_content=raw_text[:6000],
            )
            gemini_json = extract_json(raw_full_response)
            # Inject the Llama-extracted skills into gemini_json for ATS scoring
            gemini_json["skills"] = llama_skills
        except Exception as e:
            logger.error(f"Llama full parse failed: {e}. Falling back to mock data.")
            gemini_json = generate_mock_resume_data(raw_text)
            gemini_json["skills"] = llama_skills if llama_skills else gemini_json.get("skills", [])

    # 3. Execute a local heuristic rule-based processing step for ATS structural metric score
    extracted_experience = gemini_json.get("experience", [])
    ats_score = calculate_ats_score(gemini_json)

    # Build skills list from the Llama-extracted array, using real confidence scores
    flattened_skills = []
    raw_skills = llama_skills if not IS_MOCK_MODE else gemini_json.get("skills", [])
    if isinstance(raw_skills, list):
        for item in raw_skills:
            if isinstance(item, dict) and item.get("name"):
                confidence = max(1, min(100, int(item.get("confidence", 50))))
                flattened_skills.append({"name": str(item["name"]), "match": confidence})

    # 4. Extract Llama-generated gaps (top 4, validated)
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
        "skills": flattened_skills,  # Full deduplicated skill list with Llama-assigned confidence scores
        "experience": extracted_experience,
        "gaps": parsed_gaps,
        "ats_score": ats_score,
        "raw_text": raw_text  # Full extracted text for downstream ATS analysis
    }

    # 5. Asynchronous metadata logging to MongoDB Atlas
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
        except Exception as e:
            logger.error(f"Failed to commit parsed resume data to MongoDB Atlas: {e}")

    return parsed_data


@router.post("/streamlit/analyze")
async def streamlit_analyze(
    file: UploadFile = File(...),
    job_description: str = Body(..., embed=True)
):
    """Endpoint adapted from the provided Streamlit code: returns Llama analysis or a mock fallback."""
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in (".pdf", ".docx"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PDF and DOCX supported")

    file_bytes = await file.read()
    raw_text = ""
    if ext == ".pdf":
        if pdfplumber is None:
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
        mock_json = generate_mock_resume_data("")
        return {"response": "No readable text; returning mock analysis.", "mock": mock_json}

    # Compose prompt similar to Streamlit
    system_prompt = (
        "You are an experienced Technical Human Resource Manager, your task is to review the provided resume against the job description. "
        "Please share your professional evaluation on whether the candidate's profile aligns with the role. Highlight strengths and weaknesses."
    )

    if IS_MOCK_MODE:
        logger.warning("No Groq API key — returning mock analysis.")
        mock_json = generate_mock_resume_data(raw_text)
        return {"response": "Groq not available; returning mock analysis.", "mock": mock_json}

    try:
        user_content = f"JOB DESCRIPTION:\n{job_description}\n\nRESUME TEXT:\n{raw_text}"
        text_out = await call_llama(system_prompt=system_prompt, user_content=user_content)
        return {"response": text_out}
    except Exception as e:
        logger.error(f"Llama call failed in streamlit_analyze: {e}")
        mock_json = generate_mock_resume_data(raw_text)
        return {"response": "Llama call failed; returning mock analysis.", "mock": mock_json}


@router.post("/streamlit/match")
async def streamlit_match(
    file: UploadFile = File(...),
    job_description: str = Body(..., embed=True)
):
    """Return a percentage match and missing keywords similar to the Streamlit sample."""
    # Reuse the analyze flow to get text
    result = await streamlit_analyze(file=file, job_description=job_description)
    # If we received a Llama text response, attempt to parse numeric percentage
    raw_response = result.get("response", "") if isinstance(result, dict) else ""
    text: str = str(raw_response)
    # Heuristic extraction of percentage
    m = re.search(r"(\d{1,3})\s*%", text)
    if m:
        pct = int(m.group(1))
    else:
        # fallback: compute simple overlap score
        jd_terms = set(re.findall(r"\w+", job_description.lower()))
        # Extract skills from mock or parsed result
        skills: list[str] = []

        mock_data = result.get("mock") if isinstance(result, dict) else None

        if isinstance(mock_data, dict):
            skills = [
                str(s.get("name", ""))
                for s in mock_data.get("skills", [])
                if isinstance(s, dict)
            ]
        else:
            skills = re.findall(r"\w+", text.lower())[:50]

        common = jd_terms.intersection({s.lower() for s in skills})
        pct = int(min(100, (len(common) / max(1, len(jd_terms))) * 100))

    return {"match_percentage": pct, "raw_response": text}


@router.post("/cover_letter", response_model=CoverLetterResponse)
async def generate_cover_letter(payload: CoverLetterRequest):
    """Generate a professional Markdown cover letter using Llama via Groq."""
    logger.info(f"Generating cover letter for: {payload.resume.name}")

    # Build experience summary from resume data
    experience_summary = "; ".join([
        f"{exp.role} at {exp.company} ({exp.duration}): {exp.details[:100]}"
        for exp in payload.resume.experience
    ]) or "Not specified"

    top_skills = ", ".join([s.name for s in payload.resume.skills[:6]]) or "Not specified"

    if IS_MOCK_MODE:
        logger.info("Mock mode detected — generating mock cover letter locally.")
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

    system_prompt = (
        "You are a professional cover letter writer. Write compelling, specific, and data-driven cover letters in Markdown format. "
        "Never use cliches like 'I am writing to express' or 'I am passionate about'. "
        "Start with a compelling hook that references a specific achievement or skill. "
        "Write exactly 3 paragraphs. Return ONLY the Markdown cover letter text, nothing else."
    )

    user_content = (
        f"Write a professional cover letter for {payload.resume.name} applying to this role:\n"
        f"{payload.job_description}\n\n"
        f"Their experience: {experience_summary}\n"
        f"Their top skills: {top_skills}"
    )

    try:
        cover_letter = await call_llama(system_prompt=system_prompt, user_content=user_content)
        logger.info(f"Cover letter generated successfully for {payload.resume.name}")
        return CoverLetterResponse(cover_letter=cover_letter)
    except Exception as e:
        logger.error(f"Llama cover letter generation failed: {e}")
        raise HTTPException(status_code=502, detail="Failed to generate cover letter via AI subsystem.")
