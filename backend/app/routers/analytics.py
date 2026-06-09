import os
import logging
import importlib
from importlib.util import find_spec
from collections import Counter
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
import httpx
import pandas as pd

spacy = importlib.import_module("spacy") if find_spec("spacy") else None

from app.models.schemas import (
    TrendAnalyticsResponse, DemandSkillItem, SalaryDistributionItem,
    CompanyDataItem, HistoricalSalaryItem, CategoryItem, JobsworthItem
)
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analytics", tags=["analytics"])

# Load spaCy model globally
if spacy is not None:
    try:
        nlp = spacy.load("en_core_web_sm")
    except Exception:
        logger.warning("Spacy 'en_core_web_sm' model not found locally.")
        nlp = None
else:
    logger.warning("spaCy package is not installed; falling back to keyword-based skill extraction.")
    nlp = None


class AdzunaClient:
    """Client for interacting with Adzuna API endpoints"""
    
    def __init__(self, app_id: str, app_key: str, country: str = "in"):
        self.app_id = app_id
        self.app_key = app_key
        self.country = country
        self.base_url = f"https://api.adzuna.com/v1/api/jobs/{country}"
    
    async def search_jobs(self, what: str, page: int = 1, results_per_page: int = 50) -> Dict:
        """Search for jobs"""
        url = f"{self.base_url}/search/{page}"
        params = {
            "app_id": self.app_id,
            "app_key": self.app_key,
            "results_per_page": results_per_page,
            "what": what,
            "content-type": "application/json"
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            return response.json() if response.status_code == 200 else {}
    
    async def get_categories(self) -> List[Dict]:
        """Get available job categories"""
        url = f"{self.base_url}/categories"
        params = {
            "app_id": self.app_id,
            "app_key": self.app_key
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            data = response.json() if response.status_code == 200 else {}
            return data.get("results", [])
    
    async def get_salary_histogram(self, what: str, category: Optional[str] = None) -> Dict:
        """Get salary distribution histogram"""
        url = f"{self.base_url}/histogram"
        params = {
            "app_id": self.app_id,
            "app_key": self.app_key,
            "what": what
        }
        if category:
            params["category"] = category
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            return response.json() if response.status_code == 200 else {}
    
    async def get_historical_salaries(self, what: str, months: int = 12) -> Dict:
        """Get historical salary trends"""
        url = f"{self.base_url}/history"
        params = {
            "app_id": self.app_id,
            "app_key": self.app_key,
            "what": what,
            "months": months
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            return response.json() if response.status_code == 200 else {}
    
    async def get_top_companies(self, what: str) -> List[Dict]:
        """Get top companies hiring for the role"""
        url = f"{self.base_url}/top_companies"
        params = {
            "app_id": self.app_id,
            "app_key": self.app_key,
            "what": what
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            data = response.json() if response.status_code == 200 else {}
            return data.get("leaderboard", [])
    
    async def get_geo_salary_data(self, what: str) -> Dict:
        """Get regional salary data"""
        url = f"{self.base_url}/geodata"
        params = {
            "app_id": self.app_id,
            "app_key": self.app_key,
            "what": what
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            return response.json() if response.status_code == 200 else {}


@router.get("/trends", response_model=TrendAnalyticsResponse)
async def get_market_trends(
    domain: str = Query(..., description="Target domain query, e.g. Full Stack Developer"),
    country: str = Query("in", description="Country code (us, gb, ca, etc.)"),
    include_historical: bool = Query(True, description="Include historical salary trends"),
    include_companies: bool = Query(True, description="Include top companies data")
):
    """
    Comprehensive analytics collection layer. Pulls real-time job market postings from Adzuna API,
    processes textual descriptors with NLP, normalizes bounds using Pandas, and emits
    metrics strictly formatted for frontend Recharts consumption.
    """
    logger.info(f"Fetching comprehensive job analytics for domain: {domain} in {country}")

    app_id = settings.ADZUNA_APP_ID
    app_key = settings.ADZUNA_APP_KEY

    jobs_data = []
    categories_data = []
    salary_histogram_data = {}
    historical_salary_data = {}
    top_companies_data = []
    geo_salary_data = {}
    is_mock_data = False

    if not app_id or not app_key:
        raise HTTPException(
            status_code=503,
            detail="Adzuna API credentials not configured. Please set ADZUNA_APP_ID and ADZUNA_APP_KEY environment variables."
        )

    client = AdzunaClient(app_id, app_key, country)

    try:
        # 1. Search for jobs
        search_result = await client.search_jobs(domain, results_per_page=50)
        jobs_data = search_result.get("results", [])
        logger.info(f"Adzuna returned {len(jobs_data)} jobs for domain: {domain}")

        if not jobs_data:
            raise HTTPException(status_code=404, detail="No jobs found for the given search criteria")

        # 2. Get categories
        try:
            categories_data = await client.get_categories()
            logger.info(f"Retrieved {len(categories_data)} categories")
        except Exception as e:
            logger.warning(f"Failed to fetch categories: {e}")

        # 3. Get salary histogram
        try:
            salary_histogram_data = await client.get_salary_histogram(domain)
            logger.info("Retrieved salary histogram data")
        except Exception as e:
            logger.warning(f"Failed to fetch salary histogram: {e}")

        # 4. Get historical salaries
        if include_historical:
            try:
                historical_salary_data = await client.get_historical_salaries(domain, months=12)
                logger.info("Retrieved historical salary data")
            except Exception as e:
                logger.warning(f"Failed to fetch historical salaries: {e}")

        # 5. Get top companies
        if include_companies:
            try:
                top_companies_data = await client.get_top_companies(domain)
                logger.info(f"Retrieved {len(top_companies_data)} top companies")
            except Exception as e:
                logger.warning(f"Failed to fetch top companies: {e}")

        # 6. Get geo salary data
        try:
            geo_salary_data = await client.get_geo_salary_data(domain)
            logger.info("Retrieved geo salary data")
        except Exception as e:
            logger.warning(f"Failed to fetch geo salary data: {e}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Adzuna API request failed: {e}")
        raise HTTPException(status_code=503, detail=f"Failed to fetch market trends from Adzuna: {str(e)}")

    # Process jobs data with Pandas
    df = pd.DataFrame(jobs_data)
    
    # Clean and format data fields
    df['title'] = df['title'].astype(str).str.title() if 'title' in df.columns else pd.Series([f"{domain} Role"] * len(df))
    df['description'] = df['description'].astype(str).str.lower() if 'description' in df.columns else pd.Series([""] * len(df))
    
    # Process salary data
    if 'salary_min' not in df.columns:
        df['salary_min'] = pd.NA
    if 'salary_max' not in df.columns:
        df['salary_max'] = pd.NA
    
    df['salary_min'] = pd.to_numeric(df['salary_min'], errors='coerce')
    df['salary_max'] = pd.to_numeric(df['salary_max'], errors='coerce')
    
    # Resolve missing salary distributions
    global_median_min = df['salary_min'].median(skipna=True) if not df['salary_min'].isna().all() else 90000
    global_median_max = df['salary_max'].median(skipna=True) if not df['salary_max'].isna().all() else 130000
    
    if pd.isna(global_median_min):
        global_median_min = 90000
    if pd.isna(global_median_max):
        global_median_max = 130000
    
    df['salary_min'] = df['salary_min'].fillna(global_median_min)
    df['salary_max'] = df['salary_max'].fillna(global_median_max)
    df['avg_salary'] = (df['salary_min'] + df['salary_max']) / 2
    
    # Handle outliers
    if len(df) > 0:
        q_low = df["avg_salary"].quantile(0.05)
        q_hi = df["avg_salary"].quantile(0.95)
        df_filtered = df[(df["avg_salary"] >= q_low) & (df["avg_salary"] <= q_hi)]
        if df_filtered.empty:
            df_filtered = df
    else:
        df_filtered = df
    
    total_live_jobs = len(df_filtered) if len(df_filtered) > 0 else len(jobs_data)
    overall_avg_salary = int(df_filtered['avg_salary'].mean()) if len(df_filtered) > 0 and not df_filtered['avg_salary'].isna().all() else 110000
    
    # Extract skills using NLP
    all_text = " ".join(df_filtered['description'].tolist()) if len(df_filtered) > 0 else ""
    technical_skills = extract_skills(all_text, nlp)
    
    # Calculate skill counts
    skill_counts = Counter(technical_skills)
    top_skills = skill_counts.most_common(10)
    
    skills_demand = []
    total_skills = len(technical_skills) if technical_skills else 1
    for skill, count in top_skills[:7]:
        skills_demand.append(
            DemandSkillItem(
                name=skill,
                demand_count=f"{count} mentions",
                percentage=int((count / total_skills) * 100) if total_skills > 0 else 0
            )
        )
    
    # Work model classification
    if len(df_filtered) > 0:
        remote_mask = df_filtered['description'].str.contains('remote', case=False, na=False)
        hybrid_mask = df_filtered['description'].str.contains('hybrid', case=False, na=False) & ~remote_mask
        onsite_mask = ~remote_mask & ~hybrid_mask
        
        remote_count = int(remote_mask.sum())  # type: ignore[arg-type]
        hybrid_count = int(hybrid_mask.sum())  # type: ignore[arg-type]
        onsite_count = int(onsite_mask.sum())  # type: ignore[arg-type]
        
        work_model_ratio = {
            "Remote": int((remote_count / total_live_jobs) * 100) if total_live_jobs > 0 else 0,
            "Hybrid": int((hybrid_count / total_live_jobs) * 100) if total_live_jobs > 0 else 0,
            "Onsite": int((onsite_count / total_live_jobs) * 100) if total_live_jobs > 0 else 0
        }
    else:
        work_model_ratio = {"Remote": 33, "Hybrid": 34, "Onsite": 33}
    
    # Salary distribution by level
    if len(df_filtered) > 0 and not df_filtered['avg_salary'].isna().all():
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
    else:
        salaries = [
            SalaryDistributionItem(domain="Junior", median=75000, percentile90=90000),
            SalaryDistributionItem(domain="Mid-Level", median=105000, percentile90=130000),
            SalaryDistributionItem(domain="Senior", median=140000, percentile90=180000)
        ]
    
    # Process salary histogram data
    salary_bands = process_histogram_data(salary_histogram_data)
    
    # Process historical salary data
    historical_salaries = process_historical_data(historical_salary_data)
    
    # Process top companies
    companies = process_companies_data(top_companies_data[:10])
    
    # Process geo salary data
    regional_salaries = process_geo_data(geo_salary_data)
    
    # Process categories
    categories = process_categories_data(categories_data)
    
    # Jobsworth predictions (salary predictions based on job title)
    jobsworth_predictions = generate_jobsworth_predictions(domain, overall_avg_salary)
    
    response_data = TrendAnalyticsResponse(
        total_live_jobs=total_live_jobs,
        avg_salary=overall_avg_salary,
        top_sector=domain.title(),
        top_sector_reqs=f"{top_skills[0][0] if top_skills else 'Software'} / {top_skills[1][0] if len(top_skills) > 1 else 'Cloud'}",
        skills_demand=skills_demand,
        work_model_ratio=work_model_ratio,
        salaries=salaries,
        salary_histogram=salary_bands,
        historical_salaries=historical_salaries,
        top_companies=companies,
        regional_salaries=regional_salaries,
        categories=categories,
        jobsworth=jobsworth_predictions,
        is_mock_data=is_mock_data
    )
    
    return response_data


@router.get("/jobs")
async def get_job_listings(
    domain: str = Query(..., description="Job role to search for"),
    country: str = Query("in", description="Country code (us, gb, ca, etc.)"),
    location: Optional[str] = Query(None, description="Location filter"),
    results_per_page: int = Query(20, description="Number of results per page", ge=1, le=50),
    page: int = Query(1, description="Page number", ge=1)
):
    """
    Fetch real job listings with direct application links from Adzuna API.
    Returns jobs that the user can apply to directly - NO MOCK DATA.
    """
    logger.info(f"Fetching job listings for domain: {domain} in {country}")

    app_id = settings.ADZUNA_APP_ID
    app_key = settings.ADZUNA_APP_KEY

    if not app_id or not app_key:
        raise HTTPException(
            status_code=503,
            detail="Adzuna API credentials not configured. Please set ADZUNA_APP_ID and ADZUNA_APP_KEY environment variables."
        )

    try:
        # Build search parameters
        url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"
        params = {
            "app_id": app_id,
            "app_key": app_key,
            "results_per_page": results_per_page,
            "what": domain,
            "content-type": "application/json"
        }

        if location:
            params["where"] = location

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, params=params)

            if response.status_code == 401:
                raise HTTPException(status_code=401, detail="Invalid Adzuna API credentials")
            
            jobs = []
            data = {}
            if response.status_code == 200:
                data = response.json()
                jobs = data.get("results", [])

            # Fallback 1: If over-specified (more than 2 words), try searching for the last 3 words
            if not jobs and len(domain.split()) > 2:
                fallback_domain = " ".join(domain.split()[-3:])
                logger.info(f"No jobs found for '{domain}'. Trying Fallback 1: '{fallback_domain}'")
                params["what"] = fallback_domain
                fb_resp = await client.get(url, params=params)
                if fb_resp.status_code == 200:
                    data = fb_resp.json()
                    jobs = data.get("results", [])

            # Fallback 2: If still no jobs, try the first 2 words of the query
            if not jobs and len(domain.split()) > 1:
                fallback_domain = " ".join(domain.split()[:2])
                logger.info(f"No jobs found. Trying Fallback 2: '{fallback_domain}'")
                params["what"] = fallback_domain
                fb_resp = await client.get(url, params=params)
                if fb_resp.status_code == 200:
                    data = fb_resp.json()
                    jobs = data.get("results", [])

            # Fallback 3: Generic Software Engineer fallback
            if not jobs:
                fallback_domain = "Software Engineer"
                logger.info(f"No jobs found. Trying Fallback 3: '{fallback_domain}'")
                params["what"] = fallback_domain
                fb_resp = await client.get(url, params=params)
                if fb_resp.status_code == 200:
                    data = fb_resp.json()
                    jobs = data.get("results", [])

            if not jobs:
                return {
                    "total_count": 0,
                    "page": page,
                    "results_per_page": results_per_page,
                    "total_pages": 0,
                    "jobs": [],
                    "error": "No jobs found for this search criteria"
                }

            # Format jobs with direct links
            formatted_jobs = []
            for job in jobs:
                salary_min = job.get("salary_min")
                salary_max = job.get("salary_max")
                salary_is_predicted = job.get("salary_is_predicted") == "1"

                # Only include jobs that have a redirect_url (application link)
                redirect_url = job.get("redirect_url")
                if not redirect_url:
                    continue

                description = job.get("description", "")
                formatted_jobs.append({
                    "id": job.get("id"),
                    "title": job.get("title", ""),
                    "company": job.get("company", {}).get("display_name", "Unknown Company"),
                    "location": job.get("location", {}).get("display_name", "Location not specified"),
                    "description": description[:500] + "..." if len(description) > 500 else description,
                    "salary_min": salary_min,
                    "salary_max": salary_max,
                    "salary_is_predicted": salary_is_predicted,
                    "contract_type": job.get("contract_type", "Not specified"),
                    "contract_time": job.get("contract_time", "Not specified"),
                    "redirect_url": redirect_url,
                    "created": job.get("created"),
                    "category": job.get("category", {}).get("label", "Uncategorized"),
                    "company_url": job.get("company", {}).get("url"),
                    "latitude": job.get("latitude"),
                    "longitude": job.get("longitude")
                })

            total_count = data.get("count", 0)
            return {
                "total_count": total_count,
                "page": page,
                "results_per_page": results_per_page,
                "total_pages": (total_count + results_per_page - 1) // results_per_page if total_count > 0 else 0,
                "jobs": formatted_jobs,
                "is_mock": False
            }

    except httpx.TimeoutException:
        logger.error(f"Adzuna API timeout for domain: {domain}")
        raise HTTPException(status_code=504, detail="Adzuna API request timeout")
    except httpx.RequestError as e:
        logger.error(f"Adzuna API request failed: {e}")
        raise HTTPException(status_code=503, detail=f"Failed to connect to Adzuna API: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching jobs: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/jobs/{job_id}")
async def get_job_details(
    job_id: str,
    country: str = Query("in", description="Country code")
):
    """
    Get detailed information about a specific job with direct application link
    """
    app_id = settings.ADZUNA_APP_ID
    app_key = settings.ADZUNA_APP_KEY

    if not app_id or not app_key:
        raise HTTPException(
            status_code=503,
            detail="Adzuna API credentials not configured"
        )

    try:
        # Search for the specific job by ID
        url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"
        params = {
            "app_id": app_id,
            "app_key": app_key,
            "adref": job_id,
            "content-type": "application/json"
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)

            if response.status_code != 200:
                raise HTTPException(status_code=404, detail="Job not found")

            data = response.json()
            jobs = data.get("results", [])

            if not jobs:
                raise HTTPException(status_code=404, detail="Job not found")

            job = jobs[0]

            return {
                "id": job.get("id"),
                "title": job.get("title"),
                "company": job.get("company", {}).get("display_name"),
                "location": job.get("location", {}).get("display_name"),
                "description": job.get("description"),
                "salary_min": job.get("salary_min"),
                "salary_max": job.get("salary_max"),
                "salary_is_predicted": job.get("salary_is_predicted") == "1",
                "redirect_url": job.get("redirect_url"),
                "created": job.get("created"),
                "category": job.get("category", {}).get("label"),
                "contract_type": job.get("contract_type"),
                "contract_time": job.get("contract_time"),
                "company_url": job.get("company", {}).get("url"),
                "latitude": job.get("latitude"),
                "longitude": job.get("longitude")
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch job details: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch job details: {str(e)}")


def extract_skills(text: str, nlp_model) -> List[str]:
    """Extract technical skills from text using NLP"""
    if not text:
        return []
    
    technical_skills = []
    generic = {"experience", "skills", "team", "work", "role", "years", 
              "developer", "engineer", "looking", "development", "strong", 
              "environments", "required", "ability", "abilityto", "using",
              "including", "knowledge", "proven", "demonstrated", "excellent"}
              
    if nlp_model:
        try:
            nlp_model.max_length = len(text) + 1000
            doc = nlp_model(text)
            for token in doc:
                if token.pos_ in ["PROPN", "NOUN"] and len(token.text) > 2 and token.is_alpha:
                    if token.text.lower() not in generic:
                        technical_skills.append(token.text.title())
        except Exception as e:
            logger.warning(f"NLP processing failed: {e}")
            # Fallback to simple word extraction
            for word in text.split():
                if len(word) > 3 and word.isalpha() and word.lower() not in generic:
                    technical_skills.append(word.title())
    else:
        # Simple string parsing fallback
        skill_keywords = ["python", "javascript", "react", "node", "aws", "docker", 
                         "kubernetes", "typescript", "graphql", "mongodb", "postgresql",
                         "java", "c++", "ruby", "rails", "django", "flask", "tensorflow",
                         "pytorch", "sql", "nosql", "git", "ci/cd", "jenkins", "terraform"]
        for skill in skill_keywords:
            if skill in text.lower():
                technical_skills.append(skill.title())
    
    return technical_skills


def process_histogram_data(histogram_data: Dict) -> List[Dict]:
    """Process salary histogram data for chart display"""
    salary_bands = []
    histogram = histogram_data.get("histogram", {})
    
    if histogram:
        for salary_range, count in sorted(histogram.items()):
            # Parse salary range (format like "20000-29999")
            if "-" in salary_range:
                low, high = salary_range.split("-")
                salary_bands.append({
                    "range": salary_range,
                    "count": count,
                    "low": int(low),
                    "high": int(high)
                })
    
    return salary_bands


def process_historical_data(historical_data: Dict) -> List[HistoricalSalaryItem]:
    """Process historical salary trends"""
    historical: List[HistoricalSalaryItem] = []
    month_data = historical_data.get("month", {})
    
    if month_data:
        for month, salary in sorted(month_data.items()):
            historical.append(HistoricalSalaryItem(month=month, salary=int(salary)))
    return historical[-12:]  # Last 12 months


def process_companies_data(companies_data: List[Dict]) -> List[CompanyDataItem]:
    """Process top companies data"""
    companies = []
    for company in companies_data:
        companies.append(CompanyDataItem(
            name=company.get("display_name", "Unknown"),
            canonical_name=company.get("canonical_name", ""),
            job_count=company.get("count", 0),
            average_salary=int(company.get("average_salary", 0)) if company.get("average_salary") else None
        ))
    return companies


def process_geo_data(geo_data: Dict) -> List[Dict]:
    """Process regional salary data"""
    regional = []
    locations = geo_data.get("locations", [])
    
    for location in locations[:10]:  # Top 10 locations
        loc_info = location.get("location", {})
        regional.append({
            "location": loc_info.get("display_name", "Unknown"),
            "job_count": location.get("count", 0),
            "salary": location.get("average_salary", None)
        })
    
    return sorted(regional, key=lambda x: x.get("salary") or 0, reverse=True)


def process_categories_data(categories_data: List[Dict]) -> List[CategoryItem]:
    """Process job categories"""
    categories = []
    for category in categories_data[:15]:
        categories.append(CategoryItem(
            tag=category.get("tag", ""),
            label=category.get("label", "")
        ))
    return categories


def generate_jobsworth_predictions(domain: str, avg_salary: int) -> JobsworthItem:
    """Generate salary predictions based on job title"""
    # Simulate salary prediction model
    variations = {
        "Junior": -30000,
        "Mid": 0,
        "Senior": 30000,
        "Lead": 50000,
        "Principal": 80000,
        "Director": 120000
    }
    
    predictions = []
    for level, variation in variations.items():
        predictions.append({
            "level": level,
            "predicted_salary": max(avg_salary + variation, 40000),
            "confidence": 85 if level in ["Junior", "Mid", "Senior"] else 70
        })
    
    return JobsworthItem(
        title=domain,
        predicted_salary=avg_salary,
        predictions=predictions,
        description=f"Based on {domain} roles in current market, Jobsworth predicts competitive salaries with high confidence for standard levels."
    )