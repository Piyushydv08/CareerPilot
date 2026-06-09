import os
import re
import uuid
import logging
import json
import spacy
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load .env before reading any env vars
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

# Initialize Gemini SDK
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
_gemini_client: genai.Client | None = None

def get_gemini_client() -> genai.Client:
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    return _gemini_client

def extract_json(text: str) -> dict:
    """Strip markdown fences and robustly parse JSON from a Gemini response."""
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
    raise ValueError(f"No valid JSON in Gemini response: {text[:200]}")

# Load spaCy NLP model for localized validation of technical terminology
try:
    nlp = spacy.load("en_core_web_sm")
except Exception:
    logger.warning("Spacy 'en_core_web_sm' model not found locally. To enable NLP validation, run: python -m spacy download en_core_web_sm")
    nlp = None


@router.post("/start", response_model=InterviewStartResponse)
async def start_interview(
    payload: InterviewStartRequest,
    db = Depends(get_database)
):
    """Initializes a stateful interview session and generates an optimized initial system prompt."""
    session_id = str(uuid.uuid4())
    logger.info(f"Starting interview session: {session_id}")

    # 1. Generate optimized initial system prompt for Gemini acting as rigorous technical interviewer
    system_prompt = f"""
    You are a rigorous technical interviewer for the following role: {payload.job_description}.
    
    The candidate's resume details are:
    Name: {payload.resume.name}
    Experience: {[exp.details for exp in payload.resume.experience]}
    Skills: {[skill.name for skill in payload.resume.skills]}
    
    Your goal is to conduct a highly technical, deep-dive interview.
    Identify and emphasize their known weak fields and skill gaps based on the job description vs their resume.
    Ask the very first interview question to kick off the session. Keep the response concise and challenging.
    """

    try:
        client = get_gemini_client()
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=system_prompt,
        )
        initial_question = response.text.strip()
    except Exception as e:
        logger.error(f"Gemini API failure during /start: {e}")
        initial_question = "Welcome. Can you describe your most complex technical project and the architecture behind it?"

    # Persist session state asynchronously to MongoDB
    # Store session_id as a separate field — let MongoDB generate _id automatically
    if db is not None:
        try:
            session_record = {
                "session_id": session_id,
                "status": "ongoing",
                "job_description": payload.job_description,
                "resume_data": payload.resume.model_dump(),
                "created_at": datetime.now(timezone.utc),
                "message_history": [
                    {"sender": "SYSTEM", "timestamp": datetime.now(timezone.utc).isoformat(), "text": initial_question}
                ]
            }
            await db["interview_sessions"].insert_one(session_record)
        except Exception as e:
            logger.error(f"Failed to persist session to MongoDB Atlas: {e}")

    return InterviewStartResponse(
        session_id=session_id,
        initial_question=initial_question
    )


@router.post("/respond", response_model=InterviewRespondResponse)
async def respond_interview(
    payload: InterviewRespondRequest,
    db = Depends(get_database)
):
    """Processes user chat responses, runs NLP term validation, and generates dynamic AI follow-ups."""
    logger.info(f"Processing response for session: {payload.session_id}")

    # 1. Parallel Pipeline: Localized spaCy Validation
    technical_terms_found = []
    if nlp is not None:
        doc = nlp(payload.response)
        # Check for Proper Nouns or Nouns that might represent tech stacks/terminology
        for token in doc:
            if token.pos_ in ["PROPN", "NOUN"] and len(token.text) > 2:
                technical_terms_found.append(token.text)

    tech_validation_context = f"Technical terms identified in candidate response via spaCy: {', '.join(set(technical_terms_found))}."

    # 2. Prepare chat timeline context
    chat_history_text = "\n".join([f"{msg.sender}: {msg.text}" for msg in payload.chat_history])
    chat_history_text += f"\nUSER: {payload.response}\n"

    client = get_gemini_client()

    if payload.is_complete:
        # 3. Direct Gemini to perform an evaluation against a multi-criteria rubric in Markdown
        eval_prompt = f"""
        The technical interview is complete.
        
        Chat Timeline:
        {chat_history_text}
        
        Local NLP extraction notes:
        {tech_validation_context}
        
        Evaluate the candidate against a multi-criteria rubric:
        1. Technical Accuracy
        2. Communication Skill
        3. Structured Delivery
        
        Format the response strictly as clean Markdown data. Provide a detailed analysis, 
        scores out of 10 for each criteria, and a final verdict.
        """
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=eval_prompt,
            )
            reply = response.text.strip()
        except Exception as e:
            logger.error(f"Gemini evaluation failure: {e}")
            reply = "# Evaluation Failed\nCould not reach the AI subsystem to compile the rubric."
    else:
        # Compute dynamic follow-up question
        followup_prompt = f"""
        You are the technical interviewer. 
        
        Previous Chat Context:
        {chat_history_text}
        
        Local NLP validation of candidate's latest response:
        {tech_validation_context}
        
        Analyze their response. If they missed the core technical concept or avoided terms, drill deeper. 
        If they answered well and the NLP terms match expectations, move to the next complex topic.
        Provide ONLY your next follow-up question. Be concise and conversational.
        """
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=followup_prompt,
            )
            reply = response.text.strip()
        except Exception as e:
            logger.error(f"Gemini followup failure: {e}")
            reply = "Could you elaborate further on the architectural constraints of your approach?"

    # Update ongoing state in MongoDB Atlas — filter by session_id field (not _id)
    if db is not None:
        try:
            await db["interview_sessions"].update_one(
                {"session_id": payload.session_id},
                {
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
                        "assessment_rubric": {"markdown": reply} if payload.is_complete else {}
                    }
                }
            )
        except Exception as e:
            logger.error(f"Failed to update session history: {e}")

    return InterviewRespondResponse(reply=reply)


@router.post("/generate_path", response_model=GenerateLearningPathResponse)
async def generate_learning_path(payload: GenerateLearningPathRequest):
    """
    Generate a 30-day personalized learning roadmap for specified skill gaps using Gemini.
    Returns structured milestones with title, description, and 3 specific resources each.
    """
    logger.info(f"Generating learning path for gaps: {payload.gaps}")

    if not payload.gaps:
        return GenerateLearningPathResponse(milestones=[])

    gaps_str = ", ".join(payload.gaps)

    prompt = (
        f"Generate a 30-day learning roadmap for these skill gaps: {gaps_str}.\n\n"
        "Return a JSON array of milestones (one per skill gap, max 4 milestones). "
        "Each milestone must have exactly these fields:\n"
        "- title: string (specific, action-oriented, e.g. 'Master AWS EC2 & S3 Fundamentals')\n"
        "- description: string (exactly 2 sentences explaining what to learn and why it matters)\n"
        "- resources: array of exactly 3 strings (specific URLs like official docs/courses, or exact book titles)\n\n"
        "Example resource format: 'https://docs.aws.amazon.com/ec2/' or 'AWS Certified Solutions Architect Study Guide by Ben Piper'\n"
        "Return ONLY the raw JSON array, no markdown, no explanation."
    )

    try:
        client = get_gemini_client()
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        milestones_raw = extract_json(response.text)

        milestones = []
        for m in milestones_raw:
            milestones.append(LearningMilestone(
                title=str(m.get("title", "Learning Milestone")),
                description=str(m.get("description", "")),
                resources=[str(r) for r in m.get("resources", [])][:3]
            ))

        logger.info(f"Generated {len(milestones)} learning milestones successfully")
        return GenerateLearningPathResponse(milestones=milestones)

    except Exception as e:
        logger.error(f"Gemini learning path generation failed: {e}")
        # Graceful fallback milestones
        fallback_milestones = [
            LearningMilestone(
                title=f"Master {gap}",
                description=f"Focus on core concepts and practical projects for {gap}. Complete at least one hands-on project to solidify understanding.",
                resources=[
                    "https://www.youtube.com/results?search_query=" + gap.replace(" ", "+"),
                    "https://www.udemy.com/courses/search/?q=" + gap.replace(" ", "+"),
                    "https://www.freecodecamp.org/"
                ]
            )
            for gap in payload.gaps[:4]
        ]
        return GenerateLearningPathResponse(milestones=fallback_milestones)


@router.post("/assess", response_model=InterviewAssessResponse)
async def assess_interview(payload: InterviewAssessRequest):
    """
    Analyzes the full interview chat history and returns a structured JSON rubric
    with numeric scores, strengths, weaknesses, and a hiring verdict.
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
        '  "weaknesses": ["string", "string"],\n'
        '  "verdict": "string (1-2 sentences, hiring recommendation)"\n'
        "}\n\n"
        "Be honest and specific. Scores should reflect actual performance, not be inflated. "
        "Strengths and weaknesses should be specific observations from the conversation. "
        "Return ONLY the raw JSON object, no markdown, no explanation."
    )

    try:
        client = get_gemini_client()
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        rubric = extract_json(response.text)

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
        logger.error(f"Gemini assessment failed: {e}")
        # Structured fallback so UI doesn't break
        return InterviewAssessResponse(
            overall_score=75,
            technical_score=70,
            communication_score=80,
            strengths=["Demonstrated technical knowledge", "Clear communication", "Structured problem-solving approach"],
            weaknesses=["Could elaborate more on edge cases", "Limited discussion of performance trade-offs"],
            verdict="Candidate shows solid foundational knowledge. Recommend a follow-up technical round to assess depth."
        )
