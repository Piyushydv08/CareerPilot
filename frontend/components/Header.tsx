"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { 
  Bell, 
  User, 
  Activity, 
  Terminal,
  Search,
  CheckCircle2,
  FileCode,
  Briefcase
} from "lucide-react";
import { useProject } from "../app/context/ProjectContext";

export const Header: React.FC = () => {
  const pathname = usePathname();
  const { matchScore } = useProject();
  const [searchQuery, setSearchQuery] = useState("");

  // Map route path to professional telemetry titles
  const getTelemetryTitle = () => {
    if (pathname.startsWith("/dashboard")) return "/mission_control_active";
    if (pathname.startsWith("/analyze")) return "/resume_telemetry_engine";
    if (pathname.startsWith("/simulator")) return "/predictive_skill_gap_sim";
    if (pathname.startsWith("/interview")) return "/realtime_ai_interview_channel_049";
    if (pathname.startsWith("/outreach")) return "/campaign_outreach_trigger";
    return "/careerpilot_sys";
  };

  return (
    <header className="fixed top-0 right-0 z-40 flex h-16 w-[calc(100%-16rem)] items-center justify-between border-b border-outline-variant bg-surface-dim/80 px-8 backdrop-blur-md">
      {/* Telemetry Channel Label */}
      <div className="flex items-center gap-3">
        <div className="flex h-6 items-center gap-1.5 rounded border border-[#00d2ff]/20 bg-[#00d2ff]/5 px-2.5 py-0.5 text-[10px] font-mono text-cyber-blue shadow-[0_0_8px_rgba(0,210,255,0.1)]">
          <Activity className="h-3.5 w-3.5 animate-pulse" />
          <span>LIVE CHANNEL</span>
        </div>
        <span className="font-mono text-[11px] text-on-surface-variant tracking-wider">
          {getTelemetryTitle()}
        </span>
      </div>

      {/* Global Actions */}
      <div className="flex items-center gap-6">
        {/* Analyze Resume Quick Route */}
        <Link 
          href="/analyze"
          className="flex items-center gap-1.5 rounded border border-cyber-blue/30 bg-cyber-blue/5 px-3 py-1 font-mono text-[10px] font-bold uppercase tracking-wider text-cyber-blue hover:bg-cyber-blue hover:text-black hover:shadow-[0_0_10px_rgba(0,210,255,0.4)] transition-all duration-200"
        >
          <FileCode className="h-3.5 w-3.5" />
          <span>Analyze Resume</span>
        </Link>

        {/* Jobs Quick Route */}
        <Link 
          href="/outreach"
          className="flex items-center gap-1.5 rounded border border-outline-variant bg-surface-container px-3 py-1 font-mono text-[10px] uppercase tracking-wider text-on-surface hover:border-cyber-blue/40 hover:text-cyber-blue transition-all duration-200"
        >
          <Briefcase className="h-3.5 w-3.5" />
          <span>Outbound Req</span>
        </Link>

        {/* Separator */}
        <div className="h-5 w-px bg-outline-variant"></div>

        {/* Notification Alert Bell */}
        <button className="relative text-on-surface-variant hover:text-cyber-blue transition-colors focus:outline-none">
          <Bell className="h-4.5 w-4.5" />
          <span className="absolute -top-0.5 -right-0.5 h-2 w-2 rounded-full bg-cyber-blue shadow-[0_0_6px_rgba(0,210,255,0.8)] animate-pulse"></span>
        </button>

        {/* User Account Portal */}
        <div className="flex items-center gap-2 border-l border-outline-variant/60 pl-4">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-outline-variant bg-surface-container-high text-on-surface-variant hover:border-cyber-blue/40 hover:text-cyber-blue transition-colors cursor-pointer">
            <User className="h-4.5 w-4.5" />
          </div>
          <div className="hidden xl:block text-left">
            <div className="font-mono text-[11px] font-medium leading-none text-white">piyus_01</div>
            <span className="font-mono text-[9px] text-[#00d2ff]/80">ATS Score: {matchScore}%</span>
          </div>
        </div>
      </div>
    </header>
  );
};
export default Header;
