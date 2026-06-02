import os
import json
import logging
from fastapi import APIRouter, HTTPException
import google.generativeai as genai

from app.models.schemas import OutreachGenerateRequest, OutreachGenerateResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/outreach", tags=["outreach"])

# Initialize Gemini SDK
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "mock-key-replace-in-production")
genai.configure(api_key=GEMINI_API_KEY)


@router.post("/generate", response_model=OutreachGenerateResponse)
async def generate_outreach_email(payload: OutreachGenerateRequest):
    """
    Generate a professional cold outreach email using Gemini 1.5 Flash.
    Returns structured JSON with subject and body fields.
    """
    logger.info(f"Generating outreach email for {payload.candidate_name} → {payload.target_company}/{payload.target_role}")

    skills_str = ", ".join(payload.candidate_skills[:6]) if payload.candidate_skills else "software engineering"

    prompt = (
        f"Write a professional cold outreach email from {payload.candidate_name} to a recruiter at "
        f"{payload.target_company} for a {payload.target_role} position. "
        f"Their top skills are {skills_str}. "
        f"Their AI match score is {payload.match_score}%. "
        "The email should be 150 words max, confident, specific, and end with a clear CTA. "
        "Do NOT use generic openers like 'I hope this email finds you well'. "
        "Reference the company specifically and make the connection feel personal and researched. "
        "Return ONLY a JSON object with exactly two fields: subject (string) and body (string). "
        "No markdown, no explanation, no extra fields."
    )

    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(response_mime_type="application/json")
        )
        result = json.loads(response.text)

        subject = str(result.get("subject", f"{payload.target_role} Opportunity — {payload.candidate_name}"))
        body = str(result.get("body", ""))

        if not body:
            raise ValueError("Empty body returned from Gemini")

        logger.info(f"Outreach email generated successfully for {payload.candidate_name}")
        return OutreachGenerateResponse(subject=subject, body=body)

    except Exception as e:
        logger.error(f"Gemini outreach generation failed: {e}")
        # Graceful fallback
        fallback_body = (
            f"Hi,\n\n"
            f"I came across {payload.target_company}'s work and was immediately drawn to the {payload.target_role} role. "
            f"With expertise in {skills_str} and a {payload.match_score}% AI-computed compatibility score against your job spec, "
            f"I believe I can contribute meaningfully from day one.\n\n"
            f"I'd love a 15-minute conversation to explore how my background aligns with your team's goals. "
            f"Are you available for a quick call this week?\n\n"
            f"Best,\n{payload.candidate_name}"
        )
        return OutreachGenerateResponse(
            subject=f"{payload.target_role} at {payload.target_company} — {payload.match_score}% Match",
            body=fallback_body
        )
