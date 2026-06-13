from langchain_google_genai import ChatGoogleGenerativeAI

from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GOOGLE_API_KEY")

model = ChatGoogleGenerativeAI(api_key=API_KEY, model_name="gemini-1.5-flash")
response = model.invoke("Hello, how are you?")
print(response)