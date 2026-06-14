with open('app/analytics/page.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update useState
content = content.replace(
    'const [activeTab, setActiveTab] = useState<"overview" | "salary" | "companies" | "regional" | "jobs">("overview");',
    'const [activeTab, setActiveTab] = useState<"overview" | "regional" | "jobs">("overview");'
)

# 2. Update tabs list
old_tabs = """          {[
            { id: "overview", label: "Market Overview", icon: BarChart2 },
            { id: "salary", label: "Salary Analysis", icon: DollarSign },
            { id: "companies", label: "Top Companies", icon: Building2 },
            { id: "regional", label: "Regional Data", icon: MapPin },
            { id: "jobs", label: "Job Listings", icon: Briefcase }
          ].map(tab => ("""
new_tabs = """          {[
            { id: "overview", label: "Market Overview", icon: BarChart2 },
            { id: "regional", label: "Regional Data", icon: MapPin },
            { id: "jobs", label: "Job Listings", icon: Briefcase }
          ].map(tab => ("""
content = content.replace(old_tabs, new_tabs)

# 3. Remove sections
import re

salary_pattern = r'\s*\{\/\* Salary Analysis Tab \*\/\}([\s\S]*?)        \{\/\* Top Companies Tab \*\/\}'
match_salary = re.search(salary_pattern, content)
if match_salary:
    content = content.replace(match_salary.group(1), '\n')
    # wait, we can just replace the whole section from Salary Analysis Tab to Regional Data Tab
    
combined_pattern = r'\s*\{\/\* Salary Analysis Tab \*\/\}([\s\S]*?)\{\/\* Regional Data Tab \*\/\}'
match_combined = re.search(combined_pattern, content)
if match_combined:
    content = content.replace(match_combined.group(0), '\n          {/* Regional Data Tab */}')
else:
    print("Could not find combined section block.")

with open('app/analytics/page.tsx', 'w', encoding='utf-8') as f:
    f.write(content)
print("Done")
