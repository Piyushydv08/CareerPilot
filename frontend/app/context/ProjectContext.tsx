"use client";

import React, { createContext, useContext, useState, useEffect } from "react";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export interface SkillGap {
  name: string;
  category: string;
  impact: number;
  checked: boolean;
}

export interface ResumeData {
  name: string;
  email: string;
  skills: Array<{ name: string; match: number }>;
  experience: Array<{ company: string; role: string; duration: string; details: string }>;
  gaps: SkillGap[];
  ats_score?: number;
  raw_text?: string; // Full extracted resume text for ATS analysis
}

export interface ATSCategoryScores {
  skills_match: number;
  experience_relevance: number;
  keyword_density: number;
  education_certifications: number;
  formatting_completeness: number;
}

export interface ATSMatchDetail {
  match_score: number;
  category_scores: ATSCategoryScores;
  matched_keywords: string[];
  missing_keywords: string[];
  suggestions: string[];
  is_ai_powered: boolean;
}

export interface ChatMessage {
  sender: "SYSTEM" | "USER";
  timestamp: string;
  text: string;
}

interface ProjectContextType {
  resumeData: ResumeData | null;
  jobDescription: string;
  matchScore: number;
  atsMatchDetail: ATSMatchDetail | null;
  isAnalyzing: boolean;
  messages: ChatMessage[];
  sessionId: string | null;
  upcomingEngagement: {
    days: number;
    hours: number;
    minutes: number;
    company: string;
    type: string;
    platform: string;
  };
  terminalLogs: Array<{ time: string; type: "INFO" | "EXEC" | "WARN"; message: string; relativeTime: string }>;
  setJobDescription: (desc: string) => void;
  setMatchScore: React.Dispatch<React.SetStateAction<number>>;
  setResumeData: React.Dispatch<React.SetStateAction<ResumeData | null>>;
  setSessionId: React.Dispatch<React.SetStateAction<string | null>>;
  uploadResume: (file: File) => Promise<boolean>;
  triggerAnalyze: (jobDesc: string) => Promise<number>;
  sendInterviewMessage: (text: string) => Promise<void>;
  startInterviewSession: (jobDesc?: string) => Promise<string | null>;
  resetInterview: () => void;
  toggleSkillGap: (index: number) => void;
  addTerminalLog: (type: "INFO" | "EXEC" | "WARN", message: string) => void;
}

const ProjectContext = createContext<ProjectContextType | undefined>(undefined);

const initialResumeData: ResumeData | null = null;

const initialLogs: Array<{ time: string; type: "INFO" | "EXEC" | "WARN"; message: string; relativeTime: string }> = [];

export const ProjectProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [resumeData, setResumeData] = useState<ResumeData | null>(initialResumeData);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [jobDescription, setJobDescription] = useState<string>("");
  const [matchScore, setMatchScore] = useState<number>(0);
  const [atsMatchDetail, setAtsMatchDetail] = useState<ATSMatchDetail | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([
    { sender: "SYSTEM", timestamp: "14:02:11", text: "Let's pivot to system design. Imagine we are building a ride-sharing application. How would you design the backend architecture to handle high-frequency driver location updates while ensuring low latency for riders matching?" },
    { sender: "USER", timestamp: "14:04:45", text: "I'd start by breaking this into microservices to ensure we can scale independently. For the location updates specifically, since they are high-frequency and need low latency, I wouldn't write them directly to a relational database. Instead, I'd use an event-driven architecture, perhaps ingesting the streams via Kafka or AWS Kinesis." },
    { sender: "SYSTEM", timestamp: "14:05:10", text: "That makes sense for ingestion. Once the location data is in Kafka, how do you efficiently query it to find the nearest drivers for a specific rider? Standard relational queries wouldn't be fast enough here." },
    { sender: "USER", timestamp: "14:06:05", text: "To handle geospatial queries efficiently, I would use an in-memory datastore designed for this, like Redis using its geospatial indices (GeoHash)." }
  ]);

  const [upcomingEngagement, setUpcomingEngagement] = useState({
    days: 2,
    hours: 14,
    minutes: 45,
    company: "Stripe",
    type: "Technical Screen",
    platform: "Google Meet"
  });

  const [terminalLogs, setTerminalLogs] = useState(initialLogs);

  // Countdown timer for Upcoming Engagement
  useEffect(() => {
    const timer = setInterval(() => {
      setUpcomingEngagement(prev => {
        if (prev.minutes > 0) {
          return { ...prev, minutes: prev.minutes - 1 };
        } else if (prev.hours > 0) {
          return { ...prev, hours: prev.hours - 1, minutes: 59 };
        } else if (prev.days > 0) {
          return { ...prev, days: prev.days - 1, hours: 23, minutes: 59 };
        }
        return prev;
      });
    }, 60000);
    return () => clearInterval(timer);
  }, []);

  const addTerminalLog = (type: "INFO" | "EXEC" | "WARN", message: string) => {
    const now = new Date();
    const timeStr = `${now.getHours().toString().padStart(2, "0")}:${now.getMinutes().toString().padStart(2, "0")}:${now.getSeconds().toString().padStart(2, "0")}`;
    setTerminalLogs(prev => [
      { time: timeStr, type, message, relativeTime: "Just now" },
      ...prev.slice(0, 7) // keep it reasonably sized
    ]);
  };

  // Upload Resume
  const uploadResume = async (file: File): Promise<boolean> => {
    setIsAnalyzing(true);
    addTerminalLog("INFO", `Uploading resume file: ${file.name}`);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(`${BASE_URL}/resume/upload`, {
        method: "POST",
        body: formData
      });

      if (response.ok) {
        const data = await response.json();
        setResumeData(data);
        setUploadedFile(file);
        if (data.ats_score !== undefined) {
          setMatchScore(data.ats_score);
        }
        addTerminalLog("INFO", `Successfully parsed resume via backend.`);
        setIsAnalyzing(false);
        return true;
      }
      throw new Error("Backend response failed");
    } catch (e) {
      console.error("Upload failed", e);
      addTerminalLog("WARN", `Upload failed: ${file.name}`);
      setIsAnalyzing(false);
      return false;
    }
  };

  // Analyze Job Description — Gemini-powered ATS analysis
  const triggerAnalyze = async (jobDesc: string): Promise<number> => {
    setIsAnalyzing(true);
    setJobDescription(jobDesc);
    addTerminalLog("INFO", `Running ATS compatibility analysis against job description...`);

    try {
      let response;
      // Prefer new streamlit/match endpoint when file is available
      if (uploadedFile) {
        const form = new FormData();
        form.append("file", uploadedFile);
        form.append("job_description", jobDesc);
        response = await fetch(`${BASE_URL}/resume/streamlit/match`, {
          method: "POST",
          body: form
        });
      } else {
        response = await fetch(`${BASE_URL}/match/analyze`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            resume: resumeData,
            job_description: jobDesc,
            resume_raw_text: resumeData?.raw_text || null
          })
        });
      }

      if (response.ok) {
        const data = await response.json();
        // If it's the streamlit/match shape
        if (data.match_percentage !== undefined) {
          setMatchScore(data.match_percentage);
          setAtsMatchDetail(prev => prev ? { ...prev, match_score: data.match_percentage } : null);
          addTerminalLog("INFO", `ATS analysis complete (streamlit). Match score: ${data.match_percentage}%.`);
          setIsAnalyzing(false);
          return data.match_percentage;
        }
        // Otherwise assume legacy shape
        setMatchScore(data.match_score);
        setAtsMatchDetail({
          match_score: data.match_score,
          category_scores: data.category_scores,
          matched_keywords: data.matched_keywords || [],
          missing_keywords: data.missing_keywords || [],
          suggestions: data.suggestions || [],
          is_ai_powered: data.is_ai_powered || false
        });
        addTerminalLog("INFO", `ATS analysis complete. Match score: ${data.match_score}%.`);
        setIsAnalyzing(false);
        return data.match_score;
      }
      throw new Error("Backend failed");
    } catch (e) {
      console.error("ATS analysis failed", e);
      addTerminalLog("WARN", "ATS analysis failed — backend unavailable or error occurred.");
      setIsAnalyzing(false);
      setAtsMatchDetail(null);
      return 0;
    }
  };

  // Start a new Interview Session — calls /interview/start, stores session_id
  const startInterviewSession = async (jobDesc?: string): Promise<string | null> => {
    if (!resumeData) return null;
    const targetJobDesc = jobDesc || jobDescription;

    addTerminalLog("INFO", "Initializing interview session with backend...");

    try {
      const response = await fetch(`${BASE_URL}/interview/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ resume: resumeData, job_description: targetJobDesc })
      });

      if (response.ok) {
        const data = await response.json();
        setSessionId(data.session_id);
        const sysTimestamp = `${new Date().getHours().toString().padStart(2, "0")}:${new Date().getMinutes().toString().padStart(2, "0")}`;
        setMessages([{ sender: "SYSTEM", timestamp: sysTimestamp, text: data.initial_question }]);
        addTerminalLog("INFO", `Interview session started: ${data.session_id}`);
        return data.session_id;
      }
      throw new Error("Failed to start interview session");
    } catch (e) {
      console.warn("Interview start failed, using simulation", e);
      addTerminalLog("WARN", "Interview session using simulation mode.");
      return null;
    }
  };

  // Toggle Skill checkboxes in Simulator
  const toggleSkillGap = (index: number) => {
    if (!resumeData) return;

    const updatedGaps = [...resumeData.gaps];
    const previousState = updatedGaps[index].checked;
    updatedGaps[index] = { ...updatedGaps[index], checked: !previousState };

    setResumeData({
      ...resumeData,
      gaps: updatedGaps
    });

    const impact = updatedGaps[index].impact;
    setMatchScore(prev => {
      const direction = !previousState ? 1 : -1;
      const newScore = Math.min(Math.max(prev + (direction * impact), 0), 100);
      addTerminalLog("EXEC", `Simulated gap update: ${updatedGaps[index].name} (${!previousState ? 'fulfilled' : 'removed'}). Adjusting Match score by ${!previousState ? '+' : '-'}${impact}%.`);
      return newScore;
    });
  };

  // Send Interview Message — includes session_id from context
  const sendInterviewMessage = async (text: string) => {
    if (!text.trim()) return;

    const now = new Date();
    const timestamp = `${now.getHours().toString().padStart(2, "0")}:${now.getMinutes().toString().padStart(2, "0")}`;
    const userMsg: ChatMessage = { sender: "USER", timestamp, text };

    setMessages(prev => [...prev, userMsg]);
    addTerminalLog("EXEC", `Sent interview response: "${text.slice(0, 30)}..."`);

    // Simulate dot bounce typing animation latency
    await new Promise(resolve => setTimeout(resolve, 1500));

    try {
      const response = await fetch(`${BASE_URL}/interview/respond`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId ?? "local-session",
          chat_history: [...messages, userMsg],
          response: text
        })
      });

      if (response.ok) {
        const data = await response.json();
        const sysTimestamp = `${new Date().getHours().toString().padStart(2, "0")}:${new Date().getMinutes().toString().padStart(2, "0")}`;
        setMessages(prev => [...prev, { sender: "SYSTEM", timestamp: sysTimestamp, text: data.reply }]);
        addTerminalLog("INFO", `Received AI response.`);
        return;
      }
      throw new Error("Backend failed, triggering chat simulation...");
    } catch (e) {
      console.log(e);
      // Fallback conversation simulation responses
      const fallbacks = [
        "That's an excellent technical strategy. Let's delve into load balancing techniques. How would you distribute traffic across multiple regional clusters in a low-latency requirement?",
        "Solid geospatial approach using Redis. When managing Redis cluster Failovers, what partition tolerances or replication methods would you implement to secure highly concurrent nodes?",
        "Very interesting insights. To summarize, your architecture ensures decoupling via Kinesis stream brokers and memory indexing at the service layer. What metrics would you track in your monitoring logs?"
      ];

      const randomReply = fallbacks[Math.min(messages.length % fallbacks.length, fallbacks.length - 1)];
      const sysTimestamp = `${new Date().getHours().toString().padStart(2, "0")}:${new Date().getMinutes().toString().padStart(2, "0")}`;
      setMessages(prev => [...prev, { sender: "SYSTEM", timestamp: sysTimestamp, text: randomReply }]);
      addTerminalLog("INFO", `Parsed AI response simulation.`);
    }
  };

  const resetInterview = () => {
    setMessages([
      { sender: "SYSTEM", timestamp: "14:02:11", text: "Let's pivot to system design. Imagine we are building a ride-sharing application. How would you design the backend architecture to handle high-frequency driver location updates while ensuring low latency for riders matching?" }
    ]);
    setSessionId(null);
    addTerminalLog("INFO", `Interview playground environment reinitialized.`);
  };

  return (
    <ProjectContext.Provider
      value={{
        resumeData,
        jobDescription,
        matchScore,
        atsMatchDetail,
        isAnalyzing,
        messages,
        sessionId,
        upcomingEngagement,
        terminalLogs,
        setJobDescription,
        setMatchScore,
        setResumeData,
        setSessionId,
        uploadResume,
        triggerAnalyze,
        sendInterviewMessage,
        startInterviewSession,
        resetInterview,
        toggleSkillGap,
        addTerminalLog
      }}
    >
      {children}
    </ProjectContext.Provider>
  );
};

export const useProject = () => {
  const context = useContext(ProjectContext);
  if (context === undefined) {
    throw new Error("useProject must be used within a ProjectProvider");
  }
  return context;
};
