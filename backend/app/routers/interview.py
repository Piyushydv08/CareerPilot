# app/routers/interview.py
"""
Production-ready AI Interview System — CareerPilot
───────────────────────────────────────────────────
Issues fixed:
 1. Real PDF/DOCX parsing via pdfplumber + python-docx
 2. DB-driven phase state (no more message-count heuristics)
 3. Resume upload advances phase to 'technical' automatically
 4. Resume + role context injected into every technical LLM prompt
 5. Persistent target_role stored in MongoDB once extracted
 6. Backend-authoritative message history (DB is source of truth)
 7. Full exception logging with stack traces (logger.exception)
 8. Role-specific question generation via ROLE_TOPIC_MAP
 9. Structured technical engine tracking asked_topics to avoid repetition
10. Richer assessment with resume + role context
11. Skill gap analysis returned in assessment response
12. Detailed structured logging with timing throughout
"""
import asyncio
import io
import json
import logging
import os
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
import pdfplumber
from docx import Document as DocxDocument
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, UploadFile, File, Form
from fastapi.responses import JSONResponse

load_dotenv()

from app.models.schemas import (
    InterviewStartResponse,
    InterviewRespondRequest,
    InterviewRespondResponse,
    GenerateLearningPathRequest,
    GenerateLearningPathResponse,
    LearningMilestone,
    InterviewAssessRequest,
    InterviewAssessResponse,
    ChatMessageSchema,
)
from app.core.database import get_database

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/interview", tags=["interview"])

# ─── Groq Configuration ───────────────────────────────────────────────────────
# GROQ_API_KEY is read from the environment at startup via load_dotenv().
# If you update .env with a new key, restart the server process for it to take effect.
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_BASE_URL = os.environ.get(
    "GROQ_BASE_URL", "https://api.groq.com/openai/v1/chat/completions"
)
IS_MOCK_MODE = not bool(GROQ_API_KEY)

# ─── Rate-limit cooldown tracker ──────────────────────────────────────────────
# Tracks the last time a 429 was received so subsequent requests during a burst
# skip the API call entirely and go straight to the fallback, preventing cascading
# 429s on Groq's free tier.
_last_429_time: float = 0.0
_COOLDOWN_SECONDS: float = 15.0  # skip API calls for this long after a 429

if IS_MOCK_MODE:
    logger.warning("No Groq API key found – running in MOCK mode")
else:
    logger.info("Groq API key loaded – using llama-3.3-70b-versatile")

# ─── Interview Phase Order ────────────────────────────────────────────────────
PHASES = ["introduction", "job_role", "resume", "technical", "assessment"]

# ─── Role → Topic Cluster Map ─────────────────────────────────────────────────
ROLE_TOPIC_MAP: Dict[str, List[str]] = {
    "data analyst": [
        "SQL", "Excel", "Power BI", "Tableau", "Statistics",
        "A/B Testing", "Business Metrics", "Data Cleaning", "Python Pandas",
    ],
    "data scientist": [
        "Machine Learning", "Feature Engineering", "Model Evaluation",
        "Python", "Statistics", "Deep Learning", "MLOps",
        "Model Deployment", "Experiment Design",
    ],
    "machine learning engineer": [
        "ML Pipelines", "MLOps", "Model Serving", "Python",
        "TensorFlow/PyTorch", "Docker/Kubernetes", "Feature Stores",
        "A/B Testing", "Distributed Training",
    ],
    "product analyst": [
        "Metrics & KPIs", "Funnels", "A/B Experimentation",
        "Retention Analysis", "User Behavior", "SQL",
        "Product Sense", "Cohort Analysis",
    ],
    "software engineer": [
        "Data Structures", "Algorithms", "System Design",
        "Object-Oriented Design", "APIs", "Databases",
        "Concurrency", "Testing", "Code Quality",
    ],
    "backend engineer": [
        "APIs", "Databases", "System Design", "Caching",
        "Message Queues", "Authentication", "Microservices",
        "Performance", "SQL/NoSQL",
    ],
    "frontend engineer": [
        "React/Vue/Angular", "JavaScript", "CSS", "Performance",
        "State Management", "APIs", "Accessibility", "Testing",
        "Browser Internals",
    ],
    "fullstack engineer": [
        "Frontend", "Backend APIs", "Databases", "System Design",
        "Authentication", "DevOps Basics", "Testing",
    ],
    "devops engineer": [
        "CI/CD", "Docker", "Kubernetes", "Cloud Platforms",
        "Infrastructure as Code", "Monitoring", "Linux",
        "Security", "Networking",
    ],
    "product manager": [
        "Product Strategy", "Roadmapping", "Metrics",
        "User Research", "Prioritization", "Stakeholder Management",
        "Go-to-Market", "Data-Driven Decisions",
    ],
    "default": [
        "Problem Solving", "System Design", "Technical Fundamentals",
        "Code Quality", "Communication", "Past Projects",
    ],
}


def get_role_topics(role: str) -> List[str]:
    """Return topic clusters for a given role string."""
    if not role:
        return ROLE_TOPIC_MAP["default"]
    role_lower = role.lower().strip()
    for key, topics in ROLE_TOPIC_MAP.items():
        if key in role_lower or role_lower in key:
            return topics
    # Fuzzy word-level match
    for key, topics in ROLE_TOPIC_MAP.items():
        if any(word in role_lower for word in key.split()):
            return topics
    return ROLE_TOPIC_MAP["default"]


# ─── Groq Chat Helper ─────────────────────────────────────────────────────────
async def groq_chat(
    messages: List[Dict[str, str]],
    temperature: float = 0.1,
    max_tokens: int = 2048,
    response_json: bool = False,
) -> str:
    """
    Calls the Groq API with automatic retry on HTTP 429 (rate limit).

    Retry schedule: up to 2 retries with 1 s → 2 s backoff.
    In-memory cooldown: if a 429 was seen within _COOLDOWN_SECONDS, the API
    call is skipped immediately and RuntimeError('rate_limited') is raised so
    callers can go straight to their fallback without hammering the endpoint.

    Raises:
        RuntimeError('rate_limited')  – 429 exhausted or cooldown active
        RuntimeError('api_error')     – any other non-429 failure
    Never propagates raw httpx exceptions or HTTP status strings to callers.
    """
    global _last_429_time

    if IS_MOCK_MODE:
        if response_json:
            return json.dumps({
                "overall_score": 78,
                "technical_score": 75,
                "communication_score": 82,
                "resume_strength_score": 70,
                "role_fit_score": 72,
                "strengths": [
                    "Good problem solving",
                    "Clear communication",
                    "Relevant project experience",
                ],
                "weaknesses": [
                    "Could improve system design depth",
                    "Limited discussion of trade-offs",
                ],
                "missing_skills": ["Kubernetes", "Distributed Systems"],
                "verdict": (
                    "Solid candidate with a strong foundation. "
                    "Recommend a follow-up round focused on system design."
                ),
            })
        return "This is a mock response. Please set a valid GROQ_API_KEY in your .env file."

    # ── In-memory cooldown gate ────────────────────────────────────────────────
    since_last_429 = time.monotonic() - _last_429_time
    if since_last_429 < _COOLDOWN_SECONDS:
        remaining = int(_COOLDOWN_SECONDS - since_last_429)
        logger.warning(
            "Groq cooldown active — skipping API call (%ds remaining after last 429)",
            remaining,
        )
        raise RuntimeError("rate_limited")

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload: Dict[str, Any] = {
        "model": "llama-3.3-70b-versatile",
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if response_json:
        payload["response_format"] = {"type": "json_object"}

    # ── Retry loop with exponential backoff on 429 ─────────────────────────────
    _retry_delays = [1.0, 2.0]  # wait 1 s, then 2 s before giving up
    t0 = time.perf_counter()

    async with httpx.AsyncClient(timeout=60.0) as client:
        last_exc: Optional[Exception] = None
        for attempt, delay in enumerate([0.0] + _retry_delays):
            if delay:
                logger.warning(
                    "Groq 429 — retrying in %.0fs (attempt %d/%d)",
                    delay, attempt, len(_retry_delays),
                )
                await asyncio.sleep(delay)

            try:
                response = await client.post(GROQ_BASE_URL, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                elapsed = time.perf_counter() - t0
                logger.info(
                    "Groq response received in %.2fs (tokens_used=%s, attempt=%d)",
                    elapsed, data.get("usage", {}).get("total_tokens", "?"), attempt + 1,
                )
                return data["choices"][0]["message"]["content"]

            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 429:
                    _last_429_time = time.monotonic()
                    logger.error(
                        "Groq API 429 Too Many Requests (attempt %d/%d, elapsed=%.2fs): %s",
                        attempt + 1, len(_retry_delays) + 1,
                        time.perf_counter() - t0, exc,
                    )
                    last_exc = exc
                    # exhaust retries before giving up
                    continue
                else:
                    logger.error(
                        "Groq API HTTP error (status=%d, elapsed=%.2fs): %s",
                        exc.response.status_code, time.perf_counter() - t0, exc,
                    )
                    raise RuntimeError("api_error") from None

            except Exception as exc:
                logger.error(
                    "Groq API unexpected error (attempt %d, elapsed=%.2fs): %s",
                    attempt + 1, time.perf_counter() - t0, exc,
                )
                raise RuntimeError("api_error") from None

        # All retries exhausted on 429
        logger.error(
            "Groq API 429 persists after %d retries — activating %ds cooldown",
            len(_retry_delays), int(_COOLDOWN_SECONDS),
        )
        raise RuntimeError("rate_limited") from None


# ─── JSON Extraction ──────────────────────────────────────────────────────────
def extract_json_safe(text: str) -> dict:
    """Extract JSON from a model response, handling markdown fences."""
    text = text.strip()
    text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'```\s*$', '', text)
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = re.search(r'\{[\s\S]+\}', text)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    raise ValueError(f"No valid JSON in response: {text[:200]}")


# ─── Resume Text Extraction ───────────────────────────────────────────────────
def _extract_pdf_text(content: bytes) -> str:
    """Extract text from PDF bytes using pdfplumber."""
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            pages: List[str] = []
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    pages.append(page_text)
            extracted = "\n".join(pages).strip()
            logger.info("pdfplumber extracted %d chars from %d pages", len(extracted), len(pdf.pages))
            return extracted
    except Exception:
        logger.exception("pdfplumber extraction failed")
        return ""


def _extract_docx_text(content: bytes) -> str:
    """Extract text from DOCX bytes using python-docx."""
    try:
        doc = DocxDocument(io.BytesIO(content))
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        extracted = "\n".join(paragraphs)
        logger.info("python-docx extracted %d chars from %d paragraphs", len(extracted), len(paragraphs))
        return extracted
    except Exception:
        logger.exception("python-docx extraction failed")
        return ""


def extract_resume_text(content: bytes, filename: str) -> str:
    """Dispatch to the correct parser based on file extension."""
    fname = (filename or "").lower()
    if fname.endswith(".pdf"):
        return _extract_pdf_text(content)
    elif fname.endswith(".docx"):
        return _extract_docx_text(content)
    else:
        # .txt or unknown — decode as UTF-8
        return content.decode("utf-8", errors="ignore").strip()


# ─── DB Helpers ───────────────────────────────────────────────────────────────
async def get_session(db: Any, session_id: str) -> Optional[Dict[str, Any]]:
    """Load a session document from MongoDB. Returns None if unavailable."""
    if db is None:
        return None
    try:
        return await db["interview_sessions"].find_one({"session_id": session_id})
    except Exception:
        logger.exception("Failed to load session %s from DB", session_id)
        return None


async def update_session(db: Any, session_id: str, update: Dict[str, Any]) -> None:
    """Apply a MongoDB update operator to a session document."""
    if db is None:
        return
    try:
        await db["interview_sessions"].update_one({"session_id": session_id}, update)
    except Exception:
        logger.exception("Failed to update session %s in DB", session_id)


# ─── Job Role Extraction ──────────────────────────────────────────────────────
def _extract_role_from_text(text: str) -> Optional[str]:
    """
    Try to extract a job role name from a user message.
    Returns the role string or None.
    """
    if not text or len(text.strip()) < 3:
        return None
    patterns = [
        r'(?:for|targeting|applying for|preparing for|interview for|role of|position of|as a)\s+(?:a\s+|an\s+)?([a-zA-Z\s\-/]+?(?:engineer|developer|architect|manager|designer|analyst|scientist|lead|specialist|consultant))',
        r'(?:role|position|job|title)\s*(?:is|:)?\s*([a-zA-Z\s\-/]+?(?:engineer|developer|architect|manager|designer|analyst|scientist|lead|specialist|consultant))',
        r'^([a-zA-Z\s\-/]+?(?:engineer|developer|architect|manager|designer|analyst|scientist|lead|specialist|consultant))\s*$',
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if m:
            role = m.group(1).strip().rstrip('.')
            if 3 < len(role) < 80:
                return role

    # Short direct reply that names a common role
    text_stripped = text.strip().rstrip('.')
    role_keywords = [
        "engineer", "developer", "analyst", "scientist", "manager",
        "designer", "architect", "specialist", "lead", "consultant",
    ]
    if 3 < len(text_stripped) < 80 and any(kw in text_stripped.lower() for kw in role_keywords):
        return text_stripped

    return None


# ─── Phase Transition Logic ───────────────────────────────────────────────────
def detect_intent(
    user_text: str,
    current_phase: str,
    session: Dict[str, Any],
) -> str:
    """
    Determine the new phase after processing this user message.
    Returns the new phase string (may be unchanged).
    """
    if current_phase == "introduction":
        # Any meaningful response → move to job_role
        if len(user_text.strip()) > 5:
            return "job_role"

    elif current_phase == "job_role":
        # Move to resume once we have a role (either already in DB or just extracted)
        if session.get("target_role") or _extract_role_from_text(user_text):
            return "resume"

    elif current_phase == "resume":
        # Already have an uploaded resume → move to technical
        if session.get("resume_data", {}).get("raw_text"):
            return "technical"
        # User pasted a long text that looks like a resume
        text_lower = user_text.lower()
        if len(user_text) > 200 and any(
            kw in text_lower for kw in
            ["experience", "education", "skills", "work", "university",
             "college", "degree", "company", "developer", "engineer", "project"]
        ):
            return "technical"

        # If user provides a shorter answer (like briefly describing skills), also move on.
        if len(user_text.strip()) > 0:
            return "technical"

    return current_phase


# ─── Prompt Builders ──────────────────────────────────────────────────────────
_SYSTEM_PROMPT = (
    "You are Alex Chen, a professional Senior Technical Recruiter and Interviewer. "
    "You conduct structured, empathetic, and insightful technical interviews. "
    "You ask ONE question at a time. Responses are concise (2–4 sentences max). "
    "Never prefix your replies with 'Interviewer:', 'Alex:', or any label. "
    "Never break character. Be warm but rigorous."
)


def _build_intro_prompt(history: str) -> str:
    return f"""You are Alex Chen, a professional technical interviewer.

CURRENT PHASE: Introduction

CONVERSATION SO FAR:
{history or "(Session just started)"}

The candidate has just introduced themselves. Warmly acknowledge their introduction in 1 sentence, then ask what specific role or position they are targeting or preparing for. Keep it natural. ONE question only. Do NOT ask about their resume yet."""


def _build_job_role_prompt(history: str, user_text: str) -> str:
    return f"""You are Alex Chen, a professional technical interviewer.

CURRENT PHASE: Role Collection

CONVERSATION SO FAR:
{history}

CANDIDATE'S LATEST RESPONSE: "{user_text}"

If they clearly stated a target role, acknowledge it warmly (name the role) and ask them to share their resume — they can paste the text directly into chat or upload a file using the button above. If the role is still unclear, politely ask them to clarify which specific role they are preparing for. ONE response only."""


def _build_resume_prompt(history: str, target_role: str) -> str:
    return f"""You are Alex Chen, a professional technical interviewer.

CURRENT PHASE: Resume Collection

TARGET ROLE: {target_role or "the role they mentioned"}

CONVERSATION SO FAR:
{history}

The candidate is in the resume sharing phase. If they have just shared their experience or background details, acknowledge what they've shared briefly and let them know you're moving to the technical interview. If they haven't shared yet, ask them to paste their resume text or describe their key skills and experience in the chat. ONE response only."""


def _build_technical_prompt(
    history: str,
    resume_text: str,
    target_role: str,
    asked_topics: List[str],
    user_text: str,
) -> str:
    role_topics = get_role_topics(target_role)
    covered = [t for t in asked_topics if t]
    remaining = [t for t in role_topics if t not in covered]
    suggest = remaining[:3] if remaining else role_topics[:3]

    resume_snippet = resume_text[:3000] + ("...[truncated]" if len(resume_text) > 3000 else "")

    return f"""You are Alex Chen, a senior technical interviewer conducting a live technical interview.

═══════════════════════════════════════════════
CANDIDATE RESUME:
{resume_snippet if resume_snippet else "(Not provided — ask generic role-relevant questions)"}
═══════════════════════════════════════════════

TARGET ROLE: {target_role or "Software Engineer"}

TOPICS ALREADY COVERED: {", ".join(covered) if covered else "None yet"}
SUGGESTED NEXT TOPICS: {", ".join(suggest)}

INTERVIEW CONVERSATION:
{history}

CANDIDATE'S LATEST RESPONSE:
"{user_text}"

INSTRUCTIONS:
1. Silently evaluate the depth of their answer (do NOT say "Good answer" or score them out loud).
2. If the answer was shallow → drill deeper on the same topic.
3. If the answer showed competence → pivot to a new suggested topic.
4. If the resume mentions specific projects, technologies, or companies → reference them directly.
   Example: "I see you worked on a churn prediction model at [Company] — what evaluation metric did you prioritize and why?"
5. Ask exactly ONE focused technical question. Be specific, not generic.
6. Keep your response to 2-3 sentences maximum.
7. Never repeat a topic already covered.

Respond now with your next interview question ONLY. No labels, no preamble, no scoring commentary."""


# ─── ENDPOINTS ────────────────────────────────────────────────────────────────

@router.post("/start", response_model=InterviewStartResponse)
async def start_interview(db=Depends(get_database)):
    """
    Creates a new interview session. The AI introduces itself and
    asks the candidate to introduce themselves.
    Phase starts at 'introduction' and is stored in MongoDB.
    """
    session_id = str(uuid.uuid4())
    logger.info("[START] Creating new session: %s", session_id)

    intro_prompt = (
        "You are starting a fresh technical interview session. "
        "Introduce yourself as Alex Chen, Senior Technical Recruiter. "
        "Be warm and professional. Ask the candidate to introduce themselves — "
        "their name, their background, and what brings them here today. "
        "Keep it to 2-3 sentences. Do NOT ask about their role or resume yet."
    )
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": intro_prompt},
    ]

    try:
        initial_question = await groq_chat(messages, temperature=0.7, max_tokens=200)
        initial_question = re.sub(
            r'^(Interviewer|Alex|AI|System)[:\s]+', '', initial_question, flags=re.IGNORECASE
        ).strip()
    except Exception:
        logger.exception("[START] Groq API failure — using fallback greeting")
        initial_question = (
            "Hello! I'm Alex Chen, Senior Technical Recruiter. "
            "Welcome to today's technical interview session. "
            "To start, could you please introduce yourself — "
            "tell me your name, your background, and what brings you here today?"
        )

    # Persist the session document to MongoDB
    if db is not None:
        try:
            session_doc: Dict[str, Any] = {
                "session_id": session_id,
                "status": "ongoing",
                "phase": "introduction",
                "target_role": "",
                "resume_data": {"raw_text": "", "filename": "", "char_count": 0},
                "candidate_name": "",
                "asked_topics": [],
                "created_at": datetime.now(timezone.utc),
                "message_history": [
                    {
                        "sender": "SYSTEM",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "text": initial_question,
                    }
                ],
            }
            await db["interview_sessions"].insert_one(session_doc)
            logger.info("[START] Session persisted to MongoDB: %s", session_id)
        except Exception:
            logger.exception("[START] Failed to persist session %s", session_id)

    return InterviewStartResponse(session_id=session_id, initial_question=initial_question)


@router.post("/respond", response_model=InterviewRespondResponse)
async def respond_interview(
    payload: InterviewRespondRequest,
    db=Depends(get_database),
):
    """
    Processes a candidate's response and returns the next interviewer question.

    Architecture:
    - Phase is read from MongoDB (DB-authoritative, not inferred from message count)
    - Message history is maintained in MongoDB (server is source of truth)
    - Resume text and target role are injected from DB into every technical prompt
    - asked_topics is tracked to prevent repetitive questioning
    """
    sid = payload.session_id
    t_start = time.perf_counter()
    user_text = payload.response.strip()
    logger.info("[RESPOND] session=%s user_len=%d is_complete=%s", sid, len(user_text), payload.is_complete)

    # ── Load authoritative session state from MongoDB ─────────────────────────
    session = await get_session(db, sid) or {}
    current_phase: str = session.get("phase", "introduction")
    target_role: str = session.get("target_role", "")
    resume_data: Dict[str, Any] = session.get("resume_data", {})
    resume_text: str = resume_data.get("raw_text", "")
    asked_topics: List[str] = session.get("asked_topics", [])
    db_history: List[Dict[str, Any]] = session.get("message_history", [])

    logger.info(
        "[RESPOND] phase=%s role='%s' resume_chars=%d history_msgs=%d topics_covered=%s",
        current_phase, target_role, len(resume_text),
        len(db_history), asked_topics,
    )

    # ── Build chat history text (DB-authoritative, fallback to client) ────────
    history_items = db_history if db_history else [
        (m.model_dump() if isinstance(m, ChatMessageSchema) else m)
        for m in payload.chat_history
    ]
    chat_history_text = "\n".join(
        f"{item.get('sender', 'UNKNOWN')}: {item.get('text', '')}"
        for item in history_items
    )

    # ── Try to extract target role from user message if not yet stored ────────
    if not target_role and current_phase in ("introduction", "job_role", "resume"):
        extracted = _extract_role_from_text(user_text)
        if extracted:
            target_role = extracted
            logger.info("[RESPOND] Extracted target_role='%s'", target_role)

    # ── Detect phase transition ───────────────────────────────────────────────
    if payload.is_complete:
        new_phase = "assessment"
    else:
        new_phase = detect_intent(user_text, current_phase, session)

    # ── Detect pasted resume (long resume-like text in chat) ─────────────────
    pasted_resume = ""
    if current_phase == "resume" and not resume_text and len(user_text) > 200:
        text_lower = user_text.lower()
        if any(kw in text_lower for kw in
               ["experience", "education", "skills", "work", "university",
                "college", "degree", "company", "developer", "engineer", "project"]):
            pasted_resume = user_text
            resume_text = user_text
            new_phase = "technical"
            logger.info("[RESPOND] Captured pasted resume (%d chars)", len(pasted_resume))

    logger.info("[RESPOND] phase_transition: %s → %s", current_phase, new_phase)

    # ── Generate AI response ──────────────────────────────────────────────────
    if payload.is_complete:
        # ── Final assessment / closing ────────────────────────────────────────
        role_topics = get_role_topics(target_role)
        assessment_prompt = f"""You are a senior technical hiring manager wrapping up an interview.

CANDIDATE RESUME:
{resume_text or "(Not provided)"}

TARGET ROLE: {target_role or "Not specified"}
ROLE REQUIREMENTS: {", ".join(role_topics)}

COMPLETE INTERVIEW TRANSCRIPT:
{chat_history_text}

CANDIDATE'S FINAL MESSAGE: "{user_text}"

Provide a comprehensive written assessment covering:
1. **Technical Knowledge** — depth and accuracy of answers
2. **Communication** — clarity, structure, confidence
3. **Problem-Solving** — methodology, creativity
4. **Role Fit** — alignment between resume/answers and target role requirements
5. **Key Strengths** and **Areas for Improvement**
6. **Hiring Verdict** — 1-2 sentence recommendation

Format as clean Markdown. Be specific and cite actual moments from the conversation."""

        messages = [
            {"role": "system", "content": "You are a senior technical hiring manager. Be honest, specific, and constructive."},
            {"role": "user", "content": assessment_prompt},
        ]
        try:
            reply = await groq_chat(messages, temperature=0.3, max_tokens=1500)
        except Exception:
            logger.exception("[RESPOND] Assessment generation failed for session %s", sid)
            reply = (
                "## Assessment\n\n"
                "Unable to generate a detailed assessment at this time. "
                "Please use the dedicated `/interview/assess` endpoint for a structured evaluation."
            )

    else:
        # ── Generate next interview question ──────────────────────────────────
        if new_phase == "introduction":
            prompt = _build_intro_prompt(chat_history_text)
        elif new_phase == "job_role":
            prompt = _build_job_role_prompt(chat_history_text, user_text)
        elif new_phase == "resume":
            prompt = _build_resume_prompt(chat_history_text, target_role)
        else:  # technical
            prompt = _build_technical_prompt(
                chat_history_text, resume_text, target_role, asked_topics, user_text
            )

        logger.info("[RESPOND] Prompt built (phase=%s, len=%d chars)", new_phase, len(prompt))

        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        try:
            reply = await groq_chat(messages, temperature=0.7, max_tokens=400)
            reply = re.sub(
                r'^(Interviewer|Alex|AI|System)[:\s]+', '', reply, flags=re.IGNORECASE
            ).strip()
        except RuntimeError as exc:
            if str(exc) == "rate_limited":
                logger.error(
                    "[RESPOND] Groq rate-limited for session %s (phase=%s) — serving fallback",
                    sid, new_phase,
                )
            else:
                logger.error(
                    "[RESPOND] Groq API error for session %s (phase=%s) — serving fallback",
                    sid, new_phase,
                )
            import random
            tech_topics = [t for t in get_role_topics(target_role) if t not in asked_topics]
            tech_fallback = (
                f"I'm experiencing a brief technical delay, but let's keep going. "
                f"Could you tell me about your experience with {random.choice(tech_topics)}?"
            ) if tech_topics else (
                "I'm experiencing high demand right now — let's continue. "
                "Could you walk me through a challenging technical problem you solved recently?"
            )

            # Phase-appropriate fallback messages — no raw exception text ever reaches the client
            _phase_fallbacks = {
                "introduction": (
                    "Thanks for being here — I'm experiencing a brief technical delay. "
                    "Could you tell me a bit about your professional background and what brings you to this interview today?"
                ),
                "job_role": (
                    "Apologies for the brief pause — could you clarify the specific role "
                    "or position you're preparing for? That'll help me tailor the interview."
                ),
                "resume": (
                    "I'm experiencing high demand right now, but let's keep going. "
                    "Could you describe your most relevant experience or walk me through your key skills?"
                ),
                "technical": tech_fallback,
            }
            reply = _phase_fallbacks.get(
                new_phase,
                (
                    "I'm experiencing a brief technical delay. "
                    "Let's keep the conversation going — could you elaborate on your last answer?"
                ),
            )
        except Exception:
            logger.exception(
                "[RESPOND] Unexpected error during question generation for session %s (phase=%s)",
                sid, new_phase,
            )
            reply = (
                "I'm experiencing a brief technical delay. "
                "Let's keep the conversation going — could you elaborate on your last answer?"
            )

    # ── Update asked_topics if in technical phase ─────────────────────────────
    if new_phase == "technical" and reply:
        all_topics = get_role_topics(target_role)
        for topic in all_topics:
            if topic.lower() in reply.lower() and topic not in asked_topics:
                asked_topics.append(topic)
                logger.info("[RESPOND] Marked topic covered: '%s'", topic)
                break

    # ── Persist updated state to MongoDB ─────────────────────────────────────
    now_iso = datetime.now(timezone.utc).isoformat()
    set_fields: Dict[str, Any] = {
        "phase": new_phase,
        "status": "completed" if payload.is_complete else "ongoing",
        "asked_topics": asked_topics,
    }
    if target_role:
        set_fields["target_role"] = target_role
    if pasted_resume:
        set_fields["resume_data"] = {
            "raw_text": pasted_resume,
            "filename": "pasted",
            "char_count": len(pasted_resume),
        }
    if payload.is_complete:
        set_fields["assessment_rubric"] = {"markdown": reply}

    await update_session(
        db, sid,
        {
            "$set": set_fields,
            "$push": {
                "message_history": {
                    "$each": [
                        {"sender": "USER", "timestamp": now_iso, "text": user_text},
                        {"sender": "SYSTEM", "timestamp": now_iso, "text": reply},
                    ]
                }
            },
        },
    )

    elapsed = time.perf_counter() - t_start
    logger.info("[RESPOND] Completed in %.2fs — new_phase=%s", elapsed, new_phase)

    return InterviewRespondResponse(reply=reply, phase=new_phase)


@router.post("/upload_resume")
async def upload_resume(
    file: UploadFile = File(...),
    session_id: str = Form(...),
    db=Depends(get_database),
):
    """
    Accepts PDF, DOCX, or TXT resume files.
    Extracts full text using pdfplumber/python-docx, stores in MongoDB,
    and advances the interview phase to 'technical'.
    """
    filename = file.filename or "resume"
    logger.info("[UPLOAD] session=%s file='%s' content_type=%s", session_id, filename, file.content_type)

    try:
        content = await file.read()
        extracted_text = extract_resume_text(content, filename)

        if not extracted_text:
            logger.warning("[UPLOAD] No text extracted from '%s'", filename)
            return JSONResponse(
                {
                    "success": False,
                    "message": (
                        f"Could not extract text from '{filename}'. "
                        "Try saving as .txt or copy-paste the content directly in the chat."
                    ),
                },
                status_code=400,
            )

        char_count = len(extracted_text)
        logger.info("[UPLOAD] Successfully extracted %d chars from '%s'", char_count, filename)

        # Retrieve current session to keep target_role
        session = await get_session(db, session_id) or {}
        target_role = session.get("target_role", "")

        resume_doc: Dict[str, Any] = {
            "raw_text": extracted_text,
            "filename": filename,
            "char_count": char_count,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        }

        # Store resume + advance phase to 'technical'
        await update_session(
            db, session_id,
            {"$set": {"resume_data": resume_doc, "phase": "technical"}},
        )
        logger.info("[UPLOAD] Phase advanced to 'technical' for session %s", session_id)

        preview = extracted_text[:500] + ("..." if char_count > 500 else "")
        return JSONResponse({
            "success": True,
            "message": f"Resume parsed successfully — {char_count:,} characters extracted.",
            "extracted_text": preview,
            "char_count": char_count,
            "target_role": target_role,
        })

    except Exception as exc:
        logger.exception("[UPLOAD] Resume upload/parse failed for session %s", session_id)
        return JSONResponse(
            {
                "success": False,
                "message": f"Upload failed: {type(exc).__name__}: {exc}",
            },
            status_code=400,
        )


@router.post("/assess", response_model=InterviewAssessResponse)
async def assess_interview(
    payload: InterviewAssessRequest,
    db=Depends(get_database),
):
    """
    Analyzes the complete interview transcript and returns a structured assessment.
    Includes resume-strength, role-fit, skill gap, and detailed scores.
    """
    logger.info("[ASSESS] Assessing interview with %d messages", len(payload.chat_history))

    chat_history_text = "\n".join(
        f"{msg.sender}: {msg.text}" for msg in payload.chat_history
    )

    # Best-effort role extraction from transcript
    all_user_text = " ".join(
        msg.text for msg in payload.chat_history if msg.sender == "USER"
    )
    target_role = _extract_role_from_text(all_user_text) or "the target role"
    role_topics = get_role_topics(target_role)

    prompt = (
        "You are a senior technical hiring manager. Analyze this complete technical interview "
        "transcript and provide a structured, honest, specific assessment.\n\n"
        f"TARGET ROLE: {target_role}\n"
        f"ROLE REQUIREMENTS: {', '.join(role_topics)}\n\n"
        f"INTERVIEW TRANSCRIPT:\n{chat_history_text}\n\n"
        "Return a JSON object with EXACTLY these fields:\n"
        "{\n"
        '  "overall_score": <integer 0-100>,\n'
        '  "technical_score": <integer 0-100>,\n'
        '  "communication_score": <integer 0-100>,\n'
        '  "resume_strength_score": <integer 0-100, how strong their background is for this role>,\n'
        '  "role_fit_score": <integer 0-100, overall fit for the target role>,\n'
        '  "strengths": ["specific strength with example", "...", "..."],\n'
        '  "weaknesses": ["specific weakness with example", "...", "..."],\n'
        '  "missing_skills": ["skill from role requirements not demonstrated", "..."],\n'
        '  "verdict": "2-sentence hiring recommendation"\n'
        "}\n\n"
        "Rules: Scores must reflect actual observed performance, not be inflated. "
        "Strengths and weaknesses must cite specific moments from the conversation. "
        "missing_skills = skills in the role requirements that were NOT demonstrated. "
        "Return ONLY the raw JSON object. No markdown fences. No explanation."
    )

    try:
        messages = [{"role": "user", "content": prompt}]
        raw = await groq_chat(messages, temperature=0.3, max_tokens=1024, response_json=True)
        rubric = extract_json_safe(raw)

        result = InterviewAssessResponse(
            overall_score=max(0, min(100, int(rubric.get("overall_score", 75)))),
            technical_score=max(0, min(100, int(rubric.get("technical_score", 70)))),
            communication_score=max(0, min(100, int(rubric.get("communication_score", 80)))),
            resume_strength_score=max(0, min(100, int(rubric.get("resume_strength_score", 65)))),
            role_fit_score=max(0, min(100, int(rubric.get("role_fit_score", 70)))),
            strengths=[str(s) for s in rubric.get("strengths", [])[:5]],
            weaknesses=[str(w) for w in rubric.get("weaknesses", [])[:5]],
            missing_skills=[str(s) for s in rubric.get("missing_skills", [])[:8]],
            verdict=str(rubric.get("verdict", "Candidate shows promise. Recommend further evaluation.")),
        )
        logger.info(
            "[ASSESS] Complete — overall=%d technical=%d role_fit=%d",
            result.overall_score, result.technical_score, result.role_fit_score,
        )
        return result

    except Exception:
        logger.exception("[ASSESS] Groq assessment failed")
        return InterviewAssessResponse(
            overall_score=75,
            technical_score=70,
            communication_score=80,
            resume_strength_score=65,
            role_fit_score=70,
            strengths=[
                "Demonstrated technical knowledge",
                "Clear and structured communication",
                "Relevant project experience mentioned",
            ],
            weaknesses=[
                "Could provide more specific technical examples",
                "Limited discussion of system design trade-offs",
            ],
            missing_skills=[],
            verdict=(
                "Candidate shows solid foundational knowledge. "
                "Recommend a follow-up technical round focused on system design."
            ),
        )


@router.post("/generate_path", response_model=GenerateLearningPathResponse)
async def generate_learning_path(payload: GenerateLearningPathRequest):
    """Generate a personalised 30-day learning roadmap for identified skill gaps."""
    logger.info("[LEARNING_PATH] gaps=%s", payload.gaps)

    if not payload.gaps:
        return GenerateLearningPathResponse(milestones=[])

    gaps_str = ", ".join(payload.gaps)
    prompt = (
        f"Generate a 30-day learning roadmap for these skill gaps: {gaps_str}.\n\n"
        "Return a JSON array of milestones (one per skill gap, maximum 4 milestones). "
        "Each milestone MUST have exactly these fields:\n"
        '- "title": string (specific and action-oriented, e.g., "Master SQL Window Functions")\n'
        '- "description": string (2 sentences: what to learn and why it matters for the role)\n'
        '- "resources": array of exactly 3 strings (MUST be appropriate video links, such as YouTube or Udemy URLs for the specific topic)\n\n'
        "Return ONLY the raw JSON array. No markdown. No explanation."
    )

    try:
        messages = [{"role": "user", "content": prompt}]
        raw = await groq_chat(messages, temperature=0.5, max_tokens=1024, response_json=True)
        milestones_raw = extract_json_safe(raw)
        # Some models return {"milestones": [...]}
        if isinstance(milestones_raw, dict):
            milestones_raw = milestones_raw.get("milestones", list(milestones_raw.values())[0] if milestones_raw else [])

        milestones = [
            LearningMilestone(
                title=str(m.get("title", f"Master {payload.gaps[i] if i < len(payload.gaps) else 'Skill'}")),
                description=str(m.get("description", "")),
                resources=[str(r) for r in m.get("resources", [])][:3],
            )
            for i, m in enumerate(milestones_raw[:4])
            if isinstance(m, dict)
        ]
        logger.info("[LEARNING_PATH] Generated %d milestones", len(milestones))
        return GenerateLearningPathResponse(milestones=milestones)

    except Exception:
        logger.exception("[LEARNING_PATH] Generation failed, using fallback")
        fallback = [
            LearningMilestone(
                title=f"Master {gap}",
                description=(
                    f"Build foundational and advanced skills in {gap} through structured study and hands-on projects. "
                    f"Focus on real-world applications that are directly relevant to your target role."
                ),
                resources=[
                    f"https://www.youtube.com/results?search_query={gap.replace(' ', '+')}+full+course",
                    f"https://www.udemy.com/courses/search/?q={gap.replace(' ', '+')}",
                    "https://www.freecodecamp.org/",
                ],
            )
            for gap in payload.gaps[:4]
        ]
        return GenerateLearningPathResponse(milestones=fallback)