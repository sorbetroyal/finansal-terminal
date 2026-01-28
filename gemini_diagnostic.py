import os
import google.generativeai as genai
from dotenv import load_dotenv

def run_diagnostic():
    # 1. Load Environment
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")

    print("="*50)
    print("GEMINI API TANI ARACI")
    print("="*50)

    if not api_key or "YOUR_GEMINI" in api_key:
        print("[-] HATA: .env dosyasında geçerli bir GEMINI_API_KEY bulunamadı!")
        return

    print(f"[+] API Anahtarı Algılandı: {api_key[:5]}...{api_key[-5:]}")

    try:
        genai.configure(api_key=api_key)
        
        # 2. List Available Models
        print("\n[1] Kullanılabilir Modeller Listeleniyor...")
        found_models = []
        try:
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    print(f"  - {m.name}")
                    found_models.append(m.name)
        except Exception as list_e:
            print(f"  [-] Modeller listelenirken hata oluştu: {list_e}")
            return

        if not found_models:
            print("  [-] Hiç üretken model bulunamadı!")
            return

        # 3. Test Generations
        print("\n[2] Model Uyumluluk Testi Başlatılıyor...")
        
        # Test targets (we use short names without 'models/' prefix as SDK handles it)
        test_targets = ['gemini-flash-latest', 'gemini-2.0-flash', 'gemini-1.5-flash', 'gemini-pro']
        
        working_models = []
        
        for target in test_targets:
            print(f"  -> '{target}' test ediliyor...", end=" ", flush=True)
            try:
                model = genai.GenerativeModel(target)
                response = model.generate_content("Hi", generation_config={"max_output_tokens": 5})
                if response and response.text:
                    print("BAŞARILI ✅")
                    working_models.append(target)
            except Exception as e:
                err_msg = str(e).split('\n')[0]
                print(f"BAŞARISIZ ❌ ({err_msg[:60]}...)")

        # 4. Final Verdict
        print("\n" + "="*50)
        if working_models:
            print(f"SONUÇ: Uygulama için '{working_models[0]}' modeli önerilir.")
            print(f"Çalışan Modeller: {', '.join(working_models)}")
        else:
            print("SONUÇ: Hiçbir standart model ismi çalışmadı. API anahtarınızın izinlerini kontrol edin.")
        print("="*50)

    except Exception as e:
        print(f"\n[-] Beklenmedik bir hata oluştu: {e}")

if __name__ == "__main__":
    run_diagnostic()
