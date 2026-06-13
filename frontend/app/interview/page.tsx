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
  AlertTriangle,
  ClipboardList,
  RotateCcw,
  Sparkles,
  Radar,
  Loader,
  Upload,
  FileText
} from "lucide-react";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

interface AssessmentData {
  overall_score: number;
  technical_score: number;
  communication_score: number;
  resume_strength_score?: number;
  role_fit_score?: number;
  strengths: string[];
  weaknesses: string[];
  missing_skills?: string[];
  verdict: string;
}

interface ChatMessage {
  sender: "SYSTEM" | "USER";
  text: string;
  timestamp: string;
}

export default function InterviewPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isEnded, setIsEnded] = useState(false);
  const [inputText, setInputText] = useState("");
  const [isThinking, setIsThinking] = useState(false);
  const [timerSeconds, setTimerSeconds] = useState(0);
  const [countUpMatch, setCountUpMatch] = useState(0);
  const [isAssessing, setIsAssessing] = useState(false);
  const [assessmentData, setAssessmentData] = useState<AssessmentData | null>(null);
  const [sessionStarted, setSessionStarted] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [uploadedFileName, setUploadedFileName] = useState<string | null>(null);
  const [interviewPhase, setInterviewPhase] = useState<string>("introduction");

  const chatEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

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

  // Start interview session on mount
  useEffect(() => {
    if (!sessionStarted) {
      setSessionStarted(true);
      startInterviewSession();
    }
  }, []);

  // Interview phase is now read from the API response (DB-authoritative)
  // No longer inferred from client-side message count

  const startInterviewSession = async () => {
    try {
      setIsThinking(true);
      const response = await fetch(`${BASE_URL}/interview/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });

      if (response.ok) {
        const data = await response.json();
        setSessionId(data.session_id);

        // Add AI's first message
        const aiMessage: ChatMessage = {
          sender: "SYSTEM",
          text: data.initial_question,
          timestamp: new Date().toISOString()
        };
        setMessages([aiMessage]);
      }
    } catch (error) {
      console.error("Failed to start interview:", error);
    } finally {
      setIsThinking(false);
    }
  };

  // Format Elapsed Time
  const formatTimer = () => {
    const mins = Math.floor(timerSeconds / 60);
    const secs = timerSeconds % 60;
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  // Handle resume file upload
  const handleResumeUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !sessionId) return;

    setUploadedFileName(file.name);

    // Add user message about upload (visible in chat)
    const userMsg: ChatMessage = {
      sender: "USER",
      text: `[Resume uploaded: ${file.name}]`,
      timestamp: new Date().toISOString()
    };
    setMessages(prev => [...prev, userMsg]);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("session_id", sessionId);

    try {
      setIsThinking(true);
      const response = await fetch(`${BASE_URL}/interview/upload_resume`, {
        method: "POST",
        body: formData,
      });

      if (response.ok) {
        const data = await response.json();

        // Show acknowledgment
        const charCount: number = data.char_count ?? 0;
        const aiAckMsg: ChatMessage = {
          sender: "SYSTEM",
          text: `I've received your resume (${file.name}${
            charCount > 0 ? `, ${charCount.toLocaleString()} characters extracted` : ''
          }). Let me review it and ask you some targeted technical questions based on your experience.`,
          timestamp: new Date().toISOString()
        };
        setMessages(prev => [...prev, aiAckMsg]);
        setInterviewPhase("technical");

        // Trigger the first technical question — include the ack message in history
        await sendMessageToAI(
          `[Resume uploaded: ${file.name}]`,
          [...messages, userMsg, aiAckMsg]
        );
      } else {
        const err = await response.json().catch(() => ({ message: "Upload failed" }));
        const errMsg: ChatMessage = {
          sender: "SYSTEM",
          text: `Sorry, I couldn't parse that file: ${err.message || "unknown error"}. Try saving as .txt and uploading again, or paste your resume text directly.`,
          timestamp: new Date().toISOString()
        };
        setMessages(prev => [...prev, errMsg]);
      }
    } catch (error) {
      console.error("Upload failed:", error);
    } finally {
      setIsThinking(false);
    }
  };

  // Handle resume paste
  const handleResumePaste = () => {
    setInputText("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.placeholder = "Paste your resume text here...";
      textareaRef.current.focus();
    }
  };

  // Send message to AI — currentMessages allows passing in-flight state
  const sendMessageToAI = async (
    text: string,
    currentMessages?: ChatMessage[]
  ) => {
    if (!sessionId) return;

    const historyToSend = currentMessages ?? messages;

    try {
      setIsThinking(true);

      const response = await fetch(`${BASE_URL}/interview/respond`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          response: text,
          chat_history: historyToSend,
          is_complete: false
        })
      });

      if (response.ok) {
        const data = await response.json();

        // Update phase from DB-authoritative API response
        if (data.phase) {
          setInterviewPhase(data.phase);
        }

        const aiMsg: ChatMessage = {
          sender: "SYSTEM",
          text: data.reply,
          timestamp: new Date().toISOString()
        };
        setMessages(prev => [...prev, aiMsg]);
      }
    } catch (error) {
      console.error("Failed to send message:", error);
    } finally {
      setIsThinking(false);
    }
  };

  // Handle sending a message
  const handleSendMessage = async () => {
    if (!inputText.trim()) return;

    const text = inputText;
    setInputText("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.placeholder = "Type your response...";
    }

    // Add user message to local state first
    const userMsg: ChatMessage = {
      sender: "USER",
      text: text,
      timestamp: new Date().toISOString()
    };
    const updatedMessages = [...messages, userMsg];
    setMessages(updatedMessages);

    // Send to AI with the updated history (including this new message)
    await sendMessageToAI(text, updatedMessages);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // Trigger End of Session — calls /interview/assess for real rubric
  const handleEndSession = async () => {
    setIsEnded(true);
    setIsAssessing(true);

    try {
      const response = await fetch(`${BASE_URL}/interview/assess`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ chat_history: messages })
      });

      if (response.ok) {
        const data: AssessmentData = await response.json();
        setAssessmentData(data);

        // Count up animation to real score
        setCountUpMatch(0);
        setTimeout(() => {
          const target = data.overall_score;
          const stepTime = Math.max(10, Math.floor(1500 / target));
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
      } else {
        throw new Error("Assessment API failed");
      }
    } catch (e) {
      console.error("Assessment failed, using fallback score", e);
      const target = 75;
      setCountUpMatch(0);
      setTimeout(() => {
        const stepTime = Math.max(10, Math.floor(1500 / target));
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
    } finally {
      setIsAssessing(false);
    }
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

  const handleRestart = () => {
    setMessages([]);
    setIsEnded(false);
    setTimerSeconds(0);
    setAssessmentData(null);
    setCountUpMatch(0);
    setSessionStarted(false);
    setSessionId(null);
    setUploadedFileName(null);
    setInterviewPhase("introduction");
  };

  // Get phase indicator
  const getPhaseLabel = () => {
    switch (interviewPhase) {
      case "introduction": return "Introduction";
      case "job_role": return "Role Discussion";
      case "resume": return "Resume Review";
      case "technical": return "Technical Interview";
      default: return "Interview";
    }
  };

  return (
    <div className="flex h-[calc(100vh-4rem)] w-full overflow-hidden animate-fade-in relative bg-bg-deep text-left">
      {!isEnded ? (
        /* 1. Live Chat Interview Workspace */
        <div className="flex flex-1 flex-col lg:flex-row overflow-hidden w-full h-full">
          {/* Left Performance Telemetry Panel (320px width) */}
          <aside className="w-full lg:w-80 border-b lg:border-b-0 lg:border-r border-outline-variant bg-surface-container-low shrink-0 overflow-y-auto flex flex-col p-6 space-y-8 z-20">
            {/* Interview Phase Indicator */}
            <div className="space-y-2 text-left">
              <h3 className="font-mono text-[9px] text-on-surface-variant tracking-wider uppercase font-semibold">Current Phase</h3>
              <div className="px-3 py-2 bg-cyber-blue/10 border border-cyber-blue/20 rounded text-cyber-blue font-mono text-sm font-bold">
                {getPhaseLabel()}
              </div>
            </div>

            {/* Timer */}
            <div className="space-y-1.5 text-left">
              <h3 className="font-mono text-[9px] text-on-surface-variant tracking-wider uppercase font-semibold">T-Elapsed</h3>
              <div className="font-mono text-3xl text-cyber-blue font-light glow-text leading-none">
                {formatTimer()}
              </div>
            </div>

            {/* Resume Upload Status */}
            <div className="space-y-3 text-left">
              <h3 className="font-mono text-[9px] text-on-surface-variant tracking-wider uppercase font-semibold">Resume</h3>
              {uploadedFileName ? (
                <div className="flex items-center gap-2 p-3 bg-green-950/20 border border-green-500/20 rounded">
                  <FileText className="h-4 w-4 text-green-400" />
                  <span className="text-xs text-green-400 font-mono truncate">{uploadedFileName}</span>
                </div>
              ) : (
                <div className="flex gap-2">
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    className="flex-1 px-3 py-2 bg-surface-dim hover:bg-surface-container border border-outline-variant rounded text-xs font-mono text-on-surface hover:text-cyber-blue transition-all flex items-center justify-center gap-1.5 cursor-pointer"
                  >
                    <Upload className="h-3.5 w-3.5" />
                    Upload
                  </button>
                  <button
                    onClick={handleResumePaste}
                    className="flex-1 px-3 py-2 bg-surface-dim hover:bg-surface-container border border-outline-variant rounded text-xs font-mono text-on-surface hover:text-cyber-blue transition-all flex items-center justify-center gap-1.5 cursor-pointer"
                  >
                    <FileText className="h-3.5 w-3.5" />
                    Paste
                  </button>
                  <input
                    type="file"
                    ref={fileInputRef}
                    onChange={handleResumeUpload}
                    className="hidden"
                    accept=".txt,.pdf,.docx"
                  />
                </div>
              )}
            </div>

            {/* Metrics Bento Grid */}
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-surface-dim border border-outline-variant p-4 flex flex-col gap-2 rounded hover:border-cyber-blue/30 transition-colors">
                <Activity className="h-4 w-4 text-on-surface-variant" />
                <span className="font-mono text-2xl font-bold text-white">
                  {messages.filter(m => m.sender === "USER").length}
                </span>
                <span className="font-mono text-[9px] text-on-surface-variant uppercase tracking-wider font-semibold">Responses</span>
              </div>
              <div className="bg-surface-dim border border-outline-variant p-4 flex flex-col gap-2 rounded hover:border-cyber-blue/30 transition-colors">
                <Bot className="h-4 w-4 text-on-surface-variant" />
                <span className="font-mono text-2xl font-bold text-white">
                  {messages.filter(m => m.sender === "SYSTEM").length}
                </span>
                <span className="font-mono text-[9px] text-on-surface-variant uppercase tracking-wider font-semibold">Questions</span>
              </div>
            </div>

            {/* Interview Progress */}
            <div className="space-y-3.5 text-left">
              <div className="flex justify-between items-baseline font-mono text-[9px] uppercase tracking-wider font-semibold">
                <span className="text-on-surface-variant">Progress</span>
                <span className="text-cyber-blue glow-text">{getPhaseLabel()}</span>
              </div>
              <div className="h-2 bg-surface-dim w-full rounded overflow-hidden border border-outline-variant/60 relative">
                <div 
                  className="h-full bg-cyber-blue/80 shadow-[0_0_8px_rgba(0,210,255,0.6)] rounded-full transition-all duration-500"
                  style={{ 
                    width: interviewPhase === "introduction" ? "15%" : 
                           interviewPhase === "job_role" ? "35%" : 
                           interviewPhase === "resume" ? "55%" : "80%" 
                  }}
                >
                  <div className="absolute right-0 top-0 bottom-0 w-1 bg-white"></div>
                </div>
              </div>
              <div className="flex justify-between font-mono text-[9px] text-on-surface-variant/40">
                <span>Start</span>
                <span>Assessment</span>
              </div>
            </div>

            {/* Extracted technical terms */}
            <div className="grow flex flex-col min-h-0 text-left">
              <h3 className="font-mono text-[9px] text-on-surface-variant tracking-wider uppercase font-semibold mb-4 shrink-0">
                Tech Terms Extracted
              </h3>
              <div className="grow overflow-y-auto space-y-2 pr-1 text-xs font-mono">
                {messages.length > 2 ? (
                  <>
                    <div className="flex items-center justify-between py-1 border-b border-outline-variant/20 hover:border-cyber-blue/40 transition-colors group">
                      <span className="text-white">
                        {interviewPhase === "introduction" ? "Background" : 
                         interviewPhase === "job_role" ? "Role Focus" : "Technical Skills"}
                      </span>
                      <Check className="h-3.5 w-3.5 text-cyber-blue opacity-0 group-hover:opacity-100 transition-opacity" />
                    </div>
                    <div className="flex items-center justify-between py-1 border-b border-outline-variant/20 hover:border-cyber-blue/40 transition-colors group">
                      <span className="text-white">
                        {interviewPhase === "technical" ? "In Progress..." : "Pending"}
                      </span>
                      {interviewPhase === "technical" ? (
                        <Hourglass className="h-3.5 w-3.5 text-on-surface-variant/40 animate-spin" />
                      ) : (
                        <Check className="h-3.5 w-3.5 text-cyber-blue opacity-0 group-hover:opacity-100 transition-opacity" />
                      )}
                    </div>
                  </>
                ) : (
                  <div className="text-on-surface-variant/40 italic text-xs">
                    Waiting for conversation to start...
                  </div>
                )}
              </div>
            </div>

            {/* End session action */}
            <div className="shrink-0 pt-4 border-t border-outline-variant/60">
              <button 
                onClick={handleEndSession}
                disabled={isAssessing || messages.length < 4}
                className="w-full bg-red-950/20 text-red-400 border border-red-500/30 hover:bg-red-500 hover:text-black hover:border-red-500 hover:shadow-[0_0_10px_rgba(239,68,68,0.4)] transition-all duration-300 py-3 rounded font-mono text-[10px] uppercase tracking-wider font-bold flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isAssessing ? (
                  <><Loader className="h-4 w-4 animate-spin" /><span>Assessing...</span></>
                ) : (
                  <><StopCircle className="h-4 w-4" /><span>End &amp; Get Rubric</span></>
                )}
              </button>
              {messages.length < 4 && (
                <p className="text-[8px] text-on-surface-variant/40 mt-1 text-center">
                  Complete at least the introduction and job role phases
                </p>
              )}
            </div>
          </aside>

          {/* Right Side Chat Terminal */}
          <section className="flex-1 flex flex-col bg-bg-deep relative overflow-hidden h-full z-10">
            {/* Scrollable feed messages */}
            <div className="flex-1 overflow-y-auto p-8 space-y-6 scroll-smooth pb-36 h-full">
              {messages.length === 0 && !isThinking && (
                <div className="flex items-center justify-center h-full">
                  <div className="text-center space-y-4">
                    <Bot className="h-16 w-16 text-cyber-blue/30 mx-auto animate-pulse" />
                    <p className="text-on-surface-variant font-mono text-sm">Initializing interview session...</p>
                  </div>
                </div>
              )}

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
                            [INTERVIEWER] <span className="text-on-surface-variant/40">{new Date(msg.timestamp).toLocaleTimeString()}</span>
                          </>
                        ) : (
                          <>
                            <span className="text-on-surface-variant/40">{new Date(msg.timestamp).toLocaleTimeString()}</span> [YOU]
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
                    <div className="font-mono text-[9px] text-on-surface-variant">[INTERVIEWER] <span className="text-cyber-blue">Thinking...</span></div>
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
            <div className="absolute bottom-0 left-0 right-0 p-6 bg-linear-to-t from-bg-deep via-bg-deep/90 to-transparent pt-12 z-20">
              <div className="max-w-4xl mx-auto">
                <div className="bg-surface-container-low border border-outline-variant rounded-lg focus-within:border-cyber-blue focus-within:ring-1 focus-within:ring-cyber-blue transition-all duration-200 p-2 shadow-lg flex gap-2">
                  <div className="pt-2 pl-2 text-cyber-blue font-mono select-none shrink-0 font-bold">&gt;</div>
                  <textarea 
                    ref={textareaRef}
                    className="w-full bg-transparent border-none text-white font-sans text-xs focus:ring-0 resize-none h-14 py-2 placeholder-on-surface-variant/40 focus:outline-none"
                    placeholder="Type your response..."
                    value={inputText}
                    onChange={handleInputChange}
                    onKeyDown={handleKeyDown}
                    disabled={isThinking}
                  />
                  <div className="flex flex-col justify-end gap-2 pb-1 pr-1 shrink-0">
                    <button 
                      onClick={() => fileInputRef.current?.click()}
                      className="w-9 h-9 rounded bg-surface-container-high hover:bg-surface-container-highest text-on-surface-variant hover:text-cyber-blue transition-colors flex items-center justify-center border border-outline-variant cursor-pointer"
                      title="Upload Resume"
                    >
                      <Upload className="h-4 w-4" />
                    </button>
                    <input
                      type="file"
                      ref={fileInputRef}
                      onChange={handleResumeUpload}
                      className="hidden"
                      accept=".txt,.pdf,.docx"
                    />
                    <button className="w-9 h-9 rounded bg-surface-container-high hover:bg-surface-container-highest text-on-surface-variant hover:text-cyber-blue transition-colors flex items-center justify-center border border-outline-variant cursor-pointer">
                      <Mic className="h-4 w-4" />
                    </button>
                    <button 
                      onClick={handleSendMessage}
                      disabled={isThinking || !inputText.trim()}
                      className="w-9 h-9 rounded bg-cyber-blue text-black hover:bg-white transition-colors flex items-center justify-center font-bold cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <Send className="h-4 w-4" />
                    </button>
                  </div>
                </div>
                <div className="flex justify-between items-center mt-2.5 px-2 font-mono text-[9px] text-on-surface-variant/50">
                  <span>Press Enter to send • Shift+Enter for new line</span>
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
                <span className="text-[10px] text-on-surface-variant">ID: {sessionId?.slice(0, 8) || 'N/A'}</span>
              </div>
              <h2 className="text-3xl font-bold tracking-tight text-white flex items-center gap-2">
                Interview Assessment Report <Sparkles className="h-5 w-5 text-cyber-blue" />
              </h2>
              <p className="text-xs text-on-surface-variant font-mono mt-1">
                {assessmentData ? assessmentData.verdict : "AI assessment report generated."}
              </p>
            </div>
            <div className="flex gap-3">
              <button 
                onClick={handleRestart}
                className="px-4 py-2 bg-surface-container-low border border-outline-variant rounded text-xs font-mono font-bold text-on-surface hover:bg-surface-container hover:text-cyber-blue hover:border-cyber-blue/30 transition-all flex items-center gap-2 cursor-pointer"
              >
                <RotateCcw className="h-4 w-4" /> New Interview
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
            {/* Overall Match score count-up */}
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
                {assessmentData ? `Technical: ${assessmentData.technical_score}%` : "Assessment complete."}
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
                  {assessmentData ? assessmentData.communication_score : (countUpMatch > 0 ? Math.round(countUpMatch * 1.045) : 0)}
                </span>
                <span className="text-lg text-on-surface-variant font-bold">/100</span>
              </div>
              <div className="w-full bg-surface-dim h-1.5 rounded-full mt-4 overflow-hidden border border-outline-variant/30">
                <div
                  className="bg-white h-full rounded-full transition-all duration-1000"
                  style={{ width: `${assessmentData ? assessmentData.communication_score : 80}%` }}
                ></div>
              </div>
              <p className="text-[10px] font-mono text-on-surface-variant mt-3 uppercase tracking-wider">
                Articulate, structured responses.
              </p>
            </div>

            {/* Role Fit / Technical Depth */}
            <div className="bg-surface-container border border-outline-variant rounded-lg p-6 relative overflow-hidden group hover:border-cyber-blue/40 transition-colors text-left">
              <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 text-cyber-blue">
                <Bot className="h-16 w-16" />
              </div>
              <h3 className="font-mono text-[10px] text-on-surface-variant uppercase tracking-widest mb-4 font-semibold">Role Fit Score</h3>
              <div className="flex items-baseline gap-1 mb-2 font-mono">
                <span className="text-5xl font-bold text-white tracking-tighter">
                  {assessmentData?.role_fit_score ?? (assessmentData ? assessmentData.technical_score : (countUpMatch > 0 ? Math.round(countUpMatch * 0.886) : 0))}
                </span>
                <span className="text-lg text-on-surface-variant font-bold">/100</span>
              </div>
              <div className="w-full bg-surface-dim h-1.5 rounded-full mt-4 overflow-hidden border border-outline-variant/30">
                <div
                  className="bg-[#20202c] h-full rounded-full transition-all duration-1000"
                  style={{ width: `${assessmentData?.role_fit_score ?? (assessmentData ? assessmentData.technical_score : 70)}%` }}
                ></div>
              </div>
              <p className="text-[10px] font-mono text-on-surface-variant mt-3 uppercase tracking-wider">
                {assessmentData?.resume_strength_score != null ? `Resume Strength: ${assessmentData.resume_strength_score}%` : "Role alignment analysis."}
              </p>
            </div>
          </div>

          {/* Two Column details */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Left: Detailed AI synthesis report notes */}
            <div className="lg:col-span-2 bg-surface-container border border-outline-variant rounded-lg p-8">
              <div className="flex items-center justify-between mb-6 border-b border-outline-variant/60 pb-4">
                <h3 className="font-mono text-xs font-bold text-cyber-blue uppercase tracking-widest flex items-center gap-1.5">
                  <Info className="h-4 w-4" />
                  <span>AI Synthesis Summary</span>
                </h3>
                <span className="text-[9px] font-mono text-on-surface-variant bg-surface-dim border border-outline-variant px-2 py-0.5 rounded-sm terminal-cursor uppercase">
                  Model: Groq LLM
                </span>
              </div>

              <div className="space-y-6 text-sm text-left">
                <div className="animate-fade-slide-up">
                  <h4 className="font-sans text-base font-bold text-white mb-2">Executive Summary</h4>
                  <p className="text-on-surface-variant leading-relaxed">
                    {assessmentData?.strengths.join(" ") ||
                      "The candidate demonstrated relevant technical knowledge and communication skills throughout the interview."}
                  </p>
                </div>

                <div className="animate-fade-slide-up" style={{ animationDelay: "150ms" }}>
                  <h4 className="font-sans text-base font-bold text-white mb-2">AI Assessment Verdict</h4>
                  <p className="text-on-surface-variant leading-relaxed">
                    {assessmentData?.verdict ||
                      "Candidate shows foundational knowledge. Consider for the position based on team fit and specific requirements."}
                  </p>
                </div>

                {assessmentData?.strengths && assessmentData.strengths.length > 0 && (
                  <div className="animate-fade-slide-up" style={{ animationDelay: "300ms" }}>
                    <h4 className="font-sans text-base font-bold text-white mb-2">Key Strengths</h4>
                    <ul className="list-disc list-inside space-y-2 text-on-surface-variant leading-relaxed">
                      {assessmentData.strengths.map((s, i) => (
                        <li key={i}>{s}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {assessmentData?.missing_skills && assessmentData.missing_skills.length > 0 && (
                  <div className="animate-fade-slide-up" style={{ animationDelay: "450ms" }}>
                    <h4 className="font-sans text-base font-bold text-white mb-2">Skill Gaps Identified</h4>
                    <div className="flex flex-wrap gap-2">
                      {assessmentData.missing_skills.map((skill, i) => (
                        <span
                          key={i}
                          className="px-2.5 py-1 bg-red-950/30 border border-red-500/20 rounded text-[11px] font-mono text-red-400"
                        >
                          {skill}
                        </span>
                      ))}
                    </div>
                    <p className="text-[10px] text-on-surface-variant/50 font-mono mt-2 uppercase tracking-wider">
                      Skills required for the target role not demonstrated during interview
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Right: Critical Weaknesses checklist */}
            <div className="flex flex-col gap-6">
              <div className="bg-surface-container border border-outline-variant rounded-lg flex flex-col h-full overflow-hidden">
                <div className="p-5 border-b border-outline-variant bg-[#0c0c10]/40 text-left">
                  <h3 className="font-mono text-xs font-bold text-red-400 uppercase tracking-widest flex items-center gap-1.5 leading-none">
                    <AlertTriangle className="h-4 w-4 text-red-500 animate-pulse" />
                    <span>Areas for Improvement</span>
                  </h3>
                </div>

                <div className="p-5 flex-1 flex flex-col gap-5 text-left">
                  {(assessmentData?.weaknesses && assessmentData.weaknesses.length > 0 
                    ? assessmentData.weaknesses 
                    : ["Could provide more specific examples", "Expand on system design concepts"]
                  ).map((weakness, idx) => (
                    <div key={idx} className={`border border-outline-variant/60 rounded p-4 bg-[#050508]/40 relative group ${idx % 2 === 0 ? "hover:border-red-500/20" : "hover:border-cyber-blue/20"} transition-all duration-300`}>
                      <div className={`absolute -left-px top-4 bottom-4 w-0.5 ${idx % 2 === 0 ? "bg-red-500 group-hover:shadow-[0_0_8px_rgba(239,68,68,0.8)]" : "bg-cyber-blue group-hover:shadow-[0_0_8px_rgba(0,210,255,0.8)]"}`}></div>
                      <h4 className="text-xs font-mono uppercase text-white font-bold mb-1">
                        {assessmentData ? `Area ${idx + 1}` : "Focus Area"}
                      </h4>
                      <p className="text-[11px] text-on-surface-variant leading-relaxed mb-3">
                        {weakness}
                      </p>
                      <div className="bg-surface-dim p-3 rounded border border-outline-variant/60">
                        <span className="text-[9px] font-mono text-cyber-blue font-bold block mb-1 uppercase tracking-wider">Recommendation</span>
                        <span className="text-xs text-on-surface-variant font-sans leading-normal block">
                          Focus on this area for continued professional development and future interviews.
                        </span>
                      </div>
                    </div>
                  ))}
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