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
  ChevronDown
} from "lucide-react";
import { useProject } from "../context/ProjectContext";

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

  // Cover letter state
  const [coverLetter, setCoverLetter] = useState<string | null>(null);
  const [isGeneratingCover, setIsGeneratingCover] = useState(false);
  const [coverError, setCoverError] = useState<string | null>(null);
  const [showCoverPanel, setShowCoverPanel] = useState(false);

  // Steps for the parsing skeleton simulation
  const parsingSteps = [
    "Decrypting file structure...",
    "Extracting semantic typography grids...",
    "Benchmarking technical skill taxonomy...",
    "Synthesizing job alignment index..."
  ];

  // Drag-and-drop triggers
  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      await processFileUpload(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      await processFileUpload(e.target.files[0]);
    }
  };

  const processFileUpload = async (file: File) => {
    // Run visual skeleton steps timer
    setParsingStep(0);
    setCoverLetter(null);
    setShowCoverPanel(false);
    const interval = setInterval(() => {
      setParsingStep(prev => {
        if (prev < parsingSteps.length - 1) return prev + 1;
        clearInterval(interval);
        return prev;
      });
    }, 600);

    await uploadResume(file);
    clearInterval(interval);
  };

  // Trigger match recalculation
  const handleRecalculateMatch = async () => {
    if (!jobInput.trim()) return;
    setIsUpdatingMatch(true);
    await triggerAnalyze(jobInput);
    setIsUpdatingMatch(false);
  };

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  // Generate cover letter via backend
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
    } catch (e) {
      console.error("Cover letter fetch failed:", e);
      setCoverError("Could not reach the AI backend. Check your connection.");
    } finally {
      setIsGeneratingCover(false);
    }
  };

  return (
    <div className="mx-auto max-w-[1280px] p-8 animate-fade-in">
      {/* Header section */}
      <header className="mb-8">
        <h2 className="text-3xl font-bold tracking-tight text-white flex items-center gap-2">
          Telemetry Analysis <Cpu className="h-6 w-6 text-cyber-blue" />
        </h2>
        <p className="text-sm text-on-surface-variant mt-1 font-mono">
          Centralized parser targeting /api/v1/resume/upload. Drag files to index profile indices.
        </p>
      </header>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-12">
        {/* Left Side: File Upload Panel (Spans 5 cols) */}
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
              onDrop={handleDrop}
              onClick={handleUploadClick}
              className={`flex flex-col items-center justify-center border-2 border-dashed rounded-lg p-10 cursor-pointer transition-all duration-300 relative group min-h-[220px] ${dragActive
                  ? "border-cyber-blue bg-cyber-blue/[0.04] shadow-[0_0_15px_rgba(0,210,255,0.15)] scale-[0.99]"
                  : "border-outline-variant hover:border-cyber-blue/40 bg-surface-container-low"
                }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                className="hidden"
                accept=".pdf,.docx"
                onChange={handleFileChange}
              />
              <UploadCloud className={`h-12 w-12 mb-4 transition-transform duration-300 group-hover:scale-110 ${dragActive ? "text-cyber-blue" : "text-on-surface-variant group-hover:text-cyber-blue"
                }`} />
              <p className="font-sans text-sm font-semibold text-white mb-1.5 text-center">
                Drag and drop your resume file
              </p>
              <p className="font-mono text-[10px] text-on-surface-variant uppercase tracking-wider text-center">
                PDF, DOCX UP TO 8MB
              </p>
            </div>

            {/* Target Job Profile description */}
            <div className="flex flex-col gap-3 text-left">
              <label className="font-mono text-[10px] uppercase tracking-wider text-on-surface-variant font-semibold">
                Target Alignment Profile
              </label>
              <div className="relative rounded border border-outline-variant bg-[#0c0c10] p-1 shadow-sm flex gap-2">
                <textarea
                  className="w-full bg-transparent border-none text-white font-sans text-xs focus:ring-0 resize-none h-14 p-2 focus:outline-none"
                  placeholder="Paste target job post details..."
                  value={jobInput}
                  onChange={(e) => setJobInput(e.target.value)}
                />
                <button
                  onClick={handleRecalculateMatch}
                  disabled={isUpdatingMatch}
                  className="self-end p-2.5 rounded bg-cyber-blue text-black hover:bg-white transition-colors cursor-pointer shrink-0 disabled:opacity-50"
                  title="Run matching index"
                >
                  {isUpdatingMatch ? (
                    <Loader className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Send className="h-3.5 w-3.5" />
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Right Side: Parsing Progress & Results Panel (Spans 7 cols) */}
        <div className="lg:col-span-7 flex flex-col gap-6">
          {isAnalyzing ? (
            /* Shimmer skeleton indicators */
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
                    <div
                      key={step}
                      className={`flex items-center gap-3 p-3.5 rounded border transition-colors ${isCurrent
                          ? "border-cyber-blue bg-cyber-blue/5 text-cyber-blue"
                          : isDone
                            ? "border-outline-variant bg-surface-container-low text-on-surface-variant/70"
                            : "border-outline-variant/30 text-on-surface-variant/30"
                        }`}
                    >
                      <div className="h-4 w-4 shrink-0 flex items-center justify-center">
                        {isDone ? (
                          <CheckCircle className="h-4.5 w-4.5 text-cyber-blue" />
                        ) : isCurrent ? (
                          <span className="w-2 h-2 rounded-full bg-cyber-blue animate-ping"></span>
                        ) : (
                          <span className="w-1.5 h-1.5 rounded-full bg-outline-variant/40"></span>
                        )}
                      </div>
                      <span className="font-mono text-xs text-left">{step}</span>
                    </div>
                  );
                })}
              </div>

              {/* Shimmer layout boxes */}
              <div className="space-y-3 mt-4 border-t border-outline-variant/40 pt-6">
                <div className="h-4.5 bg-surface-container-high rounded shimmer-bg w-1/3"></div>
                <div className="h-4 bg-surface-container rounded shimmer-bg w-5/6"></div>
                <div className="h-4 bg-surface-container rounded shimmer-bg w-4/6"></div>
              </div>
            </div>
          ) : resumeData ? (
            /* Active Data Display */
            <div className="bento-card rounded-lg p-6 flex flex-col gap-6">
              {/* Header result info */}
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center border-b border-outline-variant/60 pb-5 gap-4">
                <div className="text-left">
                  <h3 className="text-xl font-bold text-white leading-none">{resumeData.name}</h3>
                  <span className="font-mono text-[10px] text-on-surface-variant uppercase mt-2 block">{resumeData.email}</span>
                </div>
                <div className="flex items-center gap-3.5 bg-cyber-blue/5 border border-cyber-blue/10 rounded px-3 py-1.5">
                  <div className="text-right">
                    <span className="font-mono text-[9px] text-on-surface-variant block leading-none uppercase">Match Score</span>
                    <span className="font-mono text-base font-bold text-cyber-blue mt-1 block">{matchScore}%</span>
                  </div>
                  <Brain className="h-6 w-6 text-cyber-blue animate-breathe" />
                </div>
              </div>

              {/* Skills strengths and gaps list */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Strengths */}
                <div className="text-left">
                  <span className="font-mono text-[10px] uppercase tracking-wider text-[#00d2ff] font-semibold border-b border-cyber-blue/10 pb-2 mb-3.5 block flex items-center gap-1">
                    <Sparkles className="h-3.5 w-3.5 text-cyber-blue" />
                    <span>Identified Strengths</span>
                  </span>
                  <div className="flex flex-wrap gap-2">
                    {resumeData.skills.filter(s => s.match >= 70).map(skill => (
                      <span
                        key={skill.name}
                        className="px-2.5 py-1 text-[10px] font-mono border border-cyber-blue/20 bg-cyber-blue/5 text-cyber-blue uppercase tracking-wider rounded"
                      >
                        {skill.name}0
                      </span>
                    ))}
                  </div>
                </div>

                {/* Gaps */}
                <div className="text-left">
                  <span className="font-mono text-[10px] uppercase tracking-wider text-red-400 font-semibold border-b border-red-500/10 pb-2 mb-3.5 block flex items-center gap-1">
                    <AlertTriangle className="h-3.5 w-3.5 text-red-500" />
                    <span>Structural gaps</span>
                  </span>
                  <div className="flex flex-wrap gap-2">
                    {resumeData.gaps.map(gap => (
                      <span
                        key={gap.name}
                        className="px-2.5 py-1 text-[10px] font-mono border border-red-500/20 bg-red-500/5 text-red-400 uppercase tracking-wider rounded"
                      >
                        {gap.name}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              {/* Professional History */}
              <div className="text-left border-t border-outline-variant/60 pt-6">
                <span className="font-mono text-[10px] uppercase tracking-wider text-on-surface-variant font-semibold mb-4 block uppercase">
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
                          <Calendar className="h-3 w-3" />
                          <span>{exp.duration}</span>
                        </span>
                      </div>
                      <p className="text-xs text-on-surface-variant leading-relaxed pl-5">
                        {exp.details}
                      </p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Cover Letter Generator CTA */}
              <div className="border-t border-outline-variant/60 pt-4">
                <button
                  onClick={handleGenerateCoverLetter}
                  disabled={isGeneratingCover}
                  className="w-full py-3 rounded border border-outline-variant bg-surface-container-low hover:bg-surface-container hover:border-cyber-blue/30 hover:text-cyber-blue text-white font-mono text-xs font-bold uppercase tracking-wider transition-all duration-300 flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
                >
                  {isGeneratingCover ? (
                    <><Loader className="h-4 w-4 animate-spin" /><span>Generating Cover Letter...</span></>
                  ) : (
                    <><FileEdit className="h-4 w-4" /><span>Generate Cover Letter with AI</span></>
                  )}
                </button>
              </div>
            </div>
          ) : (
            /* Blank state */
            <div className="bento-card rounded-lg p-12 flex flex-col items-center justify-center text-center text-on-surface-variant">
              <FileText className="h-16 w-16 mb-4 opacity-25" />
              <p className="font-mono text-xs uppercase tracking-wider">
                NO INGESTED PROFILE DETECTED
              </p>
              <p className="text-xs text-on-surface-variant/60 max-w-xs mt-2 leading-relaxed">
                Please drag and drop a valid resume file in the ingestion area to initialize career intelligence telemetry.
              </p>
            </div>
          )}

          {/* Cover Letter Output Panel */}
          {showCoverPanel && (
            <div className="bento-card rounded-lg p-6 flex flex-col gap-4 animate-fade-slide-up">
              <div className="flex items-center justify-between border-b border-outline-variant/60 pb-3">
                <h3 className="font-mono text-xs font-bold text-cyber-blue uppercase tracking-wider flex items-center gap-1.5">
                  <FileEdit className="h-4 w-4" />
                  <span>AI Generated Cover Letter</span>
                </h3>
                <span className="font-mono text-[9px] text-on-surface-variant bg-surface-dim border border-outline-variant px-2 py-0.5 rounded-sm uppercase">
                  Gemini 1.5 Flash
                </span>
              </div>

              {isGeneratingCover ? (
                <div className="space-y-3 animate-pulse">
                  <div className="h-4 bg-surface-container-high rounded shimmer-bg w-3/4"></div>
                  <div className="h-4 bg-surface-container rounded shimmer-bg w-full"></div>
                  <div className="h-4 bg-surface-container rounded shimmer-bg w-5/6"></div>
                  <div className="h-4 bg-surface-container rounded shimmer-bg w-full"></div>
                  <div className="h-4 bg-surface-container rounded shimmer-bg w-2/3"></div>
                </div>
              ) : coverError ? (
                <div className="flex items-center gap-2 text-red-400 font-mono text-xs p-4 border border-red-500/20 rounded bg-red-500/5">
                  <AlertTriangle className="h-4 w-4 shrink-0" />
                  <span>{coverError}</span>
                </div>
              ) : coverLetter ? (
                <div className="prose prose-invert prose-sm max-w-none text-on-surface-variant leading-relaxed text-sm [&>p]:mb-4 [&>h1]:text-white [&>h2]:text-white [&>h3]:text-cyber-blue [&>strong]:text-white">
                  <ReactMarkdown>{coverLetter}</ReactMarkdown>
                </div>
              ) : null}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
