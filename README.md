# CareerPilot — AI-Powered Career Intelligence Platform

CareerPilot is a full-stack AI career platform that helps candidates analyze their resume against job descriptions, simulate skill-gap improvements, practice live mock interviews, generate outreach campaigns, and explore real-time job market analytics — all powered by a combination of deterministic scoring engines and LLM-based reasoning (Groq/Llama, Google Gemini).

This document describes the complete system: the high-level architecture, the frontend and backend block diagrams, the data flow between every subsystem, the AI/ML pipeline, the database design, and how to run the project locally.

---

## 1. Project Summary

| | |
|---|---|
| **Name** | CareerPilot AI Telemetry Platform |
| **Version** | 2.4.0 |
| **Type** | Full-stack web application (resume intelligence + interview simulation + market analytics) |
| **Frontend** | Next.js 14 (App Router) + Tailwind CSS + Recharts + Framer Motion |
| **Backend** | FastAPI (Python, async) + Motor (MongoDB async driver) |
| **AI Layer** | Groq (Llama 3.3 70B), Google Gemini (`gemini-flash-latest` / `gemini-2.5-flash`), scikit-learn, spaCy, Sentence-Transformers |
| **Database** | MongoDB Atlas (documents) + ChromaDB (vector embeddings) |
| **External APIs** | Adzuna (live job listings & market data) |

---

## 2. High-Level Architecture (System Block Diagram)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                                   CLIENT LAYER                               │
│                                                                              │
│   ┌─────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐  │
│   │  /analyze   │   │ /simulator   │   │ /interview   │   │ /outreach    │  │
│   │  (ATS Check)│   │ (Skill Gap)  │   │ (Mock AI)    │   │ (Campaigns)  │  │
│   └─────────────┘   └──────────────┘   └──────────────┘   └──────────────┘  │
│   ┌─────────────┐   ┌──────────────┐                                       │
│   │ /analytics  │   │   /about     │      Next.js 14 App Router            │
│   │ (Market AI) │   │   /support   │      + ProjectContext (global state)  │
│   └─────────────┘   └──────────────┘                                       │
└───────────────────────────────┬──────────────────────────────────────────────┘
                                │  REST (fetch) — JSON over HTTPS
                                ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                              API GATEWAY LAYER                               │
│                     FastAPI ASGI App  (prefix: /api/v1)                     │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  Middleware Stack:                                                    │ │
│  │   1. CORS Middleware (whitelisted origins)                            │ │
│  │   2. Request Profiler (timing + IP logging)                          │ │
│  │   3. Global Exception Interceptor (500 protection + CORS headers)    │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│   ┌───────────┐ ┌───────────┐ ┌─────────────┐ ┌────────────┐ ┌───────────┐  │
│   │  /resume  │ │  /match   │ │ /interview  │ │ /analytics │ │ /outreach │  │
│   │  router   │ │  router   │ │  router     │ │  router    │ │  router   │  │
│   └───────────┘ └───────────┘ └─────────────┘ └────────────┘ └───────────┘  │
└────┬─────────────────┬──────────────┬───────────────┬───────────────┬───────┘
     │                 │              │               │               │
     ▼                 ▼              ▼               ▼               ▼
┌─────────┐    ┌────────────────┐ ┌──────────┐  ┌─────────────┐ ┌───────────┐
│ PARSING │    │ SCORING ENGINE │ │ SESSION  │  │   ADZUNA    │ │  GEMINI   │
│ LAYER   │    │ (deterministic)│ │ STATE    │  │   CLIENT    │ │  CLIENT   │
│ pdfplum-│    │ scoring.py     │ │ (MongoDB)│  │  (httpx)    │ │ (outreach │
│ ber /   │    │ skill_engine/* │ │          │  │             │ │ emails)   │
│ PyMuPDF │    │                │ │          │  │             │ │           │
│ /docx   │    │                │ │          │  │             │ │           │
└─────────┘    └────────────────┘ └──────────┘  └─────────────┘ └───────────┘
     │                 │              │
     ▼                 ▼              ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                              AI / ML INFERENCE LAYER                          │
│  ┌────────────────┐  ┌───────────────────┐  ┌───────────────────────────┐   │
│  │ Groq Llama 3.3  │  │ Google Gemini      │  │ Sentence-Transformers     │   │
│  │ 70B-Versatile   │  │ flash-latest /     │  │ (all-MiniLM-L6-v2)        │   │
│  │ — resume parse, │  │ 2.5-flash —        │  │ — semantic skill matching │   │
│  │ JD parse, inter-│  │ detailed ATS,      │  │   via cosine similarity   │   │
│  │ view Q&A, cover │  │ recommendations,   │  │                           │   │
│  │ letters         │  │ fresher-job feed   │  │                           │   │
│  └────────────────┘  └───────────────────┘  └───────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────────┘
     │                 │              │
     ▼                 ▼              ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                              PERSISTENCE LAYER                               │
│   ┌───────────────────────────┐        ┌────────────────────────────────┐   │
│   │  MongoDB Atlas (Motor)    │        │  ChromaDB (local persistent)   │   │
│   │  • resumes                │        │  • resume_jd_skills collection │   │
│   │  • detailed_ats_logs      │        │  • skill embeddings, tagged by │   │
│   │  • interview_sessions     │        │    session_id + source         │   │
│   │  • match_logs             │        │                                │   │
│   └───────────────────────────┘        └────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Frontend Architecture

### 3.1 Stack

- **Next.js 14** (App Router, `"use client"` components)
- **Tailwind CSS v4** (custom theme tokens: `cyber-blue`, `surface-*`, `bento-card` utility class)
- **Recharts** for analytics charts (bar/area/composed charts)
- **lucide-react** for icons
- **react-markdown** for rendering AI-generated Markdown (cover letters, recommendations, interview reports)
- Global client state managed via **React Context** (`ProjectContext.tsx`) — no Redux; all cross-page state (resume data, ATS match detail, interview session, terminal logs) lives in one provider wrapped around the root layout.

### 3.2 Page → Feature Block Map

```
app/
├── layout.tsx              → Root shell: Sidebar + Header + ProjectProvider
├── page.tsx                → Redirects to /analyze
├── context/
│   └── ProjectContext.tsx  → Global state + all fetch() calls to backend
├── analyze/page.tsx        → Resume upload + JD input + ATS score breakdown + cover letter + live job listings
├── simulator/page.tsx      → Skill-gap checklist with live score recalculation + AI learning roadmap
├── interview/page.tsx      → Multi-phase AI mock interview chat (intro → role → resume → technical → assessment)
├── outreach/page.tsx       → AI-generated cold outreach email composer + recruiter roster tracker
├── analytics/page.tsx      → Market intelligence dashboard (Adzuna-powered) + AI fresher-jobs widget
├── about/page.tsx          → Static documentation of feature pipelines (this is product self-documentation, not user data)
└── support/page.tsx        → Team contact page
```

### 3.3 Frontend Component / Data-Flow Diagram

```
┌────────────────────────────────────────────────────────────────────┐
│                         ProjectContext.tsx                         │
│  State: resumeData | jobDescription | matchScore | atsMatchDetail  │
│         messages | sessionId | terminalLogs | upcomingEngagement   │
│                                                                     │
│  Actions (call backend via fetch):                                 │
│   • uploadResume(file)        → POST /resume/upload                │
│   • triggerAnalyze(jobDesc)   → POST /match/analyze                │
│   • toggleSkillGap(index)     → POST /match/simulate_score          │
│   • startInterviewSession()   → POST /interview/start               │
│   • sendInterviewMessage()    → POST /interview/respond             │
└───────────┬───────────────┬────────────────┬────────────────┬──────┘
            │               │                │                │
            ▼               ▼                ▼                ▼
     /analyze page   /simulator page   /interview page   /outreach page
     (consumes        (consumes         (consumes          (consumes
      resumeData,       gaps[],           messages[],        resumeData,
      atsMatchDetail)   matchScore)       sessionId)         matchScore)
```

Every page subscribes to `useProject()` and reads/writes shared state, so an action on one page (e.g. uploading a resume on `/analyze`) is instantly available on `/simulator`, `/interview`, and `/outreach` without re-fetching.

---

## 4. Backend Architecture

### 4.1 Stack

- **FastAPI** (async ASGI, auto OpenAPI docs at `/docs` and `/redoc`)
- **Pydantic v2** — strict request/response validation (`app/models/schemas.py`)
- **Motor** — async MongoDB driver (no blocking I/O on the event loop)
- **pdfplumber + PyMuPDF (fitz) + python-docx** — resume text extraction (PyMuPDF is the primary parser for column/table-heavy resumes, with pdfplumber as fallback)
- **httpx.AsyncClient** — non-blocking outbound calls to Groq and Adzuna
- **google-genai SDK** — Gemini inference
- **scikit-learn + Sentence-Transformers + ChromaDB** — semantic skill matching
- **spaCy** — NLP-based keyword/skill extraction for market analytics text mining

### 4.2 Router Map (`/api/v1` prefix)

```
app/main.py
 ├── resume.router      (prefix: /resume)
 │     POST /upload                → Parse resume file, extract skills, score quality
 │     POST /streamlit/analyze     → Legacy Groq-based free-text analysis
 │     POST /streamlit/match       → Legacy % match utility
 │     POST /cover_letter          → AI-generated cover letter (Markdown)
 │
 ├── match.router       (prefix: /match)
 │     POST /analyze               → Full ATS pipeline: resume vs JD comparison
 │     POST /simulate_score        → Recompute ATS score with simulated added skills
 │
 ├── interview.router   (prefix: /interview)
 │     POST /start                 → Create session, AI introduces itself
 │     POST /respond               → Phase-aware conversational turn
 │     POST /upload_resume         → Attach resume text to an active session
 │     POST /assess                → Structured JSON interview rubric
 │     POST /generate_path         → 30-day learning roadmap for skill gaps
 │
 ├── analytics.router   (prefix: /analytics)
 │     GET  /trends                → Adzuna-powered market trend dashboard data
 │     GET  /jobs                  → Live job listings with apply links
 │     GET  /jobs/{job_id}         → Single job detail
 │     GET  /top-fresher-jobs      → Gemini-generated fresher job/skill recommendations
 │
 └── outreach.router    (prefix: /outreach)
       POST /generate              → Gemini-generated cold outreach email
```

### 4.3 Backend Internal Block Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            app/routers/*.py                             │
│         (FastAPI endpoint handlers — orchestrate the pipeline)          │
└──────────────┬───────────────┬───────────────┬───────────────┬──────────┘
               │               │               │               │
               ▼               ▼               ▼               ▼
   ┌────────────────┐ ┌────────────────┐ ┌──────────────┐ ┌──────────────┐
   │ app/core/       │ │ app/core/       │ │ app/core/    │ │ app/models/  │
   │ normalization.py│ │ scoring.py      │ │ skill_engine/│ │ schemas.py   │
   │                 │ │                 │ │              │ │              │
   │ Canonicalizes   │ │ Deterministic   │ │ 5-step skill │ │ Pydantic     │
   │ raw LLM strings │ │ weighted ATS    │ │ matching     │ │ request /    │
   │ ("nodejs" →     │ │ formula across  │ │ pipeline:    │ │ response     │
   │ "Node.js")      │ │ 6 pillars       │ │ normalize →  │ │ contracts    │
   │                 │ │ (skills, exp,   │ │ taxonomy     │ │              │
   │                 │ │ projects, edu,  │ │ expand →     │ │              │
   │                 │ │ certs, quality) │ │ exact/taxon- │ │              │
   │                 │ │                 │ │ omy match →  │ │              │
   │                 │ │                 │ │ embedding    │ │              │
   │                 │ │                 │ │ match →      │ │              │
   │                 │ │                 │ │ score        │ │              │
   └────────────────┘ └────────────────┘ └──────────────┘ └──────────────┘
               │               │               │
               ▼               ▼               ▼
   ┌─────────────────────────────────────────────────────────────────────┐
   │                   app/core/database.py  (Motor / MongoDB)            │
   │            app/core/vector_store.py     (ChromaDB / embeddings)      │
   └─────────────────────────────────────────────────────────────────────┘
```

---

## 5. System Design — Core Pipelines

### 5.1 Resume Upload & Parsing Pipeline

```
File Upload (PDF/DOCX)
        │
        ▼
┌───────────────────────┐
│ Text Extraction        │   PyMuPDF (primary, reading-order aware)
│                        │   → falls back to pdfplumber → falls back to python-docx
└──────────┬─────────────┘
           ▼
┌───────────────────────┐
│ Groq Llama 3.3 70B     │   COMPREHENSIVE_RESUME_PROMPT extracts:
│ Structured Extraction  │   candidate info, skills, experience, education,
│                        │   certifications, projects, achievements, keywords
└──────────┬─────────────┘
           ▼
┌───────────────────────┐
│ Normalization Layer    │   normalization.py maps raw strings to canonical
│ (app/core/normaliza-   │   forms (e.g. "react.js" → "React", "b.tech" →
│  tion.py)              │   "Bachelor of Technology")
└──────────┬─────────────┘
           ▼
┌───────────────────────┐
│ Deterministic Quality  │   calculate_resume_quality_v2() — scores out of
│ Scoring (no JD yet)    │   110 normalized to 100 across: contact info,
│                        │   summary, skills, projects, experience,
│                        │   education, certs, achievements, ATS formatting
└──────────┬─────────────┘
           ▼
┌───────────────────────┐
│ Persist to MongoDB      │   resumes collection: parsed_data, raw_text,
│ (resumes collection)    │   resume_embeddings placeholder for vector search
└───────────────────────┘
```

If Groq is unavailable (`IS_MOCK_MODE`), the system falls back to `generate_mock_resume_data()`, a regex/keyword-based heuristic extractor that never invents skills not present in the raw text.

### 5.2 ATS Match (Resume ↔ Job Description) Pipeline

```
Resume (parsed) + Job Description (raw text)
        │
        ▼
┌─────────────────────────┐
│ Detailed ATS Analysis    │  Gemini (DETAILED_ATS_PROMPT) — full resume
│ (Gemini)                 │  re-parse + general ATS readiness OR JD-aware
│                           │  match analysis, depending on whether a JD
│                           │  was supplied
└──────────┬────────────────┘
           ▼
┌─────────────────────────┐
│ JD Skill Extraction       │  Groq Llama (JD_SKILL_EXTRACTION_PROMPT)
│ (Groq)                    │  → technical_skills, soft_skills, experience/
│                           │  education/certification requirements
└──────────┬────────────────┘
           ▼
┌─────────────────────────┐
│ Normalization              │  Both resume & JD skill lists normalized to
│                            │  canonical form + deduplicated
└──────────┬────────────────┘
           ▼
┌─────────────────────────┐
│ Skill Matcher (5-step)      │  1. Normalize  2. Expand via taxonomy.json
│ (skill_engine/matcher.py)   │  3. Exact match  4. Taxonomy (parent/child)
│                             │  match  5. Semantic match via Sentence-
│                             │  Transformers cosine similarity (≥0.70)
└──────────┬────────────────┘
           ▼
┌─────────────────────────┐
│ Deterministic ATS Formula   │  calculate_comprehensive_ats_score():
│ (scoring.py)                │   Skills 40% + Experience 20% + Projects 15%
│                             │   + Education 10% + Certifications 5%
│                             │   + Resume Quality 10%
└──────────┬────────────────┘
           ▼
┌─────────────────────────┐
│ Gemini Personalized          │  If skill gaps exist, Gemini generates a
│ Recommendation                │  Markdown roadmap of technical/soft-skill
│                               │  advice + immediate-focus learning plan
└──────────┬────────────────┘
           ▼
   MatchAnalysisResponse (match_score, category_scores, matched/missing
   skills, recommendation_markdown, parsed_resume, parsed_jd)
        │
        ▼
   Stored in MongoDB (detailed_ats_logs) + skills stored in ChromaDB for
   future semantic lookups (store_skills_in_db)
```

### 5.3 Skill-Gap Simulator Pipeline

The Simulator page lets a user "check off" missing JD skills to see the score impact live:

```
User toggles a missing-skill checkbox
        │
        ▼
POST /match/simulate_score { parsed_resume, parsed_jd, simulated_technical_skills }
        │
        ▼
Inject simulated skills into a deep copy of parsed_resume["normalized"]["technical_skills"]
        │
        ▼
Re-run calculate_comprehensive_ats_score() — same deterministic math as /match/analyze
        │
        ▼
Return updated match_score + category_scores → animated score ring on frontend
```

This guarantees the simulated score is mathematically consistent with the real ATS formula (no separate "fake" scoring logic).

### 5.4 AI Mock Interview State Machine

```
            ┌──────────────┐
            │ introduction  │  AI (Alex Chen persona) greets candidate
            └──────┬───────┘
                   │ candidate responds (>5 chars)
                   ▼
            ┌──────────────┐
            │  job_role     │  Extract target role via regex/keyword patterns
            └──────┬───────┘  (_extract_role_from_text)
                   │ role detected or stored
                   ▼
            ┌──────────────┐
            │   resume      │  Candidate pastes resume text or uploads a file
            └──────┬───────┘  (/interview/upload_resume persists raw_text)
                   │ resume captured
                   ▼
            ┌──────────────┐
            │  technical    │  Role-specific topic clusters (ROLE_TOPIC_MAP)
            └──────┬───────┘  drive contextual questions; asked_topics tracked
                   │ is_complete = true
                   ▼
            ┌──────────────┐
            │  assessment   │  /interview/assess returns structured JSON rubric:
            └──────────────┘  overall/technical/communication/resume_strength/
                               role_fit scores + strengths/weaknesses/missing_skills
```

State (`phase`, `target_role`, `resume_data`, `asked_topics`, `message_history`) is **MongoDB-authoritative** — the backend never trusts client-side phase tracking, eliminating drift between client and server state across reconnects.

### 5.5 Market Analytics Pipeline

```
GET /analytics/trends?domain=...
        │
        ▼
┌─────────────────────┐
│ AdzunaClient          │  Parallel-ish calls: search_jobs, get_categories,
│ (httpx, multi-call)   │  get_salary_histogram, get_historical_salaries,
│                       │  get_top_companies, get_geo_salary_data
└──────────┬────────────┘
           ▼
┌─────────────────────┐
│ Pandas Processing      │  Cleans salary fields, fills missing values with
│                       │  medians, filters outliers (5th–95th percentile)
└──────────┬────────────┘
           ▼
┌─────────────────────┐
│ spaCy NLP Skill        │  POS-tagging (PROPN/NOUN) over job description
│ Extraction             │  text → Counter-ranked top skills
└──────────┬────────────┘
           ▼
   TrendAnalyticsResponse → Recharts dashboards on /analytics
```

A separate endpoint, `/analytics/top-fresher-jobs`, asks Gemini directly (structured JSON output mode) for the top 10 entry-level jobs and in-demand skills for 2026 BTech graduates — this is a pure LLM-knowledge endpoint, not Adzuna-backed.

---

## 6. Data Model (MongoDB Collections)

```
resumes
 ├─ filename, content_type, uploaded_at
 ├─ parsed_data: { name, email, skills[], technical_skills[], soft_skills[],
 │                 experience[], education[], projects[], certifications[],
 │                 gaps[], ats_score, strengths[], weaknesses[], recommendations[] }
 ├─ raw_extracted_text
 └─ resume_embeddings[]   (reserved for Atlas Vector Search)

detailed_ats_logs
 ├─ timestamp, job_description_snippet
 ├─ detailed_result (full Gemini parse output)
 ├─ is_ai_powered
 ├─ jd_skills[], missing_skills[]

interview_sessions
 ├─ session_id, status (ongoing|completed), phase
 ├─ target_role, resume_data { raw_text, filename, char_count }
 ├─ candidate_name, asked_topics[]
 ├─ message_history[] { sender, timestamp, text }
 └─ assessment_rubric { markdown }

match_logs   (indexed on computed_match_score, reserved for analytics)
```

ChromaDB (`chroma_data/`, local persistent client) stores a single collection, `resume_jd_skills`, with cosine-similarity HNSW indexing, used for fast in-memory semantic matching between resume and JD skill sets via `all-MiniLM-L6-v2` embeddings.

---

## 7. AI / ML Subsystem Summary

| Component | Model / Library | Purpose |
|---|---|---|
| Resume structured parsing | Groq `llama-3.3-70b-versatile` | Extract candidate info, skills, experience, projects from raw text |
| JD structured parsing | Groq `llama-3.3-70b-versatile` | Extract technical/soft skills & requirements from job descriptions |
| Detailed ATS scoring assist | Gemini `gemini-flash-latest` | Resume-only readiness scoring; JD-aware match narrative |
| Personalized recommendations | Gemini `gemini-flash-latest` | Markdown skill-gap coaching roadmap |
| Cover letter generation | Groq Llama | 3-paragraph tailored cover letters |
| Interview conversation | Groq Llama | Persona-driven multi-phase interview dialogue |
| Interview rubric | Groq Llama (JSON mode) | Structured numeric scoring + verdict |
| Outreach email generation | Gemini `gemini-2.0-flash` | Cold-outreach email subject + body |
| Fresher job/skill insights | Gemini `gemini-2.5-flash` | Knowledge-based job market suggestions |
| Semantic skill matching | Sentence-Transformers (`all-MiniLM-L6-v2`) + scikit-learn cosine distance | Matches resume skills to JD skills that are textually different but semantically equivalent |
| Market text mining | spaCy (`en_core_web_sm`) | POS-tag based skill keyword extraction from live job descriptions |
| Skill taxonomy expansion | `taxonomy.json` (static hierarchy) | Maps specific tools → parent skill categories (e.g. PyTorch → Deep Learning) |

Every LLM-touching endpoint has a deterministic, non-AI fallback path (`IS_MOCK_MODE` / `IS_GEMINI_MOCK` / `IS_GROQ_MOCK`) so the application degrades gracefully rather than failing outright when an API key is missing or a provider rate-limits.

---

## 8. Request Lifecycle Example (End-to-End)

Walkthrough of a user uploading a resume, pasting a job description, and getting an ATS score:

```
1. User drags a PDF onto /analyze
2. Frontend: uploadResume(file) → POST /resume/upload (multipart/form-data)
3. Backend: PyMuPDF/pdfplumber extracts text → Groq parses structured fields
            → normalization.py canonicalizes skill names
            → calculate_resume_quality_v2() computes a quality score
            → MongoDB stores the resume document
            → Response: { name, email, skills[], technical_skills[], ... }
4. Frontend: setResumeData(response) — now visible across all pages
5. User pastes a job description and clicks "Run ATS Check"
6. Frontend: triggerAnalyze(jobDesc) → POST /match/analyze
7. Backend: Gemini detailed-ATS parse + Groq JD-skill extraction
            → normalization + SkillMatcher 5-step pipeline
            → calculate_comprehensive_ats_score() (deterministic formula)
            → Gemini personalized recommendation (if gaps exist)
            → Response: { match_score, category_scores, matched_skills,
                            missing_skills, recommendation_markdown, ... }
8. Frontend: renders ScoreRing, CategoryBars, matched/missing keyword chips,
            and the Markdown recommendation panel
9. Missing skills auto-populate resumeData.gaps → visible immediately on
   /simulator without any extra network call
```

---

## 9. Local Development Setup

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate          # Windows: .\venv\Scripts\activate
pip install -r requirements.txt

# .env (create this file in backend/)
PORT=8000
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=careerpilot
CORS_ORIGINS=http://localhost:3000
GROQ_API_KEY=your_groq_key
GEMINI_API_KEY=your_gemini_key
ADZUNA_APP_ID=your_adzuna_app_id
ADZUNA_APP_KEY=your_adzuna_app_key

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- Swagger docs: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Frontend

```bash
cd frontend
npm install

# .env.local (create this file in frontend/)
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1

npm run dev
```

Open `http://localhost:3000` (redirects to `/analyze`).

---

## 10. Repository Structure

```
.
├── backend/
│   ├── app/
│   │   ├── main.py                      # FastAPI app, middleware, router mounting
│   │   ├── core/
│   │   │   ├── config.py                # Pydantic Settings (.env loader)
│   │   │   ├── database.py              # Motor client + index setup
│   │   │   ├── normalization.py         # Canonical skill/degree/title maps
│   │   │   ├── scoring.py               # Deterministic ATS scoring formulas
│   │   │   ├── vector_store.py          # ChromaDB client + semantic matching
│   │   │   └── skill_engine/
│   │   │       ├── matcher.py           # 5-step skill matching orchestrator
│   │   │       ├── skill_normalizer.py
│   │   │       ├── skill_expander.py
│   │   │       ├── taxonomy_manager.py
│   │   │       ├── taxonomy.json
│   │   │       ├── embedding_matcher.py
│   │   │       └── scorer.py
│   │   ├── models/
│   │   │   └── schemas.py               # All Pydantic request/response models
│   │   └── routers/
│   │       ├── resume.py
│   │       ├── match.py
│   │       ├── interview.py
│   │       ├── analytics.py
│   │       └── outreach.py
│   └── requirements.txt
│
└── frontend/
    ├── app/
    │   ├── layout.tsx
    │   ├── page.tsx
    │   ├── globals.css
    │   ├── context/ProjectContext.tsx
    │   ├── analyze/page.tsx
    │   ├── simulator/page.tsx
    │   ├── interview/page.tsx
    │   ├── outreach/page.tsx
    │   ├── analytics/page.tsx
    │   ├── about/page.tsx
    │   └── support/page.tsx
    ├── components/
    │   ├── Sidebar.tsx
    │   └── Header.tsx
    └── package.json
```

---

## 11. Design Principles Used Throughout

- **Deterministic-first scoring**: ATS match percentage is always computed by an explicit weighted formula (`scoring.py`), never solely by an LLM's subjective opinion — LLMs are used for *extraction* and *narrative recommendations*, not for the final numeric score. This keeps scores reproducible and explainable.
- **Graceful AI degradation**: every Groq/Gemini call path has a deterministic or heuristic fallback so the app keeps functioning without API keys.
- **Server-authoritative state**: the interview phase machine and session history live in MongoDB, not in the browser, preventing desync across reloads or multiple tabs.
- **Normalization layer as a single source of truth**: all raw, messy LLM-extracted strings ("node", "ReactJS", "b.tech") pass through `app/core/normalization.py` before being compared, scored, or displayed — this keeps matching logic accurate and skill chips consistent across the UI.
- **Layered skill matching**: exact → taxonomy (parent/child) → semantic (embeddings) — ensures skills that are phrased differently but mean the same thing (e.g. "PyTorch" satisfying a "Deep Learning" requirement) are still credited.
