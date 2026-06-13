"""
Universal ATS Normalization Layer
Converts raw strings extracted from resumes and job descriptions into canonical forms.
"""

TECHNICAL_SKILL_MAP = {
    "nodejs": "Node.js", "node": "Node.js", "node.js": "Node.js", "node js": "Node.js",
    "react": "React", "reactjs": "React", "react.js": "React", "react js": "React",
    "javascript": "JavaScript", "js": "JavaScript", "java script": "JavaScript",
    "typescript": "TypeScript", "ts": "TypeScript", "type script": "TypeScript",
    "aws": "AWS", "amazon web services": "AWS", "aws ec2": "AWS",
    "gcp": "GCP", "google cloud": "GCP", "google cloud platform": "GCP",
    "kubernetes": "Kubernetes", "k8s": "Kubernetes",
    "mongodb": "MongoDB", "mongo": "MongoDB",
    "postgresql": "PostgreSQL", "postgres": "PostgreSQL",
    "powerbi": "Power BI", "power bi": "Power BI",
    "ml": "Machine Learning", "machine learning": "Machine Learning",
    "ai": "Artificial Intelligence", "artificial intelligence": "Artificial Intelligence",
    "nlp": "Natural Language Processing", "natural language processing": "Natural Language Processing",
    "mysql": "MySQL", "redis": "Redis", "git": "Git",
    "vue": "Vue.js", "vue.js": "Vue.js", "vuejs": "Vue.js",
    "angular": "Angular",
    "next.js": "Next.js", "nextjs": "Next.js",
    "express": "Express.js", "express.js": "Express.js", "express js": "Express.js",
    "django": "Django", "flask": "Flask", "fastapi": "FastAPI",
    "java": "Java", "kotlin": "Kotlin", "swift": "Swift",
    "go": "Go", "golang": "Go", "rust": "Rust",
    "html": "HTML", "html5": "HTML", "css": "CSS", "css3": "CSS",
    "tailwind": "Tailwind CSS", "tailwindcss": "Tailwind CSS",
    "jenkins": "Jenkins", "terraform": "Terraform", "ansible": "Ansible",
    "kafka": "Apache Kafka", "elasticsearch": "Elasticsearch",
    "nginx": "Nginx", "linux": "Linux", "python": "Python",
    "ci/cd": "CI/CD", "rest": "REST APIs", "rest api": "REST APIs", "restful": "REST APIs",
    "c++": "C++", "cpp": "C++", "c#": "C#", "csharp": "C#",
}

SOFT_SKILL_MAP = {
    "good communication": "Communication", "communication skills": "Communication", "excellent communication": "Communication", "communication": "Communication",
    "strong leadership": "Leadership", "leadership skills": "Leadership", "leadership": "Leadership",
    "problem solving skills": "Problem Solving", "problem solver": "Problem Solving", "problem solving": "Problem Solving",
    "critical thinking ability": "Critical Thinking", "critical thinking": "Critical Thinking",
    "presentation and communication skills": "Presentation Skills", "presentation skills": "Presentation Skills",
    "analytical skills": "Analytical Thinking", "analytical thinking": "Analytical Thinking",
    "teamwork": "Teamwork", "team player": "Teamwork",
    "stakeholder management": "Stakeholder Management", "stakeholder communication": "Stakeholder Management",
}

EDUCATION_DEGREE_MAP = {
    "b.tech": "Bachelor of Technology", "bachelors of technology": "Bachelor of Technology", "bachelor in technology": "Bachelor of Technology", "bachelor's degree in technology": "Bachelor of Technology", "bachelor of technology": "Bachelor of Technology",
    "b.e.": "Bachelor of Engineering", "bachelor of engineering": "Bachelor of Engineering",
    "b.sc": "Bachelor of Science", "bachelor of science": "Bachelor of Science",
    "m.tech": "Master of Technology", "masters of technology": "Master of Technology", "master in technology": "Master of Technology", "master of technology": "Master of Technology",
    "m.e.": "Master of Engineering", "master of engineering": "Master of Engineering",
    "m.sc": "Master of Science", "master of science": "Master of Science",
    "mba": "Master of Business Administration", "master of business administration": "Master of Business Administration",
    "phd": "Doctor of Philosophy", "doctorate": "Doctor of Philosophy", "doctor of philosophy": "Doctor of Philosophy",
}

EDUCATION_FIELD_MAP = {
    "computer science": "Computer Science", "computer science engineering": "Computer Science", "cse": "Computer Science", "cs": "Computer Science",
    "information technology": "Information Technology", "it": "Information Technology",
    "electronics and communication": "Electronics and Communication Engineering", "ece": "Electronics and Communication Engineering",
    "artificial intelligence and machine learning": "Artificial Intelligence and Machine Learning", "ai/ml": "Artificial Intelligence and Machine Learning", "aiml": "Artificial Intelligence and Machine Learning",
    "data science": "Data Science", "ds": "Data Science",
}

CERTIFICATION_MAP = {
    "aws cloud practitioner": "AWS Certified Cloud Practitioner", "aws certified cloud practitioner": "AWS Certified Cloud Practitioner",
    "google data analytics cert": "Google Data Analytics Professional Certificate", "google data analytics professional certificate": "Google Data Analytics Professional Certificate",
    "microsoft power bi cert": "Microsoft Power BI Certification", "microsoft power bi certification": "Microsoft Power BI Certification",
}

PROJECT_DOMAIN_MAP = {
    "ml project": "Machine Learning", "machine learning project": "Machine Learning", "machine learning": "Machine Learning",
    "data analytics project": "Data Analytics", "business analytics project": "Data Analytics", "data analytics": "Data Analytics",
    "dashboard project": "Data Visualization", "visualization dashboard": "Data Visualization", "data visualization": "Data Visualization",
    "web app development": "Web Development", "full stack application": "Web Development", "web development": "Web Development",
    "backend api project": "Backend Development", "backend development": "Backend Development",
    "cloud computing": "Cloud Computing", "cyber security": "Cyber Security", "mobile development": "Mobile Development",
}

JOB_TITLE_MAP = {
    "software developer": "Software Engineer", "software engineer": "Software Engineer",
    "backend developer": "Backend Engineer", "backend engineer": "Backend Engineer",
    "frontend developer": "Frontend Engineer", "frontend engineer": "Frontend Engineer",
    "full stack developer": "Full Stack Engineer", "full stack engineer": "Full Stack Engineer",
    "data analyst": "Data Analyst", "business analyst": "Business Analyst",
    "ml engineer": "Machine Learning Engineer", "machine learning engineer": "Machine Learning Engineer",
    "ai engineer": "Artificial Intelligence Engineer", "artificial intelligence engineer": "Artificial Intelligence Engineer",
    "data scientist": "Data Scientist",
}


def normalize_string(val: str, mapping: dict) -> str:
    if not isinstance(val, str):
        return str(val)
    # Clean whitespace: strip and replace multiple spaces with single space
    clean_val = " ".join(val.strip().split())
    # Return canonical mapped value or title case if not found
    return mapping.get(clean_val.lower(), clean_val.title())

def normalize_technical_skill(skill: str) -> str:
    if not isinstance(skill, str): return skill
    clean_skill = " ".join(skill.strip().split())
    return TECHNICAL_SKILL_MAP.get(clean_skill.lower(), clean_skill)

def normalize_soft_skill(skill: str) -> str:
    return normalize_string(skill, SOFT_SKILL_MAP)

def normalize_education_degree(degree: str) -> str:
    return normalize_string(degree, EDUCATION_DEGREE_MAP)

def normalize_education_field(field: str) -> str:
    return normalize_string(field, EDUCATION_FIELD_MAP)

def normalize_certification(cert: str) -> str:
    return normalize_string(cert, CERTIFICATION_MAP)

def normalize_project_domain(domain: str) -> str:
    return normalize_string(domain, PROJECT_DOMAIN_MAP)

def normalize_job_title(title: str) -> str:
    return normalize_string(title, JOB_TITLE_MAP)

def normalize_keyword(keyword: str) -> str:
    # Keywords often map back to technical skills or domains
    if not isinstance(keyword, str): return keyword
    lowered = keyword.lower().strip()
    if lowered in TECHNICAL_SKILL_MAP:
        return TECHNICAL_SKILL_MAP[lowered]
    if lowered in PROJECT_DOMAIN_MAP:
        return PROJECT_DOMAIN_MAP[lowered]
    return keyword.strip().title()

def deduplicate_normalized_list(items: list) -> list:
    """Helper to remove duplicates after normalization while preserving order"""
    seen = set()
    result = []
    for item in items:
        if not isinstance(item, str): continue
        if item.lower() not in seen:
            seen.add(item.lower())
            result.append(item)
    return result
