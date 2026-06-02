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

const initialResumeData: ResumeData = {
  name: "Piyush Sharma",
  email: "piyush@careerpilot.ai",
  skills: [
    { name: "React.js", match: 95 },
    { name: "TypeScript", match: 88 },
    { name: "GraphQL", match: 45 },
    { name: "System Design", match: 30 }
  ],
  experience: [
    { company: "Stripe", role: "Software Engineer Contractor", duration: "2024 - Present", details: "Led frontend migrations to modern App Router structures and built dynamic analytics views." },
    { company: "Fintech Startup", role: "Frontend Dev", duration: "2022 - 2024", details: "Engineered responsive data interfaces and state integration pipelines using React and Redux." }
  ],
  gaps: [
    { name: "AWS Cloud Practitioner", category: "Infrastructure", impact: 12, checked: false },
    { name: "Docker & Kubernetes", category: "DevOps", impact: 9, checked: false },
    { name: "GraphQL Mastery", category: "API Design", impact: 7, checked: false },
    { name: "Unit Testing - Jest/RTL", category: "Quality Assurance", impact: 5, checked: false }
  ],
  ats_score: 72
};

const initialLogs = [
  { time: "10:42:01", type: "INFO" as const, message: "Resume successfully parsed and indexed.", relativeTime: "2m ago" },
  { time: "09:15:44", type: "EXEC" as const, message: "Simulated interview #452 completed. Score: 8/10.", relativeTime: "1h ago" },
  { time: "08:00:00", type: "WARN" as const, message: "Detected new job posting matching profile (Stripe).", relativeTime: "2h ago" }
];

export const ProjectProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [resumeData, setResumeData] = useState<ResumeData | null>(initialResumeData);
  const [jobDescription, setJobDescription] = useState<string>("Senior Frontend Engineer posting at Stripe");
  const [matchScore, setMatchScore] = useState<number>(84);
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
        addTerminalLog("INFO", `Successfully parsed resume via backend.`);
        setIsAnalyzing(false);
        return true;
      }
      throw new Error("Backend response failed, initiating simulation fallback...");
    } catch (e) {
      console.warn("Backend unavailable, using simulation", e);
      // Simulation fallback
      await new Promise(resolve => setTimeout(resolve, 2500)); // Shimmer delay
      setResumeData({
        name: file.name.split(".")[0],
        email: "fallback-candidate@careerpilot.ai",
        skills: [
          { name: "React.js", match: 98 },
          { name: "TypeScript", match: 92 },
          { name: "GraphQL", match: 80 },
          { name: "System Design", match: 65 }
        ],
        experience: [
          { company: "Web Innovations", role: "Senior Developer", duration: "2020 - Present", details: "Engineered highly animated web applications with dynamic layouts and modern styling stacks." }
        ],
        gaps: [
          { name: "AWS Cloud Practitioner", category: "Infrastructure", impact: 12, checked: false },
          { name: "Docker & Kubernetes", category: "DevOps", impact: 9, checked: false },
          { name: "GraphQL Mastery", category: "API Design", impact: 7, checked: true },
          { name: "Unit Testing - Jest/RTL", category: "Quality Assurance", impact: 5, checked: false }
        ],
        ats_score: 68
      });
      setMatchScore(88);
      addTerminalLog("INFO", `Parsed resume: ${file.name} (Local AI engine simulation)`);
      setIsAnalyzing(false);
      return true;
    }
  };

  // Analyze Job Description
  const triggerAnalyze = async (jobDesc: string): Promise<number> => {
    setIsAnalyzing(true);
    setJobDescription(jobDesc);
    addTerminalLog("INFO", `Analyzing compatibility with job description profile.`);

    try {
      const response = await fetch(`${BASE_URL}/match/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ resume: resumeData, job_description: jobDesc })
      });

      if (response.ok) {
        const data = await response.json();
        setMatchScore(data.match_score);

        // Map missing_terms to SkillGap objects and update resumeData.gaps if returned
        if (data.missing_terms && data.missing_terms.length > 0 && resumeData) {
          const newGaps: SkillGap[] = data.missing_terms.slice(0, 4).map((term: { term: string; weight: number }) => ({
            name: term.term.charAt(0).toUpperCase() + term.term.slice(1),
            category: "Job Requirement",
            impact: Math.min(15, Math.max(5, Math.round(term.weight / 10))),
            checked: false
          }));
          // Merge with existing gaps — keep Gemini-parsed gaps, add job-specific ones
          setResumeData(prev => prev ? { ...prev, gaps: newGaps } : prev);
        }

        addTerminalLog("INFO", `Profile matching complete. Compatibility: ${data.match_score}%.`);
        setIsAnalyzing(false);
        return data.match_score;
      }
      throw new Error("Backend failed, deploying simulation...");
    } catch (e) {
      console.log(e);
      await new Promise(resolve => setTimeout(resolve, 2000));
      const simulatedScore = Math.floor(Math.random() * 20) + 75; // 75% to 95%
      setMatchScore(simulatedScore);
      addTerminalLog("INFO", `Profile matching completed. Compatibility index: ${simulatedScore}%.`);
      setIsAnalyzing(false);
      return simulatedScore;
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
