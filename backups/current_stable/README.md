# 📊 Finansal Terminal - AI Destekli Borsa & Portföy Yönetin Asistanı

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28%2B-red?style=for-the-badge&logo=streamlit)
![Supabase](https://img.shields.io/badge/Supabase-Backend-green?style=for-the-badge&logo=supabase)
![Gemini AI](https://img.shields.io/badge/Gemini_AI-Integrated-purple?style=for-the-badge&logo=google-gemini)

**Finansal Terminal**, Borsa İstanbul (BIST), Kripto Para, ABD Borsaları, Emtialar ve Yatırım Fonlarını (TEFAS) tek bir yerden takip etmenizi, portföyünüzü yönetmenizi ve gelişmiş stratejiler oluşturmanızı sağlayan kapsamlı bir web uygulamasıdır. İçerisindeki yapay zeka entegrasyonu (Gemini) sayesinde, portföyünüzü analiz eder, haberleri yorumlar ve size özel yatırım tavsiyeleri sunar.

---

## 🌟 Öne Çıkan Özellikler

### 1. 💼 Varlıklarım (Strateji Merkezi)
Portföyünüzdeki tüm varlıkları tek bakışta görün.
- **Akıllı Kart Tasarımı:** Her varlık için özel tasarlanmış, anlık fiyat değişimlerini ve kar/zarar durumunu gösteren "Slim" kartlar.
- **Hızlı Strateji Oluşturma:** Varlıklarınıza saniyeler içinde "AL" veya "SAT" stratejileri ekleyin.
- **Öncelikli Sıralama:** Stratejisi olan varlıklar ve belirlediğiniz varlık tiplerine (Kripto > BIST > ABD...) göre otomatik sıralama.
- **Takip Edilenler:** Portföyünüzde olmayan ancak radarınızdaki varlıklar için ayrı bir sekme.

### 2. 📈 Piyasa Takibi (Market Data)
Dünya piyasalarını anlık olarak izleyin.
- **BIST 100 & 30:** Canlı veri ve değişimler.
- **Kripto Paralar:** Binance üzerinden anlık takip.
- **ABD Borsaları:** Apple, Tesla, Google gibi devleri ve ETF'leri izleyin.
- **Emtia & Döviz:** Altın, Gümüş, Dolar, Euro kurları.
- **Yatırım Fonları:** TEFAS verileriyle fon performanslarını analiz edin.

### 3. 🤖 AI Destekli Portföy Analizi (Gemini)
Google Gemini yapay zekası ile portföyünüzü güçlendirin.
- **Portföy Yorumu:** Varlık dağılımınızı analiz edip risk ve fırsatları raporlar.
- **Haber Analizi:** Piyasayı etkileyen son haberleri derler ve yorumlar.
- **Sohbet Modu:** Finansal sorularınızı yapay zekaya sorun, anında yanıt alın.

### 4. 🔭 İzleme Listesi (Smart Watchlist)
Varlıklarınızı sadece fiyatıyla değil, teknik gücüyle takip edin.
- **Akıllı Teknik Skor (0-10):** Supertrend, KAMA, OBV ve ADX indikatörlerini harmanlayan, momentum dostu özel bir puanlama algoritması.
- **"Elmas" Giriş Tespiti:** Sadece yükselen değil, aynı zamanda trend desteğine (KAMA/ST) yakın olan "ideal giriş" noktalarındaki varlıkları parlatır.
- **Otomatik Sıralama:** Listenizdeki varlıklar teknik potansiyeline göre (En güçlüden zayıfa) saniyeler içinde otomatik olarak sıralanır.
- **TEFAS Fon Analizi:** Normalde teknik analiz yapılamayan TEFAS fonları için özel geliştirilmiş sentetik veri motoru ile indikatör desteği.
- **Zenginleştirilmiş Kartlar:** Sparkline grafikler, her indikatör için özel renk kodlu badge'ler ve trend şiddetine duyarlı ADX göstergeleri.

### 5. 🤖 AI Destekli Portföy Analizi (Gemini)
Google Gemini yapay zekası ile portföyünüzü güçlendirin.
- **Portföy Yorumu:** Varlık dağılımınızı analiz edip risk ve fırsatları raporlar.
- **Haber Analizi:** Piyasayı etkileyen son haberleri derler ve yorumlar.
- **Sohbet Modu:** Finansal sorularınızı yapay zekaya sorun, anında yanıt alın.

### 6. 📊 Teknik Analiz & Grafikler
- **TradingView Entegrasyonu:** Profesyonel grafikler ve indikatörlerle derinlemesine analiz yapın.
- **Özel İndikatörler:** RSI, MACD, Bollinger Bantları, Supertrend, KAMA ve daha fazlası.

### 7. 🔔 Haberler & Bildirimler
- **KAP Haberleri:** Borsa İstanbul şirketlerinden gelen son dakika bildirimleri (KAP).
- **Ekonomik Takvim:** Önemli ekonomik verileri ve açıklamaları takip edin.

---

## 🚀 Kurulum ve Başlatma

Proje Python tabanlıdır ve Streamlit kütüphanesi üzerine inşa edilmiştir.

### Gereksinimler
- Python 3.10 veya üzeri
- `pip` paket yöneticisi

### Adım 1: Depoyu Klonlayın
```bash
git clone https://github.com/sorbetroyal/finansal-terminal.git
cd finansal-terminal
```

### Adım 2: Gerekli Kütüphaneleri Yükleyin
```bash
pip install -r requirements.txt
```

### Adım 3: Uygulamayı Başlatın
Uygulamayı çalıştırmak için terminalde şu komutu kullanın:
```bash
streamlit run app.py
```
Veya hazır `Baslat.bat` dosyasını çift tıklayarak çalıştırabilirsiniz (Windows için).

---

## 🛠️ Kullanılan Teknolojiler

*   **Frontend:** [Streamlit](https://streamlit.io/) - Hızlı ve interaktif veri uygulamaları için.
*   **Veri Kaynakları:**
    *   `yfinance`: Yahoo Finance verileri (ABD, Kripto, Döviz).
    *   `tefas-crawler` (veya benzeri): Yatırım fonu verileri.
    *   `Borsapy`: BIST verileri için (veya alternatif API'ler).
*   **Veritabanı & Auth:** [Supabase](https://supabase.com/) - Kullanıcı yönetimi ve veri saklama (PostgreSQL).
*   **Yapay Zeka:** [Google Gemini API](https://deepmind.google/technologies/gemini/) - Doğal dil işleme ve finansal analiz.
*   **Grafikler:** `plotly`, `TradingView Widget`.

---

## 📝 Lisans

Bu proje kişisel kullanım ve eğitim amaçlı geliştirilmiştir. Ticari yatırım tavsiyesi içermez. Verilerde gecikmeler olabilir.

---

**Geliştirici:** Yılmaz (ve Antigravity AI 🤖)
