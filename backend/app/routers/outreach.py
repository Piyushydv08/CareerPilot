import os
import re
import json
import logging
from fastapi import APIRouter, HTTPException
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load .env before reading any env vars
load_dotenv()

from app.models.schemas import OutreachGenerateRequest, OutreachGenerateResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/outreach", tags=["outreach"])

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
        client = get_gemini_client()
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        result = extract_json(response.text)

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
