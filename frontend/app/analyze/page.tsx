"use client";

import React, { useState, useRef } from "react";
import ReactMarkdown from "react-markdown";
import {
  UploadCloud,
  FileText,
  Cpu,
  CheckCircle,
  Sparkles,
  AlertTriangle,
  Brain,
  Building,
  Calendar,
  Send,
  Loader,
  FileEdit,
  TrendingUp,
  Briefcase,
  MapPin,
  Wifi,
  File
} from "lucide-react";
import { useProject, ResumeData } from "../context/ProjectContext";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export default function AnalyzePage() {
  const {
    resumeData,
    uploadResume,
    triggerAnalyze,
    isAnalyzing,
    jobDescription,
    matchScore
  } = useProject();

  const [dragActive, setDragActive] = useState(false);
  const [parsingStep, setParsingStep] = useState(0);
  const [jobInput, setJobInput] = useState(jobDescription);
  const [isUpdatingMatch, setIsUpdatingMatch] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploadedFileName, setUploadedFileName] = useState<string | null>(null);

  // Keep a local ref to freshly uploaded resume data to avoid stale closure
  const freshResumeRef = useRef<ResumeData | null>(null);

  // Cover letter state
  const [coverLetter, setCoverLetter] = useState<string | null>(null);
  const [isGeneratingCover, setIsGeneratingCover] = useState(false);
  const [coverError, setCoverError] = useState<string | null>(null);
  const [showCoverPanel, setShowCoverPanel] = useState(false);

  // Job listings state
  type JobItem = {
    id: string;
    title: string;
    company: string;
    location: string;
    description: string;
    salary_min: number | null;
    salary_max: number | null;
    salary_is_predicted: boolean;
    contract_time: string;
    redirect_url: string;
    created: string;
    category: string;
  };
  type JobsData = { total_count: number; jobs: JobItem[] };
  const [jobsData, setJobsData] = useState<JobsData | null>(null);
  const [isFetchingJobs, setIsFetchingJobs] = useState(false);
  const [jobsError, setJobsError] = useState<string | null>(null);

  const parsingSteps = [
    "Decrypting file structure...",
    "Extracting semantic typography grids...",
    "Benchmarking technical skill taxonomy...",
    "Synthesizing job alignment index..."
  ];

  // Build search query from resume skills + optional JD
  const buildSearchDomain = (resume: ResumeData | null, jd: string) => {
    if (jd.trim()) {
      // Split by common separators to isolate the main job title/role
      const parts = jd.trim().split(/\s+(?:at|for|posting|in|with|on)\b/i);
      const cleanTitle = parts[0].trim();
      if (cleanTitle) {
        // Return the first 4 words of the job title
        return cleanTitle.split(/\s+/).slice(0, 4).join(" ");
      }
      return jd.trim().split(/\s+/).slice(0, 4).join(" ");
    }
    
    if (resume?.skills && resume.skills.length > 0) {
      // Use top 2 skills for a broad, technology-focused search query
      return resume.skills
        .sort((a, b) => b.match - a.match)
        .slice(0, 2)
        .map(s => s.name)
        .join(" ");
    }
    return "software developer";
  };

  const fetchJobs = async (searchDomain: string) => {
    setIsFetchingJobs(true);
    setJobsError(null);
    try {
      const res = await fetch(
        `${BASE_URL}/analytics/jobs?domain=${encodeURIComponent(searchDomain)}&results_per_page=6`
      );
      if (res.ok) {
        const data = await res.json();
        setJobsData(data);
      } else {
        setJobsError("Could not load job listings. Please try again.");
      }
    } catch {
      setJobsError("Jobs service unreachable. Check your connection.");
    } finally {
      setIsFetchingJobs(false);
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") setDragActive(true);
    else if (e.type === "dragleave") setDragActive(false);
  };

  const processFileUpload = async (file: File) => {
    setUploadedFileName(file.name);
    setParsingStep(0);
    setCoverLetter(null);
    setShowCoverPanel(false);
    setJobsData(null);
    freshResumeRef.current = null;

    const interval = setInterval(() => {
      setParsingStep(prev => {
        if (prev < parsingSteps.length - 1) return prev + 1;
        clearInterval(interval);
        return prev;
      });
    }, 600);

    await uploadResume(file);
    clearInterval(interval);

    // After upload, use context resumeData via a small delay for state to settle
    // Then fetch jobs based on resume skills
    setTimeout(async () => {
      // Read freshest resumeData from context via ref pattern
      const currentResume = freshResumeRef.current ?? resumeData;
      const domain = buildSearchDomain(currentResume, jobInput);
      await fetchJobs(domain);
    }, 800);
  };

  // Sync fresh resume ref whenever resumeData changes
  // This is done via a useEffect-like pattern using the ref
  if (resumeData && resumeData !== freshResumeRef.current) {
    freshResumeRef.current = resumeData;
  }

  const handleRecalculateMatch = async () => {
    if (!resumeData && !jobInput.trim()) return;
    setIsUpdatingMatch(true);

    if (jobInput.trim()) {
      await triggerAnalyze(jobInput);
    }
    setIsUpdatingMatch(false);

    // Use the freshest resume data available
    const currentResume = freshResumeRef.current ?? resumeData;
    const domain = buildSearchDomain(currentResume, jobInput);
    await fetchJobs(domain);
  };

  const handleUploadClick = () => fileInputRef.current?.click();

  const handleGenerateCoverLetter = async () => {
    if (!resumeData) return;
    setIsGeneratingCover(true);
    setCoverError(null);
    setShowCoverPanel(true);
    try {
      const response = await fetch(`${BASE_URL}/resume/cover_letter`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          resume: resumeData,
          job_description: jobInput || jobDescription
        })
      });
      if (response.ok) {
        const data = await response.json();
        setCoverLetter(data.cover_letter);
      } else {
        setCoverError("Cover letter generation failed. Please try again.");
      }
    } catch {
      setCoverError("Could not reach the AI backend. Check your connection.");
    } finally {
      setIsGeneratingCover(false);
    }
  };

  return (
    <div className="mx-auto max-w-[1280px] p-8 animate-fade-in">
      <header className="mb-8">
        <h2 className="text-3xl font-bold tracking-tight text-white flex items-center gap-2">
          Telemetry Analysis <Cpu className="h-6 w-6 text-cyber-blue" />
        </h2>
        <p className="text-sm text-on-surface-variant mt-1 font-mono">
          Centralized parser targeting /api/v1/resume/upload. Drag files to index profile indices.
        </p>
      </header>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-12">
        {/* Left Side */}
        <div className="lg:col-span-5 flex flex-col gap-6">
          <div className="bento-card rounded-lg p-6 flex flex-col gap-6">
            <h3 className="font-mono text-[10px] uppercase tracking-wider text-on-surface-variant font-semibold">
              Profile File Ingestion
            </h3>

            {/* Drag drop zone */}
            <div
              onDragEnter={handleDrag}
              onDragOver={handleDrag}
              onDragLeave={handleDrag}
              onDrop={async (e) => {
                e.preventDefault();
                e.stopPropagation();
                setDragActive(false);
                if (e.dataTransfer.files?.[0]) await processFileUpload(e.dataTransfer.files[0]);
              }}
              onClick={handleUploadClick}
              className={`flex flex-col items-center justify-center border-2 border-dashed rounded-lg cursor-pointer transition-all duration-300 relative group min-h-[180px] ${dragActive
                  ? "border-cyber-blue bg-cyber-blue/[0.04] shadow-[0_0_15px_rgba(0,210,255,0.15)] scale-[0.99]"
                  : uploadedFileName
                    ? "border-cyber-blue/40 bg-cyber-blue/[0.02]"
                    : "border-outline-variant hover:border-cyber-blue/40 bg-surface-container-low"
                }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                className="hidden"
                accept=".pdf,.docx"
                onChange={async (e) => {
                  if (e.target.files?.[0]) await processFileUpload(e.target.files[0]);
                }}
              />

              {uploadedFileName ? (
                <div className="flex flex-col items-center gap-3 p-8">
                  <div className="w-10 h-10 rounded-full bg-cyber-blue/10 border border-cyber-blue/30 flex items-center justify-center">
                    <File className="h-5 w-5 text-cyber-blue" />
                  </div>
                  <div className="text-center">
                    <p className="font-mono text-[11px] text-cyber-blue font-semibold truncate max-w-[200px]">
                      {uploadedFileName}
                    </p>
                    <p className="font-mono text-[9px] text-on-surface-variant/50 uppercase tracking-wider mt-1">
                      Resume indexed · click to replace
                    </p>
                  </div>
                  <div className="flex items-center gap-1.5 mt-1">
                    <CheckCircle className="h-3.5 w-3.5 text-cyber-blue" />
                    <span className="font-mono text-[9px] text-cyber-blue uppercase tracking-wider">Profile Active</span>
                  </div>
                </div>
              ) : (
                <div className="flex flex-col items-center p-10">
                  <UploadCloud className={`h-12 w-12 mb-4 transition-transform duration-300 group-hover:scale-110 ${dragActive ? "text-cyber-blue" : "text-on-surface-variant group-hover:text-cyber-blue"
                    }`} />
                  <p className="font-sans text-sm font-semibold text-white mb-1.5 text-center">
                    Drag and drop your resume file
                  </p>
                  <p className="font-mono text-[10px] text-on-surface-variant uppercase tracking-wider text-center">
                    PDF, DOCX UP TO 8MB
                  </p>
                </div>
              )}
            </div>

            {/* Job Description */}
            <div className="flex flex-col gap-3 text-left">
              <div className="flex items-center justify-between">
                <label className="font-mono text-[10px] uppercase tracking-wider text-on-surface-variant font-semibold flex items-center gap-1.5">
                  <Briefcase className="h-3 w-3 text-cyber-blue" />
                  Job Description
                </label>
                <span className="font-mono text-[9px] text-on-surface-variant/50 uppercase tracking-wider border border-outline-variant/30 px-1.5 py-0.5 rounded-sm">
                  Optional
                </span>
              </div>
              <div className="relative rounded border border-outline-variant bg-[#0c0c10] shadow-sm flex flex-col overflow-hidden focus-within:border-cyber-blue/40 transition-colors duration-300">
                <textarea
                  className="w-full bg-transparent border-none text-white font-sans text-xs focus:ring-0 resize-none h-28 p-3 focus:outline-none placeholder:text-on-surface-variant/40 leading-relaxed"
                  placeholder={"Paste a job posting or describe the role you're targeting...\n\ne.g. Senior Frontend Engineer at a fintech startup..."}
                  value={jobInput}
                  onChange={(e) => setJobInput(e.target.value)}
                />
                <div className="flex items-center justify-between px-3 py-2 border-t border-outline-variant/30 bg-[#08080c]">
                  <span className="font-mono text-[9px] text-on-surface-variant/40 uppercase tracking-wider">
                    {jobInput.trim()
                      ? `${jobInput.trim().split(/\s+/).length} words · refines job matching`
                      : resumeData
                        ? "Jobs matched to your resume skills"
                        : "Upload resume first"}
                  </span>
                  <button
                    onClick={handleRecalculateMatch}
                    disabled={isUpdatingMatch || (!resumeData && !jobInput.trim())}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-cyber-blue text-black hover:bg-white transition-colors cursor-pointer shrink-0 disabled:opacity-30 disabled:cursor-not-allowed font-mono text-[9px] font-bold uppercase tracking-wider"
                  >
                    {isUpdatingMatch
                      ? <><Loader className="h-3 w-3 animate-spin" /><span>Scanning...</span></>
                      : <><Send className="h-3 w-3" /><span>Analyze</span></>}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Side */}
        <div className="lg:col-span-7 flex flex-col gap-6">
          {isAnalyzing ? (
            <div className="bento-card rounded-lg p-8 flex flex-col gap-6 animate-pulse">
              <h3 className="font-mono text-[10px] uppercase tracking-wider text-cyber-blue font-bold flex items-center gap-2">
                <Loader className="h-4 w-4 animate-spin" />
                <span>PARSING INTEGRATION ON SITE...</span>
              </h3>
              <div className="space-y-4">
                {parsingSteps.map((step, idx) => {
                  const isCurrent = idx === parsingStep;
                  const isDone = idx < parsingStep;
                  return (
                    <div key={step} className={`flex items-center gap-3 p-3.5 rounded border transition-colors ${isCurrent ? "border-cyber-blue bg-cyber-blue/5 text-cyber-blue"
                        : isDone ? "border-outline-variant bg-surface-container-low text-on-surface-variant/70"
                          : "border-outline-variant/30 text-on-surface-variant/30"
                      }`}>
                      <div className="h-4 w-4 shrink-0 flex items-center justify-center">
                        {isDone ? <CheckCircle className="h-4 w-4 text-cyber-blue" />
                          : isCurrent ? <span className="w-2 h-2 rounded-full bg-cyber-blue animate-ping" />
                            : <span className="w-1.5 h-1.5 rounded-full bg-outline-variant/40" />}
                      </div>
                      <span className="font-mono text-xs">{step}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : resumeData ? (
            <div className="bento-card rounded-lg p-6 flex flex-col gap-6">
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center border-b border-outline-variant/60 pb-5 gap-4">
                <div className="text-left">
                  <h3 className="text-xl font-bold text-white leading-none">{resumeData.name}</h3>
                  <span className="font-mono text-[10px] text-on-surface-variant uppercase mt-2 block">{resumeData.email}</span>
                </div>
                <div className="flex items-center gap-3.5 bg-cyber-blue/5 border border-cyber-blue/10 rounded px-3 py-1.5">
                  <div className="text-right">
                    <span className="font-mono text-[9px] text-on-surface-variant block leading-none uppercase">ATS Score</span>
                    <span className="font-mono text-base font-bold text-cyber-blue mt-1 block">{matchScore}%</span>
                  </div>
                  <Brain className="h-6 w-6 text-cyber-blue animate-breathe" />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="text-left">
                  <span className="font-mono text-[10px] uppercase tracking-wider text-[#00d2ff] font-semibold border-b border-cyber-blue/10 pb-2 mb-3.5 flex items-center gap-1">
                    <Sparkles className="h-3.5 w-3.5 text-cyber-blue" />
                    <span>Identified Strengths</span>
                  </span>
                  <div className="flex flex-wrap gap-2 mt-3.5">
                    {resumeData.skills.filter(s => s.match >= 70).map(skill => (
                      <span key={skill.name} className="px-2.5 py-1 text-[10px] font-mono border border-cyber-blue/20 bg-cyber-blue/5 text-cyber-blue uppercase tracking-wider rounded">
                        {skill.name}
                      </span>
                    ))}
                  </div>
                </div>
                <div className="text-left">
                  <span className="font-mono text-[10px] uppercase tracking-wider text-red-400 font-semibold border-b border-red-500/10 pb-2 mb-3.5 flex items-center gap-1">
                    <AlertTriangle className="h-3.5 w-3.5 text-red-500" />
                    <span>Structural Gaps</span>
                  </span>
                  <div className="flex flex-wrap gap-2 mt-3.5">
                    {resumeData.gaps.map(gap => (
                      <span key={gap.name} className="px-2.5 py-1 text-[10px] font-mono border border-red-500/20 bg-red-500/5 text-red-400 uppercase tracking-wider rounded">
                        {gap.name}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              <div className="text-left border-t border-outline-variant/60 pt-6">
                <span className="font-mono text-[10px] uppercase tracking-wider text-on-surface-variant font-semibold mb-4 block">
                  Telemetry Career History
                </span>
                <div className="space-y-4">
                  {resumeData.experience.map((exp, idx) => (
                    <div key={idx} className="p-4 rounded border border-outline-variant/50 bg-[#07070a]/50 hover:border-cyber-blue/20 transition-colors">
                      <div className="flex flex-col sm:flex-row sm:justify-between items-start sm:items-center gap-2 mb-2">
                        <h4 className="font-sans text-sm font-semibold text-white flex items-center gap-1.5">
                          <Building className="h-3.5 w-3.5 text-cyber-blue" />
                          <span>{exp.company}</span>
                          <span className="text-on-surface-variant font-mono text-xs font-normal">| {exp.role}</span>
                        </h4>
                        <span className="font-mono text-[10px] text-on-surface-variant shrink-0 flex items-center gap-1">
                          <Calendar className="h-3 w-3" />{exp.duration}
                        </span>
                      </div>
                      <p className="text-xs text-on-surface-variant leading-relaxed pl-5">{exp.details}</p>
                    </div>
                  ))}
                </div>
              </div>

              <div className="border-t border-outline-variant/60 pt-4">
                <button
                  onClick={handleGenerateCoverLetter}
                  disabled={isGeneratingCover}
                  className="w-full py-3 rounded border border-outline-variant bg-surface-container-low hover:bg-surface-container hover:border-cyber-blue/30 hover:text-cyber-blue text-white font-mono text-xs font-bold uppercase tracking-wider transition-all duration-300 flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
                >
                  {isGeneratingCover
                    ? <><Loader className="h-4 w-4 animate-spin" /><span>Generating Cover Letter...</span></>
                    : <><FileEdit className="h-4 w-4" /><span>Generate Cover Letter with AI</span></>}
                </button>
              </div>
            </div>
          ) : (
            <div className="bento-card rounded-lg p-12 flex flex-col items-center justify-center text-center text-on-surface-variant">
              <FileText className="h-16 w-16 mb-4 opacity-25" />
              <p className="font-mono text-xs uppercase tracking-wider">NO INGESTED PROFILE DETECTED</p>
              <p className="text-xs text-on-surface-variant/60 max-w-xs mt-2 leading-relaxed">
                Please drag and drop a valid resume file in the ingestion area to initialize career intelligence telemetry.
              </p>
            </div>
          )}

          {/* Cover Letter Panel */}
          {showCoverPanel && (
            <div className="bento-card rounded-lg p-6 flex flex-col gap-4 animate-fade-slide-up">
              <div className="flex items-center justify-between border-b border-outline-variant/60 pb-3">
                <h3 className="font-mono text-xs font-bold text-cyber-blue uppercase tracking-wider flex items-center gap-1.5">
                  <FileEdit className="h-4 w-4" /><span>AI Generated Cover Letter</span>
                </h3>
                <span className="font-mono text-[9px] text-on-surface-variant bg-surface-dim border border-outline-variant px-2 py-0.5 rounded-sm uppercase">
                  Gemini 1.5 Flash
                </span>
              </div>
              {isGeneratingCover ? (
                <div className="space-y-3 animate-pulse">
                  {[3 / 4, 1, 5 / 6, 1, 2 / 3].map((w, i) => (
                    <div key={i} className="h-4 bg-surface-container rounded shimmer-bg" style={{ width: `${w * 100}%` }} />
                  ))}
                </div>
              ) : coverError ? (
                <div className="flex items-center gap-2 text-red-400 font-mono text-xs p-4 border border-red-500/20 rounded bg-red-500/5">
                  <AlertTriangle className="h-4 w-4 shrink-0" /><span>{coverError}</span>
                </div>
              ) : coverLetter ? (
                <div className="prose prose-invert prose-sm max-w-none text-on-surface-variant leading-relaxed text-sm [&>p]:mb-4 [&>h1]:text-white [&>h2]:text-white [&>h3]:text-cyber-blue [&>strong]:text-white">
                  <ReactMarkdown>{coverLetter}</ReactMarkdown>
                </div>
              ) : null}
            </div>
          )}

          {/* Job Listings Panel */}
          {(isFetchingJobs || jobsData || jobsError) && (
            <div className="bento-card rounded-lg p-6 flex flex-col gap-5 animate-fade-slide-up">
              <div className="flex items-center justify-between border-b border-outline-variant/60 pb-3">
                <h3 className="font-mono text-xs font-bold text-cyber-blue uppercase tracking-wider flex items-center gap-1.5">
                  <TrendingUp className="h-4 w-4" /><span>Matched Job Listings</span>
                </h3>
                {jobsData && (
                  <div className="flex items-center gap-2">
                    {jobInput.trim() && (
                      <span className="font-mono text-[9px] text-amber-400 border border-amber-400/20 bg-amber-400/5 px-2 py-0.5 rounded-sm uppercase tracking-wider">
                        JD Filter Active
                      </span>
                    )}
                    <span className="font-mono text-[9px] text-on-surface-variant bg-surface-dim border border-outline-variant px-2 py-0.5 rounded-sm uppercase tracking-wider flex items-center gap-1">
                      <Wifi className="h-2.5 w-2.5 text-cyber-blue" />
                      {jobsData.total_count.toLocaleString()} live openings
                    </span>
                  </div>
                )}
              </div>

              {isFetchingJobs && (
                <div className="space-y-3 animate-pulse">
                  {[1, 2, 3].map(i => (
                    <div key={i} className="p-4 rounded border border-outline-variant/30 bg-surface-container-low flex flex-col gap-2">
                      <div className="h-4 bg-surface-container-high rounded shimmer-bg w-2/3" />
                      <div className="h-3 bg-surface-container rounded shimmer-bg w-1/3" />
                      <div className="h-3 bg-surface-container rounded shimmer-bg w-full mt-1" />
                      <div className="h-3 bg-surface-container rounded shimmer-bg w-4/5" />
                    </div>
                  ))}
                </div>
              )}

              {jobsError && !isFetchingJobs && (
                <div className="flex items-center gap-2 text-red-400 font-mono text-xs p-4 border border-red-500/20 rounded bg-red-500/5">
                  <AlertTriangle className="h-4 w-4 shrink-0" /><span>{jobsError}</span>
                </div>
              )}

              {jobsData && !isFetchingJobs && (
                <div className="flex flex-col gap-3">
                  {jobsData.jobs.length === 0 ? (
                    <p className="font-mono text-[10px] text-on-surface-variant/50 text-center py-6 uppercase tracking-wider">
                      No jobs found for your profile. Try adding a job description above.
                    </p>
                  ) : (
                    <>
                      {jobsData.jobs.map((job) => {
                        const salary = job.salary_min
                          ? `₹${Math.round(job.salary_min / 1000)}k${job.salary_is_predicted ? " est." : ""}`
                          : null;
                        const isRemote = job.location?.toLowerCase().includes("remote") || job.location === "IN";
                        const workType = isRemote ? "Remote" : job.contract_time === "full_time" ? "Full-time" : job.contract_time ?? "—";
                        const daysAgo = job.created
                          ? Math.max(0, Math.floor((Date.now() - new Date(job.created).getTime()) / 86400000))
                          : null;
                        return (
                          <a
                            key={job.id}
                            href={job.redirect_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="group p-4 rounded border border-outline-variant/40 bg-[#07070a]/50 hover:border-cyber-blue/40 hover:bg-cyber-blue/[0.03] transition-all duration-200 flex flex-col gap-2.5"
                          >
                            <div className="flex items-start justify-between gap-3">
                              <div className="flex-1 min-w-0">
                                <h4 className="text-sm font-semibold text-white group-hover:text-cyber-blue transition-colors leading-snug truncate">
                                  {job.title}
                                </h4>
                                <div className="flex items-center gap-1.5 mt-0.5">
                                  <Building className="h-3 w-3 text-on-surface-variant shrink-0" />
                                  <span className="font-mono text-[10px] text-on-surface-variant truncate">{job.company}</span>
                                </div>
                              </div>
                              {salary && (
                                <div className="shrink-0 flex flex-col items-end">
                                  <span className="font-mono text-sm font-bold text-cyber-blue">{salary}</span>
                                  {job.salary_is_predicted && (
                                    <span className="font-mono text-[8px] text-on-surface-variant/50 uppercase">predicted</span>
                                  )}
                                </div>
                              )}
                            </div>
                            <div className="flex items-center gap-3 flex-wrap">
                              <span className="flex items-center gap-1 font-mono text-[9px] text-on-surface-variant/70">
                                <MapPin className="h-2.5 w-2.5" />{job.location || "Location not specified"}
                              </span>
                              <span className={`font-mono text-[9px] px-1.5 py-0.5 rounded-sm border uppercase tracking-wider ${isRemote ? "text-cyber-blue border-cyber-blue/20 bg-cyber-blue/5"
                                  : "text-on-surface-variant border-outline-variant/30 bg-surface-container-low"
                                }`}>{workType}</span>
                              <span className="font-mono text-[9px] px-1.5 py-0.5 rounded-sm border border-outline-variant/20 bg-surface-container-low text-on-surface-variant/60 uppercase tracking-wider">
                                {job.category}
                              </span>
                              {daysAgo !== null && (
                                <span className="font-mono text-[9px] text-on-surface-variant/40 ml-auto">
                                  {daysAgo === 0 ? "Today" : `${daysAgo}d ago`}
                                </span>
                              )}
                            </div>
                            <p className="text-[11px] text-on-surface-variant/60 leading-relaxed line-clamp-2">
                              {job.description.slice(0, 180)}...
                            </p>
                            <div className="flex items-center justify-end pt-1">
                              <span className="font-mono text-[9px] text-cyber-blue uppercase tracking-wider flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                View & Apply <Send className="h-2.5 w-2.5" />
                              </span>
                            </div>
                          </a>
                        );
                      })}
                      <p className="font-mono text-[9px] text-on-surface-variant/40 text-center pt-1 uppercase tracking-wider">
                        Showing {jobsData.jobs.length} of {jobsData.total_count.toLocaleString()} openings · Adzuna India
                      </p>
                    </>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}