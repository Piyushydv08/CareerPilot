"use client";

import React, { useState, useEffect } from "react";
import { 
  Target, 
  Radar, 
  Award, 
  MapIcon, 
  CheckSquare, 
  Plus, 
  Check, 
  Sparkles,
  ArrowRight,
  TrendingUp,
  GraduationCap,
  Loader,
  ExternalLink
} from "lucide-react";
import { useProject } from "../context/ProjectContext";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

interface Milestone {
  title: string;
  description: string;
  resources: string[];
}

export default function SimulatorPage() {
  const { resumeData, matchScore, toggleSkillGap } = useProject();
  const [animatedScore, setAnimatedScore] = useState(matchScore);
  const [milestones, setMilestones] = useState<Milestone[]>([]);
  const [showLearningPath, setShowLearningPath] = useState(false);
  const [isGeneratingPath, setIsGeneratingPath] = useState(false);
  const [pathError, setPathError] = useState<string | null>(null);

  // Animate the match score transitions smoothly!
  useEffect(() => {
    if (animatedScore !== matchScore) {
      const direction = matchScore > animatedScore ? 1 : -1;
      const timer = setInterval(() => {
        setAnimatedScore(prev => {
          if (prev === matchScore) {
            clearInterval(timer);
            return prev;
          }
          return prev + direction;
        });
      }, 20);
      return () => clearInterval(timer);
    }
  }, [matchScore, animatedScore]);

  // Handle generating real learning path via backend
  const handleGeneratePath = async () => {
    if (!resumeData) return;
    const activeCheckedGaps = resumeData.gaps.filter(g => g.checked).map(g => g.name);

    if (activeCheckedGaps.length === 0) {
      setShowLearningPath(true);
      setMilestones([]);
      return;
    }

    setIsGeneratingPath(true);
    setPathError(null);
    setShowLearningPath(true);

    try {
      const response = await fetch(`${BASE_URL}/interview/generate_path`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ gaps: activeCheckedGaps })
      });

      if (response.ok) {
        const data = await response.json();
        setMilestones(data.milestones || []);
      } else {
        setPathError("Failed to generate roadmap. Please try again.");
      }
    } catch (e) {
      console.error("Learning path generation failed:", e);
      setPathError("Could not reach the AI backend. Check your connection.");
    } finally {
      setIsGeneratingPath(false);
    }
  };

  // SVG Circular progress mathematics
  const circumference = 251.2; // 2 * pi * 40 (from mockup radius 40)
  const strokeDashoffset = circumference - (animatedScore / 100) * circumference;

  return (
    <div className="mx-auto max-w-[1280px] p-8 animate-fade-in text-left">
      {/* Page Header */}
      <header className="mb-8">
        <h2 className="text-3xl font-bold tracking-tight text-white flex items-center gap-2">
          Predictive Simulator <Target className="h-6 w-6 text-cyber-blue animate-pulse" />
        </h2>
        <p className="text-sm text-on-surface-variant mt-1 font-mono">
          Simulate score indexing by checking missing curriculum nodes. Live SVG telemetry calculation.
        </p>
      </header>

      {/* Grid Canvas */}
      <div className="grid grid-cols-1 gap-8 lg:grid-cols-12">
        {/* Left Side: Score Dial & Profile Strengths (Spans 5 cols) */}
        <div className="lg:col-span-5 flex flex-col gap-6">
          <div className="bento-card rounded-lg p-6 flex flex-col items-center justify-center gap-8 min-h-[360px] relative overflow-hidden group">
            {/* Ambient cyber blue backing glow */}
            <div className="absolute inset-0 bg-cyber-blue/[0.01] pointer-events-none z-0"></div>

            {/* Glowing SVG Circular Dial */}
            <div className="relative w-48 h-48 flex items-center justify-center z-10 animate-breathe">
              <svg className="w-full h-full absolute inset-0 -rotate-90" viewBox="0 0 100 100">
                {/* Background ring track */}
                <circle 
                  className="text-surface-container-highest stroke-current" 
                  cx="50" 
                  cy="50" 
                  fill="transparent" 
                  r="40" 
                  strokeWidth="8"
                ></circle>
                {/* Progress glowing ring */}
                <circle 
                  className={`stroke-current progress-ring__circle transition-all duration-300 ${
                    animatedScore === 100 ? "text-cyber-blue" : "text-white"
                  }`} 
                  cx="50" 
                  cy="50" 
                  fill="transparent" 
                  r="40" 
                  strokeWidth="8"
                  strokeDasharray={circumference}
                  strokeDashoffset={strokeDashoffset}
                  strokeLinecap="square"
                  style={{
                    filter: "drop-shadow(0 0 6px rgba(0, 210, 255, 0.4))"
                  }}
                ></circle>
              </svg>

              {/* Text inside Dial */}
              <div className="flex flex-col items-center justify-center">
                <span className="font-mono text-[9px] text-on-surface-variant uppercase tracking-widest leading-none mb-1">
                  MATCH SCORE
                </span>
                <span className="font-mono text-5xl font-bold text-white tracking-tighter glow-text">
                  {animatedScore}%
                </span>
              </div>
            </div>

            {/* Profile analysis list details */}
            <div className="w-full z-10 border-t border-outline-variant/60 pt-6">
              <h3 className="font-mono text-[10px] uppercase tracking-wider text-on-surface-variant font-semibold mb-4 flex items-center gap-1.5 leading-none">
                <Radar className="h-3.5 w-3.5 text-cyber-blue" />
                <span>Simulated Profile Analytics</span>
              </h3>

              <div className="space-y-4 text-xs font-mono">
                {/* Strengths */}
                <div>
                  <span className="text-[10px] text-on-surface-variant block mb-2 font-semibold">Strengths Identified</span>
                  <div className="flex flex-wrap gap-1.5">
                    {resumeData?.skills.filter(s => s.match >= 70).slice(0, 4).map(skill => (
                      <span
                        key={skill.name}
                        className="px-2 py-0.5 rounded text-[9px] border border-cyber-blue/20 bg-cyber-blue/5 text-cyber-blue uppercase font-bold tracking-wider"
                      >
                        {skill.name}
                      </span>
                    ))}
                    {(!resumeData || resumeData.skills.filter(s => s.match >= 70).length === 0) && (
                      <span className="text-[10px] text-on-surface-variant italic font-semibold">
                        No strengths indexed yet. Upload a resume first.
                      </span>
                    )}
                  </div>
                </div>

                {/* Weaknesses */}
                <div>
                  <span className="text-[10px] text-on-surface-variant block mb-2 font-semibold">Missing from JD</span>
                  <div className="flex flex-wrap gap-1.5">
                    {resumeData?.gaps.filter(g => !g.checked).map(gap => (
                      <span 
                        key={gap.name}
                        className="px-2 py-0.5 rounded text-[9px] border border-red-500/20 bg-red-500/5 text-red-400 uppercase font-bold tracking-wider"
                      >
                        {gap.name.split(" ")[0]}
                      </span>
                    ))}
                    {resumeData?.gaps.filter(g => !g.checked).length === 0 && (
                      <span className="text-[10px] text-cyber-blue italic font-semibold">
                        {resumeData?.gaps.length === 0
                          ? "Analyze a job description to see missing skills."
                          : "All missing JD skills simulated as fulfilled!"}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Side: Skill Gap checklist matrix (Spans 7 cols) */}
        <div className="lg:col-span-7 flex flex-col gap-6">
          <div className="bento-card rounded-lg p-6 flex flex-col gap-6">
            <div className="flex justify-between items-end border-b border-outline-variant/60 pb-4 gap-4">
              <div>
                <h3 className="font-mono text-xs font-bold text-white uppercase tracking-wider mb-1">
                  Predictive Gap Checklist
                </h3>
                <p className="text-xs text-on-surface-variant font-mono">
                  These are skills required by the job description not found in your resume. Toggle to simulate score impact.
                </p>
              </div>
              <span className="font-mono text-[10px] text-cyber-blue bg-cyber-blue/5 border border-cyber-blue/20 rounded px-2.5 py-0.5 uppercase tracking-wider shrink-0">
                SR. FRONTEND ENGINEER
              </span>
            </div>

            {/* Checklist elements */}
            <div className="space-y-3">
              {resumeData?.gaps.map((gap, index) => (
                <label 
                  key={gap.name}
                  className={`flex items-center justify-between p-4 rounded border transition-all duration-200 cursor-pointer group ${
                    gap.checked 
                      ? "border-cyber-blue/40 bg-cyber-blue/[0.03] shadow-[0_0_8px_rgba(0,210,255,0.05)]" 
                      : "border-outline-variant/60 bg-[#07070a]/40 hover:border-cyber-blue/20 hover:bg-[#0c0c12]/50"
                  }`}
                >
                  <div className="flex items-center gap-4">
                    {/* Custom Checkbox */}
                    <div className="relative shrink-0 flex items-center justify-center">
                      <input 
                        type="checkbox"
                        checked={gap.checked}
                        onChange={() => toggleSkillGap(index)}
                        className="hidden"
                      />
                      <div className={`h-5 w-5 rounded border flex items-center justify-center transition-all ${
                        gap.checked 
                          ? "border-cyber-blue bg-cyber-blue text-black" 
                          : "border-outline-variant group-hover:border-cyber-blue/60"
                      }`}>
                        {gap.checked && <Check className="h-3.5 w-3.5 stroke-[3px]" />}
                      </div>
                    </div>
                    
                    <div className="flex flex-col text-left">
                      <span className={`text-sm font-semibold transition-colors duration-200 ${
                        gap.checked ? "text-cyber-blue font-bold" : "text-white group-hover:text-cyber-blue/95"
                      }`}>
                        {gap.name}
                      </span>
                      <span className="font-mono text-[10px] text-on-surface-variant uppercase mt-0.5">
                        {gap.category}
                      </span>
                    </div>
                  </div>

                  <span className="font-mono text-xs font-bold text-cyber-blue bg-cyber-blue/10 border border-cyber-blue/20 px-2.5 py-1 rounded">
                    +{gap.impact}%
                  </span>
                </label>
              ))}
            </div>

            {/* Action generate trigger */}
            <div className="border-t border-outline-variant/60 pt-4 flex gap-4">
              <button 
                onClick={handleGeneratePath}
                disabled={isGeneratingPath}
                className="w-full rounded bg-white py-3 font-mono text-xs font-bold text-black uppercase tracking-wider hover:bg-cyber-blue hover:text-black hover:shadow-[0_0_15px_rgba(0,210,255,0.5)] transition-all duration-300 flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
              >
                {isGeneratingPath ? (
                  <><Loader className="h-4.5 w-4.5 animate-spin" /><span>Generating Roadmap...</span></>
                ) : (
                  <><Award className="h-4.5 w-4.5" /><span>Generate Learning Roadmap</span></>
                )}
              </button>
            </div>
          </div>

          {/* Dynamic Learning Roadmap Drawer */}
          {showLearningPath && (
            <div className="bento-card rounded-lg p-6 flex flex-col gap-6 animate-fade-slide-up bg-surface-container-low border-cyber-blue/20">
              <div className="flex items-center gap-2 border-b border-outline-variant/60 pb-3">
                <GraduationCap className="h-5 w-5 text-cyber-blue animate-pulse" />
                <h3 className="font-mono text-xs font-bold text-white uppercase tracking-wider">
                  Target Curriculum Roadmap
                </h3>
              </div>

              {isGeneratingPath ? (
                <div className="space-y-4 animate-pulse">
                  {[1, 2, 3].map(i => (
                    <div key={i} className="space-y-2">
                      <div className="h-4 bg-surface-container-high rounded shimmer-bg w-1/2"></div>
                      <div className="h-3 bg-surface-container rounded shimmer-bg w-full"></div>
                      <div className="h-3 bg-surface-container rounded shimmer-bg w-4/5"></div>
                    </div>
                  ))}
                </div>
              ) : pathError ? (
                <div className="font-mono text-xs text-red-400 p-4 border border-red-500/20 rounded bg-red-500/5">
                  {pathError}
                </div>
              ) : milestones.length === 0 ? (
                <div className="text-center font-mono text-xs text-on-surface-variant/60 py-4">
                  Please select one or more gap matrices in the checklist to generate customized learning milestones.
                </div>
              ) : (
                <div className="space-y-6 relative pl-4 border-l border-outline-variant/80 ml-2 py-2">
                  {milestones.map((milestone, idx) => (
                    <div key={idx} className="relative group text-left">
                      {/* Pulsing indicator block */}
                      <span className="absolute -left-[21px] top-1 h-3.5 w-3.5 rounded-full border border-cyber-blue bg-[#0c0c10] flex items-center justify-center">
                        <span className="h-1.5 w-1.5 rounded-full bg-cyber-blue animate-pulse"></span>
                      </span>

                      <div className="flex flex-col">
                        <span className="font-mono text-[9px] text-cyber-blue uppercase tracking-wider">
                          MILESTONE {(idx + 1).toString().padStart(2, "0")}: IN PROGRESS
                        </span>
                        <h4 className="font-sans text-sm font-semibold text-white mt-1 leading-snug">
                          {milestone.title}
                        </h4>
                        <p className="text-xs text-on-surface-variant mt-2 leading-relaxed max-w-lg">
                          {milestone.description}
                        </p>
                        {milestone.resources.length > 0 && (
                          <div className="mt-3 flex flex-wrap gap-2">
                            {milestone.resources.map((resource, rIdx) => {
                              const isLink = resource.startsWith("http") || resource.startsWith("www.");
                              const href = resource.startsWith("www.") ? `https://${resource}` : resource;
                              return (
                                <a
                                  key={rIdx}
                                  href={isLink ? href : undefined}
                                  target={isLink ? "_blank" : undefined}
                                  rel="noopener noreferrer"
                                  className="flex items-center gap-1 px-2 py-0.5 text-[9px] font-mono border border-cyber-blue/20 bg-cyber-blue/5 text-cyber-blue rounded hover:bg-cyber-blue/10 transition-colors"
                                >
                                  {isLink && <ExternalLink className="h-2.5 w-2.5" />}
                                  <span className="truncate max-w-[200px]">{resource.replace(/^https?:\/\//, "")}</span>
                                </a>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
