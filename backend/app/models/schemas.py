from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Literal, Dict, Any

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
    raw_text: Optional[str] = None  # Full extracted resume text for ATS analysis
    technical_skills: List[str] = Field(default_factory=list)
    soft_skills: List[str] = Field(default_factory=list)

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
    resume_raw_text: Optional[str] = None  # Full raw resume text for deep ATS analysis

class MissingTerm(BaseModel):
    term: str
    weight: float

class ATSCategoryScores(BaseModel):
    skills_match: int = Field(..., ge=0, le=100, description="How well resume skills align with JD requirements")
    experience_relevance: int = Field(..., ge=0, le=100, description="How relevant experience is to the role")
    keyword_density: int = Field(..., ge=0, le=100, description="Presence of important JD keywords in resume")
    education_certifications: int = Field(..., ge=0, le=100, description="Education/cert fit for the role")
    formatting_completeness: int = Field(..., ge=0, le=100, description="Resume structure and completeness score")

class MatchAnalysisResponse(BaseModel):
    match_score: int = Field(..., ge=0, le=100)
    category_scores: ATSCategoryScores
    matched_keywords: List[str] = Field(default_factory=list)
    missing_keywords: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    recommendation_markdown: Optional[str] = None
    missing_terms: List[MissingTerm] = Field(default_factory=list)  # Kept for backward compat
    is_ai_powered: bool = False
    resume_skills: List[str] = Field(default_factory=list)   # Skills extracted from resume
    jd_skills: List[str] = Field(default_factory=list)        # Skills required by JD
    matched_skills: List[str] = Field(default_factory=list)   # jd_skills ∩ resume_skills
    missing_skills: List[str] = Field(default_factory=list)   # jd_skills − resume_skills
    gap_skills: List[str] = Field(default_factory=list)       # Alias of missing_skills (backward compat)
    missing_soft_skills: List[str] = Field(default_factory=list)
    technical_skills_breakdown: Optional[dict] = None
    parsed_resume: Dict[str, Any] = Field(default_factory=dict)
    parsed_jd: Dict[str, Any] = Field(default_factory=dict)

class SimulateScoreRequest(BaseModel):
    parsed_resume: Dict[str, Any]
    parsed_jd: Dict[str, Any]
    simulated_technical_skills: List[str]

class SimulateScoreResponse(BaseModel):
    match_score: int
    category_scores: ATSCategoryScores

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
    phase: str = "technical"  # Current phase after this response (DB-authoritative)

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
    resume_strength_score: int = 0   # How strong the resume is for the target role
    role_fit_score: int = 0          # Overall role-fit alignment score
    strengths: List[str]
    weaknesses: List[str]
    missing_skills: List[str] = []   # Skills required by role not demonstrated
    verdict: str

# --- Trend Analytics Models ---
class DemandSkillItem(BaseModel):
    name: str
    demand_count: str
    percentage: int


class SalaryDistributionItem(BaseModel):
    domain: str
    median: int
    percentile90: int


class CompanyDataItem(BaseModel):
    name: str
    canonical_name: str
    job_count: int
    average_salary: Optional[int] = None


class HistoricalSalaryItem(BaseModel):
    month: str
    salary: int


class CategoryItem(BaseModel):
    tag: str
    label: str


class JobsworthItem(BaseModel):
    title: str
    predicted_salary: int
    predictions: List[Dict[str, Any]]
    description: str


class TrendAnalyticsResponse(BaseModel):
    total_live_jobs: int
    avg_salary: int
    top_sector: str
    top_sector_reqs: str
    skills_demand: List[DemandSkillItem]
    work_model_ratio: Dict[str, int]
    salaries: List[SalaryDistributionItem]
    salary_histogram: List[Dict[str, Any]] = []
    historical_salaries: List[HistoricalSalaryItem] = []
    top_companies: List[CompanyDataItem] = []
    regional_salaries: List[Dict[str, Any]] = []
    categories: List[CategoryItem] = []
    jobsworth: Optional[JobsworthItem] = None
    is_mock_data: bool

# Add these to your existing schemas.py

class JobListingItem(BaseModel):
    id: str
    title: str
    company: str
    location: str
    description: str
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_is_predicted: bool = False
    contract_type: str
    contract_time: str
    redirect_url: str
    created: str
    category: str
    company_url: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class JobListingsResponse(BaseModel):
    total_count: int
    page: int
    results_per_page: int
    total_pages: int
    jobs: List[JobListingItem]

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
