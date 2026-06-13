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
try:
    import fitz  # PyMuPDF — primary PDF parser
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False
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
You are a Senior Hiring Manager, Domain Expert and Technical Interviewer reviewing candidate resumes.

Your task is to identify the candidate's demonstrated competencies from projects, experience, education,
certifications and technical work. Extract all relevant skills that a recruiter would consider while
evaluating the candidate. Do not simply collect keywords — focus on actual competencies evidenced
within the resume.

Return ONLY valid JSON matching this exact schema:
{
  "technical_skills": [],
  "domain_tools": [],
  "behavioral_indicators": [],
  "representative_skills": []
}

CATEGORY DEFINITIONS:

technical_skills — Hard competencies demonstrated through projects, experience, certifications,
  coursework or technical activities. Include ALL of the following types:
  Programming: Python, Java, C++, JavaScript, TypeScript, Go, Rust, Kotlin, Swift, Scala
  Web frameworks: React, Node.js, Express.js, Next.js, Django, FastAPI, Flask, Vue.js, Angular
  Databases: SQL, PostgreSQL, MongoDB, MySQL, Redis, Elasticsearch, SQLite
  Data/ML: Pandas, NumPy, Matplotlib, Seaborn, Scikit-Learn, TensorFlow, PyTorch, Keras,
           OpenCV, NLTK, spaCy, XGBoost, LightGBM, Power BI, Tableau, Excel
  Cloud/Infra: AWS, Azure, GCP, Docker, Kubernetes, Terraform, Ansible, Jenkins, CI/CD
  Security/Auth: JWT, OAuth, bcrypt, SSL/TLS
  Other: Git, Linux, HTML, CSS, Tailwind CSS, REST APIs, GraphQL, Socket.IO, WebSockets

PYTHON LIBRARY RULE (CRITICAL):
The following MUST always be classified as technical_skills — NEVER as domain_tools or behavioral_indicators:
  Pandas, NumPy, Matplotlib, Seaborn, Scikit-Learn, TensorFlow, PyTorch, Keras,
  OpenCV, NLTK, spaCy, FastAPI, Flask, Django

domain_tools — Professional software platforms used within a domain (NOT technical competencies):
  Examples: Jira, Confluence, HubSpot, Trello, Asana, ServiceNow, Notion, Slack, Postman, VSCode
  Note: Postman and VSCode are tools, not technical skills.

behavioral_indicators — Personal, workplace or interpersonal capabilities:
  Examples: Leadership, Communication, Problem Solving, Stakeholder Management,
            Teamwork, Presentation Skills, Attention to Detail

representative_skills — The most representative technical skills for UI display (8-12 items max).
  Prefer skills that best answer: "Which technologies would a recruiter notice in 5-10 seconds?"

  RANKING PRIORITY (apply in this order when selecting representative_skills):
  Tier 1 — Core Technologies (HIGHEST PRIORITY, select first):
    Programming Languages: Python, Java, JavaScript, TypeScript, C++, C#, Go, Kotlin, Swift, SQL
    Major Frameworks: React, Node.js, Express.js, Next.js, FastAPI, Django, Flask, Vue.js, Angular,
                      Spring Boot, Laravel
    Primary Databases: MongoDB, PostgreSQL, MySQL, Redis
    ML/AI Frameworks: Scikit-Learn, TensorFlow, PyTorch, Keras
    Analytics Tools: Power BI, Tableau
    Cloud/Infra: AWS, Azure, GCP, Docker, Kubernetes

  Tier 2 — Major Libraries & Platforms (select after Tier 1):
    Pandas, NumPy, Matplotlib, Seaborn, OpenCV, spaCy, NLTK, XGBoost, LightGBM,
    Redux, Tailwind CSS, Bootstrap, Firebase, Elasticsearch

  Tier 3 — Supporting Technologies (include only if space remains after Tier 1+2):
    JWT, OAuth, Socket.IO, REST APIs, GraphQL, WebSockets, bcrypt, Multer,
    Git, Linux, HTML, CSS, GitHub Actions, Webpack, Vite

  EXAMPLE — MERN Stack Developer:
  Technical skills: JavaScript, React, Node.js, Express.js, MongoDB, Socket.IO, JWT, REST APIs, Redux, Git
  Poor representative: [JavaScript, React, Node.js, Socket.IO, JWT, REST APIs]
  CORRECT representative: [JavaScript, React, Node.js, Express.js, MongoDB, Redux, Git]

  EXAMPLE — Data Science:
  Technical skills: Python, Pandas, NumPy, Matplotlib, Scikit-Learn, TensorFlow, Power BI, SQL
  CORRECT representative: [Python, SQL, Scikit-Learn, TensorFlow, Power BI, Pandas]
  (NOT Matplotlib, NumPy alone — recruiters care about ML frameworks and analytics tools first)

  Return representative_skills as plain strings: ["React", "Node.js", "MongoDB", ...]
  Maximum 12 items. Minimum 6 items.

Return ONLY raw JSON, no markdown, no explanation.
"""


# ── Always-technical skills set (for post-processing validation) ─────────────
_RESUME_ALWAYS_TECHNICAL: set[str] = {
    "python", "pandas", "numpy", "matplotlib", "seaborn", "scipy",
    "scikit-learn", "sklearn", "scikit learn", "tensorflow", "pytorch", "keras", "xgboost",
    "lightgbm", "opencv", "nltk", "spacy", "fastapi", "flask", "django",
    "react", "reactjs", "react.js", "node.js", "nodejs", "next.js", "nextjs",
    "express.js", "express", "vue.js", "angular", "typescript", "javascript",
    "sql", "postgresql", "postgres", "mysql", "mongodb", "redis",
    "elasticsearch", "power bi", "powerbi", "power_bi", "tableau", "excel",
    "aws", "azure", "gcp", "docker", "kubernetes", "k8s", "terraform",
    "ansible", "jenkins", "git", "linux", "ci/cd",
    "machine learning", "deep learning", "nlp", "natural language processing",
    "generative ai", "llms", "llm", "prompt engineering", "langchain",
    "java", "c++", "cpp", "c#", "csharp", "go", "golang", "rust",
    "kotlin", "swift", "scala", "html", "css",
    "jwt", "oauth", "socket.io", "websockets", "graphql", "rest apis",
    "redux", "redux toolkit", "rtk query", "tailwind css", "tailwindcss",
}

# ── Tier-based representative skill ranker ──────────────────────────────────
# Determines display priority: recruiters notice Tier 1 first.
_REPR_TIER: dict[str, int] = {
    # Tier 1 — Core Technologies (score 1 = highest priority)
    "python": 1, "java": 1, "javascript": 1, "typescript": 1,
    "c++": 1, "cpp": 1, "c#": 1, "csharp": 1, "go": 1, "golang": 1,
    "kotlin": 1, "swift": 1, "scala": 1, "rust": 1, "sql": 1,
    "react": 1, "node.js": 1, "nodejs": 1, "express.js": 1, "express": 1,
    "next.js": 1, "nextjs": 1, "fastapi": 1, "django": 1, "flask": 1,
    "vue.js": 1, "angular": 1, "spring boot": 1, "spring": 1,
    "mongodb": 1, "postgresql": 1, "postgres": 1, "mysql": 1, "redis": 1,
    "scikit-learn": 1, "sklearn": 1, "scikit learn": 1,
    "tensorflow": 1, "pytorch": 1, "keras": 1,
    "power bi": 1, "powerbi": 1, "tableau": 1,
    "aws": 1, "azure": 1, "gcp": 1, "docker": 1, "kubernetes": 1, "k8s": 1,
    "machine learning": 1, "deep learning": 1, "generative ai": 1,
    "langchain": 1, "llm": 1, "llms": 1,
    # Tier 2 — Major Libraries & Platforms (score 2)
    "pandas": 2, "numpy": 2, "matplotlib": 2, "seaborn": 2,
    "opencv": 2, "spacy": 2, "nltk": 2, "xgboost": 2, "lightgbm": 2,
    "redux": 2, "tailwind css": 2, "tailwindcss": 2, "bootstrap": 2,
    "firebase": 2, "elasticsearch": 2, "terraform": 2, "ansible": 2,
    "jenkins": 2, "ci/cd": 2, "linux": 2, "git": 2,
    "excel": 2, "nlp": 2, "natural language processing": 2,
    # Tier 3 — Supporting Technologies (score 3 = lowest priority)
    "jwt": 3, "oauth": 3, "bcrypt": 3, "socket.io": 3,
    "rest apis": 3, "graphql": 3, "websockets": 3, "multer": 3,
    "html": 3, "css": 3, "github actions": 3, "webpack": 3, "vite": 3,
    "redux toolkit": 3, "rtk query": 3, "prompt engineering": 3,
}


def _get_skill_tier(name: str) -> int:
    """Return display tier for a skill name (lower = higher priority, default Tier 2)."""
    return _REPR_TIER.get(name.lower().strip(), 2)


def rank_representative_skills(technical_skills: list, candidate_repr: list, max_count: int = 10) -> list[str]:
    """
    Deterministic recruiter-grade representative skill selection.

    1. Start with LLM-suggested representative_skills (if any).
    2. Re-rank by tier (Tier 1 first, Tier 3 last), then by confidence within tier.
    3. Fill remaining slots from technical_skills sorted the same way.
    4. Cap at max_count (default 10, never exceed 12).

    Returns a flat list of strings (names only — no confidence objects).
    """
    max_count = min(max_count, 12)  # hard cap

    def get_name(item) -> str:
        return (item["name"] if isinstance(item, dict) else str(item)).strip()

    def get_conf(item) -> int:
        return item.get("confidence", 50) if isinstance(item, dict) else 50

    # Build lookup: name_lower → (tier, confidence) from full technical_skills
    tech_lookup: dict[str, tuple[int, int]] = {}
    for item in technical_skills:
        n = get_name(item)
        tech_lookup[n.lower()] = (_get_skill_tier(n), get_conf(item))

    # Candidate repr names (from LLM suggestion, may be strings or dicts)
    repr_names = [get_name(i) for i in candidate_repr]
    repr_lower: set[str] = {n.lower() for n in repr_names}

    # Re-rank LLM suggestions by tier then descending confidence
    ranked_repr = sorted(
        repr_names,
        key=lambda n: (_get_skill_tier(n), -tech_lookup.get(n.lower(), (2, 50))[1]),
    )

    # Fill from technical_skills not already in repr (same sort key)
    fill_pool = sorted(
        [get_name(i) for i in technical_skills if get_name(i).lower() not in repr_lower],
        key=lambda n: (_get_skill_tier(n), -tech_lookup.get(n.lower(), (2, 50))[1]),
    )

    # Deduplicate and cap
    seen: set[str] = set()
    final: list[str] = []
    for name in ranked_repr + fill_pool:
        key = name.lower()
        if key not in seen:
            seen.add(key)
            final.append(name)
        if len(final) >= max_count:
            break

    return final


def validate_resume_extraction(raw: dict) -> dict:
    """
    Post-processing validation pass on Groq resume extraction output.

    Enforces:
    1. All 4 required keys exist.
    2. Known technical skills (Pandas, React, etc.) moved from domain_tools/behavioral_indicators
       into technical_skills if Groq misclassified them.
    3. Behavioral phrases removed from technical_skills.
    4. representative_skills fallback: if empty, auto-select top 8 from technical_skills.
    5. Deduplicate all lists.
    """
    result: dict = {
        "technical_skills": list(raw.get("technical_skills", []) or []),
        "domain_tools":     list(raw.get("domain_tools", []) or []),
        "behavioral_indicators": list(raw.get("behavioral_indicators", []) or []),
        "representative_skills": list(raw.get("representative_skills", []) or []),
    }

    # 1. Move always-technical skills out of wrong categories
    for cat in ["domain_tools", "behavioral_indicators"]:
        keep = []
        for item in result[cat]:
            item_name = item["name"] if isinstance(item, dict) else str(item)
            if item_name.lower().strip() in _RESUME_ALWAYS_TECHNICAL:
                # Move to technical_skills if not already there
                existing_names = {
                    (s["name"] if isinstance(s, dict) else s).lower()
                    for s in result["technical_skills"]
                }
                if item_name.lower() not in existing_names:
                    result["technical_skills"].append(item)
            else:
                keep.append(item)
        result[cat] = keep

    # 2. Remove behavioral phrases from technical_skills
    behavioral_signals = [
        "leadership", "communication", "problem solving", "teamwork",
        "stakeholder", "presentation", "attention to detail", "analytical",
        "interpersonal", "collaboration", "mentoring", "time management",
    ]
    clean_tech = []
    for item in result["technical_skills"]:
        item_name = (item["name"] if isinstance(item, dict) else str(item)).lower()
        if any(sig in item_name for sig in behavioral_signals):
            result["behavioral_indicators"].append(item)
        else:
            clean_tech.append(item)
    result["technical_skills"] = clean_tech

    # 3. Apply deterministic tier-based ranking to representative_skills
    #    Always re-rank regardless of whether LLM provided suggestions,
    #    to ensure Tier 1 skills (languages, frameworks, DBs) appear first.
    result["representative_skills"] = rank_representative_skills(
        technical_skills=result["technical_skills"],
        candidate_repr=result["representative_skills"],
        max_count=10,  # default cap at 10; hard-capped at 12 inside the function
    )

    # 4. Deduplicate all lists (by name, case-insensitive)
    for key in ["technical_skills", "domain_tools", "behavioral_indicators", "representative_skills"]:
        seen: set[str] = set()
        deduped = []
        for item in result[key]:
            name = (item["name"] if isinstance(item, dict) else str(item)).lower().strip()
            if name and name not in seen:
                seen.add(name)
                deduped.append(item)
        result[key] = deduped

    return result


# ── Deterministic Resume Quality Score ───────────────────────────────────────
def calculate_resume_quality_score(parsed_data_json: dict) -> int:
    """
    Deterministic resume quality score (0–100) across six weighted pillars.
    Used when the user uploads a resume WITHOUT a job description.

    Weights V2:
      Contact Information  = 10%
      Skills Section       = 20%
      Experience Section   = 25%
      Completeness         = 15%
      Projects             = 15%
      Achievements         = 15%
    """
    total = 0

    # ── 1. Contact Information (10 pts) ───────────────────────────────────────
    contact = parsed_data_json.get("contact_info", "")
    candidate_name = parsed_data_json.get("candidate_name", "")
    has_email = bool(re.search(r'[\w.-]+@[\w.-]+', contact))
    has_phone = bool(re.search(r'\+?[\d\s\-()]{7,}', contact))
    has_name  = bool(candidate_name and candidate_name.strip() and candidate_name != "Unknown Candidate")
    has_social = bool(re.search(r'linkedin|github|portfolio', contact, re.IGNORECASE))

    contact_pts = 0
    if has_name:   contact_pts += 2
    if has_email:  contact_pts += 3
    if has_phone:  contact_pts += 3
    if has_social: contact_pts += 2
    total += contact_pts  # max 10

    # ── 2. Skills Section (20 pts) ─────────────────────────────────────────────
    raw_skills = parsed_data_json.get("skills", [])
    projects_raw = parsed_data_json.get("projects", []) or []
    experience_raw = parsed_data_json.get("experience", []) or []

    project_tech_text = " ".join(
        " ".join(str(t).lower() for t in proj.get("technologies", []))
        + " " + str(proj.get("description", "")).lower()
        for proj in projects_raw if isinstance(proj, dict)
    )
    experience_text = " ".join(
        str(exp.get("details", "")).lower() + " " + str(exp.get("role", "")).lower()
        for exp in experience_raw if isinstance(exp, dict)
    )

    skill_quality_pts = 0.0
    unique_skills = 0
    if isinstance(raw_skills, list):
        for s in raw_skills:
            if not isinstance(s, dict):
                continue
            name = str(s.get("name", "")).lower().strip()
            if not name:
                continue
            confidence = int(s.get("confidence", 50))
            in_projects = name in project_tech_text
            in_experience = name in experience_text
            if in_projects and in_experience:
                evidence_weight = 1.0
            elif in_projects or in_experience:
                evidence_weight = 0.75
            else:
                evidence_weight = 0.4
            skill_quality_pts += (confidence / 100) * evidence_weight
            unique_skills += 1

    skills_pts = min(20, round((skill_quality_pts / 8.0) * 20))
    total += skills_pts  # max 20

    # ── 3. Experience Section (25 pts) ────────────────────────────────────────
    experience_list = parsed_data_json.get("experience", [])
    active_verbs = {
        "led", "developed", "engineered", "built", "managed", "created", "designed",
        "architected", "optimized", "increased", "decreased", "improved", "spearheaded",
        "orchestrated", "deployed", "launched", "migrated", "automated", "reduced",
        "scaled", "integrated", "implemented", "delivered", "established", "streamlined",
        "analyzed", "maintained", "collaborated", "researched", "executed", "trained",
    }

    verb_pts = 0
    duration_pts = 0
    has_recent = False
    for exp in experience_list:
        details = exp.get("details", "").lower()
        duration = str(exp.get("duration", "")).lower()
        words = set(details.split())
        has_verb = bool(words.intersection(active_verbs))
        if has_verb and verb_pts < 15:
            verb_pts = min(verb_pts + 5, 15)

        if "present" in duration or "current" in duration or "2024" in duration or "2025" in duration or "2026" in duration:
            has_recent = True

    if has_recent:
        duration_pts = 10
    elif len(experience_list) >= 1:
        duration_pts = 5

    exp_quality_pts = verb_pts + duration_pts
    total += exp_quality_pts  # max 25

    # ── 4. Completeness (15 pts) ──────────────────────────────────────────────
    completeness_pts = 0
    if experience_list:              completeness_pts += 4
    if unique_skills >= 4:           completeness_pts += 3
    if has_name:                     completeness_pts += 2
    if parsed_data_json.get("education"):
        completeness_pts += 3
    if parsed_data_json.get("projects"):
        completeness_pts += 2
    if parsed_data_json.get("certifications"):
        completeness_pts += 1
    total += min(completeness_pts, 15)

    # ── 5. Projects (15 pts) ──────────────────────────────────────────────────
    projects = parsed_data_json.get("projects", [])
    project_count = len(projects) if isinstance(projects, list) else 0

    all_project_techs: set = set()
    if isinstance(projects, list):
        for proj in projects:
            techs = proj.get("technologies", [])
            if isinstance(techs, list):
                all_project_techs.update(str(t).lower() for t in techs if t)

    tech_diversity = len(all_project_techs)

    project_pts = 0
    if project_count >= 3:    project_pts += 8
    elif project_count == 2:  project_pts += 5
    elif project_count == 1:  project_pts += 3

    if tech_diversity >= 5:   project_pts += 7
    elif tech_diversity >= 3: project_pts += 4
    elif tech_diversity >= 1: project_pts += 2

    total += min(project_pts, 15)

    # ── 6. Achievements (15 pts) ──────────────────────────────────────────────
    # "increased accuracy by 20%", "reduced latency by 40%", "served 1000 users", etc.
    achievement_pattern = re.compile(
        r'(\b(?:increased|decreased|reduced|improved|served|processed|saved|generated|grew|achieved|accelerated)\b[\s\w]{0,30}(?:\d+%|\$\d+|\d+\s*(?:million|billion|k|m)\b|\d+\s*(?:users|clients|requests|services|ms|seconds|records|hours|days|weeks|months|years|times|x)))',
        re.IGNORECASE
    )

    achievement_count = 0
    for exp in experience_list:
        details = exp.get("details", "")
        matches = achievement_pattern.findall(details)
        achievement_count += len(matches)

    for proj in projects:
        desc = proj.get("description", "")
        matches = achievement_pattern.findall(desc)
        achievement_count += len(matches)

    achievement_pts = min(15, achievement_count * 2)
    total += achievement_pts  # max 15

    # --- Defensive Logging (Issue 3 verification) ---
    logger.info(f"ATS Pillar - Contact Info: {contact_pts} pts")
    logger.info(f"ATS Pillar - Skills: {skills_pts} pts")
    logger.info(f"ATS Pillar - Experience: {exp_quality_pts} pts")
    logger.info(f"ATS Pillar - Sections Completeness: {completeness_pts} pts")
    logger.info(f"ATS Pillar - Projects: {min(project_pts, 15)} pts")
    logger.info(f"ATS Pillar - Achievements: {achievement_pts} pts (Count: {achievement_count})")
    logger.info(f"ATS Total Raw Score: {total} pts (capped at 100)")
    # ------------------------------------------------

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

def _extract_projects_heuristic(raw_text: str, detected_skills: list[dict]) -> list[dict]:
    """Lightweight heuristic project extraction for mock mode (no LLM)."""
    lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
    projects = []
    project_header_pattern = re.compile(r'^(project|projects?:?)\s*[:\-]?\s*(.+)', re.IGNORECASE)
    skill_names_lower = {s["name"].lower() for s in detected_skills}
    for i, line in enumerate(lines):
        m = project_header_pattern.match(line)
        if m and m.group(2).strip():
            name = m.group(2).strip()[:80]
            desc_lines = []
            techs_found = set()
            for j in range(i + 1, min(i + 4, len(lines))):
                desc_lines.append(lines[j])
                for sk in skill_names_lower:
                    if sk in lines[j].lower():
                        techs_found.add(sk.title())
            projects.append({
                "name": name,
                "technologies": list(techs_found),
                "description": " ".join(desc_lines)[:300]
            })
        if len(projects) >= 4:
            break
    return projects

def _extract_experience_heuristic(raw_text: str) -> list[dict]:
    """Lightweight heuristic experience extraction for mock mode (no LLM)."""
    lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
    experience = []
    # Look for lines containing a date range pattern (e.g. 2021 - 2023, 2022 - Present)
    date_pattern = re.compile(r'(20\d{2}|19\d{2}).{0,6}(20\d{2}|present|current)', re.IGNORECASE)
    for i, line in enumerate(lines):
        if date_pattern.search(line):
            # Assume the line itself or the line above contains role/company
            context_line = lines[i - 1] if i > 0 else line
            duration_match = date_pattern.search(line)
            duration = duration_match.group(0) if duration_match else ""
            details_lines = []
            for j in range(i + 1, min(i + 5, len(lines))):
                if date_pattern.search(lines[j]):
                    break
                details_lines.append(lines[j])
            experience.append({
                "company": context_line[:60],
                "role": line.split(duration)[0].strip()[:60] if duration else context_line[:60],
                "duration": duration,
                "details": " ".join(details_lines)[:400]
            })
        if len(experience) >= 4:
            break
    return experience

def generate_mock_resume_data(raw_text: str) -> dict:
    """
    Generate resume data from actual extracted text when Groq is unavailable.
    NO hardcoded skill lists — only detects skills actually present in the text.
    """
    lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
    candidate_name = "Unknown Candidate"
    if lines:
        for line in lines[:5]:
            if "@" not in line and "http" not in line and 3 < len(line) < 40:
                candidate_name = line
                break

    email_match = re.search(r'[\w.-]+@[\w.-]+', raw_text)
    email = email_match.group(0) if email_match else ""

    phone_match = re.search(r'\+?[\d\s\-()]{10,}', raw_text)
    phone = phone_match.group(0).strip() if phone_match else ""

    # Only detect skills that are actually present in the resume text
    COMMON_TECH_TERMS = [
        "Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "Go", "Rust", "Kotlin", "Swift",
        "React", "Angular", "Vue.js", "Next.js", "Node.js", "Express.js", "Django", "Flask", "FastAPI",
        "Spring", "Laravel", "Ruby on Rails",
        "AWS", "GCP", "Azure", "Docker", "Kubernetes", "Terraform", "Jenkins", "CI/CD",
        "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch", "SQLite",
        "HTML", "CSS", "Tailwind CSS", "GraphQL", "REST APIs",
        "Git", "Linux", "Nginx",
        "Machine Learning", "Deep Learning", "TensorFlow", "PyTorch", "Scikit-learn",
        "Pandas", "NumPy", "Power BI", "Tableau", "Excel", "SQL",
    ]

    detected_skills = []
    text_lower = raw_text.lower()
    for tech in COMMON_TECH_TERMS:
        pattern = r'\b' + re.escape(tech.lower()) + r'\b'
        if re.search(pattern, text_lower):
            confidence = 85 if text_lower.count(tech.lower()) > 1 else 70
            detected_skills.append({"name": tech, "confidence": confidence})

    contact_info = " ".join(filter(None, [email, phone]))

    return {
        "candidate_name": candidate_name,
        "contact_info": contact_info,
        "skills": detected_skills,  # Only skills actually found in text — never hardcoded
        "experience": _extract_experience_heuristic(raw_text),
        "gaps": [],
        "education": [],
        "projects": _extract_projects_heuristic(raw_text, detected_skills),
        "certifications": [],
    }


@router.post("/upload", response_model=ResumeDataSchema)
async def upload_resume(
    file: UploadFile = File(...),
    db = Depends(get_database)
):
    """
    Multipart resume upload endpoint.
    Extracts text via pdfplumber/python-docx, then calls Groq for structured parsing.
    Returns a ResumeDataSchema including a deterministic resume_quality_score.
    No Gemini involvement.
    """
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
        # ── Primary: PyMuPDF (handles two-column, table-heavy resumes) ──────────
        if HAS_PYMUPDF:
            try:
                doc = fitz.open(stream=file_bytes, filetype="pdf")
                for page in doc:
                    page_dict: dict = page.get_text("dict")  # type: ignore[assignment]
                    blocks = page_dict["blocks"]
                    # Sort blocks top-to-bottom, left-to-right for reading order
                    blocks_sorted = sorted(blocks, key=lambda b: (round(b["bbox"][1] / 20), b["bbox"][0]))
                    for block in blocks_sorted:
                        if block["type"] == 0:  # text block
                            for line in block.get("lines", []):
                                line_text = " ".join(span["text"] for span in line.get("spans", []))
                                if line_text.strip():
                                    raw_text += line_text + "\n"
                    raw_text += "\n"  # page separator
                doc.close()
                logger.info(f"PyMuPDF extracted {len(raw_text)} chars from PDF")
            except Exception as e:
                logger.warning(f"PyMuPDF failed ({e}), falling back to pdfplumber")
                raw_text = ""

        # ── Fallback: pdfplumber ─────────────────────────────────────────────
        if not raw_text.strip():
            try:
                with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            raw_text += page_text + "\n"
                logger.info(f"pdfplumber extracted {len(raw_text)} chars from PDF")
            except Exception as e:
                logger.error(f"pdfplumber also failed: {e}")
                raise HTTPException(status_code=500, detail="Failed to parse PDF content stream.")
    elif ext == ".docx":
        raw_text = extract_text_from_docx(file_bytes)

    if not raw_text.strip():
        raise HTTPException(status_code=400, detail="No readable text found in the file. Could be an image-only file.")

    # 2. Run Groq skill extraction (Call A — resume skills, structured 4-field format)
    resume_technical_skills: list = []    # complete ATS inventory
    resume_representative_skills: list = []  # curated UI display subset
    resume_soft_skills: list = []

    if IS_MOCK_MODE:
        logger.info("No Groq API key — generating resume data from actual text content (no hardcoded skills).")
        mock_data = generate_mock_resume_data(raw_text)
        mock_skills = mock_data.get("skills", [])
        # Apply the same deterministic tiered ranking used for live Groq output
        validated_mock = validate_resume_extraction({
            "technical_skills": mock_skills,
            "domain_tools": [],
            "behavioral_indicators": [],
            "representative_skills": [],
        })
        resume_technical_skills = validated_mock["technical_skills"]
        resume_representative_skills = validated_mock["representative_skills"]
        resume_soft_skills = validated_mock["behavioral_indicators"]
        parsed_data_json = mock_data
    else:
        # ── Call A: Recruiter-grade structured skill extraction via Llama ─────────
        try:
            raw_llama_response = await call_llama(
                system_prompt=RESUME_SKILL_EXTRACTION_PROMPT,
                user_content=raw_text[:6000],
            )
            parsed_llama = extract_json(raw_llama_response)

            # Handle both new structured format and legacy flat array
            if isinstance(parsed_llama, dict):
                # New structured 4-field format
                validated = validate_resume_extraction(parsed_llama)
                resume_technical_skills = validated["technical_skills"]
                resume_representative_skills = validated["representative_skills"]
                resume_soft_skills = validated["behavioral_indicators"]
            elif isinstance(parsed_llama, list):
                # Legacy flat array fallback (LLM returned old format)
                logger.warning("Groq returned legacy flat array — applying structured fallback.")
                resume_technical_skills = parsed_llama
                resume_representative_skills = sorted(
                    parsed_llama,
                    key=lambda s: s.get("confidence", 50) if isinstance(s, dict) else 50,
                    reverse=True,
                )[:8]
            else:
                resume_technical_skills = []
                resume_representative_skills = []

            # Write debug output
            debug_output = {
                "technical_skills": resume_technical_skills,
                "representative_skills": resume_representative_skills,
            }
            with open("resume_skill_extraction.json", "w", encoding="utf-8") as f:
                f.write(json.dumps(debug_output, indent=2, ensure_ascii=False))
            logger.info(
                f"Groq extracted {len(resume_technical_skills)} technical skills, "
                f"{len(resume_representative_skills)} representative skills from resume."
            )
        except Exception as e:
            logger.error(f"Groq skill extraction failed: {e}. Using text-scan fallback.")
            fallback = generate_mock_resume_data(raw_text).get("skills", [])
            resume_technical_skills = fallback
            resume_representative_skills = fallback[:8]

        # ── Call B: Full structured parse (experience, contact, education, projects) ─
        FULL_PARSE_PROMPT = """\
You are an expert HR parser. Extract structured data from the raw resume text into this exact JSON schema:
{
  "candidate_name": "string",
  "contact_info": "string (email, phone, LinkedIn, GitHub — comma separated)",
  "experience": [
    {
      "company": "str",
      "role": "str",
      "duration": "str",
      "details": "str (bulleted metrics combined)"
    }
  ],
  "education": [
    {
      "degree": "str",
      "institution": "str",
      "year": "str"
    }
  ],
  "projects": [
    {
      "name": "str",
      "technologies": ["str"],
      "description": "str"
    }
  ],
  "certifications": ["str"],
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
            parsed_data_json = extract_json(raw_full_response)
            # Attach skills for quality scoring (use technical_skills as full inventory)
            parsed_data_json["skills"] = resume_technical_skills
            # Write clean parsed output for debugging
            parsed = extract_json(raw_full_response)
            with open("resume_full_parse.json", "w", encoding="utf-8") as f:
                json.dump(parsed, f, indent=4)
        except Exception as e:
            logger.error(f"Groq full parse failed: {e}. Using text-scan fallback.")
            parsed_data_json = generate_mock_resume_data(raw_text)
            parsed_data_json["skills"] = resume_technical_skills if resume_technical_skills else parsed_data_json.get("skills", [])

    # 3. Calculate deterministic Resume Quality Score
    # Use technical_skills for quality scoring (complete inventory)
    resume_quality_score = calculate_resume_quality_score(parsed_data_json)
    logger.info(f"RESUME_QUALITY_SCORE: {resume_quality_score}")
    print(f"\nRESUME_QUALITY_SCORE: {resume_quality_score}")
    print(f"TECHNICAL_SKILLS_COUNT: {len(resume_technical_skills)}")
    print(f"REPRESENTATIVE_SKILLS_COUNT: {len(resume_representative_skills)}\n")

    # 3.5 Generate Resume-Only Strengths, Weaknesses, Recommendations
    strengths, weaknesses, recommendations = [], [], []
    if not IS_MOCK_MODE:
        RESUME_ONLY_ANALYSIS_PROMPT = """\
You are an expert Technical Recruiter. Analyze this resume and return exactly a JSON object with:
{
  "strengths": ["str"],
  "weaknesses": ["str"],
  "recommendations": ["str"]
}
Keep points concise. No markdown or explanations.
"""
        try:
            analysis_resp = await call_llama(
                system_prompt=RESUME_ONLY_ANALYSIS_PROMPT,
                user_content=raw_text[:6000]
            )
            analysis_json = extract_json(analysis_resp)
            strengths = analysis_json.get("strengths", [])
            weaknesses = analysis_json.get("weaknesses", [])
            recommendations = analysis_json.get("recommendations", [])
        except Exception as e:
            logger.error(f"Groq Resume-Only Analysis failed: {e}")

    # 4. Build skills list from representative skills (for UI display in resume-only mode)
    #    The 'skills' array = representative skills curated for display.
    #    The complete technical_skills inventory is available via raw_text for ATS matching.
    flattened_skills = []
    raw_repr = resume_representative_skills
    if isinstance(raw_repr, list):
        for item in raw_repr:
            if isinstance(item, dict) and item.get("name"):
                confidence = max(1, min(100, int(item.get("confidence", 50))))
                flattened_skills.append({"name": str(item["name"]), "match": confidence})
            elif isinstance(item, str) and item:
                flattened_skills.append({"name": item, "match": 75})

    # 5. Extract gaps (top 4, validated) — used only in resume-only mode before JD upload
    raw_gaps = parsed_data_json.get("gaps", [])
    parsed_gaps = []
    for gap in raw_gaps[:4]:
        parsed_gaps.append({
            "name": str(gap.get("name", "Unknown Gap")),
            "category": str(gap.get("category", "General")),
            "impact": max(5, min(15, int(gap.get("impact", 8)))),
            "checked": False,
        })

    extracted_experience = parsed_data_json.get("experience", [])
    extracted_education = parsed_data_json.get("education", [])
    extracted_projects = parsed_data_json.get("projects", [])
    extracted_certifications = parsed_data_json.get("certifications", [])

    tech_skills_clean = [s["name"] if isinstance(s, dict) else str(s) for s in resume_technical_skills]
    soft_skills_clean = [s["name"] if isinstance(s, dict) else str(s) for s in resume_soft_skills]

    parsed_data = {
        "name": parsed_data_json.get("candidate_name", "Unknown Candidate"),
        "email": parsed_data_json.get("contact_info", "No Contact Info Found"),
        "skills": flattened_skills,
        "technical_skills": tech_skills_clean,
        "soft_skills": soft_skills_clean,
        "experience": extracted_experience,
        "education": extracted_education,
        "projects": extracted_projects,
        "certifications": extracted_certifications,
        "gaps": parsed_gaps,
        "ats_score": resume_quality_score,
        "resume_quality_score": resume_quality_score,
        "raw_text": raw_text,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "recommendations": recommendations,
    }

    # 6. Persist metadata to MongoDB Atlas
    resume_id_str = None
    if db is not None:
        try:
            document_record = {
                "filename": file.filename,
                "content_type": file.content_type,
                "uploaded_at": datetime.now(timezone.utc),
                "parsed_data": parsed_data,
                "raw_extracted_text": raw_text,
                "resume_embeddings": [],
            }
            result = await db["resumes"].insert_one(document_record)
            resume_id_str = str(result.inserted_id)
            logger.info(f"Resume metadata inserted to Atlas: {resume_id_str}")
        except Exception as e:
            logger.error(f"Failed to commit parsed resume data to MongoDB Atlas: {e}")

    parsed_data["resume_id"] = resume_id_str
    return parsed_data


@router.post("/streamlit/analyze")
async def streamlit_analyze(
    file: UploadFile = File(...),
    job_description: str = Body(..., embed=True)
):
    """Endpoint adapted from the Streamlit code: returns Groq analysis or a mock fallback."""
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
        mock_json = generate_mock_resume_data("")
        return {"response": "No readable text; returning mock analysis.", "mock": mock_json}

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
        logger.error(f"Groq call failed in streamlit_analyze: {e}")
        mock_json = generate_mock_resume_data(raw_text)
        return {"response": "Groq call failed; returning mock analysis.", "mock": mock_json}


@router.post("/streamlit/match")
async def streamlit_match(
    file: UploadFile = File(...),
    job_description: str = Body(..., embed=True)
):
    """Return a percentage match and missing keywords similar to the Streamlit sample."""
    result = await streamlit_analyze(file=file, job_description=job_description)
    raw_response = result.get("response", "") if isinstance(result, dict) else ""
    text: str = str(raw_response)
    m = re.search(r"(\d{1,3})\s*%", text)
    if m:
        pct = int(m.group(1))
    else:
        jd_terms = set(re.findall(r"\w+", job_description.lower()))
        skills: list[str] = []
        if isinstance(result, dict) and isinstance(result.get("mock"), dict):
            skills = [
                str(s.get("name", ""))
                for s in result["mock"].get("skills", [])
                if isinstance(s, dict) and "name" in s
            ]
        else:
            skills = re.findall(r"\w+", text.lower())[:50]

        common = jd_terms.intersection({s.lower() for s in skills})
        pct = int(min(100, (len(common) / max(1, len(jd_terms))) * 100))

    return {"match_percentage": pct, "raw_response": text}


@router.post("/cover_letter", response_model=CoverLetterResponse)
async def generate_cover_letter(payload: CoverLetterRequest):
    """Generate a professional Markdown cover letter using Groq/Llama."""
    logger.info(f"Generating cover letter for: {payload.resume.name}")

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
        logger.error(f"Groq cover letter generation failed: {e}")
        raise HTTPException(status_code=502, detail="Failed to generate cover letter via AI subsystem.")