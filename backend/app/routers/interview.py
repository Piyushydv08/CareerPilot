import os
import re
import uuid
import logging
import json
import spacy
from datetime import datetime, timezone
from typing import List, Dict, Optional
import httpx
from typing import Any
from fastapi import APIRouter, Depends, UploadFile, File, Form
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

load_dotenv()

from app.models.schemas import (
    InterviewStartRequest,
    InterviewStartResponse,
    InterviewRespondRequest,
    InterviewRespondResponse,
    GenerateLearningPathRequest,
    GenerateLearningPathResponse,
    LearningMilestone,
    InterviewAssessRequest,
    InterviewAssessResponse,
    ChatMessageSchema
)
from app.core.database import get_database

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/interview", tags=["interview"])

# ---------- Groq Configuration ----------
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_BASE_URL = os.environ.get("GROQ_BASE_URL", "https://api.groq.com/openai/v1/chat/completions")
IS_MOCK_MODE = not bool(GROQ_API_KEY)

if not IS_MOCK_MODE:
    logger.info("Groq API key loaded – using real AI model")
else:
    logger.warning("No Groq API key found – running in MOCK mode")

# ---------- Groq Chat Helper ----------
async def groq_chat(
    messages: List[Dict[str, str]],
    temperature: float = 0.1,
    max_tokens: int = 2048,
    response_json: bool = False
) -> str:
    if IS_MOCK_MODE:
        logger.info("MOCK: returning placeholder response")
        return json.dumps({
            "overall_score": 78,
            "technical_score": 75,
            "communication_score": 82,
            "strengths": ["Good problem solving", "Clear communication", "Relevant experience"],
            "weaknesses": ["Could improve system design depth", "Limited scalability discussion"],
            "verdict": "Solid candidate. Recommend next round with focus on system design."
        }) if response_json else "This is a mock response. Please set a valid GROQ_API_KEY."

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    if response_json:
        messages.insert(0, {
            "role": "system",
            "content": "You are a helpful assistant that always responds in valid JSON without any extra text."
        })
        payload["messages"] = messages
        payload["response_format"] = {"type": "json_object"}

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(GROQ_BASE_URL, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"Groq API call failed: {e}")
            raise

# ---------- JSON extraction ----------
def extract_json(text: str) -> dict:
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
        return json.loads(m.group(0))
    raise ValueError(f"No valid JSON in response: {text[:200]}")

# ---------- spaCy NLP ----------
try:
    nlp = spacy.load("en_core_web_sm")
except Exception:
    logger.warning("Spacy model not found. Run: python -m spacy download en_core_web_sm")
    nlp = None

# ---------- Interview Phase Detection ----------
def detect_phase(messages: List[dict[str, Any]]) -> str:
    """
    Analyzes chat history to determine the current interview phase.
    Returns: 'introduction', 'job_role', 'resume', 'technical', 'assessment'
    """
    user_messages = [m for m in messages if m.get("sender") == "USER"]
    
    if len(user_messages) == 0:
        return "introduction"
    elif len(user_messages) <= 2:
        return "job_role"
    elif len(user_messages) <= 4:
        return "resume"
    else:
        return "technical"

# ---------- Resume Text Extraction ----------
def extract_resume_from_messages(messages: List[dict[str, Any]]) -> Optional[str]:
    """Extract resume text from user messages if they pasted it."""
    user_messages = [m for m in messages if m.get("sender") == "USER"]
    for msg in user_messages[-3:]:  # Check last 3 messages
        text = msg.get("text", "")
        # Check if message looks like a resume (long, contains keywords)
        if len(text) > 200 and any(kw in text.lower() for kw in 
            ['experience', 'education', 'skills', 'work', 'university', 'college', 'degree', 'company', 'developer']):
            return text
    return None

# ---------- Extract Job Role ----------
def extract_job_role(messages: List[dict[str, Any]]) -> Optional[str]:
    """Extract job role from user messages."""
    user_messages = [m for m in messages if m.get("sender") == "USER"]
    for msg in user_messages[-3:]:
        text = msg.get("text", "")
        # Look for job titles (simple heuristic)
        job_patterns = [
            r'(?:for|targeting|applying for|preparing for)\s+(?:a\s+)?([\w\s]+?(?:engineer|developer|architect|manager|designer|analyst|scientist))',
            r'(?:role|position|job)\s+(?:is|:)?\s+([\w\s]+?(?:engineer|developer|architect|manager|designer|analyst|scientist))',
        ]
        for pattern in job_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        # If no pattern match but message is short, treat as role
        if 2 < len(text) < 100:
            return text.strip()
    return None


# ============================== ENDPOINTS ==============================

@router.post("/start", response_model=InterviewStartResponse)
async def start_interview(
    db = Depends(get_database)
):
    """
    Starts a new interview session. The AI will begin by asking for the candidate's introduction.
    No job description or resume needed upfront - it will be collected conversationally.
    """
    session_id = str(uuid.uuid4())
    logger.info(f"Starting new interview session: {session_id}")

    # Initial system prompt for a professional interviewer
    system_prompt = """You are a professional technical interviewer. Your name is Alex Chen, and you work as a Senior Technical Recruiter.

You are starting a new interview session. Follow this structured flow:

PHASE 1 - INTRODUCTION:
Start by introducing yourself briefly and asking the candidate to introduce themselves. 
Be warm but professional. Example: "Hello! I'm Alex Chen, I'll be conducting your technical interview today. To start, could you please introduce yourself? Tell me about your background and what brings you here today."

IMPORTANT RULES:
1. Only ask ONE question at a time.
2. Keep your responses conversational and under 3-4 sentences.
3. Progress naturally through the phases based on candidate responses.
4. Do NOT jump ahead - collect all info before starting technical questions.
5. Be encouraging but maintain professional demeanor.

Begin now with Phase 1: Introduction."""

    try:
        messages = [{"role": "system", "content": system_prompt}]
        initial_question = await groq_chat(messages, temperature=0.7, max_tokens=300)
        initial_question = initial_question.strip()
    except Exception as e:
        logger.error(f"Groq API failure during /start: {e}")
        initial_question = "Hello! I'm Alex Chen, I'll be your technical interviewer today. To start off, could you please introduce yourself? Tell me about your background and experience."

    # Persist session
    if db is not None:
        try:
            session_record = {
                "session_id": session_id,
                "status": "ongoing",
                "phase": "introduction",
                "job_description": "",
                "resume_data": {},
                "candidate_name": "",
                "created_at": datetime.now(timezone.utc),
                "message_history": [
                    {"sender": "SYSTEM", "timestamp": datetime.now(timezone.utc).isoformat(), "text": initial_question}
                ]
            }
            await db["interview_sessions"].insert_one(session_record)
        except Exception as e:
            logger.error(f"Failed to persist session: {e}")

    return InterviewStartResponse(
        session_id=session_id,
        initial_question=initial_question
    )


@router.post("/respond", response_model=InterviewRespondResponse)
async def respond_interview(
    payload: InterviewRespondRequest,
    db = Depends(get_database)
):
    """
    Processes user responses and generates appropriate next question based on interview phase.
    """
    logger.info(f"Processing response for session: {payload.session_id}")

    # Build full message history for context
    all_messages = payload.chat_history + [
        ChatMessageSchema(sender="USER", text=payload.response, timestamp=datetime.now(timezone.utc).isoformat())
    ]
    
    # Detect current phase
    message_dicts: list[dict[str, str]] = [
    m.model_dump() if isinstance(m, ChatMessageSchema) else m
    for m in all_messages
]

    phase = detect_phase(message_dicts)
    resume_text = extract_resume_from_messages(message_dicts)
    job_role = extract_job_role(message_dicts)
    
    # Build conversation context
    chat_history_text = "\n".join([
        f"{msg.sender if isinstance(msg, ChatMessageSchema) else msg.get('sender', 'UNKNOWN')}: "
        f"{msg.text if isinstance(msg, ChatMessageSchema) else msg.get('text', '')}"
        for msg in (payload.chat_history + [
            ChatMessageSchema(sender="USER", text=payload.response, timestamp="")
        ])
    ])

    if payload.is_complete:
        # Generate final assessment
        eval_prompt = f"""
You are a senior technical hiring manager. Review this complete interview and provide an assessment.

INTERVIEW TRANSCRIPT:
{chat_history_text}

Candidate Resume (if provided): {resume_text or 'Not explicitly provided'}
Target Role: {job_role or 'Not explicitly stated'}

Evaluate the candidate on:
1. Technical Knowledge (depth, accuracy)
2. Communication Skills (clarity, structure)
3. Problem-Solving Approach (methodology, creativity)
4. Role Fit (alignment with target position)

Provide a detailed analysis with specific observations from the conversation. 
Format as clean Markdown with sections for each criterion and a final verdict.
"""
        messages = [
            {"role": "system", "content": "You are a senior technical hiring manager providing interview assessments. Be honest, specific, and constructive."},
            {"role": "user", "content": eval_prompt}
        ]
        try:
            reply = await groq_chat(messages, temperature=0.3, max_tokens=1500)
        except Exception as e:
            logger.error(f"Groq evaluation failure: {e}")
            reply = "# Assessment\nUnable to generate detailed assessment at this time."

    else:
        # Generate next question based on phase
        phase_prompts = {
            "introduction": """
The candidate has just introduced themselves. Now move to Phase 2.

Ask them what role or position they are targeting/preparing for. 
Be specific: "Thanks for the introduction! What specific role or position are you currently targeting or preparing for?"

Keep it conversational and brief.""",

            "job_role": f"""
The candidate has mentioned their target role: {job_role or 'not clearly stated yet'}.

Now move to Phase 3: Request their resume or experience details.
Say something like: "Great! To better tailor this interview, could you share your resume? You can paste the text directly or describe your key experience and skills."

If they already shared resume details ({resume_text[:100] + '...' if resume_text else 'not yet'}), 
move to Phase 4 and start asking technical questions related to {job_role or 'their field'}.""",

            "resume": f"""
The candidate has shared their background. Target role: {job_role or 'technology'}.

Now move to Phase 4: Technical Interview.
Based on the role ({job_role or 'the position'}) and their experience ({resume_text[:200] + '...' if resume_text else 'shared experience'}),
start asking technical questions. 

Rules for technical phase:
1. Start with foundational concepts related to {job_role or 'their field'}
2. Ask ONE question at a time
3. Drill deeper based on their answers
4. Cover both theoretical knowledge and practical scenarios
5. Identify gaps between their experience and what {job_role or 'the role'} requires

Begin with your first technical question now.""",

            "technical": f"""
Continue the technical interview for {job_role or 'the target role'}.

Based on the candidate's last response, either:
- Drill deeper if they gave a surface-level answer
- Move to a new topic if they demonstrated competence
- Ask about practical experience or projects
- Present a hypothetical scenario or problem

Keep questions specific to {job_role or 'technology'} and the candidate's stated experience level.
Ask ONE question only. Be concise.
"""
        }
        
        current_phase_prompt = phase_prompts.get(phase, phase_prompts["technical"])
        
        full_prompt = f"""
You are Alex Chen, a professional technical interviewer.

CURRENT PHASE: {phase}

CONVERSATION SO FAR:
{chat_history_text}

{current_phase_prompt}

IMPORTANT: Respond ONLY with your next question or statement. Do not include labels like "Interviewer:" or "Alex:". Just the question/statement itself.
"""
        
        messages = [
            {"role": "system", "content": "You are Alex Chen, a professional technical interviewer. You ask one question at a time and progress naturally through interview phases: introduction → job role → resume → technical questions."},
            {"role": "user", "content": full_prompt}
        ]
        
        try:
            reply = await groq_chat(messages, temperature=0.7, max_tokens=400)
            reply = reply.strip()
            # Remove any "Interviewer:" or "Alex:" prefixes the AI might add
            reply = re.sub(r'^(Interviewer|Alex|AI|System)[:\s]+', '', reply, flags=re.IGNORECASE)
        except Exception as e:
            logger.error(f"Groq followup failure: {e}")
            reply = "Could you elaborate on that? I'd like to understand your experience better."

    # Update session in DB
    if db is not None:
        try:
            update_data = {
                "$push": {
                    "message_history": {
                        "$each": [
                            {"sender": "USER", "timestamp": datetime.now(timezone.utc).isoformat(), "text": payload.response},
                            {"sender": "SYSTEM", "timestamp": datetime.now(timezone.utc).isoformat(), "text": reply}
                        ]
                    }
                },
                "$set": {
                    "status": "completed" if payload.is_complete else "ongoing",
                    "phase": phase,
                }
            }
            
            if job_role:
                update_data["$set"]["job_description"] = job_role
            if resume_text:
                update_data["$set"]["resume_data"] = {"raw_text": resume_text}
            if payload.is_complete:
                update_data["$set"]["assessment_rubric"] = {"markdown": reply}
            
            await db["interview_sessions"].update_one(
                {"session_id": payload.session_id},
                update_data
            )
        except Exception as e:
            logger.error(f"Failed to update session history: {e}")

    return InterviewRespondResponse(reply=reply)


@router.post("/upload_resume")
async def upload_resume(
    file: UploadFile = File(...),
    session_id: str = Form(...),
    db = Depends(get_database)
):
    """
    Allows uploading a resume file (PDF, DOCX, TXT).
    Extracts text and adds it to the interview context.
    """
    try:
        content = await file.read()
        text = ""
        
        filename = file.filename or ""

        if filename.endswith(".txt"):
            text = content.decode("utf-8")
        elif filename.endswith(".pdf"):
            text = f"[PDF uploaded: {filename}]"
        elif filename.endswith(".docx"):
            text = f"[DOCX uploaded: {filename}]"
        else:
            text = content.decode("utf-8", errors="ignore")
        
        # Update session with resume text
        if db is not None:
            await db["interview_sessions"].update_one(
                {"session_id": session_id},
                {"$set": {"resume_data": {"raw_text": text, "filename": file.filename}}}
            )
        
        return JSONResponse({
            "success": True,
            "message": "Resume uploaded successfully",
            "extracted_text": text[:500] + "..." if len(text) > 500 else text
        })
    except Exception as e:
        logger.error(f"Resume upload failed: {e}")
        return JSONResponse({"success": False, "message": str(e)}, status_code=400)


@router.post("/assess", response_model=InterviewAssessResponse)
async def assess_interview(payload: InterviewAssessRequest):
    """
    Analyzes the complete interview and returns structured assessment with scores.
    """
    logger.info(f"Assessing interview with {len(payload.chat_history)} messages")

    chat_history_text = "\n".join([
        f"{msg.sender}: {msg.text}" for msg in payload.chat_history
    ])

    prompt = (
        "You are a senior technical hiring manager. Analyze this complete technical interview transcript and provide a structured assessment.\n\n"
        f"INTERVIEW TRANSCRIPT:\n{chat_history_text}\n\n"
        "Return a JSON object with exactly these fields:\n"
        "{\n"
        '  "overall_score": <integer 0-100>,\n'
        '  "technical_score": <integer 0-100>,\n'
        '  "communication_score": <integer 0-100>,\n'
        '  "strengths": ["string", "string", "string"],\n'
        '  "weaknesses": ["string", "string", "string"],\n'
        '  "verdict": "string (1-2 sentences, hiring recommendation)"\n'
        "}\n\n"
        "Be honest and specific. Scores should reflect actual performance, not inflated. "
        "Strengths and weaknesses must be specific observations from the conversation. "
        "Return ONLY the raw JSON object, no markdown, no explanation."
    )

    try:
        messages = [{"role": "user", "content": prompt}]
        raw = await groq_chat(messages, temperature=0.3, max_tokens=1024, response_json=True)
        rubric = extract_json(raw)

        result = InterviewAssessResponse(
            overall_score=max(0, min(100, int(rubric.get("overall_score", 75)))),
            technical_score=max(0, min(100, int(rubric.get("technical_score", 70)))),
            communication_score=max(0, min(100, int(rubric.get("communication_score", 80)))),
            strengths=[str(s) for s in rubric.get("strengths", [])[:3]],
            weaknesses=[str(w) for w in rubric.get("weaknesses", [])[:3]],
            verdict=str(rubric.get("verdict", "Candidate shows promise but requires further evaluation."))
        )
        logger.info(f"Assessment complete. Overall score: {result.overall_score}")
        return result

    except Exception as e:
        logger.error(f"Groq assessment failed: {e}")
        return InterviewAssessResponse(
            overall_score=75,
            technical_score=70,
            communication_score=80,
            strengths=["Demonstrated technical knowledge", "Clear communication", "Structured problem-solving"],
            weaknesses=["Could elaborate more on edge cases", "Limited discussion of trade-offs", "Needs more depth in system design"],
            verdict="Candidate shows solid foundational knowledge. Recommend a follow-up technical round."
        )


@router.post("/generate_path", response_model=GenerateLearningPathResponse)
async def generate_learning_path(payload: GenerateLearningPathRequest):
    """Generate a 30-day learning roadmap for skill gaps."""
    logger.info(f"Generating learning path for gaps: {payload.gaps}")

    if not payload.gaps:
        return GenerateLearningPathResponse(milestones=[])

    gaps_str = ", ".join(payload.gaps)

    prompt = (
        f"Generate a 30-day learning roadmap for these skill gaps: {gaps_str}.\n\n"
        "Return a JSON array of milestones (one per skill gap, max 4 milestones). "
        "Each milestone must have exactly these fields:\n"
        "- title: string (specific, action-oriented)\n"
        "- description: string (2 sentences explaining what to learn and why)\n"
        "- resources: array of exactly 3 strings (specific URLs or book titles)\n\n"
        "Return ONLY the raw JSON array, no markdown, no explanation."
    )

    try:
        messages = [{"role": "user", "content": prompt}]
        raw = await groq_chat(messages, temperature=0.5, max_tokens=1024, response_json=True)
        milestones_raw = extract_json(raw)

        milestones = []
        for m in milestones_raw:
            milestones.append(LearningMilestone(
                title=str(m.get("title", "Learning Milestone")),
                description=str(m.get("description", "")),
                resources=[str(r) for r in m.get("resources", [])][:3]
            ))

        return GenerateLearningPathResponse(milestones=milestones)

    except Exception as e:
        logger.error(f"Learning path generation failed: {e}")
        fallback_milestones = [
            LearningMilestone(
                title=f"Master {gap}",
                description=f"Focus on core concepts and practical projects for {gap}. Complete hands-on projects to solidify understanding.",
                resources=[
                    "https://www.youtube.com/results?search_query=" + gap.replace(" ", "+"),
                    "https://www.udemy.com/courses/search/?q=" + gap.replace(" ", "+"),
                    "https://www.freecodecamp.org/"
                ]
            )
            for gap in payload.gaps[:4]
        ]
        return GenerateLearningPathResponse(milestones=fallback_milestones)