import re

with open('app/analytics/page.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update state
state_old = "const [fresherJobs, setFresherJobs] = useState<any[]>([]);"
state_new = "const [fresherJobs, setFresherJobs] = useState<any[]>([]);\n  const [fresherSkills, setFresherSkills] = useState<any[]>([]);"
content = content.replace(state_old, state_new)

# 2. Update fetch logic
fetch_old = """setFresherJobs(result.jobs || []);
      }"""
fetch_new = """setFresherJobs(result.jobs || []);
        setFresherSkills(result.skills || []);
      }"""
content = content.replace(fetch_old, fetch_new)

# 3. Replace Skills Demand Index section
old_skills_chart_pattern = r'<\s*div\s+className="bento-card rounded-lg p-6"\s*>\s*<\s*h3[^>]*>\s*<\s*BarChart2[^>]*>\s*Skills Demand Index\s*</h3\s*>[\s\S]*?<\s*/\s*ResponsiveContainer\s*>\s*<\s*/\s*div\s*>'

new_skills_chart = """<div className="bento-card rounded-lg p-6">
                <h3 className="font-mono text-xs font-bold text-cyber-blue uppercase tracking-wider mb-6 flex items-center gap-2">
                  <BarChart2 className="h-4 w-4" />
                  Top Fresher Skills (AI)
                </h3>
                {loadingFresherJobs ? (
                  <div className="w-full h-[300px] flex items-center justify-center">
                    <Loader className="h-8 w-8 animate-spin text-cyber-blue" />
                  </div>
                ) : fresherSkills.length > 0 ? (
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={fresherSkills} margin={{ top: 5, right: 5, left: -20, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                      <XAxis dataKey="name" tick={{ fill: "#9ca3af", fontSize: 10, fontFamily: "monospace" }} axisLine={{ stroke: "rgba(255,255,255,0.1)" }} tickLine={false} />
                      <YAxis tick={{ fill: "#9ca3af", fontSize: 10, fontFamily: "monospace" }} axisLine={false} tickLine={false} unit="%" />
                      <Tooltip content={<CustomTooltip currencySymbol={currencySymbol} locale={locale} />} />
                      <Bar dataKey="percentage" name="Demand %" fill="#00ff88" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="w-full h-[300px] flex items-center justify-center text-on-surface-variant font-mono text-sm">
                    No skills data fetched.
                  </div>
                )}
              </div>"""

content = re.sub(old_skills_chart_pattern, new_skills_chart, content)

with open('app/analytics/page.tsx', 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated frontend page.tsx")
