import os
import logging
from collections import Counter
from fastapi import APIRouter, HTTPException, Query
import httpx
import pandas as pd
import spacy

from app.models.schemas import TrendAnalyticsResponse, DemandSkillItem, SalaryDistributionItem

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analytics", tags=["analytics"])

# Load spaCy model globally
try:
    nlp = spacy.load("en_core_web_sm")
except Exception:
    logger.warning("Spacy 'en_core_web_sm' model not found locally.")
    nlp = None


@router.get("/trends", response_model=TrendAnalyticsResponse)
async def get_market_trends(domain: str = Query(..., description="Target domain query, e.g. Full Stack Developer")):
    """
    Analytics collection layer. Pulls real-time job market postings from the Adzuna API,
    processes textual descriptors with NLP, normalizes bounds using Pandas, and emits
    metrics strictly formatted for frontend Recharts consumption.
    """
    logger.info(f"Fetching job analytics for domain: {domain}")

    app_id = os.environ.get("ADZUNA_APP_ID")
    app_key = os.environ.get("ADZUNA_APP_KEY")

    jobs_data = []
    is_mock_data = False

    # 1. Pull real-time job market postings from the Adzuna API
    if app_id and app_key:
        try:
            url = "https://api.adzuna.com/v1/api/jobs/us/search/1"
            params = {
                "app_id": app_id,
                "app_key": app_key,
                "results_per_page": 50,
                "what": domain,
                "content-type": "application/json"
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    jobs_data = data.get("results", [])
                    logger.info(f"Adzuna returned {len(jobs_data)} jobs for domain: {domain}")
                else:
                    logger.warning(f"Adzuna API returned non-200 status: {response.status_code}. Falling back to mock data.")
                    is_mock_data = True
        except Exception as e:
            logger.error(f"Adzuna API request failed: {e}")
            is_mock_data = True

    # Mock data fallback for development if API credentials are not provisioned
    if not jobs_data:
        is_mock_data = True
        logger.info("Falling back to local generated mock data for Pandas analysis.")
        jobs_data = [
            {"title": f"Senior {domain}", "description": "Looking for React, Node.js and TypeScript experts. Fully remote setup.", "salary_min": 120000, "salary_max": 160000, "location": {"display_name": "San Francisco, CA"}},
            {"title": f"{domain} Engineer", "description": "Need Python, AWS, and Docker skills. Hybrid role.", "salary_min": None, "salary_max": 140000, "location": {"display_name": "New York, NY"}},
            {"title": f"Lead {domain}", "description": "Strong architectural skills in Next.js, GraphQL, and AWS. Remote work.", "salary_min": 140000, "salary_max": None, "location": {"display_name": "Austin, TX"}},
            {"title": f"Junior {domain}", "description": "Experience with React, HTML, CSS, JavaScript in office environments.", "salary_min": None, "salary_max": None, "location": {"display_name": "Onsite, Seattle, WA"}},
            {"title": f"{domain} DevOps", "description": "Extensive CI/CD, Kubernetes, and remote pipeline experience required.", "salary_min": 110000, "salary_max": 150000, "location": {"display_name": "Denver, CO"}}
        ] * 12  # Inflate mock data volume to simulate a realistic batch

    # 2. Ingest raw job records into a Pandas DataFrame
    df = pd.DataFrame(jobs_data)

    # 3. Clean and format data fields
    df['title'] = df['title'].astype(str).str.title()
    df['description'] = df['description'].astype(str).str.lower()

    if 'salary_min' not in df.columns:
        df['salary_min'] = pd.NA
    if 'salary_max' not in df.columns:
        df['salary_max'] = pd.NA

    # Coerce salaries to numerical limits
    df['salary_min'] = pd.to_numeric(df['salary_min'], errors='coerce')
    df['salary_max'] = pd.to_numeric(df['salary_max'], errors='coerce')

    # Resolve empty or missing salary distributions by computing standard median values
    global_median_min = df['salary_min'].median(skipna=True)
    global_median_max = df['salary_max'].median(skipna=True)

    # Safe fallback if entirely NaNs
    if pd.isna(global_median_min): global_median_min = 90000
    if pd.isna(global_median_max): global_median_max = 130000

    df['salary_min'] = df['salary_min'].fillna(global_median_min)
    df['salary_max'] = df['salary_max'].fillna(global_median_max)

    # Compute true localized average
    df['avg_salary'] = (df['salary_min'] + df['salary_max']) / 2

    # Handle Outliers (drop bottom 5% and top 5%)
    q_low = df["avg_salary"].quantile(0.05)
    q_hi  = df["avg_salary"].quantile(0.95)
    df_filtered = df[(df["avg_salary"] >= q_low) & (df["avg_salary"] <= q_hi)]

    if df_filtered.empty:
        df_filtered = df  # Safety fallback

    total_live_jobs = len(df_filtered)
    overall_avg_salary = int(df_filtered['avg_salary'].mean())

    # 4. Implement text processing with spaCy to extract recurring skill keywords
    all_text = " ".join(df_filtered['description'].tolist())

    technical_skills = []
    if nlp:
        # Accommodate large concatenated text block limitations
        nlp.max_length = len(all_text) + 1000
        doc = nlp(all_text)
        for token in doc:
            # Strict token filtering (Targeting proper nouns, alphabetic logic)
            if token.pos_ in ["PROPN", "NOUN"] and len(token.text) > 2 and token.is_alpha:
                generic = {"experience", "skills", "team", "work", "role", "years", "developer", "engineer", "looking", "development", "strong", "environments"}
                if token.text.lower() not in generic:
                    technical_skills.append(token.text.title())
    else:
        # Regex fallback string parsing
        for word in all_text.split():
            if len(word) > 3 and word.isalpha():
                technical_skills.append(word.title())

    # 5. Calculate counts for every top skill & isolate remote-work markers
    skill_counts = Counter(technical_skills)
    top_skills = skill_counts.most_common(7)

    skills_demand = []
    for skill, count in top_skills:
        skills_demand.append(
            DemandSkillItem(
                name=skill,
                demand_count=f"{count} mentions",
                percentage=int((count / len(technical_skills)) * 100) if len(technical_skills) > 0 else 0
            )
        )

    # Remote vs Hybrid vs Onsite — mutually exclusive classification
    # Priority: remote > hybrid > onsite (a job can only be in one bucket)
    remote_mask = df_filtered['description'].str.contains('remote', case=False, na=False)
    hybrid_mask = df_filtered['description'].str.contains('hybrid', case=False, na=False) & ~remote_mask
    onsite_mask = ~remote_mask & ~hybrid_mask

    remote_count = int(remote_mask.sum())
    hybrid_count = int(hybrid_mask.sum())
    onsite_count = int(onsite_mask.sum())

    work_model_ratio = {
        "Remote": int((remote_count / total_live_jobs) * 100) if total_live_jobs > 0 else 0,
        "Hybrid": int((hybrid_count / total_live_jobs) * 100) if total_live_jobs > 0 else 0,
        "Onsite": int((onsite_count / total_live_jobs) * 100) if total_live_jobs > 0 else 0
    }

    # Group average salary bounds into clear data bands (Junior, Mid, Senior)
    salaries = [
        SalaryDistributionItem(
            domain="Junior",
            median=int(df_filtered['avg_salary'].quantile(0.25)),
            percentile90=int(df_filtered['avg_salary'].quantile(0.40))
        ),
        SalaryDistributionItem(
            domain="Mid-Level",
            median=int(df_filtered['avg_salary'].median()),
            percentile90=int(df_filtered['avg_salary'].quantile(0.75))
        ),
        SalaryDistributionItem(
            domain="Senior",
            median=int(df_filtered['avg_salary'].quantile(0.80)),
            percentile90=int(df_filtered['avg_salary'].max())
        )
    ]

    # 6. Export the summarized data structure into clean Recharts-optimized JSON
    response_data = TrendAnalyticsResponse(
        total_live_jobs=total_live_jobs,  # Real count — no artificial multiplier
        avg_salary=overall_avg_salary,
        top_sector=domain.title(),
        top_sector_reqs=f"{top_skills[0][0] if top_skills else 'Software'} / {top_skills[1][0] if len(top_skills) > 1 else 'Cloud'}",
        skills_demand=skills_demand,
        work_model_ratio=work_model_ratio,
        salaries=salaries,
        is_mock_data=is_mock_data
    )

    return response_data
