import os
import uuid
import logging
import json
import spacy
from fastapi import APIRouter, Depends
import google.generativeai as genai

from app.models.schemas import (
    InterviewStartRequest, 
    InterviewStartResponse, 
    InterviewRespondRequest, 
    InterviewRespondResponse
)
from app.core.database import get_database

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/interview", tags=["interview"])

# Initialize Gemini SDK
genai.configure(api_key=os.environ.get("GEMINI_API_KEY", "mock-key-replace-in-production"))

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
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(system_prompt)
        initial_question = response.text.strip()
    except Exception as e:
        logger.error(f"Gemini API failure during /start: {e}")
        initial_question = "Welcome. Can you describe your most complex technical project and the architecture behind it?"

    # Persist session state asynchronously to MongoDB
    if db is not None:
        try:
            session_record = {
                "_id": session_id,
                "status": "ongoing",
                "job_description": payload.job_description,
                "resume_data": payload.resume.model_dump(),
                "message_history": [
                    {"sender": "SYSTEM", "timestamp": "now", "text": initial_question}
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
    
    model = genai.GenerativeModel('gemini-1.5-flash')
    
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
            response = model.generate_content(eval_prompt)
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
            response = model.generate_content(followup_prompt)
            reply = response.text.strip()
        except Exception as e:
            logger.error(f"Gemini followup failure: {e}")
            reply = "Could you elaborate further on the architectural constraints of your approach?"

    # Update ongoing state in MongoDB Atlas
    if db is not None:
        try:
            await db["interview_sessions"].update_one(
                {"_id": payload.session_id},
                {
                    "$push": {
                        "message_history": {
                            "$each": [
                                {"sender": "USER", "timestamp": "now", "text": payload.response},
                                {"sender": "SYSTEM", "timestamp": "now", "text": reply}
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
