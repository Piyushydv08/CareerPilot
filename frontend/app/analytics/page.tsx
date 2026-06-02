"use client";

import React, { useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ComposedChart,
  Legend
} from "recharts";
import {
  BarChart2,
  Search,
  Loader,
  AlertTriangle,
  Briefcase,
  DollarSign,
  Globe,
  AlertCircle
} from "lucide-react";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

interface AnalyticsData {
  total_live_jobs: number;
  avg_salary: number;
  top_sector: string;
  top_sector_reqs: string;
  skills_demand: Array<{ name: string; demand_count: string; percentage: number }>;
  work_model_ratio: { Remote: number; Hybrid: number; Onsite: number };
  salaries: Array<{ domain: string; median: number; percentile90: number }>;
  is_mock_data: boolean;
}

// Custom tooltip styles for Recharts
const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-[#0c0c14] border border-outline-variant rounded p-3 shadow-lg font-mono text-xs">
        <p className="text-cyber-blue font-bold mb-1">{label}</p>
        {payload.map((entry: any, i: number) => (
          <p key={i} style={{ color: entry.color }}>
            {entry.name}: {typeof entry.value === "number" && entry.value > 1000 
              ? `$${entry.value.toLocaleString()}` 
              : `${entry.value}%`}
          </p>
        ))}
      </div>
    );
  }
  return null;
};

export default function AnalyticsPage() {
  const [domain, setDomain] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<AnalyticsData | null>(null);

  const handleSearch = async () => {
    if (!domain.trim()) return;
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `${BASE_URL}/analytics/trends?domain=${encodeURIComponent(domain.trim())}`
      );

      if (response.ok) {
        const result: AnalyticsData = await response.json();
        setData(result);
      } else {
        setError(`Failed to fetch analytics: ${response.status}`);
      }
    } catch (e) {
      console.error("Analytics fetch failed:", e);
      setError("Could not reach the backend. Make sure the API server is running.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") handleSearch();
  };

  return (
    <div className="mx-auto max-w-[1280px] p-8 animate-fade-in text-left">
      {/* Header */}
      <header className="mb-8">
        <h2 className="text-3xl font-bold tracking-tight text-white flex items-center gap-2">
          Job Market Analytics <BarChart2 className="h-6 w-6 text-cyber-blue" />
        </h2>
        <p className="text-sm text-on-surface-variant mt-1 font-mono">
          Real-time market intelligence via Adzuna API. NLP-processed skills demand and salary distributions.
        </p>
      </header>

      {/* Search Bar */}
      <div className="bento-card rounded-lg p-6 mb-8">
        <div className="flex gap-3">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-on-surface-variant" />
            <input
              type="text"
              value={domain}
              onChange={e => setDomain(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Search domain, e.g. Full Stack Developer, Machine Learning Engineer..."
              className="w-full bg-[#07070a]/60 border border-outline-variant rounded pl-9 pr-4 py-3 text-white font-sans text-sm focus:outline-none focus:border-cyber-blue transition-colors"
            />
          </div>
          <button
            onClick={handleSearch}
            disabled={isLoading || !domain.trim()}
            className="px-6 py-3 rounded bg-cyber-blue text-black font-mono text-xs font-bold uppercase tracking-wider hover:bg-white hover:shadow-[0_0_15px_rgba(0,210,255,0.5)] transition-all duration-300 flex items-center gap-2 cursor-pointer disabled:opacity-50 shrink-0"
          >
            {isLoading ? (
              <><Loader className="h-4 w-4 animate-spin" /><span>Scanning...</span></>
            ) : (
              <><Search className="h-4 w-4" /><span>Analyze</span></>
            )}
          </button>
        </div>
      </div>

      {/* Error State */}
      {error && (
        <div className="bento-card rounded-lg p-6 mb-8 border-red-500/20 bg-red-500/5 flex items-center gap-3 text-red-400">
          <AlertTriangle className="h-5 w-5 shrink-0" />
          <p className="font-mono text-sm">{error}</p>
        </div>
      )}

      {/* Loading Skeleton */}
      {isLoading && (
        <div className="grid grid-cols-1 gap-8">
          {/* Stat cards skeleton */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[1, 2, 3].map(i => (
              <div key={i} className="bento-card rounded-lg p-6 animate-pulse">
                <div className="h-3 bg-surface-container-high rounded shimmer-bg w-1/3 mb-4"></div>
                <div className="h-10 bg-surface-container rounded shimmer-bg w-1/2 mb-2"></div>
                <div className="h-3 bg-surface-container rounded shimmer-bg w-2/3"></div>
              </div>
            ))}
          </div>
          {/* Chart skeletons */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <div className="bento-card rounded-lg p-6 animate-pulse">
              <div className="h-3 bg-surface-container-high rounded shimmer-bg w-1/3 mb-6"></div>
              <div className="h-64 bg-surface-container rounded shimmer-bg"></div>
            </div>
            <div className="bento-card rounded-lg p-6 animate-pulse">
              <div className="h-3 bg-surface-container-high rounded shimmer-bg w-1/3 mb-6"></div>
              <div className="h-64 bg-surface-container rounded shimmer-bg"></div>
            </div>
          </div>
        </div>
      )}

      {/* Results */}
      {data && !isLoading && (
        <div className="grid grid-cols-1 gap-8 animate-fade-in">

          {/* Mock data warning */}
          {data.is_mock_data && (
            <div className="flex items-center gap-3 p-4 rounded border border-amber-500/20 bg-amber-500/5 text-amber-400 font-mono text-xs">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>Showing simulated market data — Adzuna API credentials not configured or returned no results.</span>
            </div>
          )}

          {/* Stat Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Total Jobs */}
            <div className="bento-card rounded-lg p-6 relative overflow-hidden group hover:border-cyber-blue/40 transition-colors">
              <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 text-cyber-blue">
                <Briefcase className="h-12 w-12" />
              </div>
              <h3 className="font-mono text-[10px] text-on-surface-variant uppercase tracking-widest mb-3 font-semibold">
                Live Job Listings
              </h3>
              <span className="font-mono text-4xl font-bold text-white tracking-tighter">
                {data.total_live_jobs.toLocaleString()}
              </span>
              <p className="font-mono text-[10px] text-on-surface-variant mt-2 uppercase tracking-wider">
                {data.top_sector} market
              </p>
            </div>

            {/* Avg Salary */}
            <div className="bento-card rounded-lg p-6 relative overflow-hidden group hover:border-cyber-blue/40 transition-colors">
              <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 text-cyber-blue">
                <DollarSign className="h-12 w-12" />
              </div>
              <h3 className="font-mono text-[10px] text-on-surface-variant uppercase tracking-widest mb-3 font-semibold">
                Average Salary
              </h3>
              <span className="font-mono text-4xl font-bold text-cyber-blue tracking-tighter glow-text">
                ${data.avg_salary.toLocaleString()}
              </span>
              <p className="font-mono text-[10px] text-on-surface-variant mt-2 uppercase tracking-wider">
                Top req: {data.top_sector_reqs}
              </p>
            </div>

            {/* Work Model */}
            <div className="bento-card rounded-lg p-6 relative overflow-hidden group hover:border-cyber-blue/40 transition-colors">
              <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 text-cyber-blue">
                <Globe className="h-12 w-12" />
              </div>
              <h3 className="font-mono text-[10px] text-on-surface-variant uppercase tracking-widest mb-3 font-semibold">
                Work Model Split
              </h3>
              <div className="space-y-2">
                {Object.entries(data.work_model_ratio).map(([key, val]) => (
                  <div key={key} className="flex items-center justify-between font-mono text-xs">
                    <span className="text-on-surface-variant">{key}</span>
                    <div className="flex items-center gap-2">
                      <div className="w-20 h-1.5 bg-surface-dim rounded overflow-hidden">
                        <div
                          className="h-full rounded"
                          style={{
                            width: `${val}%`,
                            backgroundColor: key === "Remote" ? "rgba(0,210,255,0.8)" : key === "Hybrid" ? "rgba(255,255,255,0.4)" : "rgba(100,100,120,0.5)"
                          }}
                        ></div>
                      </div>
                      <span className="text-white font-bold w-8 text-right">{val}%</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Skills Demand Bar Chart */}
            <div className="bento-card rounded-lg p-6">
              <h3 className="font-mono text-xs font-bold text-cyber-blue uppercase tracking-wider mb-6 flex items-center gap-1.5">
                <BarChart2 className="h-4 w-4" />
                <span>Skills Demand Index</span>
              </h3>
              <ResponsiveContainer width="100%" height={280}>
                <BarChart
                  data={data.skills_demand}
                  margin={{ top: 5, right: 5, left: -20, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                  <XAxis
                    dataKey="name"
                    tick={{ fill: "#9ca3af", fontSize: 10, fontFamily: "monospace" }}
                    axisLine={{ stroke: "rgba(255,255,255,0.1)" }}
                    tickLine={false}
                  />
                  <YAxis
                    tick={{ fill: "#9ca3af", fontSize: 10, fontFamily: "monospace" }}
                    axisLine={false}
                    tickLine={false}
                    unit="%"
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar
                    dataKey="percentage"
                    name="Demand %"
                    fill="rgba(0,210,255,0.8)"
                    radius={[2, 2, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Salary Distribution ComposedChart */}
            <div className="bento-card rounded-lg p-6">
              <h3 className="font-mono text-xs font-bold text-cyber-blue uppercase tracking-wider mb-6 flex items-center gap-1.5">
                <DollarSign className="h-4 w-4" />
                <span>Salary Distribution by Level</span>
              </h3>
              <ResponsiveContainer width="100%" height={280}>
                <ComposedChart
                  data={data.salaries}
                  margin={{ top: 5, right: 5, left: -10, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                  <XAxis
                    dataKey="domain"
                    tick={{ fill: "#9ca3af", fontSize: 10, fontFamily: "monospace" }}
                    axisLine={{ stroke: "rgba(255,255,255,0.1)" }}
                    tickLine={false}
                  />
                  <YAxis
                    tick={{ fill: "#9ca3af", fontSize: 10, fontFamily: "monospace" }}
                    axisLine={false}
                    tickLine={false}
                    tickFormatter={v => `$${(v / 1000).toFixed(0)}k`}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <Legend
                    wrapperStyle={{ fontFamily: "monospace", fontSize: "10px", color: "#9ca3af" }}
                  />
                  <Bar
                    dataKey="median"
                    name="Median"
                    fill="rgba(0,210,255,0.6)"
                    radius={[2, 2, 0, 0]}
                    barSize={28}
                  />
                  <Bar
                    dataKey="percentile90"
                    name="90th Pctile"
                    fill="rgba(255,255,255,0.3)"
                    radius={[2, 2, 0, 0]}
                    barSize={28}
                  />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}

      {/* Empty State (initial) */}
      {!data && !isLoading && !error && (
        <div className="bento-card rounded-lg p-16 flex flex-col items-center justify-center text-center text-on-surface-variant">
          <BarChart2 className="h-16 w-16 mb-4 opacity-20" />
          <p className="font-mono text-xs uppercase tracking-wider mb-2">
            No domain indexed yet
          </p>
          <p className="text-xs text-on-surface-variant/60 max-w-xs leading-relaxed">
            Enter a job domain above to analyze real-time market intelligence, skill demand trends, and salary distributions.
          </p>
        </div>
      )}
    </div>
  );
}
