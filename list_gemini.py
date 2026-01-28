import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

print("GEMINI MODELS:")
for m in genai.list_models():
    if 'gemini' in m.name.lower() and 'generateContent' in m.supported_generation_methods:
        print(f" - {m.name}")
