from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Literal

# --- Resume Models ---
class SkillSchema(BaseModel):
    name: str
    match: int = Field(..., ge=0, le=100)

class ExperienceSchema(BaseModel):
    company: str
    role: str
    duration: str
    details: str

class SkillGapSchema(BaseModel):
    name: str
    category: str
    impact: int = Field(..., ge=0, le=100)
    checked: bool = False

class ResumeDataSchema(BaseModel):
    name: str
    email: str
    skills: List[SkillSchema]
    experience: List[ExperienceSchema]
    gaps: List[SkillGapSchema]
    ats_score: Optional[int] = 0

# --- Cover Letter Models ---
class CoverLetterRequest(BaseModel):
    resume: ResumeDataSchema
    job_description: str

class CoverLetterResponse(BaseModel):
    cover_letter: str

# --- Match Analysis Models ---
class MatchAnalysisRequest(BaseModel):
    resume: Optional[ResumeDataSchema] = None
    job_description: str

class MissingTerm(BaseModel):
    term: str
    weight: float

class MatchAnalysisResponse(BaseModel):
    match_score: int = Field(..., ge=0, le=100)
    tfidf_score: float
    semantic_score: float
    missing_terms: List[MissingTerm]

# --- Interview Models ---
class InterviewStartRequest(BaseModel):
    resume: ResumeDataSchema
    job_description: str

class InterviewStartResponse(BaseModel):
    session_id: str
    initial_question: str

class ChatMessageSchema(BaseModel):
    sender: Literal["SYSTEM", "USER"]
    timestamp: str
    text: str

class InterviewRespondRequest(BaseModel):
    session_id: str
    chat_history: List[ChatMessageSchema]
    response: str
    is_complete: bool = False

class InterviewRespondResponse(BaseModel):
    reply: str

# --- Interview: Learning Path Models ---
class GenerateLearningPathRequest(BaseModel):
    gaps: List[str]

class LearningMilestone(BaseModel):
    title: str
    description: str
    resources: List[str]

class GenerateLearningPathResponse(BaseModel):
    milestones: List[LearningMilestone]

# --- Interview: Assessment Rubric Models ---
class InterviewAssessRequest(BaseModel):
    chat_history: List[ChatMessageSchema]

class InterviewAssessResponse(BaseModel):
    overall_score: int
    technical_score: int
    communication_score: int
    strengths: List[str]
    weaknesses: List[str]
    verdict: str

# --- Trend Analytics Models ---
class SalaryDistributionItem(BaseModel):
    domain: str
    median: int
    percentile90: int

class DemandSkillItem(BaseModel):
    name: str
    demand_count: str
    percentage: int

class TrendAnalyticsResponse(BaseModel):
    total_live_jobs: int
    avg_salary: int
    top_sector: str
    top_sector_reqs: str
    skills_demand: List[DemandSkillItem]
    work_model_ratio: dict  # {"Remote": int, "Hybrid": int, "Onsite": int}
    salaries: List[SalaryDistributionItem]
    is_mock_data: bool = False

# --- Outreach Models ---
class OutreachGenerateRequest(BaseModel):
    candidate_name: str
    candidate_skills: List[str]
    target_company: str
    target_role: str
    match_score: int

class OutreachGenerateResponse(BaseModel):
    subject: str
    body: str

# --- Database Core Schemas ---
class ResumeDocument(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    raw_content: str
    skills: List[str]
    education: str
    project_summaries: str
    resume_embeddings: List[float] = Field(default_factory=list, description="Vector embeddings (e.g. 768 or 1536 dims)")

class JobDescription(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    title: str
    company: str
    requirements_text: str
    core_tech_stack: List[str]
    job_embeddings: List[float] = Field(default_factory=list, description="Vector embeddings for semantic search")

class MatchAnalysisSession(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    user_id: str
    resume_id: str
    job_id: str
    tfidf_score: float
    semantic_vector_score: float
    blended_metric: float

class InterviewSession(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    status: Literal["ongoing", "completed"]
    message_history: List[dict] = Field(default_factory=list, description="List of dicts containing query-response history")
    assessment_rubric: dict = Field(default_factory=dict, description="JSON rubric on completion")
