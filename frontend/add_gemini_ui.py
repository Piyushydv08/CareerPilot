import re

with open('app/analytics/page.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Import useEffect
if 'useEffect' not in content[:200]:
    content = content.replace('import React, { useState } from "react";', 'import React, { useState, useEffect } from "react";')

# 2. Add State and Fetch Logic
state_marker = 'const [activeTab, setActiveTab]'
state_str = """const [fresherJobs, setFresherJobs] = useState<any[]>([]);
  const [loadingFresherJobs, setLoadingFresherJobs] = useState(false);"""

if "const [fresherJobs, setFresherJobs]" not in content:
    content = content.replace(state_marker, f'{state_marker}\n  {state_str}')

fetch_logic = """
  const fetchFresherJobs = async () => {
    if (fresherJobs.length > 0 || loadingFresherJobs) return;
    setLoadingFresherJobs(true);
    try {
      const response = await fetch(`${BASE_URL}/analytics/top-fresher-jobs`);
      if (response.ok) {
        const result = await response.json();
        setFresherJobs(result.jobs || []);
      }
    } catch (e) {
      console.error("Failed to fetch fresher jobs", e);
    } finally {
      setLoadingFresherJobs(false);
    }
  };

  useEffect(() => {
    if (data && activeTab === "overview") {
      fetchFresherJobs();
    }
  }, [data, activeTab]);
"""

fetch_marker = 'const currencySymbol'
if "fetchFresherJobs =" not in content:
    content = content.replace(fetch_marker, f'{fetch_logic}\n  {fetch_marker}')

# 3. Replace the Salary by Experience Level section
old_section_pattern = r'<\s*div\s+className="bento-card rounded-lg p-6"\s*>\s*<\s*h3[^>]*>\s*<\s*DollarSign[^>]*>\s*Salary by Experience Level\s*</h3\s*>[\s\S]*?<\s*/\s*ResponsiveContainer\s*>\s*<\s*/\s*div\s*>'
new_section = """<div className="bento-card rounded-lg p-6">
                <h3 className="font-mono text-xs font-bold text-cyber-blue uppercase tracking-wider mb-6 flex items-center gap-2">
                  <Sparkles className="h-4 w-4" />
                  Top 10 BTech Fresher Jobs (2026)
                </h3>
                {loadingFresherJobs ? (
                  <div className="flex flex-col gap-4 animate-pulse">
                    {[...Array(4)].map((_, i) => (
                       <div key={i} className="h-16 bg-surface-container rounded-md w-full"></div>
                    ))}
                  </div>
                ) : (
                  <div className="space-y-4 h-[300px] overflow-y-auto pr-2 custom-scrollbar">
                    {fresherJobs.map((job, idx) => (
                      <div key={idx} className="bg-surface-dim/30 rounded p-3 border border-outline-variant/30 hover:border-cyber-blue/30 transition-colors group">
                        <div className="flex justify-between items-start mb-1 gap-2">
                          <h4 className="text-sm font-bold text-white group-hover:text-cyber-blue transition-colors">
                            {idx + 1}. {job.title}
                          </h4>
                          <span className="text-xs font-mono text-cyber-blue whitespace-nowrap bg-cyber-blue/10 px-2 py-0.5 rounded">
                            {job.expected_salary}
                          </span>
                        </div>
                        <p className="text-[10px] text-on-surface-variant mb-2">{job.description}</p>
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] font-mono text-on-surface-variant">Demand Index:</span>
                          <div className="flex-1 h-1.5 bg-surface-container rounded-full overflow-hidden">
                            <div className="h-full bg-cyber-blue rounded-full" style={{ width: `${job.demand}%` }}></div>
                          </div>
                          <span className="text-[10px] font-mono text-white">{job.demand}%</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>"""

content = re.sub(old_section_pattern, new_section, content)

with open('app/analytics/page.tsx', 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated page.tsx")
