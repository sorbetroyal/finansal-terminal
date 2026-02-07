# 🎯 Planlanan Özellikler - Finansal Terminal

## ✨ Kısa Vadeli İyileştirmeler (1-2 saat)

### 1. Tema Tercihini Kaydetme
- **Öncelik:** Yüksek
- **Süre:** ~30 dakika
- **Açıklama:** Kullanıcının tema tercihini (dark/light) Supabase user_preferences tablosunda sakla
- **Fayda:** Her giriş yaptığında tercih edilen tema otomatik gelir
- **Teknik:** 
  - Supabase'de `user_preferences` tablosu
  - `theme` column (text: 'dark' veya 'light')
  - Login sonrası tema yükleme

### 2. Otomatik Tema (Saat Bazlı)
- **Öncelik:** Orta
- **Süre:** ~20 dakika
- **Açıklama:** Saat 06:00-18:00 arası açık tema, 18:00-06:00 arası koyu tema
- **Fayda:** Gözleri yormayan akıllı tema geçişi
- **Teknik:**
  - `datetime.now().hour` ile kontrol
  - "Auto" seçeneği ekle (Dark/Light/Auto)
  - Her sayfa yüklemede saat kontrolü

### 3. Özelleştirilebilir Accent Rengi
- **Öncelik:** Düşük
- **Süre:** ~45 dakika
- **Açıklama:** Kullanıcı kendi accent rengini seçebilsin
- **Renkler:** Turkuaz (#00f2ff), Mor (#a78bfa), Yeşil (#22c55e), Turuncu (#f97316), Pembe (#ec4899)
- **Teknik:**
  - Renk seçici dropdown
  - CSS değişkenlerini dinamik güncelle
  - Supabase'de sakla

---

## 📊 Orta Vadeli Özellikler (1 gün)

### 4. Portföy Karşılaştırma
- **Öncelik:** Yüksek
- **Süre:** ~2-3 saat
- **Açıklama:** 2 portföyü yan yana karşılaştırma ve performans grafiği overlay
- **Özellikler:**
  - Dropdown'dan 2 portföy seç
  - Yan yana metrikler
  - Overlay performans grafiği
  - Hangi portföy daha iyi analizi

### 5. PDF Rapor Export
- **Öncelik:** Yüksek
- **Süre:** ~3-4 saat
- **Açıklama:** Aylık/Haftalık portföy performans raporu PDF olarak indir
- **İçerik:**
  - Portföy özeti
  - Performans grafikleri
  - Varlık dağılımı
  - Kar/Zarar tablosu
  - AI önerileri
- **Teknik:** 
  - `reportlab` veya `weasyprint` kütüphanesi
  - HTML to PDF dönüştürme
  - Marka logosu ve profesyonel tasarım

### 6. Excel Export
- **Öncelik:** Orta
- **Süre:** ~1 saat
- **Açıklama:** Tüm varlıkları ve işlemleri Excel'e aktar
- **Teknik:**
  - `pandas.to_excel()`
  - Çoklu sheet'ler (Portföyler, Varlıklar, İşlemler, Performans)

### 7. Bildirim Sistemi
- **Öncelik:** Orta
- **Süre:** ~4-5 saat
- **Özellikler:**
  - Fiyat alarmları (hedef fiyat, yüzde değişim)
  - Günlük özet e-postası
  - Strateji tetikleme bildirimi
- **Teknik:**
  - Background task (Celery veya Streamlit ile periyodik kontrol)
  - Email (SMTP)
  - In-app notifications

---

## 🚀 Uzun Vadeli Özellikler (1-2 hafta)

### 8. PWA (Progressive Web App)
- **Öncelik:** Yüksek
- **Süre:** ~1-2 gün
- **Açıklama:** Uygulamayı mobil cihazlara yüklenebilir hale getir
- **Özellikler:**
  - Offline çalışma
  - Push notifications
  - Home screen icon
  - Native app hissi
- **Teknik:**
  - Service Worker
  - Manifest.json
  - Cachelenmiş veri

### 9. Gelişmiş Analiz Dashboard'u
- **Öncelik:** Orta
- **Süre:** ~3-4 gün
- **Özellikler:**
  - Sektör analizi
  - Korelasyon matrisi
  - Risk analizi (VAR, Sharpe Ratio)
  - Monte Carlo simülasyonu
  - Backtesting

### 10. Sosyal Özellikler
- **Öncelik:** Düşük
- **Süre:** ~5-7 gün
- **Özellikler:**
  - Portföy paylaşma (gizlilik ayarlarıyla)
  - Topluluk önerileri
  - En iyi performans gösteren portföyler
  - Yorum ve tartışma
- **Teknik:**
  - Public/Private portföy ayarı
  - Social feed
  - Like/Comment sistemi

### 11. Mobil Uygulama
- **Öncelik:** Orta
- **Süre:** ~2-3 hafta
- **Açıklama:** React Native veya Flutter ile native mobil app
- **Özellikler:**
  - Tüm desktop özelliklerini içerir
  - Daha hızlı performans
  - Biometric giriş
  - Widget'lar

### 12. Eğitim Modülü
- **Öncelik:** Düşük
- **Süre:** ~1-2 hafta
- **Açıklama:** Yatırım eğitimi içerikleri
- **İçerik:**
  - Video dersler
  - Quiz'ler
  - Pratik senaryolar
  - Sertifika sistemi

---

## 🎨 UI/UX İyileştirmeleri

### Yapılacaklar:
- [ ] Tema geçiş animasyonu (smooth fade)
- [ ] Kompakt/Geniş layout modu
- [ ] Drag & drop ile portföy sıralaması
- [ ] Grafikte zoom ve pan özelliği
- [ ] Klavye kısayolları (hotkeys)
- [ ] Dark theme için OLED modu (pure black)
- [ ] Accessibility improvements (ARIA labels, keyboard navigation)
- [ ] Multi-language support (TR/EN başlangıç)

---

## 🔧 Teknik İyileştirmeler

### Yapılacaklar:
- [ ] Redis cache entegrasyonu
- [ ] Background task queue (Celery)
- [ ] Database indexleme optimizasyonu
- [ ] API rate limiting
- [ ] Error tracking (Sentry)
- [ ] Analytics (posthog, mixpanel)
- [ ] A/B testing framework
- [ ] Automated testing (pytest)
- [ ] CI/CD pipeline
- [ ] Docker containerization

---

## 📝 Notlar

**Güncel Durum:**
- ✅ Koyu/Açık tema sistemi çalışıyor
- ✅ Portföy detay dialog'ları düzgün
- ✅ Varlık ekleme/silme sistemi stabil
- ✅ Performans grafikleri aktif
- ✅ AI analiz çalışıyor

**Bir Sonraki Sprint:**
1. Açık tema kontrast iyileştirmesi (ŞİMDİ)
2. Tema tercihini kaydetme
3. PDF export
4. Portföy karşılaştırma

**Son Güncelleme:** 2026-02-04 19:07
