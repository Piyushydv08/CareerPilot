"use client";

import React, { useState, useEffect, useRef } from "react";
import { 
  Mic, 
  Send, 
  Volume2, 
  Check, 
  Hourglass, 
  StopCircle, 
  Activity, 
  Bot,
  User as UserIcon,
  Download,
  Share2,
  Info,
  List,
  AlertTriangle,
  ClipboardList,
  Play,
  RotateCcw,
  Sparkles,
  Radar
} from "lucide-react";
import { useProject, ChatMessage } from "../context/ProjectContext";

export default function InterviewPage() {
  const { 
    messages, 
    sendInterviewMessage, 
    resetInterview,
    matchScore
  } = useProject();

  const [isEnded, setIsEnded] = useState(false);
  const [inputText, setInputText] = useState("");
  const [isThinking, setIsThinking] = useState(false);
  const [timerSeconds, setTimerSeconds] = useState(863); // Starts at 14:23
  const [countUpMatch, setCountUpMatch] = useState(0);

  const chatEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll chat window
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isThinking]);

  // Live Timer tick
  useEffect(() => {
    if (isEnded) return;
    const timer = setInterval(() => {
      setTimerSeconds(prev => prev + 1);
    }, 1000);
    return () => clearInterval(timer);
  }, [isEnded]);

  // Format Elapsed Time
  const formatTimer = () => {
    const mins = Math.floor(timerSeconds / 60);
    const secs = timerSeconds % 60;
    const ms = Math.floor(Math.random() * 99);
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}.${ms.toString().padStart(2, "0")}`;
  };

  // Trigger End of Session & Assessment Count-up
  const handleEndSession = () => {
    setIsEnded(true);
    // Count up animation for report
    setCountUpMatch(0);
    setTimeout(() => {
      const target = 88;
      const stepTime = Math.floor(1500 / target);
      let current = 0;
      const countInterval = setInterval(() => {
        current += 1;
        setCountUpMatch(current);
        if (current >= target) {
          clearInterval(countInterval);
          setCountUpMatch(target);
        }
      }, stepTime);
    }, 200);
  };

  // Textarea input auto-grow
  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputText(e.target.value);
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      const scrollHeight = textareaRef.current.scrollHeight;
      textareaRef.current.style.height = `${Math.min(scrollHeight, 160)}px`;
    }
  };

  const handleSendMessage = async () => {
    if (!inputText.trim()) return;
    const text = inputText;
    setInputText("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";

    setIsThinking(true);
    await sendInterviewMessage(text);
    setIsThinking(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleRestart = () => {
    resetInterview();
    setIsEnded(false);
    setTimerSeconds(863);
  };

  return (
    <div className="flex h-[calc(100vh-4rem)] w-full overflow-hidden animate-fade-in relative bg-[#030305] text-left">
      {!isEnded ? (
        /* 1. Live Chat Interview Workspace */
        <div className="flex flex-1 flex-col lg:flex-row overflow-hidden w-full h-full">
          {/* Left Performance Telemetry Panel (320px width) */}
          <aside className="w-full lg:w-80 border-b lg:border-b-0 lg:border-r border-outline-variant bg-surface-container-low shrink-0 overflow-y-auto flex flex-col p-6 space-y-8 z-20">
            {/* Timer */}
            <div className="space-y-1.5 text-left">
              <h3 className="font-mono text-[9px] text-on-surface-variant tracking-wider uppercase font-semibold">T-Elapsed</h3>
              <div className="font-mono text-3.5xl text-cyber-blue font-light glow-text leading-none">
                {formatTimer()}
              </div>
            </div>

            {/* Metrics Bento Grid */}
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-surface-dim border border-outline-variant p-4 flex flex-col gap-2 rounded hover:border-cyber-blue/30 transition-colors">
                <Activity className="h-4.5 w-4.5 text-on-surface-variant" />
                <span className="font-mono text-2xl font-bold text-white">86%</span>
                <span className="font-mono text-[9px] text-on-surface-variant uppercase tracking-wider font-semibold">Pacing Score</span>
              </div>
              <div className="bg-surface-dim border border-outline-variant p-4 flex flex-col gap-2 rounded hover:border-cyber-blue/30 transition-colors">
                <Bot className="h-4.5 w-4.5 text-on-surface-variant" />
                <span className="font-mono text-2xl font-bold text-white">A-</span>
                <span className="font-mono text-[9px] text-on-surface-variant uppercase tracking-wider font-semibold">Clarity Rating</span>
              </div>
            </div>

            {/* Confidence Metric Progress Bar */}
            <div className="space-y-3.5 text-left">
              <div className="flex justify-between items-baseline font-mono text-[9px] uppercase tracking-wider font-semibold">
                <span className="text-on-surface-variant">Confidence Metric</span>
                <span className="text-cyber-blue glow-text">Stable</span>
              </div>
              <div className="h-2 bg-surface-dim w-full rounded overflow-hidden border border-outline-variant/60 relative">
                <div 
                  className="h-full bg-cyber-blue/80 shadow-[0_0_8px_rgba(0,210,255,0.6)] rounded-full transition-all duration-500"
                  style={{ width: "78%" }}
                >
                  <div className="absolute right-0 top-0 bottom-0 w-1 bg-white"></div>
                </div>
              </div>
              <div className="flex justify-between font-mono text-[9px] text-on-surface-variant/40">
                <span>Low</span>
                <span>High</span>
              </div>
            </div>

            {/* Extracted technical terms */}
            <div className="flex-grow flex flex-col min-h-0 text-left">
              <h3 className="font-mono text-[9px] text-on-surface-variant tracking-wider uppercase font-semibold mb-4 shrink-0">
                Tech Terms Extracted
              </h3>
              <div className="flex-grow overflow-y-auto space-y-2 pr-1 text-xs font-mono">
                <div className="flex items-center justify-between py-1 border-b border-outline-variant/20 hover:border-cyber-blue/40 transition-colors group">
                  <span className="text-white">Microservices</span>
                  <Check className="h-3.5 w-3.5 text-cyber-blue opacity-0 group-hover:opacity-100 transition-opacity" />
                </div>
                <div className="flex items-center justify-between py-1 border-b border-outline-variant/20 hover:border-cyber-blue/40 transition-colors group">
                  <span className="text-white">Event-Driven Arch</span>
                  <Check className="h-3.5 w-3.5 text-cyber-blue opacity-0 group-hover:opacity-100 transition-opacity" />
                </div>
                <div className="flex items-center justify-between py-1 border-b border-outline-variant/20 hover:border-cyber-blue/40 transition-colors group">
                  <span className="text-white">Kubernetes</span>
                  <Check className="h-3.5 w-3.5 text-cyber-blue opacity-0 group-hover:opacity-100 transition-opacity" />
                </div>
                <div className="flex items-center justify-between py-1 border-b border-outline-variant/20 hover:border-cyber-blue/40 transition-colors text-on-surface-variant/60 italic group">
                  <span>CAP Theorem</span>
                  <Hourglass className="h-3.5 w-3.5 text-on-surface-variant/40 animate-spin" />
                </div>
              </div>
            </div>

            {/* End session action */}
            <div className="shrink-0 pt-4 border-t border-outline-variant/60">
              <button 
                onClick={handleEndSession}
                className="w-full bg-red-950/20 text-red-400 border border-red-500/30 hover:bg-red-500 hover:text-black hover:border-red-500 hover:shadow-[0_0_10px_rgba(239,68,68,0.4)] transition-all duration-300 py-3 rounded font-mono text-[10px] uppercase tracking-wider font-bold flex items-center justify-center gap-2 cursor-pointer"
              >
                <StopCircle className="h-4.5 w-4.5" />
                <span>End &amp; Get Rubric</span>
              </button>
            </div>
          </aside>

          {/* Right Side Chat Terminal */}
          <section className="flex-1 flex flex-col bg-bg-deep relative overflow-hidden h-full z-10">
            {/* Scrollable feed messages */}
            <div className="flex-1 overflow-y-auto p-8 space-y-6 scroll-smooth pb-36 h-full">
              {messages.map((msg, index) => {
                const isSystem = msg.sender === "SYSTEM";
                return (
                  <div 
                    key={index}
                    className={`flex gap-4 max-w-3xl animate-fade-slide-up ${
                      isSystem ? "text-left" : "ml-auto justify-end text-right"
                    }`}
                  >
                    {isSystem && (
                      <div className="w-8 h-8 rounded bg-surface-container border border-outline-variant flex items-center justify-center shrink-0">
                        <Bot className="h-4 w-4 text-cyber-blue" />
                      </div>
                    )}
                    
                    <div className="space-y-1.5 flex flex-col">
                      <div className="font-mono text-[9px] text-on-surface-variant">
                        {isSystem ? (
                          <>
                            [SYSTEM.AI] <span className="text-on-surface-variant/40">{msg.timestamp}</span>
                          </>
                        ) : (
                          <>
                            <span className="text-on-surface-variant/40">{msg.timestamp}</span> [USER]
                          </>
                        )}
                      </div>
                      
                      <div className={`border rounded-lg p-4 font-sans text-xs leading-relaxed shadow-sm tracking-wide ${
                        isSystem 
                          ? "bg-surface-container border-outline-variant text-white rounded-tl-none text-left" 
                          : "bg-cyber-blue/10 border-cyber-blue/20 text-cyber-blue rounded-tr-none text-left inline-block"
                      }`}>
                        {msg.text}
                      </div>
                    </div>

                    {!isSystem && (
                      <div className="w-8 h-8 rounded bg-cyber-blue/20 border border-cyber-blue/40 flex items-center justify-center shrink-0">
                        <UserIcon className="h-4 w-4 text-cyber-blue" />
                      </div>
                    )}
                  </div>
                );
              })}

              {/* Typing Shimmer */}
              {isThinking && (
                <div className="flex gap-4 max-w-3xl text-left animate-fade-in">
                  <div className="w-8 h-8 rounded bg-surface-container border border-outline-variant flex items-center justify-center shrink-0">
                    <Bot className="h-4 w-4 text-cyber-blue animate-pulse" />
                  </div>
                  <div className="space-y-1.5 flex flex-col">
                    <div className="font-mono text-[9px] text-on-surface-variant">[SYSTEM.AI] <span className="text-cyber-blue">Processing...</span></div>
                    <div className="bg-surface-container border border-outline-variant rounded-lg rounded-tl-none p-4 flex items-center gap-1.5 shrink-0">
                      <span className="w-1.5 h-1.5 bg-cyber-blue rounded-full animate-ping" style={{ animationDelay: "0.2s" }}></span>
                      <span className="w-1.5 h-1.5 bg-cyber-blue rounded-full animate-ping" style={{ animationDelay: "0.4s" }}></span>
                      <span className="w-1.5 h-1.5 bg-cyber-blue rounded-full animate-ping" style={{ animationDelay: "0.6s" }}></span>
                    </div>
                  </div>
                </div>
              )}

              <div ref={chatEndRef}></div>
            </div>

            {/* Input Bar Overlay */}
            <div className="absolute bottom-0 left-0 right-0 p-6 bg-gradient-to-t from-bg-deep via-bg-deep/90 to-transparent pt-12 z-20">
              <div className="max-w-4xl mx-auto">
                <div className="bg-surface-container-low border border-outline-variant rounded-lg focus-within:border-cyber-blue focus-within:ring-1 focus-within:ring-cyber-blue transition-all duration-200 p-2 shadow-lg flex gap-2">
                  <div className="pt-2 pl-2 text-cyber-blue font-mono select-none shrink-0 font-bold">&gt;</div>
                  <textarea 
                    ref={textareaRef}
                    className="w-full bg-transparent border-none text-white font-sans text-xs focus:ring-0 resize-none h-14 py-2 placeholder-on-surface-variant/40 focus:outline-none"
                    placeholder="Speak or type your response..."
                    value={inputText}
                    onChange={handleInputChange}
                    onKeyDown={handleKeyDown}
                    disabled={isThinking}
                  />
                  <div className="flex flex-col justify-end gap-2 pb-1 pr-1 shrink-0">
                    <button className="w-9 h-9 rounded bg-surface-container-high hover:bg-surface-container-highest text-on-surface-variant hover:text-cyber-blue transition-colors flex items-center justify-center border border-outline-variant cursor-pointer">
                      <Mic className="h-4 w-4" />
                    </button>
                    <button 
                      onClick={handleSendMessage}
                      disabled={isThinking}
                      className="w-9 h-9 rounded bg-cyber-blue text-black hover:bg-white transition-colors flex items-center justify-center font-bold cursor-pointer disabled:opacity-50"
                    >
                      <Send className="h-4 w-4" />
                    </button>
                  </div>
                </div>
                <div className="flex justify-between items-center mt-2.5 px-2 font-mono text-[9px] text-on-surface-variant/50">
                  <span>Press Enter to send, Shift+Enter for new line.</span>
                  <div className="flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-cyber-blue animate-pulse"></span>
                    <span>CONNECTION SECURE</span>
                  </div>
                </div>
              </div>
            </div>
          </section>
        </div>
      ) : (
        /* 2. Interactive Synthesized Assessment Report */
        <div className="flex-1 overflow-y-auto p-8 lg:p-12 animate-fade-slide-up w-full h-full z-10 text-left">
          {/* Top Panel Assessment Header */}
          <div className="flex flex-col md:flex-row justify-between items-start md:items-end mb-8 gap-4 border-b border-outline-variant pb-6">
            <div>
              <div className="flex items-center gap-2 mb-2 font-mono">
                <span className="px-2 py-0.5 bg-surface-container-highest border border-outline-variant rounded-sm text-[9px] text-cyber-blue tracking-wider uppercase font-bold shadow-[0_0_6px_rgba(0,210,255,0.2)] animate-pulse">
                  SESSION ENDED
                </span>
                <span className="text-[10px] text-on-surface-variant">ID: INT-8924-X</span>
              </div>
              <h2 className="text-3xl font-bold tracking-tight text-white flex items-center gap-2">
                Senior Frontend Engineer Assessment Report <Sparkles className="h-5.5 w-5.5 text-cyber-blue" />
              </h2>
              <p className="text-xs text-on-surface-variant font-mono mt-1">Generated telemetry report on October 24, 2023.</p>
            </div>
            <div className="flex gap-3">
              <button 
                onClick={handleRestart}
                className="px-4 py-2 bg-surface-container-low border border-outline-variant rounded text-xs font-mono font-bold text-on-surface hover:bg-surface-container hover:text-cyber-blue hover:border-cyber-blue/30 transition-all flex items-center gap-2 cursor-pointer"
              >
                <RotateCcw className="h-4 w-4" /> Restart Session
              </button>
              <button className="px-4 py-2 bg-surface-container-low border border-outline-variant rounded text-xs font-mono font-bold text-on-surface hover:bg-surface-container transition-all flex items-center gap-2 cursor-pointer">
                <Download className="h-4 w-4" /> Export PDF
              </button>
              <button className="px-4 py-2 bg-cyber-blue text-black rounded text-xs font-mono font-bold hover:bg-white hover:shadow-[0_0_10px_rgba(0,210,255,0.4)] transition-all flex items-center gap-2 cursor-pointer">
                <Share2 className="h-4 w-4" /> Share Report
              </button>
            </div>
          </div>

          {/* Dynamic Metrics Bento Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            {/* Match score bar count up */}
            <div className="bg-surface-container border border-outline-variant rounded-lg p-6 relative overflow-hidden group hover:border-cyber-blue/40 transition-colors text-left">
              <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 text-cyber-blue animate-breathe">
                <Radar className="h-16 w-16" />
              </div>
              <h3 className="font-mono text-[10px] text-on-surface-variant uppercase tracking-widest mb-4 font-semibold">Overall Match Index</h3>
              <div className="flex items-baseline gap-1 mb-2 font-mono">
                <span className="text-5xl font-bold text-cyber-blue tracking-tighter glow-text">
                  {countUpMatch}
                </span>
                <span className="text-lg text-on-surface-variant font-bold">%</span>
              </div>
              <div className="w-full bg-surface-dim h-1.5 rounded-full mt-4 overflow-hidden border border-outline-variant/30">
                <div 
                  className="bg-cyber-blue h-full rounded-full shadow-[0_0_10px_rgba(0,210,255,0.7)] transition-all duration-1000"
                  style={{ width: `${countUpMatch}%` }}
                ></div>
              </div>
              <p className="text-[10px] font-mono text-on-surface-variant mt-3 uppercase tracking-wider">
                Exceeds benchmark baseline criteria by 14%.
              </p>
            </div>

            {/* Communication gauge */}
            <div className="bg-surface-container border border-outline-variant rounded-lg p-6 relative overflow-hidden group hover:border-cyber-blue/40 transition-colors text-left">
              <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 text-cyber-blue">
                <Volume2 className="h-16 w-16" />
              </div>
              <h3 className="font-mono text-[10px] text-on-surface-variant uppercase tracking-widest mb-4 font-semibold">Communication Clarity</h3>
              <div className="flex items-baseline gap-1 mb-2 font-mono">
                <span className="text-5xl font-bold text-white tracking-tighter">
                  {countUpMatch > 0 ? Math.round(countUpMatch * 1.045) : 0}
                </span>
                <span className="text-lg text-on-surface-variant font-bold">/100</span>
              </div>
              <div className="w-full bg-surface-dim h-1.5 rounded-full mt-4 overflow-hidden border border-outline-variant/30">
                <div 
                  className="bg-white h-full rounded-full transition-all duration-1000"
                  style={{ width: "92%" }}
                ></div>
              </div>
              <p className="text-[10px] font-mono text-on-surface-variant mt-3 uppercase tracking-wider">
                Articulate, structured framework context.
              </p>
            </div>

            {/* Tech Depth */}
            <div className="bg-surface-container border border-outline-variant rounded-lg p-6 relative overflow-hidden group hover:border-cyber-blue/40 transition-colors text-left">
              <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 text-cyber-blue">
                <Bot className="h-16 w-16" />
              </div>
              <h3 className="font-mono text-[10px] text-on-surface-variant uppercase tracking-widest mb-4 font-semibold">Technical Depth</h3>
              <div className="flex items-baseline gap-1 mb-2 font-mono">
                <span className="text-5xl font-bold text-white tracking-tighter">
                  {countUpMatch > 0 ? Math.round(countUpMatch * 0.886) : 0}
                </span>
                <span className="text-lg text-on-surface-variant font-bold">/100</span>
              </div>
              <div className="w-full bg-surface-dim h-1.5 rounded-full mt-4 overflow-hidden border border-outline-variant/30">
                <div 
                  className="bg-[#20202c] h-full rounded-full transition-all duration-1000"
                  style={{ width: "78%" }}
                ></div>
              </div>
              <p className="text-[10px] font-mono text-on-surface-variant mt-3 uppercase tracking-wider">
                Strong engineering core, superficial edges.
              </p>
            </div>
          </div>

          {/* Two Column details */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Left: Detailed AI synthesis report notes */}
            <div className="lg:col-span-2 bg-surface-container border border-outline-variant rounded-lg p-8">
              <div className="flex items-center justify-between mb-6 border-b border-outline-variant/60 pb-4">
                <h3 className="font-mono text-xs font-bold text-cyber-blue uppercase tracking-widest flex items-center gap-1.5">
                  <Info className="h-4.5 w-4.5" />
                  <span>AI Synthesis Summary</span>
                </h3>
                <span className="text-[9px] font-mono text-on-surface-variant bg-surface-dim border border-outline-variant px-2 py-0.5 rounded-sm terminal-cursor uppercase">
                  Model: cp-v4-turbo
                </span>
              </div>

              <div className="space-y-6 text-sm text-left">
                <div className="animate-fade-slide-up">
                  <h4 className="font-sans text-base font-bold text-white mb-2">Executive Summary</h4>
                  <p className="text-on-surface-variant leading-relaxed">
                    The candidate demonstrated a robust understanding of modern React paradigms and component architecture. They successfully navigated the architectural design questions, showing a preference for composition over inheritance and highlighting the importance of memoization in large-scale applications.
                  </p>
                </div>

                <div className="animate-fade-slide-up" style={{ animationDelay: "150ms" }}>
                  <h4 className="font-sans text-base font-bold text-white mb-2">Technical Deep-Dive</h4>
                  <p className="text-on-surface-variant leading-relaxed mb-3">
                    When asked about managing complex state across deeply nested components, the candidate immediately identified Context API and state management libraries like Redux or Zustand. Their explanation of <code className="font-mono bg-surface-dim px-1.5 py-0.5 rounded border border-outline-variant text-cyber-blue">useReducer</code> combined with Context was textbook.
                  </p>
                  <p className="text-on-surface-variant leading-relaxed">
                    However, during the performance optimization segment, the response lacked empirical depth. The candidate stated:
                    <span className="font-mono text-xs text-cyber-blue block my-2 p-3 bg-surface-dim rounded border border-cyber-blue/15 shadow-sm leading-normal">
                      &quot;I would use useMemo and useCallback everywhere to prevent re-renders.&quot;
                    </span>
                    This indicates a common anti-pattern. <strong className="text-white">Over-memoization</strong> can lead to worse performance due to the overhead of dependency comparison. A more nuanced understanding of React&apos;s rendering lifecycle was expected for a Senior role.
                  </p>
                </div>

                <div className="animate-fade-slide-up" style={{ animationDelay: "300ms" }}>
                  <h4 className="font-sans text-base font-bold text-white mb-2">Behavioral Indicators</h4>
                  <ul className="list-disc list-inside space-y-2 text-on-surface-variant leading-relaxed">
                    <li>Takes proactive ownership of technical debt.</li>
                    <li>Pragmatic approach to testing (favors integration over exhaustive unit tests).</li>
                    <li>Slight tendency to interrupt when eager to answer.</li>
                  </ul>
                </div>
              </div>
            </div>

            {/* Right: Critical Weaknesses checklist */}
            <div className="flex flex-col gap-6">
              <div className="bg-surface-container border border-outline-variant rounded-lg flex flex-col h-full overflow-hidden">
                <div className="p-5 border-b border-outline-variant bg-[#0c0c10]/40 text-left">
                  <h3 className="font-mono text-xs font-bold text-red-400 uppercase tracking-widest flex items-center gap-1.5 leading-none">
                    <AlertTriangle className="h-4.5 w-4.5 text-red-500 animate-pulse" />
                    <span>Critical Weaknesses</span>
                  </h3>
                </div>

                <div className="p-5 flex-1 flex flex-col gap-5 text-left">
                  {/* Weakness 1 */}
                  <div className="border border-outline-variant/60 rounded p-4 bg-[#050508]/40 relative group hover:border-red-500/20 transition-all duration-300">
                    <div className="absolute -left-[1px] top-4 bottom-4 w-[2px] bg-red-500 group-hover:shadow-[0_0_8px_rgba(239,68,68,0.8)]"></div>
                    <h4 className="text-xs font-mono uppercase text-white font-bold mb-1">Performance Anti-Patterns</h4>
                    <p className="text-[11px] text-on-surface-variant leading-relaxed mb-3">
                      Advocated for indiscriminate use of React memoization hooks without understanding the memory overhead tradeoffs.
                    </p>
                    <div className="bg-surface-dim p-3 rounded border border-outline-variant/60">
                      <span className="text-[9px] font-mono text-cyber-blue font-bold block mb-1 uppercase tracking-wider">Action Item</span>
                      <span className="text-xs text-on-surface-variant font-sans leading-normal block">
                        Probe deeper on profiling tools (React DevTools Profiler) in follow-up round. Ask for a specific scenario where memoization hurt performance.
                      </span>
                    </div>
                  </div>

                  {/* Weakness 2 */}
                  <div className="border border-outline-variant/60 rounded p-4 bg-[#050508]/40 relative group hover:border-cyber-blue/20 transition-all duration-300">
                    <div className="absolute -left-[1px] top-4 bottom-4 w-[2px] bg-cyber-blue group-hover:shadow-[0_0_8px_rgba(0,210,255,0.8)]"></div>
                    <h4 className="text-xs font-mono uppercase text-white font-bold mb-1">CSS Architecture</h4>
                    <p className="text-[11px] text-on-surface-variant leading-relaxed mb-3">
                      Struggled to articulate the differences between utility-first frameworks (Tailwind) and CSS-in-JS solutions under heavy load.
                    </p>
                    <div className="bg-surface-dim p-3 rounded border border-outline-variant/60">
                      <span className="text-[9px] font-mono text-cyber-blue font-bold block mb-1 uppercase tracking-wider">Action Item</span>
                      <span className="text-xs text-on-surface-variant font-sans leading-normal block">
                        Provide a complex layout requirement in a potential technical take-home test to evaluate practical implementation.
                      </span>
                    </div>
                  </div>
                </div>

                <div className="p-4 border-t border-outline-variant mt-auto">
                  <button className="w-full py-2 bg-surface-dim text-on-surface hover:text-cyber-blue text-xs font-mono font-bold rounded border border-outline-variant hover:border-cyber-blue/30 transition-all flex items-center justify-center gap-1.5 cursor-pointer">
                    <ClipboardList className="h-4 w-4" /> Add to Pipeline Notes
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
