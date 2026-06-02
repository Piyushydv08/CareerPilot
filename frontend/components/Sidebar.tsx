"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { 
  LayoutDashboard, 
  Cpu, 
  BrainCircuit, 
  MessageSquareCode, 
  SendHorizontal, 
  Settings, 
  HelpCircle,
  Sparkles,
  Compass
} from "lucide-react";

export const Sidebar: React.FC = () => {
  const pathname = usePathname();

  const navItems = [
    { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
    { name: "Engine", href: "/analyze", icon: Cpu },
    { name: "Simulator", href: "/simulator", icon: BrainCircuit },
    { name: "Interview", href: "/interview", icon: MessageSquareCode },
    { name: "Outreach", href: "/outreach", icon: SendHorizontal },
  ];

  return (
    <nav className="fixed left-0 top-0 z-50 flex h-screen w-64 flex-col border-r border-outline-variant bg-surface-dim p-6 transition-all duration-300">
      {/* Brand logo */}
      <div className="mb-10 flex items-center gap-3 px-2">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-cyber-blue/30 bg-cyber-blue/10 text-cyber-blue shadow-[0_0_15px_rgba(0,210,255,0.2)] animate-pulse">
          <Compass className="h-6 w-6" />
        </div>
        <div>
          <h1 className="font-sans text-xl font-bold tracking-tight text-white">
            Career<span className="text-cyber-blue font-mono glow-text">Pilot</span>
          </h1>
          <span className="font-mono text-[10px] text-on-surface-variant tracking-widest block uppercase">AI Co-Pilot v2.4.0</span>
        </div>
      </div>

      {/* Navigation links */}
      <div className="flex-1 space-y-1">
        {navItems.map((item) => {
          const isActive = pathname.startsWith(item.href);
          const Icon = item.icon;
          return (
            <Link
              key={item.name}
              href={item.href}
              className={`group flex items-center gap-3 rounded-md px-3 py-2.5 font-mono text-xs uppercase tracking-wider transition-all duration-200 ${
                isActive
                  ? "bg-cyber-blue/10 text-cyber-blue border-r-2 border-cyber-blue shadow-[inset_0_0_10px_rgba(0,210,255,0.05)] font-bold scale-[0.98]"
                  : "text-on-surface-variant hover:bg-surface-container hover:text-white"
              }`}
            >
              <Icon className={`h-4.5 w-4.5 transition-transform duration-300 group-hover:scale-110 ${
                isActive ? "text-cyber-blue" : "text-on-surface-variant group-hover:text-cyber-blue"
              }`} />
              <span>{item.name}</span>
            </Link>
          );
        })}
      </div>

      {/* CTA Pro Upgrade Card */}
      <div className="mb-6 rounded-lg border border-outline-variant/60 bg-surface-container-low p-4 relative overflow-hidden group hover:border-cyber-blue/40 transition-all duration-300">
        <div className="absolute top-0 right-0 p-2 opacity-5 group-hover:opacity-10 text-cyber-blue">
          <Sparkles className="h-10 w-10 animate-breathe" />
        </div>
        <h4 className="text-[11px] font-mono text-white uppercase tracking-wider mb-1 font-semibold">Elevate Your Flight</h4>
        <p className="text-[10px] text-on-surface-variant leading-relaxed mb-3">Gain full analytics, unlimited AI mocks & live outbound sequence triggers.</p>
        <button className="w-full rounded bg-white py-1.5 font-mono text-[10px] font-bold text-black uppercase tracking-wider hover:bg-cyber-blue hover:text-black hover:shadow-[0_0_10px_rgba(0,210,255,0.5)] transition-all duration-200">
          Upgrade to Pro
        </button>
      </div>

      {/* Footer Nav */}
      <div className="space-y-1 border-t border-outline-variant/50 pt-4">
        <Link
          href="/settings"
          className="flex items-center gap-3 rounded-md px-3 py-2 font-mono text-[11px] text-on-surface-variant transition-all hover:bg-surface-container hover:text-white"
        >
          <Settings className="h-4 w-4" />
          <span>Settings</span>
        </Link>
        <Link
          href="/support"
          className="flex items-center gap-3 rounded-md px-3 py-2 font-mono text-[11px] text-on-surface-variant transition-all hover:bg-surface-container hover:text-white"
        >
          <HelpCircle className="h-4 w-4" />
          <span>Support</span>
        </Link>
      </div>
    </nav>
  );
};
export default Sidebar;
