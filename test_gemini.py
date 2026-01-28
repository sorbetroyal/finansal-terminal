import os
import google.generativeai as genai
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key or "YOUR_GEMINI" in api_key:
    print("HATA: .env dosyasında geçerli bir GEMINI_API_KEY bulunamadı!")
    exit()

print(f"API Anahtarı kontrol ediliyor: {api_key[:5]}...{api_key[-5:]}")

try:
    genai.configure(api_key=api_key)
    
    print("\n--- Kullanılabilir Modeller Listeleniyor ---")
    available_models = []
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"Model Adı: {m.name}")
            available_models.append(m.name)
    
    if not available_models:
        print("HATA: generateContent destekleyen hiç model bulunamadı!")
        exit()

    # En uygun modeli seçmeye çalışalım
    target_models = ['models/gemini-1.5-flash', 'models/gemini-1.5-pro', 'models/gemini-pro']
    selected_model = None
    
    for tm in target_models:
        if tm in available_models:
            selected_model = tm
            break
    
    if not selected_model:
        selected_model = available_models[0]
        
    print(f"\n--- Test Mesajı Gönderiliyor (Model: {selected_model}) ---")
    model = genai.GenerativeModel(selected_model.replace('models/', ''))
    response = model.generate_content("Merhaba, sistem çalışıyor mu? Sadece 'EVET' de.")
    print(f"Yanıt: {response.text}")
    print("\nBAŞARILI: Sistem bu model ile sorunsuz çalışıyor.")

except Exception as e:
    print(f"\nHATA OLUŞTU: {e}")
    print("\nİpucu: Eğer 404 alıyorsanız, model isimlerinin başına 'models/' ekleyip eklemediğimizi kontrol etmeliyiz.")
