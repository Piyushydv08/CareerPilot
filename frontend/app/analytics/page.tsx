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
  Legend,
  AreaChart,
  Area
} from "recharts";
import {
  BarChart2,
  Search,
  Loader,
  AlertTriangle,
  Briefcase,
  DollarSign,
  Globe,
  AlertCircle,
  TrendingUp,
  Building2,
  MapPin,
  Tag,
  Sparkles,
  Calendar,
  ExternalLink,
  Filter,
  X,
  Clock
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
  salary_histogram: Array<{ range: string; count: number; low: number; high: number }>;
  historical_salaries: Array<{ month: string; salary: number }>;
  top_companies: Array<{ name: string; canonical_name: string; job_count: number; average_salary: number | null }>;
  regional_salaries: Array<{ location: string; job_count: number; salary: number }>;
  categories: Array<{ tag: string; label: string }>;
  jobsworth: {
    title: string;
    predicted_salary: number;
    predictions: Array<{ level: string; predicted_salary: number; confidence: number }>;
    description: string;
  } | null;
  is_mock_data: boolean;
}

interface Job {
  id: string;
  title: string;
  company: string;
  location: string;
  description: string;
  salary_min: number | null;
  salary_max: number | null;
  salary_is_predicted: boolean;
  contract_type: string;
  contract_time: string;
  redirect_url: string;
  created: string;
  category: string;
  company_url?: string;
}

const CustomTooltip = ({ active, payload, label, isSalary = false, currencySymbol = "$", locale = "en-US" }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-[#0c0c14] border border-outline-variant rounded p-3 shadow-lg font-mono text-xs">
        <p className="text-cyber-blue font-bold mb-1">{label}</p>
        {payload.map((entry: any, i: number) => (
          <p key={i} style={{ color: entry.color }}>
            {entry.name}: {isSalary || entry.name.includes("Salary") || entry.name.includes("Median")
              ? `${currencySymbol}${entry.value.toLocaleString(locale)}`
              : entry.name.includes("Count") || entry.name === "Jobs"
              ? `${entry.value.toLocaleString()} jobs`
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
  const [country, setCountry] = useState("in");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [activeTab, setActiveTab] = useState<"overview" | "salary" | "companies" | "regional" | "jobs">("overview");
  
  // Job listing states
  const [jobs, setJobs] = useState<Job[]>([]);
  const [jobsLoading, setJobsLoading] = useState(false);
  const [jobsError, setJobsError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalJobs, setTotalJobs] = useState(0);
  const [location, setLocation] = useState("");
  const [showFilters, setShowFilters] = useState(false);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [contractTypeFilter, setContractTypeFilter] = useState("");
  const [contractTimeFilter, setContractTimeFilter] = useState("");

  const currencySymbol = country === "in" ? "₹" : "$";
  const locale = country === "in" ? "en-IN" : "en-US";

  const handleSearch = async () => {
    if (!domain.trim()) return;
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `${BASE_URL}/analytics/trends?domain=${encodeURIComponent(domain.trim())}&country=${encodeURIComponent(country)}&include_historical=true&include_companies=true`
      );

      if (response.ok) {
        const result: AnalyticsData = await response.json();
        setData(result);
        setActiveTab("overview");
      } else {
        const errorData = await response.json().catch(() => ({}));
        setError(errorData.detail || `Failed to fetch analytics: ${response.status}`);
      }
    } catch (e) {
      console.error("Analytics fetch failed:", e);
      setError("Could not reach the backend. Make sure the API server is running.");
    } finally {
      setIsLoading(false);
    }
  };

  const searchJobs = async (page: number = 1) => {
    if (!domain.trim()) {
      setJobsError("Please enter a job title to search");
      return;
    }
    
    setJobsLoading(true);
    setJobsError(null);
    setSelectedJob(null);
    
    try {
      let url = `${BASE_URL}/analytics/jobs?domain=${encodeURIComponent(domain.trim())}&country=${encodeURIComponent(country)}&page=${page}&results_per_page=15`;
      
      if (location.trim()) {
        url += `&location=${encodeURIComponent(location.trim())}`;
      }
      
      const response = await fetch(url);
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Failed to fetch jobs: ${response.status}`);
      }
      
      const result = await response.json();
      setJobs(result.jobs || []);
      setTotalPages(result.total_pages || 0);
      setTotalJobs(result.total_count || 0);
      setCurrentPage(page);
      
      if (result.jobs && result.jobs.length === 0) {
        setJobsError("No jobs found for this search criteria. Try a different job title or location.");
      }
    } catch (e) {
      console.error("Jobs fetch failed:", e);
      setJobsError(e instanceof Error ? e.message : "Failed to fetch job listings");
    } finally {
      setJobsLoading(false);
    }
  };

  const handleJobsSearch = () => {
    setCurrentPage(1);
    searchJobs(1);
  };

  const formatSalary = (min: number | null, max: number | null, isPredicted: boolean) => {
    if (!min && !max) return "Salary not specified";
    if (min && max) return `${currencySymbol}${min.toLocaleString(locale)} - ${currencySymbol}${max.toLocaleString(locale)}`;
    if (min) return `From ${currencySymbol}${min.toLocaleString(locale)}`;
    if (max) return `Up to ${currencySymbol}${max.toLocaleString(locale)}`;
    return "Salary not specified";
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) return "Today";
    if (diffDays === 1) return "Yesterday";
    if (diffDays < 7) return `${diffDays} days ago`;
    if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
    return date.toLocaleDateString();
  };

  const openJobLink = (url: string) => {
    window.open(url, "_blank", "noopener,noreferrer");
  };

  const goToPage = (page: number) => {
    if (page >= 1 && page <= totalPages) {
      searchJobs(page);
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  };

  const clearFilters = () => {
    setLocation("");
    setContractTypeFilter("");
    setContractTimeFilter("");
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") handleSearch();
  };

  const handleJobsKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") handleJobsSearch();
  };

  const formatMonth = (month: string) => {
    const [year, monthNum] = month.split("-");
    return `${monthNum}/${year.slice(2)}`;
  };

  // Filter jobs client-side
  const filteredJobs = jobs.filter(job => {
    if (contractTypeFilter && job.contract_type !== contractTypeFilter) return false;
    if (contractTimeFilter && job.contract_time !== contractTimeFilter) return false;
    return true;
  });

  return (
    <div className="mx-auto max-w-[1400px] p-8 animate-fade-in text-left">
      {/* Header */}
      <header className="mb-8">
        <h2 className="text-3xl font-bold tracking-tight text-white flex items-center gap-2">
          Job Market Analytics <BarChart2 className="h-6 w-6 text-cyber-blue" />
        </h2>
        <p className="text-sm text-on-surface-variant mt-1 font-mono">
          Real-time market intelligence via Adzuna API. Search jobs, view analytics, and apply directly.
        </p>
      </header>

      {/* Search Bar */}
      <div className="bento-card rounded-lg p-6 mb-8">
        <div className="flex gap-3 flex-wrap">
          <div className="flex-1 min-w-[200px] relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-on-surface-variant" />
            <input
              type="text"
              value={domain}
              onChange={e => setDomain(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Search job title, e.g. Full Stack Developer, Data Scientist..."
              className="w-full bg-[#07070a]/60 border border-outline-variant rounded pl-9 pr-4 py-3 text-white font-sans text-sm focus:outline-none focus:border-cyber-blue transition-colors"
            />
          </div>
          <select
            value={country}
            onChange={e => setCountry(e.target.value)}
            className="bg-[#07070a]/60 border border-outline-variant rounded px-3 py-3 text-white font-sans text-sm focus:outline-none focus:border-cyber-blue transition-colors"
            aria-label="Country"
          >
            <option value="in">India (IN)</option>
            <option value="us">United States (US)</option>
            <option value="gb">United Kingdom (GB)</option>
            <option value="ca">Canada (CA)</option>
            <option value="au">Australia (AU)</option>
          </select>
          <button
            onClick={handleSearch}
            disabled={isLoading || !domain.trim()}
            className="px-6 py-3 rounded bg-cyber-blue text-black font-mono text-xs font-bold uppercase tracking-wider hover:bg-white hover:shadow-[0_0_15px_rgba(0,210,255,0.5)] transition-all duration-300 flex items-center gap-2 cursor-pointer disabled:opacity-50 shrink-0"
          >
            {isLoading ? (
              <><Loader className="h-4 w-4 animate-spin" /><span>Analyzing...</span></>
            ) : (
              <><BarChart2 className="h-4 w-4" /><span>Get Analytics</span></>
            )}
          </button>
        </div>
      </div>

      {/* Tab Navigation */}
      {data && !isLoading && (
        <div className="flex gap-2 border-b border-outline-variant pb-2 mb-6 overflow-x-auto">
          {[
            { id: "overview", label: "Market Overview", icon: BarChart2 },
            { id: "salary", label: "Salary Analysis", icon: DollarSign },
            { id: "companies", label: "Top Companies", icon: Building2 },
            { id: "regional", label: "Regional Data", icon: MapPin },
            { id: "jobs", label: "Job Listings", icon: Briefcase }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`px-4 py-2 rounded-t-lg font-mono text-xs flex items-center gap-2 transition-all whitespace-nowrap ${
                activeTab === tab.id
                  ? "text-cyber-blue border-b-2 border-cyber-blue bg-cyber-blue/5"
                  : "text-on-surface-variant hover:text-white"
              }`}
            >
              <tab.icon className="h-3.5 w-3.5" />
              {tab.label}
            </button>
          ))}
        </div>
      )}

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
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            {[1, 2, 3, 4].map(i => (
              <div key={i} className="bento-card rounded-lg p-6 animate-pulse">
                <div className="h-3 bg-surface-container-high rounded w-1/3 mb-4"></div>
                <div className="h-10 bg-surface-container rounded w-1/2 mb-2"></div>
                <div className="h-3 bg-surface-container rounded w-2/3"></div>
              </div>
            ))}
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <div className="bento-card rounded-lg p-6 animate-pulse">
              <div className="h-3 bg-surface-container-high rounded w-1/3 mb-6"></div>
              <div className="h-64 bg-surface-container rounded"></div>
            </div>
            <div className="bento-card rounded-lg p-6 animate-pulse">
              <div className="h-3 bg-surface-container-high rounded w-1/3 mb-6"></div>
              <div className="h-64 bg-surface-container rounded"></div>
            </div>
          </div>
        </div>
      )}

      {/* Analytics Results */}
      {data && !isLoading && activeTab !== "jobs" && (
        <div className="grid grid-cols-1 gap-8 animate-fade-in">
          {/* Stat Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="bento-card rounded-lg p-6 relative overflow-hidden group hover:border-cyber-blue/40 transition-colors">
              <Briefcase className="absolute top-4 right-4 h-5 w-5 opacity-20 group-hover:opacity-40" />
              <h3 className="font-mono text-[10px] text-on-surface-variant uppercase tracking-widest mb-3">Live Jobs</h3>
              <span className="font-mono text-3xl font-bold text-white">{data.total_live_jobs.toLocaleString()}</span>
              <p className="font-mono text-[10px] text-on-surface-variant mt-2">{data.top_sector} market</p>
            </div>

            <div className="bento-card rounded-lg p-6 relative overflow-hidden group hover:border-cyber-blue/40 transition-colors">
              <DollarSign className="absolute top-4 right-4 h-5 w-5 opacity-20 group-hover:opacity-40" />
              <h3 className="font-mono text-[10px] text-on-surface-variant uppercase tracking-widest mb-3">Avg Salary</h3>
              <span className="font-mono text-3xl font-bold text-cyber-blue glow-text">{currencySymbol}{data.avg_salary.toLocaleString(locale)}</span>
              <p className="font-mono text-[10px] text-on-surface-variant mt-2">Top req: {data.top_sector_reqs}</p>
            </div>

            <div className="bento-card rounded-lg p-6 relative overflow-hidden group hover:border-cyber-blue/40 transition-colors">
              <Globe className="absolute top-4 right-4 h-5 w-5 opacity-20 group-hover:opacity-40" />
              <h3 className="font-mono text-[10px] text-on-surface-variant uppercase tracking-widest mb-3">Remote Jobs</h3>
              <span className="font-mono text-3xl font-bold text-white">{data.work_model_ratio.Remote}%</span>
              <p className="font-mono text-[10px] text-on-surface-variant mt-2">of total listings</p>
            </div>

            <div className="bento-card rounded-lg p-6 relative overflow-hidden group hover:border-cyber-blue/40 transition-colors">
              <TrendingUp className="absolute top-4 right-4 h-5 w-5 opacity-20 group-hover:opacity-40" />
              <h3 className="font-mono text-[10px] text-on-surface-variant uppercase tracking-widest mb-3">Skills Tracked</h3>
              <span className="font-mono text-3xl font-bold text-white">{data.skills_demand.length}</span>
              <p className="font-mono text-[10px] text-on-surface-variant mt-2">top in-demand skills</p>
            </div>
          </div>

          {/* Work Model & Jobsworth */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div className="bento-card rounded-lg p-6 md:col-span-1">
              <h3 className="font-mono text-xs font-bold text-cyber-blue uppercase tracking-wider mb-4 flex items-center gap-2">
                <Globe className="h-4 w-4" />
                Work Model
              </h3>
              <div className="space-y-4">
                {Object.entries(data.work_model_ratio).map(([key, val]) => (
                  <div key={key}>
                    <div className="flex justify-between text-xs font-mono mb-1">
                      <span className="text-on-surface-variant">{key}</span>
                      <span className="text-white font-bold">{val}%</span>
                    </div>
                    <div className="w-full h-2 bg-surface-dim rounded overflow-hidden">
                      <div
                        className="h-full rounded transition-all duration-500"
                        style={{
                          width: `${val}%`,
                          backgroundColor: key === "Remote" ? "#00d2ff" : key === "Hybrid" ? "#00ff88" : "#ff6b6b"
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {data.jobsworth && (
              <div className="bento-card rounded-lg p-6 md:col-span-3">
                <h3 className="font-mono text-xs font-bold text-cyber-blue uppercase tracking-wider mb-4 flex items-center gap-2">
                  <Sparkles className="h-4 w-4" />
                  Jobsworth AI Prediction
                </h3>
                <p className="text-sm text-on-surface-variant mb-4">{data.jobsworth.description}</p>
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3">
                  {data.jobsworth.predictions.map((pred, idx) => (
                    <div key={idx} className="bg-surface-dim/30 rounded p-3 text-center">
                      <p className="text-xs text-on-surface-variant">{pred.level}</p>
                      <p className="text-sm font-bold text-cyber-blue">{currencySymbol}{pred.predicted_salary.toLocaleString(locale)}</p>
                      <p className="text-[10px] text-on-surface-variant">{pred.confidence}%</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Overview Tab Content */}
          {activeTab === "overview" && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              <div className="bento-card rounded-lg p-6">
                <h3 className="font-mono text-xs font-bold text-cyber-blue uppercase tracking-wider mb-6 flex items-center gap-2">
                  <BarChart2 className="h-4 w-4" />
                  Skills Demand Index
                </h3>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={data.skills_demand} margin={{ top: 5, right: 5, left: -20, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                    <XAxis dataKey="name" tick={{ fill: "#9ca3af", fontSize: 10, fontFamily: "monospace" }} axisLine={{ stroke: "rgba(255,255,255,0.1)" }} tickLine={false} />
                    <YAxis tick={{ fill: "#9ca3af", fontSize: 10, fontFamily: "monospace" }} axisLine={false} tickLine={false} unit="%" />
                    <Tooltip content={<CustomTooltip currencySymbol={currencySymbol} locale={locale} />} />
                    <Bar dataKey="percentage" name="Demand %" fill="#00d2ff" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <div className="bento-card rounded-lg p-6">
                <h3 className="font-mono text-xs font-bold text-cyber-blue uppercase tracking-wider mb-6 flex items-center gap-2">
                  <DollarSign className="h-4 w-4" />
                  Salary by Experience Level
                </h3>
                <ResponsiveContainer width="100%" height={300}>
                  <ComposedChart data={data.salaries} margin={{ top: 5, right: 5, left: -10, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                    <XAxis dataKey="domain" tick={{ fill: "#9ca3af", fontSize: 10, fontFamily: "monospace" }} axisLine={{ stroke: "rgba(255,255,255,0.1)" }} tickLine={false} />
                    <YAxis tick={{ fill: "#9ca3af", fontSize: 10, fontFamily: "monospace" }} axisLine={false} tickLine={false} tickFormatter={v => `${currencySymbol}${(v / 1000).toFixed(0)}k`} />
                    <Tooltip content={<CustomTooltip isSalary currencySymbol={currencySymbol} locale={locale} />} />
                    <Legend wrapperStyle={{ fontFamily: "monospace", fontSize: "10px" }} />
                    <Bar dataKey="median" name="Median Salary" fill="#00d2ff" radius={[4, 4, 0, 0]} barSize={40} />
                    <Bar dataKey="percentile90" name="90th Percentile" fill="#34d399" radius={[4, 4, 0, 0]} barSize={40} />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>

              {data.categories.length > 0 && (
                <div className="bento-card rounded-lg p-6 lg:col-span-2">
                  <h3 className="font-mono text-xs font-bold text-cyber-blue uppercase tracking-wider mb-6 flex items-center gap-2">
                    <Tag className="h-4 w-4" />
                    Related Categories
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {data.categories.slice(0, 12).map(cat => (
                      <span key={cat.tag} className="px-3 py-1.5 rounded-full bg-surface-dim/50 text-xs text-on-surface-variant font-mono hover:bg-cyber-blue/20 hover:text-cyber-blue transition-colors cursor-default">
                        {cat.label}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Salary Analysis Tab */}
          {activeTab === "salary" && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              <div className="bento-card rounded-lg p-6">
                <h3 className="font-mono text-xs font-bold text-cyber-blue uppercase tracking-wider mb-6 flex items-center gap-2">
                  <DollarSign className="h-4 w-4" />
                  Salary Distribution
                </h3>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={data.salary_histogram} margin={{ top: 5, right: 5, left: -20, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                    <XAxis dataKey="range" tick={{ fill: "#9ca3af", fontSize: 10, fontFamily: "monospace" }} axisLine={{ stroke: "rgba(255,255,255,0.1)" }} tickLine={false} angle={-15} textAnchor="end" height={60} />
                    <YAxis tick={{ fill: "#9ca3af", fontSize: 10, fontFamily: "monospace" }} axisLine={false} tickLine={false} />
                    <Tooltip content={<CustomTooltip currencySymbol={currencySymbol} locale={locale} />} />
                    <Bar dataKey="count" name="Number of Jobs" fill="#00d2ff" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <div className="bento-card rounded-lg p-6">
                <h3 className="font-mono text-xs font-bold text-cyber-blue uppercase tracking-wider mb-6 flex items-center gap-2">
                  <Calendar className="h-4 w-4" />
                  Historical Salary Trends
                </h3>
                <ResponsiveContainer width="100%" height={300}>
                  <AreaChart data={data.historical_salaries} margin={{ top: 5, right: 5, left: -10, bottom: 5 }}>
                    <defs>
                      <linearGradient id="salaryGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#00d2ff" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#00d2ff" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                    <XAxis dataKey="month" tick={{ fill: "#9ca3af", fontSize: 10, fontFamily: "monospace" }} tickFormatter={formatMonth} axisLine={{ stroke: "rgba(255,255,255,0.1)" }} tickLine={false} />
                    <YAxis tick={{ fill: "#9ca3af", fontSize: 10, fontFamily: "monospace" }} tickFormatter={v => `${currencySymbol}${(v / 1000).toFixed(0)}k`} axisLine={false} tickLine={false} />
                    <Tooltip content={<CustomTooltip isSalary currencySymbol={currencySymbol} locale={locale} />} />
                    <Area type="monotone" dataKey="salary" name="Avg Salary" stroke="#00d2ff" fill="url(#salaryGradient)" strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* Top Companies Tab */}
          {activeTab === "companies" && data.top_companies.length > 0 && (
            <div className="bento-card rounded-lg p-6">
              <h3 className="font-mono text-xs font-bold text-cyber-blue uppercase tracking-wider mb-6 flex items-center gap-2">
                <Building2 className="h-4 w-4" />
                Top Hiring Companies
              </h3>
              <div className="overflow-x-auto">
                <table className="w-full text-left">
                  <thead className="border-b border-outline-variant">
                    <tr className="text-xs font-mono text-on-surface-variant">
                      <th className="pb-3">Company</th>
                      <th className="pb-3 text-right">Open Positions</th>
                      <th className="pb-3 text-right">Avg Salary</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.top_companies.map((company, idx) => (
                      <tr key={idx} className="border-b border-outline-variant/30 hover:bg-surface-dim/20 transition-colors">
                        <td className="py-3 text-sm font-medium text-white">{company.name}</td>
                        <td className="py-3 text-right text-sm text-on-surface-variant">{company.job_count.toLocaleString()}</td>
                        <td className="py-3 text-right text-sm text-cyber-blue">
                          {company.average_salary ? `${currencySymbol}${company.average_salary.toLocaleString(locale)}` : "N/A"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Regional Data Tab */}
          {activeTab === "regional" && data.regional_salaries.length > 0 && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              <div className="bento-card rounded-lg p-6">
                <h3 className="font-mono text-xs font-bold text-cyber-blue uppercase tracking-wider mb-6 flex items-center gap-2">
                  <MapPin className="h-4 w-4" />
                  Top Paying Locations
                </h3>
                <ResponsiveContainer width="100%" height={400}>
                  <BarChart data={data.regional_salaries.slice(0, 8)} layout="vertical" margin={{ top: 5, right: 5, left: 100, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                    <XAxis type="number" tick={{ fill: "#9ca3af", fontSize: 10, fontFamily: "monospace" }} tickFormatter={v => `${currencySymbol}${(v / 1000).toFixed(0)}k`} axisLine={{ stroke: "rgba(255,255,255,0.1)" }} />
                    <YAxis type="category" dataKey="location" tick={{ fill: "#9ca3af", fontSize: 10, fontFamily: "monospace" }} width={120} axisLine={false} tickLine={false} />
                    <Tooltip content={<CustomTooltip isSalary currencySymbol={currencySymbol} locale={locale} />} />
                    <Bar dataKey="salary" name="Average Salary" fill="#00d2ff" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <div className="bento-card rounded-lg p-6">
                <h3 className="font-mono text-xs font-bold text-cyber-blue uppercase tracking-wider mb-6 flex items-center gap-2">
                  <Briefcase className="h-4 w-4" />
                  Job Distribution by Location
                </h3>
                <div className="space-y-4">
                  {data.regional_salaries.slice(0, 8).map((loc, idx) => (
                    <div key={idx}>
                      <div className="flex justify-between text-xs font-mono mb-1">
                        <span className="text-on-surface-variant truncate max-w-[200px]">{loc.location}</span>
                        <span className="text-white font-bold">{loc.job_count.toLocaleString()} jobs</span>
                      </div>
                      <div className="w-full h-2 bg-surface-dim rounded overflow-hidden">
                        <div
                          className="h-full rounded transition-all duration-500"
                          style={{
                            width: `${(loc.job_count / (data.regional_salaries[0]?.job_count || 1)) * 100}%`,
                            backgroundColor: "#00d2ff"
                          }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* JOB LISTINGS TAB - Real API Data Only */}
      {activeTab === "jobs" && (
        <div className="space-y-6">
          {/* Job Search Bar */}
          <div className="bento-card rounded-lg p-6">
            <div className="flex gap-3 flex-wrap">
              <div className="flex-1 min-w-[200px] relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-on-surface-variant" />
                <input
                  type="text"
                  value={domain}
                  onChange={e => setDomain(e.target.value)}
                  onKeyDown={handleJobsKeyDown}
                  placeholder="Job title, e.g. Full Stack Developer, Data Scientist..."
                  className="w-full bg-[#07070a]/60 border border-outline-variant rounded pl-9 pr-4 py-3 text-white font-sans text-sm focus:outline-none focus:border-cyber-blue transition-colors"
                />
              </div>
              <div className="min-w-[180px] relative">
                <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-on-surface-variant" />
                <input
                  type="text"
                  value={location}
                  onChange={e => setLocation(e.target.value)}
                  onKeyDown={handleJobsKeyDown}
                  placeholder="Location (optional)"
                  className="w-full bg-[#07070a]/60 border border-outline-variant rounded pl-9 pr-4 py-3 text-white font-sans text-sm focus:outline-none focus:border-cyber-blue transition-colors"
                />
              </div>
              <select
                value={country}
                onChange={e => setCountry(e.target.value)}
                className="bg-[#07070a]/60 border border-outline-variant rounded px-3 py-3 text-white font-sans text-sm focus:outline-none focus:border-cyber-blue transition-colors"
                aria-label="Country"
              >
                <option value="in">India (IN)</option>
                <option value="us">United States (US)</option>
                <option value="gb">United Kingdom (GB)</option>
                <option value="ca">Canada (CA)</option>
                <option value="au">Australia (AU)</option>
              </select>
              <button
                onClick={() => setShowFilters(!showFilters)}
                className="px-4 py-3 rounded bg-surface-dim/50 text-on-surface-variant font-mono text-xs uppercase tracking-wider hover:bg-surface-dim transition-all flex items-center gap-2"
              >
                <Filter className="h-4 w-4" />
                Filters
              </button>
              <button
                onClick={handleJobsSearch}
                disabled={jobsLoading || !domain.trim()}
                className="px-6 py-3 rounded bg-cyber-blue text-black font-mono text-xs font-bold uppercase tracking-wider hover:bg-white hover:shadow-[0_0_15px_rgba(0,210,255,0.5)] transition-all duration-300 flex items-center gap-2 cursor-pointer disabled:opacity-50"
              >
                {jobsLoading ? (
                  <><Loader className="h-4 w-4 animate-spin" /><span>Searching...</span></>
                ) : (
                  <><Search className="h-4 w-4" /><span>Find Jobs</span></>
                )}
              </button>
            </div>

            {/* Filters Panel */}
            {showFilters && (
              <div className="mt-6 pt-6 border-t border-outline-variant">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="font-mono text-xs font-bold text-cyber-blue uppercase tracking-wider">Advanced Filters</h3>
                  <button onClick={clearFilters} className="text-xs text-on-surface-variant hover:text-cyber-blue flex items-center gap-1">
                    <X className="h-3 w-3" />
                    Clear all
                  </button>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <select
                    value={contractTypeFilter}
                    onChange={e => setContractTypeFilter(e.target.value)}
                    className="bg-[#07070a]/60 border border-outline-variant rounded px-3 py-2 text-white text-sm"
                  >
                    <option value="">Contract Type: Any</option>
                    <option value="permanent">Permanent</option>
                    <option value="contract">Contract</option>
                  </select>
                  
                  <select
                    value={contractTimeFilter}
                    onChange={e => setContractTimeFilter(e.target.value)}
                    className="bg-[#07070a]/60 border border-outline-variant rounded px-3 py-2 text-white text-sm"
                  >
                    <option value="">Work Hours: Any</option>
                    <option value="full_time">Full Time</option>
                    <option value="part_time">Part Time</option>
                  </select>
                </div>
              </div>
            )}
          </div>

          {/* Results Summary */}
          {filteredJobs.length > 0 && !jobsLoading && (
            <div className="flex justify-between items-center">
              <p className="text-sm text-on-surface-variant font-mono">
                Found <span className="text-cyber-blue font-bold">{totalJobs.toLocaleString()}</span> jobs
              </p>
              {totalPages > 0 && (
                <p className="text-xs text-on-surface-variant font-mono">
                  Page {currentPage} of {totalPages}
                </p>
              )}
            </div>
          )}

          {/* Job Listings */}
          {jobsLoading ? (
            <div className="space-y-4">
              {[1, 2, 3, 4, 5].map(i => (
                <div key={i} className="bento-card rounded-lg p-6 animate-pulse">
                  <div className="h-5 bg-surface-container-high rounded w-1/3 mb-3"></div>
                  <div className="h-3 bg-surface-container rounded w-1/4 mb-4"></div>
                  <div className="h-20 bg-surface-container rounded"></div>
                </div>
              ))}
            </div>
          ) : jobsError ? (
            <div className="bento-card rounded-lg p-12 flex flex-col items-center justify-center text-center text-on-surface-variant border-red-500/20 bg-red-500/5">
              <AlertTriangle className="h-12 w-12 mb-4 text-red-400" />
              <p className="font-mono text-sm text-red-400">{jobsError}</p>
              <p className="text-xs text-on-surface-variant/60 mt-2">Make sure your Adzuna API credentials are configured correctly.</p>
            </div>
          ) : filteredJobs.length > 0 ? (
            <>
              <div className="space-y-4">
                {filteredJobs.map((job) => (
                  <div
                    key={job.id}
                    className="bento-card rounded-lg p-6 hover:border-cyber-blue/40 transition-all cursor-pointer group"
                    onClick={() => setSelectedJob(selectedJob?.id === job.id ? null : job)}
                  >
                    <div className="flex justify-between items-start flex-wrap gap-4">
                      <div className="flex-1">
                        <h3 className="text-lg font-semibold text-white group-hover:text-cyber-blue transition-colors">
                          {job.title}
                        </h3>
                        <div className="flex flex-wrap gap-4 mt-2 text-sm text-on-surface-variant">
                          <span className="flex items-center gap-1">
                            <Building2 className="h-3.5 w-3.5" />
                            {job.company}
                          </span>
                          <span className="flex items-center gap-1">
                            <MapPin className="h-3.5 w-3.5" />
                            {job.location}
                          </span>
                          <span className="flex items-center gap-1">
                            <DollarSign className="h-3.5 w-3.5" />
                            {formatSalary(job.salary_min, job.salary_max, job.salary_is_predicted)}
                            {job.salary_is_predicted && (
                              <span className="text-[10px] text-amber-400 ml-1">(estimated)</span>
                            )}
                          </span>
                          <span className="flex items-center gap-1">
                            <Clock className="h-3.5 w-3.5" />
                            {formatDate(job.created)}
                          </span>
                        </div>
                        <div className="flex flex-wrap gap-2 mt-3">
                          <span className="px-2 py-1 rounded-full bg-cyber-blue/10 text-cyber-blue text-xs font-mono">
                            {job.contract_type === "permanent" ? "Permanent" : job.contract_type || "Not specified"}
                          </span>
                          <span className="px-2 py-1 rounded-full bg-surface-dim text-on-surface-variant text-xs font-mono">
                            {job.contract_time === "full_time" ? "Full Time" : job.contract_time === "part_time" ? "Part Time" : job.contract_time || "Not specified"}
                          </span>
                          <span className="px-2 py-1 rounded-full bg-surface-dim text-on-surface-variant text-xs font-mono flex items-center gap-1">
                            <Tag className="h-3 w-3" />
                            {job.category}
                          </span>
                        </div>
                        <p className="mt-3 text-sm text-on-surface-variant/80 line-clamp-2">
                          {job.description}
                        </p>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          openJobLink(job.redirect_url);
                        }}
                        className="px-4 py-2 rounded bg-cyber-blue text-black font-mono text-xs font-bold uppercase tracking-wider hover:bg-white transition-all flex items-center gap-2 shrink-0"
                      >
                        <ExternalLink className="h-3.5 w-3.5" />
                        Apply Now
                      </button>
                    </div>

                    {/* Expanded Job Details */}
                    {selectedJob?.id === job.id && (
                      <div className="mt-6 pt-6 border-t border-outline-variant animate-fade-in">
                        <h4 className="font-mono text-xs font-bold text-cyber-blue uppercase tracking-wider mb-3">
                          Full Description
                        </h4>
                        <p className="text-sm text-on-surface-variant/90 whitespace-pre-wrap">
                          {job.description}
                        </p>
                        <div className="mt-4 flex gap-3">
                          <button
                            onClick={() => openJobLink(job.redirect_url)}
                            className="px-6 py-2 rounded bg-cyber-blue text-black font-mono text-xs font-bold uppercase tracking-wider hover:bg-white transition-all flex items-center gap-2"
                          >
                            <ExternalLink className="h-3.5 w-3.5" />
                            Apply for this position
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex justify-center gap-2 mt-8">
                  <button
                    onClick={() => goToPage(currentPage - 1)}
                    disabled={currentPage === 1}
                    className="px-4 py-2 rounded bg-surface-dim/50 text-on-surface-variant hover:bg-surface-dim disabled:opacity-30 disabled:cursor-not-allowed transition-all"
                  >
                    Previous
                  </button>
                  
                  <div className="flex gap-2">
                    {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                      let pageNum;
                      if (totalPages <= 5) {
                        pageNum = i + 1;
                      } else if (currentPage <= 3) {
                        pageNum = i + 1;
                      } else if (currentPage >= totalPages - 2) {
                        pageNum = totalPages - 4 + i;
                      } else {
                        pageNum = currentPage - 2 + i;
                      }
                      
                      return (
                        <button
                          key={pageNum}
                          onClick={() => goToPage(pageNum)}
                          className={`w-10 h-10 rounded transition-all ${
                            currentPage === pageNum
                              ? "bg-cyber-blue text-black font-bold"
                              : "bg-surface-dim/50 text-on-surface-variant hover:bg-surface-dim"
                          }`}
                        >
                          {pageNum}
                        </button>
                      );
                    })}
                  </div>
                  
                  <button
                    onClick={() => goToPage(currentPage + 1)}
                    disabled={currentPage === totalPages}
                    className="px-4 py-2 rounded bg-surface-dim/50 text-on-surface-variant hover:bg-surface-dim disabled:opacity-30 disabled:cursor-not-allowed transition-all"
                  >
                    Next
                  </button>
                </div>
              )}
            </>
          ) : !jobsLoading && domain && (
            <div className="bento-card rounded-lg p-16 flex flex-col items-center justify-center text-center text-on-surface-variant">
              <Briefcase className="h-16 w-16 mb-4 opacity-20" />
              <p className="font-mono text-xs uppercase tracking-wider mb-2">No jobs found</p>
              <p className="text-xs text-on-surface-variant/60 max-w-xs">
                Try a different job title or location.
              </p>
            </div>
          )}

          {/* Empty State for Jobs */}
          {!domain && !jobsLoading && (
            <div className="bento-card rounded-lg p-16 flex flex-col items-center justify-center text-center text-on-surface-variant">
              <Search className="h-16 w-16 mb-4 opacity-20" />
              <p className="font-mono text-xs uppercase tracking-wider mb-2">Search for jobs</p>
              <p className="text-xs text-on-surface-variant/60 max-w-xs">
                Enter a job title above to find real job opportunities with direct application links.
              </p>
            </div>
          )}
        </div>
      )}

      {/* Empty State for Analytics */}
      {!data && !isLoading && !error && activeTab !== "jobs" && (
        <div className="bento-card rounded-lg p-16 flex flex-col items-center justify-center text-center text-on-surface-variant">
          <BarChart2 className="h-16 w-16 mb-4 opacity-20" />
          <p className="font-mono text-xs uppercase tracking-wider mb-2">No domain indexed yet</p>
          <p className="text-xs text-on-surface-variant/60 max-w-xs leading-relaxed">
            Enter a job domain above to analyze real-time market intelligence, skill demand trends, and salary distributions.
          </p>
        </div>
      )}
    </div>
  );
}