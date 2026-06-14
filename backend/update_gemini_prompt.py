import re

with open('app/routers/analytics.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_prompt = '''prompt = """Provide the top 10 jobs for freshers in 2026 after just completing a BTech degree. 
        Return the result as a JSON array of objects, where each object has:
        - 'title': string, the job title
        - 'description': string, brief description of the role
        - 'expected_salary': string, expected starting salary range (in USD or INR)
        - 'demand': number, estimated demand percentage or score out of 100
        Return ONLY valid JSON and nothing else. Do not wrap it in markdown block.
        """'''

new_prompt = '''prompt = """Provide the top 10 jobs for freshers in 2026 after just completing a BTech degree. 
        Also provide a list of the top 10 most in-demand skills overall for these 10 jobs.
        Return the result as a JSON object with two keys: 'jobs' and 'skills'.
        The 'jobs' key should be an array of objects, where each object has:
        - 'title': string, the job title
        - 'description': string, brief description of the role
        - 'expected_salary': string, expected starting salary range (in USD or INR)
        - 'demand': number, estimated demand percentage or score out of 100
        The 'skills' key should be an array of objects, where each object has:
        - 'name': string, the skill name (e.g. Python, AI, Cloud Computing)
        - 'percentage': number, demand percentage out of 100
        Return ONLY valid JSON and nothing else. Do not wrap it in markdown block.
        """'''

content = content.replace(old_prompt, new_prompt)

old_return = '''jobs_data = json.loads(response.text)
        return {"jobs": jobs_data}'''

new_return = '''data = json.loads(response.text)
        return {"jobs": data.get("jobs", []), "skills": data.get("skills", [])}'''

content = content.replace(old_return, new_return)

with open('app/routers/analytics.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated backend route")
