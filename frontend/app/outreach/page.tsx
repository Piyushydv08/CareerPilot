"use client";

import React, { useState } from "react";
import { 
  SendHorizontal, 
  Sparkles, 
  Copy, 
  Check, 
  Mail, 
  ExternalLink, 
  Briefcase, 
  User, 
  ArrowRight,
  TrendingUp,
  RotateCcw,
  BadgeAlert,
  Loader
} from "lucide-react";
import { useProject } from "../context/ProjectContext";

interface OutreachContact {
  id: string;
  name: string;
  role: string;
  company: string;
  status: "DRAFTED" | "DISPATCHED" | "REPLIED" | "PENDING";
  lastActive: string;
}

export default function OutreachPage() {
  const { matchScore } = useProject();
  const [selectedTemplate, setSelectedTemplate] = useState("stripe_frontend");
  const [copied, setCopied] = useState(false);
  const [emailSubject, setEmailSubject] = useState("Sr. Frontend Engineer - Profile Telemetry Alignment");
  const [emailBody, setEmailBody] = useState(
    `Hi Recruiter,\n\nI recently synthesized my technical roadmap against Stripe's senior frontend engineering profile and indexed an 88% structural compatibility score.\n\nHaving built scalable microservices state engines in TypeScript and React at Stripe contractor teams previously, I'd love to connect regarding technical loops in Stripe regional networks.\n\nMy indexed report details are compiled here: careerpilot.ai/share/piyus_stripe\n\nBest,\nPiyush Sharma`
  );
  
  const [contacts, setContacts] = useState<OutreachContact[]>([
    { id: "c1", name: "Sarah Connor", role: "Principal Talent Executive", company: "Stripe", status: "PENDING", lastActive: "10m ago" },
    { id: "c2", name: "David Miller", role: "Engineering Lead", company: "Stripe", status: "DISPATCHED", lastActive: "1h ago" },
    { id: "c3", name: "Jessica Alba", role: "Lead Frontend Recruiter", company: "Netflix", status: "DRAFTED", lastActive: "4h ago" },
    { id: "c4", name: "Mark Zuckerberg", role: "Founder & Recruiter", company: "Meta", status: "REPLIED", lastActive: "2d ago" }
  ]);

  const [isSending, setIsSending] = useState(false);

  // Email Templates
  const templates = {
    stripe_frontend: {
      subject: "Sr. Frontend Engineer - Profile Telemetry Alignment",
      body: `Hi Recruiter,\n\nI recently synthesized my technical roadmap against Stripe's senior frontend engineering profile and indexed an 88% structural compatibility score.\n\nHaving built scalable microservices state engines in TypeScript and React at Stripe contractor teams previously, I'd love to connect regarding technical loops in Stripe regional networks.\n\nMy indexed report details are compiled here: careerpilot.ai/share/piyus_stripe\n\nBest,\nPiyush Sharma`
    },
    netflix_frontend: {
      subject: "UI Architect Opportunities - High Match Telemetry",
      body: `Hi Talent Team,\n\nMy profile has indexed a 92% compatibility score with Netflix's core UI Architecture specifications.\n\nWith extensive experience in React rendering pipelines, memoization performance audits, and high-contrast aesthetic designs, I am highly interested in contributing to Netflix streaming clients.\n\nFull assessment rubric shareable link: careerpilot.ai/share/piyus_netflix\n\nRegards,\nPiyush Sharma`
    },
    generic_tech: {
      subject: "Technical Engineering Profile Telemetry - Piyush Sharma",
      body: `Dear Engineering Lead,\n\nI am reaching out regarding Senior Frontend Engineer reqs. My profile has successfully parsed an overall match index of ${matchScore}% across modern TypeScript/React benchmarks.\n\nI would welcome the opportunity to outline my work in micro-interactions and high-performance frontend state structures.\n\nReview my AI assessment results here: careerpilot.ai/share/piyus\n\nSincerely,\nPiyush Sharma`
    }
  };

  const handleSelectTemplate = (key: keyof typeof templates) => {
    setSelectedTemplate(key);
    setEmailSubject(templates[key].subject);
    setEmailBody(templates[key].body);
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(`Subject: ${emailSubject}\n\n${emailBody}`);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDispatchOutreach = async (contactId: string) => {
    setIsSending(true);
    await new Promise(resolve => setTimeout(resolve, 1000));
    setContacts(prev => prev.map(c => {
      if (c.id === contactId) {
        return { ...c, status: "DISPATCHED", lastActive: "Just now" };
      }
      return c;
    }));
    setIsSending(false);
  };

  return (
    <div className="mx-auto max-w-[1280px] p-8 animate-fade-in text-left">
      {/* Page Header */}
      <header className="mb-8">
        <h2 className="text-3xl font-bold tracking-tight text-white flex items-center gap-2">
          Outbound Campaigns <SendHorizontal className="h-6 w-6 text-cyber-blue" />
        </h2>
        <p className="text-sm text-on-surface-variant mt-1 font-mono">
          Outreach dispatcher targeting recruiter portals. Dynamic compiler and sequence tracking nodes.
        </p>
      </header>

      {/* Grid Layout */}
      <div className="grid grid-cols-1 gap-8 lg:grid-cols-12">
        {/* Left Side: Sequence Builder (Spans 7 cols) */}
        <div className="lg:col-span-7 flex flex-col gap-6">
          <div className="bento-card rounded-lg p-6 flex flex-col gap-6">
            <div className="flex justify-between items-center border-b border-outline-variant/60 pb-4">
              <h3 className="font-mono text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
                <Sparkles className="h-4.5 w-4.5 text-cyber-blue animate-pulse" />
                <span>AI Sequence compiler</span>
              </h3>
              
              <div className="flex gap-2">
                <button 
                  onClick={() => handleSelectTemplate("stripe_frontend")}
                  className={`px-3 py-1 font-mono text-[9px] uppercase tracking-wider rounded border ${
                    selectedTemplate === "stripe_frontend" 
                      ? "border-cyber-blue bg-cyber-blue/10 text-cyber-blue" 
                      : "border-outline-variant text-on-surface-variant hover:text-white"
                  }`}
                >
                  Stripe
                </button>
                <button 
                  onClick={() => handleSelectTemplate("netflix_frontend")}
                  className={`px-3 py-1 font-mono text-[9px] uppercase tracking-wider rounded border ${
                    selectedTemplate === "netflix_frontend" 
                      ? "border-cyber-blue bg-cyber-blue/10 text-cyber-blue" 
                      : "border-outline-variant text-on-surface-variant hover:text-white"
                  }`}
                >
                  Netflix
                </button>
                <button 
                  onClick={() => handleSelectTemplate("generic_tech")}
                  className={`px-3 py-1 font-mono text-[9px] uppercase tracking-wider rounded border ${
                    selectedTemplate === "generic_tech" 
                      ? "border-cyber-blue bg-cyber-blue/10 text-cyber-blue" 
                      : "border-outline-variant text-on-surface-variant hover:text-white"
                  }`}
                >
                  AI Match
                </button>
              </div>
            </div>

            {/* Fields edit */}
            <div className="space-y-4 font-mono text-xs text-left">
              <div className="flex flex-col gap-2">
                <label className="text-on-surface-variant font-semibold">EMAIL SUBJECT LINE</label>
                <input 
                  type="text" 
                  value={emailSubject}
                  onChange={(e) => setEmailSubject(e.target.value)}
                  className="w-full bg-[#07070a]/60 border border-outline-variant rounded p-2.5 text-white focus:outline-none focus:border-cyber-blue transition-colors font-sans text-xs"
                />
              </div>

              <div className="flex flex-col gap-2">
                <label className="text-on-surface-variant font-semibold">EMAIL BODY COMPILER</label>
                <textarea 
                  value={emailBody}
                  onChange={(e) => setEmailBody(e.target.value)}
                  className="w-full bg-[#07070a]/60 border border-outline-variant rounded p-2.5 text-white focus:outline-none focus:border-cyber-blue transition-colors font-sans text-xs h-64 resize-none leading-relaxed"
                />
              </div>
            </div>

            {/* Action Bar */}
            <div className="border-t border-outline-variant/60 pt-4 flex justify-between items-center">
              <span className="font-mono text-[10px] text-on-surface-variant flex items-center gap-1.5">
                <BadgeAlert className="h-4 w-4 text-cyber-blue" />
                <span>Generated via CareerPilot AI Sequence</span>
              </span>

              <button 
                onClick={handleCopy}
                className="px-4 py-2 bg-white text-black hover:bg-cyber-blue hover:text-black font-mono text-xs font-bold uppercase tracking-wider rounded transition-all flex items-center gap-2 cursor-pointer hover:shadow-[0_0_10px_rgba(0,210,255,0.4)]"
              >
                {copied ? (
                  <>
                    <Check className="h-4.5 w-4.5" /> Copied!
                  </>
                ) : (
                  <>
                    <Copy className="h-4.5 w-4.5" /> Copy Sequence
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Right Side: Contact Roster list (Spans 5 cols) */}
        <div className="lg:col-span-5 flex flex-col gap-6">
          <div className="bento-card rounded-lg p-6 flex flex-col gap-6">
            <div className="border-b border-outline-variant/60 pb-4">
              <h3 className="font-mono text-xs font-bold text-white uppercase tracking-wider">
                Recruiter Target Roster
              </h3>
              <p className="text-xs text-on-surface-variant font-mono mt-1">
                Active recruiter nodes synchronized under Stripe pipeline.
              </p>
            </div>

            <div className="space-y-4">
              {contacts.map((contact) => {
                let statusBadge = "border-outline-variant text-on-surface-variant bg-surface-dim";
                if (contact.status === "DISPATCHED") statusBadge = "border-[#00d2ff]/20 bg-[#00d2ff]/5 text-cyber-blue";
                if (contact.status === "REPLIED") statusBadge = "border-green-500/20 bg-green-500/5 text-green-400";
                if (contact.status === "PENDING") statusBadge = "border-amber-500/20 bg-amber-500/5 text-amber-400";

                return (
                  <div 
                    key={contact.id} 
                    className="p-4 rounded border border-outline-variant/50 bg-[#07070a]/40 hover:border-cyber-blue/20 transition-all flex flex-col gap-3 group text-left"
                  >
                    <div className="flex justify-between items-start gap-2">
                      <div>
                        <h4 className="font-sans text-sm font-semibold text-white group-hover:text-cyber-blue transition-colors flex items-center gap-1">
                          <User className="h-3.5 w-3.5" />
                          <span>{contact.name}</span>
                        </h4>
                        <span className="font-mono text-[9px] text-on-surface-variant uppercase mt-1 block">
                          {contact.role} @ <strong className="text-white font-normal">{contact.company}</strong>
                        </span>
                      </div>
                      
                      <span className={`px-2 py-0.5 rounded text-[8px] font-mono border font-bold shrink-0 uppercase tracking-wider leading-none ${statusBadge}`}>
                        {contact.status}
                      </span>
                    </div>

                    <div className="flex justify-between items-center border-t border-outline-variant/35 pt-2.5 mt-1 font-mono text-[9px] text-on-surface-variant">
                      <span>Telemetry: {contact.lastActive}</span>
                      
                      {contact.status === "DRAFTED" || contact.status === "PENDING" ? (
                        <button 
                          onClick={() => handleDispatchOutreach(contact.id)}
                          disabled={isSending}
                          className="text-cyber-blue hover:underline hover:glow-text font-bold flex items-center gap-1 uppercase cursor-pointer disabled:opacity-50"
                        >
                          {isSending ? (
                            <Loader className="h-3 w-3 animate-spin" />
                          ) : (
                            <>
                              <span>Dispatch</span>
                              <ArrowRight className="h-3 w-3" />
                            </>
                          )}
                        </button>
                      ) : (
                        <span className="text-on-surface-variant/40 uppercase font-semibold flex items-center gap-1">
                          <Mail className="h-3 w-3 text-cyber-blue/60" /> Inbound active
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Inline statistics tracker */}
          <div className="bento-card rounded-lg p-6 flex flex-col gap-4 relative overflow-hidden group">
            <div className="absolute top-0 right-0 p-4 opacity-5 text-cyber-blue animate-pulse">
              <TrendingUp className="h-14 w-14" />
            </div>
            
            <h4 className="font-mono text-[10px] text-on-surface-variant uppercase tracking-widest leading-none font-semibold">
              Campaign Analytics
            </h4>
            
            <div className="grid grid-cols-2 gap-4 mt-2">
              <div className="text-left font-mono">
                <span className="text-2xl font-bold text-white leading-none">3</span>
                <span className="text-[9px] text-on-surface-variant block mt-1 uppercase tracking-wider">Dispatched Sequences</span>
              </div>
              <div className="text-left font-mono">
                <span className="text-2xl font-bold text-cyber-blue glow-text leading-none">33%</span>
                <span className="text-[9px] text-on-surface-variant block mt-1 uppercase tracking-wider">Recruiter Response Rate</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
