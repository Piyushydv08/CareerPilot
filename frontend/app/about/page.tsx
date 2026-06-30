"use client";

import React from "react";
import {
  Info,
  Cpu,
  BrainCircuit,
  MessageSquareCode,
  SendHorizontal,
  BarChart2,
  Database,
  Key,
  Terminal,
  Server,
  Code2,
  ShieldAlert,
  ArrowUpRight
} from "lucide-react";

export default function AboutPage() {
  return (
    <div className="mx-auto max-w-[1280px] p-8 animate-fade-in text-left">
      {/* Header */}
      <header className="mb-10 border-b border-outline-variant/40 pb-6">
        <h2 className="text-3xl font-bold tracking-tight text-white flex items-center gap-3">
          Platform Specifications & Telemetry Details <Info className="h-7 w-7 text-cyber-blue animate-pulse" />
        </h2>
        <p className="text-sm text-on-surface-variant mt-2 font-mono leading-relaxed">
          Comprehensive technical documentation detailing page routing telemetry, backend microservice pipelines, database schemas, and AI model configurations powering the CareerPilot v2.4.0 architecture.
        </p>
      </header>

      {/* Grid: Page Specifications */}
      <section className="mb-12">
        <h3 className="font-mono text-xs font-bold text-cyber-blue uppercase tracking-widest border-b border-outline-variant/60 pb-3 mb-6 flex items-center gap-2">
          <Code2 className="h-4 w-4" />
          <span>Detailed Page Telemetry & Feature Workflows</span>
        </h3>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Card 1: Engine */}
          <div className="bento-card rounded-lg p-6 flex flex-col gap-5">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded bg-cyber-blue/10 border border-cyber-blue/30 flex items-center justify-center shrink-0">
                <Cpu className="h-5 w-5 text-cyber-blue" />
              </div>
              <div>
                <h4 className="font-sans text-base font-bold text-white leading-none">Telemetry Engine</h4>
                <span className="font-mono text-[9px] text-cyber-blue uppercase tracking-wider">/analyze</span>
              </div>
            </div>
            <div className="text-xs text-on-surface-variant flex-1 flex flex-col gap-4">
              <p className="leading-relaxed">
                <strong>What it has:</strong> An ingestion hub equipped with a drag-and-drop file upload zone supporting PDF and DOCX formats, a structural resume text extractor, a comprehensive job description input terminal, and a live "Run ATS Check" diagnostic button.
              </p>
              <p className="leading-relaxed">
                <strong>How it works:</strong> Ingested files are fed into async backend parsers (`pdfplumber` and `docx`) that extract raw strings. The Gemini model (`gemini-flash-latest`) analyzes structural profiles, while a Sentence-Transformer semantic search model compares candidate capabilities against normalized requirements extracted from job descriptions.
              </p>
              <p className="leading-relaxed">
                <strong>User Benefit:</strong> Calculates a highly accurate ATS compatibility score with category-specific matching details (skills match, experience relevance, formatting completeness), exposes critical keyword gaps, and drafts AI-customized cover letters to help resumes pass automated screens.
              </p>
            </div>
          </div>

          {/* Card 2: Simulator */}
          <div className="bento-card rounded-lg p-6 flex flex-col gap-5">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded bg-cyber-blue/10 border border-cyber-blue/30 flex items-center justify-center shrink-0">
                <BrainCircuit className="h-5 w-5 text-cyber-blue" />
              </div>
              <div>
                <h4 className="font-sans text-base font-bold text-white leading-none">Predictive Simulator</h4>
                <span className="font-mono text-[9px] text-cyber-blue uppercase tracking-wider">/simulator</span>
              </div>
            </div>
            <div className="text-xs text-on-surface-variant flex-1 flex flex-col gap-4">
              <p className="leading-relaxed">
                <strong>What it has:</strong> A dynamic checklist of missing resume skills extracted from the job description alongside estimated scoring impacts, checklist checkboxes, and an automated learning path generator.
              </p>
              <p className="leading-relaxed">
                <strong>How it works:</strong> Monitors user interactions to simulate the hypothetical impact of acquiring missing skills. Toggling a checklist checkbox triggers the `/match/simulate_score` endpoint to re-run the mathematical matching formula.
              </p>
              <p className="leading-relaxed">
                <strong>User Benefit:</strong> Provides a sandboxed simulation to identify which skills yield the highest resume score increase, and triggers a structured AI-compiled learning roadmap containing targeted study resources to help candidates efficiently fill their knowledge gaps.
              </p>
            </div>
          </div>

          {/* Card 3: Interview */}
          <div className="bento-card rounded-lg p-6 flex flex-col gap-5">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded bg-cyber-blue/10 border border-cyber-blue/30 flex items-center justify-center shrink-0">
                <MessageSquareCode className="h-5 w-5 text-cyber-blue" />
              </div>
              <div>
                <h4 className="font-sans text-base font-bold text-white leading-none">AI Mock Interview</h4>
                <span className="font-mono text-[9px] text-cyber-blue uppercase tracking-wider">/interview</span>
              </div>
            </div>
            <div className="text-xs text-on-surface-variant flex-1 flex flex-col gap-4">
              <p className="leading-relaxed">
                <strong>What it has:</strong> An immersive mock interview panel featuring a progressive message logger, realistic AI typing state indicators, dynamic text inputs, and playground control actions.
              </p>
              <p className="leading-relaxed">
                <strong>How it works:</strong> Starts a customized interview session via FastAPI endpoints (`/interview/start`). The session keeps track of conversational states and uses the candidate's resume and job requirements to generate tailored, highly realistic technical screening questions.
              </p>
              <p className="leading-relaxed">
                <strong>User Benefit:</strong> Recreates live interview scenarios under real-time conditions, allowing candidates to practice, refine their technical articulation, and review feedback in a low-stakes simulator.
              </p>
            </div>
          </div>

          {/* Card 4: Outreach */}
          <div className="bento-card rounded-lg p-6 flex flex-col gap-5">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded bg-cyber-blue/10 border border-cyber-blue/30 flex items-center justify-center shrink-0">
                <SendHorizontal className="h-5 w-5 text-cyber-blue" />
              </div>
              <div>
                <h4 className="font-sans text-base font-bold text-white leading-none">Campaign Outreach</h4>
                <span className="font-mono text-[9px] text-cyber-blue uppercase tracking-wider">/outreach</span>
              </div>
            </div>
            <div className="text-xs text-on-surface-variant flex-1 flex flex-col gap-4">
              <p className="leading-relaxed">
                <strong>What it has:</strong> Outreach copy generator tools, customized email sequencing templates, outbound applications record tracker, and direct copy-paste interfaces.
              </p>
              <p className="leading-relaxed">
                <strong>How it works:</strong> Gathers matching telemetry data (resume strengths, role specifications, target company names) to compose personalized cold pitches, networking messages, and cover letters using Gemini LLM models.
              </p>
              <p className="leading-relaxed">
                <strong>User Benefit:</strong> Eliminates writer's block by drafting high-converting, tailored email outreaches that highlight actual overlapping capabilities, saving time and keeping pipelines organized.
              </p>
            </div>
          </div>

          {/* Card 5: Analytics */}
          <div className="bento-card rounded-lg p-6 flex flex-col gap-5 lg:col-span-2">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded bg-cyber-blue/10 border border-cyber-blue/30 flex items-center justify-center shrink-0">
                <BarChart2 className="h-5 w-5 text-cyber-blue" />
              </div>
              <div>
                <h4 className="font-sans text-base font-bold text-white leading-none">Career Intelligence</h4>
                <span className="font-mono text-[9px] text-cyber-blue uppercase tracking-wider">/analytics</span>
              </div>
            </div>
            <div className="text-xs text-on-surface-variant flex-1 flex flex-col gap-4">
              <p className="leading-relaxed">
                <strong>What it has:</strong> A central intelligence dashboard featuring charts rendering overall skill matches, category scores (formatting, keyword density), and interactive timeline logs.
              </p>
              <p className="leading-relaxed">
                <strong>How it works:</strong> Aggregates historically stored MongoDB telemetry logs of previous ATS checks, parses performance vectors, and serves formatted JSON data to visual React charting libraries.
              </p>
              <p className="leading-relaxed">
                <strong>User Benefit:</strong> Delivers clear visual reports on candidate progress, demonstrating skill growth and profile readiness to guide strategic career moves.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Grid: Backend Tech Stack & Database Architecture */}
      <section className="mb-12">
        <h3 className="font-mono text-xs font-bold text-cyber-blue uppercase tracking-widest border-b border-outline-variant/60 pb-3 mb-6 flex items-center gap-2">
          <Server className="h-4 w-4" />
          <span>Backend Microservices & Databases Stack</span>
        </h3>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Tech stack */}
          <div className="bento-card rounded-lg p-6 flex flex-col gap-4">
            <h4 className="font-sans text-base font-bold text-white flex items-center gap-2 border-b border-outline-variant/30 pb-2">
              <Terminal className="h-4 w-4 text-cyber-blue" /> Asynchronous Python FastAPI Engine
            </h4>
            <div className="text-xs text-on-surface-variant space-y-4 leading-relaxed">
              <p>
                The core backend service is built using **FastAPI**, an ASGI framework that provides extremely fast routing, automated OpenAPI generation, and asynchronous execution.
              </p>
              <p>
                Unlike standard blocking synchronous Python APIs, FastAPI utilizes Python's `async/await` syntax. This allows CareerPilot to handle multiple concurrent telemetry requests (such as processing file uploads while generating text recommendations) on a single thread without CPU blocking.
              </p>
              <div className="space-y-3 border-l-2 border-cyber-blue/30 pl-4 mt-3">
                <p><strong>· pdfplumber & python-docx:</strong> Extract structural textual content from PDF/DOCX candidate resume uploads by scanning line coordinates and typography grids.</p>
                <p><strong>· Pydantic v2:</strong> Enforces strict type checking and validation guards on request/response payloads to protect backend data integrity.</p>
                <p><strong>· Motor client:</strong> Serves as the asynchronous driver connecting FastAPI endpoints directly to MongoDB Atlas, avoiding blocking latency.</p>
              </div>
            </div>
          </div>

          {/* Database & Vectors */}
          <div className="bento-card rounded-lg p-6 flex flex-col gap-4">
            <h4 className="font-sans text-base font-bold text-white flex items-center gap-2 border-b border-outline-variant/30 pb-2">
              <Database className="h-4 w-4 text-cyber-blue" /> NoSQL MongoDB & Semantic ChromaDB
            </h4>
            <div className="text-xs text-on-surface-variant space-y-4 leading-relaxed">
              <p>
                We use a hybrid storage design to support both traditional database operations and advanced vector-based semantic analysis.
              </p>
              <p>
                This split layer ensures MongoDB handles structured logging and document storage, while ChromaDB handles semantic vector matching.
              </p>
              <div className="space-y-3 border-l-2 border-cyber-blue/30 pl-4 mt-3">
                <p><strong>· MongoDB database:</strong> Stores profile information, session analytics, telemetry histories, and dynamic mock interview chat logs.</p>
                <p><strong>· ChromaDB vector database:</strong> Indexes normalized skill sets using advanced text embeddings.</p>
                <p><strong>· Sentence-Transformers:</strong> Powers semantic vector comparisons to identify missing skills that are semantically identical (e.g. "ReactJS" matching "React").</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Section: API Integration Details */}
      <section className="mb-8">
        <h3 className="font-mono text-xs font-bold text-cyber-blue uppercase tracking-widest border-b border-outline-variant/60 pb-3 mb-6 flex items-center gap-2">
          <Key className="h-4 w-4" />
          <span>API Key-Vault Configuration & Model Implementations</span>
        </h3>

        <div className="bento-card rounded-lg p-6">
          <div className="flex items-center gap-2 border-b border-outline-variant/30 pb-3 mb-4 text-amber-400">
            <ShieldAlert className="h-4 w-4 shrink-0" />
            <span className="font-mono text-xs font-bold uppercase tracking-wider">Credential Telemetry</span>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 text-xs text-on-surface-variant">
            {/* Gemini */}
            <div className="flex flex-col gap-2 p-4 rounded bg-[#07070a]/50 border border-outline-variant/50">
              <span className="font-mono text-[10px] text-cyber-blue uppercase font-bold tracking-wider">Google Gemini API</span>
              <p className="leading-relaxed">
                <strong>Key used:</strong> `GEMINI_API_KEY`
              </p>
              <p className="leading-relaxed">
                <strong>Model:</strong> `gemini-flash-latest`
              </p>
              <p className="text-[11px] text-on-surface-variant/80 mt-1 leading-relaxed">
                Powers structural resume parsing, cover letter generation, AI recommendation markdown compiles, and mock interview questions.
              </p>
            </div>

            {/* Groq */}
            <div className="flex flex-col gap-2 p-4 rounded bg-[#07070a]/50 border border-outline-variant/50">
              <span className="font-mono text-[10px] text-cyber-blue uppercase font-bold tracking-wider">Groq API</span>
              <p className="leading-relaxed">
                <strong>Key used:</strong> `GROQ_API_KEY`
              </p>
              <p className="leading-relaxed">
                <strong>Model:</strong> `llama-3.3-70b-versatile`
              </p>
              <p className="text-[11px] text-on-surface-variant/80 mt-1 leading-relaxed">
                Inferences the `llama-3.3-70b-versatile` model to parse pasted job descriptions into structured JSON requirements instantly.
              </p>
            </div>

            {/* Adzuna */}
            <div className="flex flex-col gap-2 p-4 rounded bg-[#07070a]/50 border border-outline-variant/50">
              <span className="font-mono text-[10px] text-cyber-blue uppercase font-bold tracking-wider">Adzuna API</span>
              <p className="leading-relaxed">
                <strong>Keys used:</strong> `ADZUNA_APP_ID`, `ADZUNA_APP_KEY`
              </p>
              <p className="leading-relaxed">
                <strong>Endpoint:</strong> `api.adzuna.com`
              </p>
              <p className="text-[11px] text-on-surface-variant/80 mt-1 leading-relaxed">
                Queries live, location-filtered job openings matching the candidate's canonical skill profile to return matching job opportunities.
              </p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
