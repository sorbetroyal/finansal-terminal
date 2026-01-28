import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

test_models = [
    'gemini-1.5-flash',
    'gemini-1.5-flash-latest',
    'gemini-1.5-pro',
    'gemini-pro',
    'models/gemini-1.5-flash',
    'models/gemini-pro'
]

results = []
for m_name in test_models:
    try:
        print(f"Testing {m_name}...")
        model = genai.GenerativeModel(m_name)
        response = model.generate_content("Hi", generation_config={"max_output_tokens": 5})
        print(f"  SUCCESS: {m_name}")
        results.append(m_name)
    except Exception as e:
        print(f"  FAILED: {m_name} - {str(e)[:50]}...")

print("\nWORKING MODELS: " + str(results))
