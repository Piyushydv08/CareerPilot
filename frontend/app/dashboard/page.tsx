"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { 
  Radar, 
  CalendarClock, 
  Video, 
  MoreHorizontal, 
  TrendingUp, 
  Terminal as TerminalIcon, 
  ExternalLink,
  ChevronRight,
  Sparkles,
  Zap,
  BarChart2
} from "lucide-react";
import { 
  BarChart, 
  Bar, 
  XAxis, 
  Tooltip, 
  ResponsiveContainer,
  Cell
} from "recharts";
import { useProject } from "../context/ProjectContext";

// Simple simulated data for Market Volatility
const chartData = [
  { day: "Mon", volatility: 40, active: false },
  { day: "Tue", volatility: 35, active: false },
  { day: "Wed", volatility: 60, active: false },
  { day: "Thu", volatility: 55, active: false },
  { day: "Fri", volatility: 85, active: true },
  { day: "Sat", volatility: 70, active: false }
];

export default function Dashboard() {
  const { matchScore, upcomingEngagement, terminalLogs, resumeData } = useProject();
  const [mounted, setMounted] = useState(false);

  // Avoid SSR hydration warning for dynamic values/charts
  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return (
      <div className="flex min-h-[80vh] items-center justify-center">
        <div className="h-10 w-10 animate-spin rounded-full border-2 border-t-cyber-blue border-r-transparent"></div>
      </div>
    );
  }

  // Format countdown string
  const formatNum = (n: number) => n.toString().padStart(2, "0");

  return (
    <div className="mx-auto max-w-[1280px] p-8 animate-fade-in">
      {/* Dashboard Telemetry Canvas Header */}
      <header className="mb-8 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-3xl font-bold tracking-tight text-white flex items-center gap-2">
            Mission Control <span className="h-2 w-2 rounded-full bg-cyber-blue shadow-[0_0_8px_rgba(0,210,255,0.8)] animate-pulse"></span>
          </h2>
          <p className="text-sm text-on-surface-variant mt-1 font-mono">System telemetry operational. Target profile matching online.</p>
        </div>
        <div className="flex h-9 items-center gap-2 border border-outline-variant bg-[#0c0c10] px-3 py-1 font-mono text-[10px] uppercase text-[#00d2ff]">
          <TerminalIcon className="h-3.5 w-3.5" />
          <span>STATUS: NOMINAL</span>
        </div>
      </header>

      {/* Bento Grid */}
      <div className="grid grid-cols-1 gap-6 md:grid-cols-12">
        {/* Match Score (Hero Bento Panel) */}
        <div className="bento-card col-span-1 flex flex-col justify-between overflow-hidden rounded-lg p-6 md:col-span-4 relative group">
          {/* Subtle glow border */}
          <div className="absolute inset-0 bg-cyber-blue/[0.02] group-hover:bg-cyber-blue/[0.04] transition-all duration-300 pointer-events-none"></div>
          
          <div className="flex justify-between items-start mb-8 relative z-10">
            <h3 className="font-mono text-[10px] uppercase tracking-wider text-on-surface-variant font-semibold">Target ATS Score</h3>
            <Radar className="h-5 w-5 text-cyber-blue glow-text animate-breathe" />
          </div>

          <div className="relative z-10">
            <div className="flex items-baseline gap-1">
              <span className="font-mono text-6xl font-bold text-cyber-blue glow-text tracking-tighter">
                {matchScore}
              </span>
              <span className="text-2xl font-mono text-on-surface-variant font-bold">%</span>
            </div>
            <p className="font-mono text-[11px] text-on-surface-variant mt-2 tracking-wide uppercase">
              Target: Sr. Frontend Engineer
            </p>
          </div>

          {/* Mini dynamic animated bar */}
          <div className="w-full h-1.5 bg-surface-container-high mt-6 rounded-full overflow-hidden relative z-10 border border-outline-variant/30">
            <div 
              className="h-full bg-gradient-to-r from-cyber-indigo to-cyber-blue rounded-full transition-all duration-1000 shadow-[0_0_10px_rgba(0,210,255,0.8)]"
              style={{ width: `${matchScore}%` }}
            ></div>
          </div>
        </div>

        {/* Countdown Engagement Panel (Bento spans 8 cols) */}
        <div className="bento-card col-span-1 rounded-lg p-6 md:col-span-8 flex flex-col justify-between group">
          <div className="flex justify-between items-start mb-6">
            <h3 className="font-mono text-[10px] uppercase tracking-wider text-on-surface-variant font-semibold">Upcoming Engagement</h3>
            <CalendarClock className="h-5 w-5 text-on-surface-variant group-hover:text-cyber-blue transition-colors" />
          </div>

          <div className="flex flex-col sm:flex-row items-center gap-6">
            {/* Clock blocks */}
            <div className="flex gap-2">
              <div className="flex flex-col items-center bg-surface-container-low p-3.5 rounded border border-outline-variant/60 min-w-[70px] hover:border-cyber-blue/40 transition-colors shadow-sm">
                <span className="font-mono text-3xl font-bold text-white leading-none">
                  {formatNum(upcomingEngagement.days)}
                </span>
                <span className="font-mono text-[9px] text-on-surface-variant mt-2.5 uppercase tracking-wider">DAYS</span>
              </div>
              <div className="flex flex-col items-center bg-surface-container-low p-3.5 rounded border border-outline-variant/60 min-w-[70px] hover:border-cyber-blue/40 transition-colors shadow-sm">
                <span className="font-mono text-3xl font-bold text-white leading-none">
                  {formatNum(upcomingEngagement.hours)}
                </span>
                <span className="font-mono text-[9px] text-on-surface-variant mt-2.5 uppercase tracking-wider">HRS</span>
              </div>
              <div className="flex flex-col items-center bg-surface-container-low p-3.5 rounded border border-outline-variant/60 min-w-[70px] hover:border-cyber-blue/40 transition-colors shadow-sm">
                <span className="font-mono text-3xl font-bold text-cyber-blue glow-text leading-none animate-pulse">
                  {formatNum(upcomingEngagement.minutes)}
                </span>
                <span className="font-mono text-[9px] text-cyber-blue mt-2.5 uppercase tracking-wider font-semibold">MIN</span>
              </div>
            </div>

            {/* Info details */}
            <div className="flex-1 border-t sm:border-t-0 sm:border-l border-outline-variant/60 pt-4 sm:pt-0 sm:pl-6 text-left w-full">
              <span className="rounded bg-cyber-indigo/10 border border-cyber-indigo/20 px-2 py-0.5 text-[9px] font-mono text-cyber-indigo uppercase tracking-wider">
                {upcomingEngagement.type}
              </span>
              <h4 className="font-sans text-xl font-bold text-white mt-2 leading-tight">
                Interview Panel at {upcomingEngagement.company}
              </h4>
              <p className="font-mono text-xs text-on-surface-variant flex items-center gap-1.5 mt-2">
                <Video className="h-4 w-4 text-cyber-blue" />
                <span>Google Meet video call</span>
              </p>
              <Link 
                href="/simulator" 
                className="mt-4 inline-flex items-center gap-1.5 font-mono text-[10px] font-bold uppercase tracking-wider text-cyber-blue hover:underline hover:glow-text group"
              >
                <span>Prepare in Simulator</span>
                <ChevronRight className="h-3 w-3 transition-transform group-hover:translate-x-1" />
              </Link>
            </div>
          </div>
        </div>

        {/* Skill Gap Matrix (Bento 6 cols) */}
        <div className="bento-card col-span-1 rounded-lg p-6 md:col-span-6">
          <div className="flex justify-between items-start mb-6">
            <h3 className="font-mono text-[10px] uppercase tracking-wider text-on-surface-variant font-semibold">Skill Gap Matrix</h3>
            <button className="text-on-surface-variant hover:text-cyber-blue transition-colors">
              <MoreHorizontal className="h-5 w-5" />
            </button>
          </div>

          <div className="space-y-4">
            {resumeData?.skills.map((skill) => {
              const isWarning = skill.match <= 40;
              return (
                <div key={skill.name} className="flex items-center justify-between font-mono text-xs group">
                  <span className="text-white w-1/3 flex items-center gap-1.5 text-left font-medium">
                    {skill.name}
                    {isWarning && (
                      <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse inline-block"></span>
                    )}
                  </span>
                  
                  <div className="flex-grow mx-4 flex items-center gap-3.5">
                    <div className="w-full h-1.5 bg-surface-container-high rounded-full overflow-hidden border border-outline-variant/30 relative">
                      <div 
                        className={`h-full rounded-full transition-all duration-1000 ${
                          isWarning 
                            ? "bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.6)]" 
                            : "bg-cyber-blue shadow-[0_0_8px_rgba(0,210,255,0.6)] group-hover:bg-gradient-to-r group-hover:from-cyber-indigo group-hover:to-cyber-blue"
                        }`}
                        style={{ width: `${skill.match}%` }}
                      ></div>
                    </div>
                    <span className={`w-8 text-right font-bold ${isWarning ? "text-red-400" : "text-cyber-blue"}`}>
                      {skill.match}%
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Volatility Index Chart (Bento 6 cols) */}
        <div className="bento-card col-span-1 rounded-lg p-6 md:col-span-6 flex flex-col justify-between group">
          <div className="flex justify-between items-start mb-6">
            <h3 className="font-mono text-[10px] uppercase tracking-wider text-on-surface-variant font-semibold">Market Volatility Index</h3>
            <TrendingUp className="h-5 w-5 text-on-surface-variant group-hover:text-cyber-blue transition-colors" />
          </div>

          {/* Recharts container */}
          <div className="h-32 w-full mt-2 relative">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 10, right: 0, left: 0, bottom: 0 }}>
                <XAxis 
                  dataKey="day" 
                  axisLine={false} 
                  tickLine={false} 
                  tick={{ fill: "#a0a0b0", fontSize: 10, fontFamily: "JetBrains Mono" }} 
                />
                <Tooltip 
                  cursor={{ fill: "rgba(255,255,255,0.02)" }}
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      return (
                        <div className="rounded border border-outline-variant bg-[#0c0c10] p-2 font-mono text-[10px] text-white shadow-lg">
                          <div>Day Volatility</div>
                          <span className="font-bold text-cyber-blue">{payload[0].value}% Index</span>
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                <Bar dataKey="volatility" radius={[2, 2, 0, 0]}>
                  {chartData.map((entry, index) => (
                    <Cell 
                      key={`cell-${index}`} 
                      fill={entry.active ? "#00d2ff" : "#1a1a24"}
                      className="transition-all duration-300 cursor-pointer"
                      style={{
                        filter: entry.active ? "drop-shadow(0 0 5px rgba(0,210,255,0.5))" : "none"
                      }}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Activity Log Terminal (Bento Spans 12 columns) */}
        <div className="bento-card col-span-1 rounded-lg overflow-hidden md:col-span-12 relative">
          <div className="p-4 border-b border-outline-variant bg-surface-container-low/70 flex justify-between items-center">
            <div className="flex items-center gap-2 font-mono text-[10px] text-on-surface-variant uppercase font-semibold">
              <TerminalIcon className="h-4 w-4 text-cyber-blue" />
              <span>Telemetry Logs</span>
            </div>
            <span className="font-mono text-[10px] text-cyber-blue/80 font-bold terminal-cursor">
              tail -f activity.log
            </span>
          </div>

          <div className="p-4 font-mono text-[11px] text-on-surface-variant flex flex-col gap-2 bg-[#060608] h-48 overflow-y-auto">
            {terminalLogs.map((log, index) => {
              let labelClass = "text-cyber-blue bg-cyber-blue/5 border border-cyber-blue/10";
              if (log.type === "EXEC") labelClass = "text-cyber-indigo bg-cyber-indigo/5 border border-cyber-indigo/10";
              if (log.type === "WARN") labelClass = "text-red-500 bg-red-500/5 border border-red-500/10";
              
              return (
                <div 
                  key={index}
                  className="flex items-start gap-4 hover:bg-surface-container-low px-2 py-1 rounded transition-colors group animate-fade-slide-up"
                  style={{ animationDelay: `${index * 80}ms` }}
                >
                  <span className="text-cyber-blue/60 font-semibold shrink-0">[{log.time}]</span>
                  <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold shrink-0 leading-none ${labelClass}`}>
                    {log.type}
                  </span>
                  <span className="text-on-surface/90 flex-grow text-left leading-relaxed">{log.message}</span>
                  <span className="text-[10px] text-on-surface-variant/40 shrink-0 select-none group-hover:text-cyber-blue/50">
                    {log.relativeTime}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
