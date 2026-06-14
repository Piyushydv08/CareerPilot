import re

with open('app/routers/analytics.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add imports for Gemini at the top
imports = """from google import genai
from google.genai import types
import json

def get_gemini_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY is not configured.")
    return genai.Client(api_key=api_key)
"""

if "import json" not in content:
    content = content.replace('import pandas as pd', 'import pandas as pd\n' + imports)

# Add the new route
new_route = """
@router.get("/top-fresher-jobs")
async def get_top_fresher_jobs():
    \"\"\"
    Uses Gemini API to fetch top 10 jobs for freshers in 2026 after BTech.
    \"\"\"
    try:
        client = get_gemini_client()
        prompt = \"\"\"Provide the top 10 jobs for freshers in 2026 after just completing a BTech degree. 
        Return the result as a JSON array of objects, where each object has:
        - 'title': string, the job title
        - 'description': string, brief description of the role
        - 'expected_salary': string, expected starting salary range (in USD or INR)
        - 'demand': number, estimated demand percentage or score out of 100
        Return ONLY valid JSON and nothing else. Do not wrap it in markdown block.
        \"\"\"
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                response_mime_type="application/json",
            )
        )
        
        if not response.text:
            raise HTTPException(status_code=500, detail="Empty response from Gemini API.")
            
        jobs_data = json.loads(response.text)
        return {"jobs": jobs_data}
        
    except json.JSONDecodeError:
        logger.error(f"Failed to parse Gemini response as JSON: {response.text}")
        raise HTTPException(status_code=500, detail="Failed to parse response from AI.")
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch data from AI: {str(e)}")
"""

if "@router.get(\"/top-fresher-jobs\")" not in content:
    content = content + new_route

with open('app/routers/analytics.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Done updating analytics.py')
