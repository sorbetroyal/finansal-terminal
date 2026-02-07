from utils import (get_current_data, load_portfolio, add_asset, remove_asset, delete_asset,
                   get_history, create_portfolio, delete_portfolio, save_all_portfolios, get_all_holdings, get_portfolio_history,
                   load_selected_portfolios, save_selected_portfolios, get_portfolio_metrics, fetch_all_prices_parallel,
                   load_alerts, add_alert, delete_alert, check_alerts, archive_alert, migrate_local_to_supabase, claim_orphaned_supabase_data, 
                   is_gold_tl_asset, get_asset_details, get_gemini_api_key, save_gemini_api_key,
                   get_watchlist, add_to_watchlist, remove_from_watchlist, get_strategy_signal,
                   calculate_kama, calculate_supertrend, calculate_obv, calculate_adx, calculate_technical_scores_bulk, PRICE_CACHE)
from auth import init_auth_state, get_current_user, render_auth_page, logout
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import requests
import time
import os
import google.generativeai as genai
import json
# --- HELPER: CRYPTO FEAR & GREED ---
@st.cache_data(ttl=3600)
def get_crypto_fng():
    try:
        import requests
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get("https://api.alternative.me/fng/?limit=1", headers=headers, timeout=5)
        if r.status_code == 200:
            return r.json().get("data", [{}])[0]
    except:
        return None
    return None

# ==================== DIALOG FUNCTIONS ====================

@st.dialog("🤖 Yapay Zeka Analizi", width="large")
def ai_analysis_dialog(portfolio_data):
    st.markdown("""
        <style>
            .ai-loading { color: #00f2ff; font-weight: 600; padding: 20px; text-align: center; }
            .ai-response { background: rgba(255,255,255,0.03); border-radius: 12px; padding: 20px; border: 1px solid rgba(255,255,255,0.05); color: #e0e0e0; line-height: 1.6; }
            .ai-response h1, .ai-response h2, .ai-response h3 { color: #00f2ff !important; margin-top: 20px; }
            .ai-response strong { color: #ffffff; }
            .key-input { background: rgba(255,255,255,0.05); border: 1px solid rgba(0,242,255,0.2); border-radius: 8px; padding: 10px; color: white; width: 100%; margin-bottom: 10px; }
        </style>
    """, unsafe_allow_html=True)

    api_key = get_gemini_api_key()
    
    if not api_key:
        st.info("💡 Portföy analizi yapabilmek için kendi **Gemini API Key**'inizi girmelisiniz.")
        st.markdown("""
            1. [Google AI Studio](https://aistudio.google.com/app/apikey) adresinden ücretsiz anahtarınızı alın.
            2. Aşağıdaki alana yapıştırıp kaydedin. Anahtarınız güvenli bir şekilde Supabase üzerinde saklanacaktır.
        """)
        new_key = st.text_input("Gemini API Key", type="password", placeholder="AIzaSy...")
        if st.button("Anahtarı Kaydet ve Devam Et"):
            if new_key:
                success, error_or_msg = save_gemini_api_key(new_key)
                if success:
                    st.success("API Anahtarı başarıyla kaydedildi!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"⚠️ Hata: {error_or_msg}")
                    st.info("İpucu: Eğer 'relation does not exist' hatası alıyorsanız, Supabase SQL Editor üzerinden tabloyu oluşturmalısınız.")
            else:
                st.warning("Lütfen bir anahtar girin.")
        return

    try:
        genai.configure(api_key=api_key)
        
        current_date_str = datetime.now().strftime("%d.%m.%Y")

        prompt = f"""
        Sen kıdemli bir finansal analist, portföy yöneticisi ve makroekonomistisin.
        Bugünün Tarihi: {current_date_str}

        Yatırımcı Profili:
        Risk Seviyesi: Orta-Yüksek
        Vade: Orta Uzun Vadeli
        Kıyaslama (Benchmark): Portföy performansını mutlaka Türkiye’deki güncel USD kuru ile kıyasla.

        Veri Seti: {portfolio_data} 
        (Not: Bu veri; maliyetler, güncel fiyatlar, son gün/hafta/ay kapanış verilerini ve fonların içindeki mikro varlık dağılımını (fon_icerikleri_ozeti) içermektedir.)

        Analiz Gereksinimleri:
        1. **Zamana Yayılmış Performans Analizi:** Son gün, son hafta ve son ay bazında portföyün nasıl bir trend izlediğini yorumla. 
        Toplam kâr/zarar durumunu, Türkiye enflasyonu karşısındaki reel kaybı veya kazancı net bir şekilde belirt.

        2. **Risk ve Volatilite Analizi:** Orta-yüksek risk profilime göre portföyün "stres testini" yap. Bütün varlıkları incele ve değerlendir.
        Sektörel yoğunlaşma (örn: sadece havacılık veya sadece banka) olup olmadığını denetle. 
        Portföydeki fon ve oks/bes fonlarının içindeki varlık dağılımını tabloya dök. Buna göre toplam BIST, ABD EFT/Hisse, altın/gümüş vb. oranları sun. 
        **Portföydeki fonların ve oks/bes fonlarının (fon_icerikleri_ozeti) içindeki varlık dağılımına bakarak, dolaylı yoldan artan riskleri (örn: fon içindeki aşırı hisse yoğunluğu) de dikkate al.** 
        Güncel trendlere göre riskleri sun.

        3. **Makroekonomik Bağlam:** Mevcut piyasa koşullarını (Merkez Bankası kararları, küresel faiz beklentileri ve jeopolitik durumlar) portföydeki varlıklarla ilişkilendirerek analiz et.

        4. **Stratejik Re-balans ve Somut Varlık Önerileri:** Performansı düşük olan veya risk dengesini bozan "zayıf halkaları" belirle. 
        **Önerilerini sadece genel kategorilerle sınırlama; doğrudan VARLIK İSİMLERİ (Örn: THYAO, GARAN, BTC, IPB Fonu vb.) vererek somut tavsiyelerde bulun.**
        Hangi varlıkta pozisyon azaltılmalı, hangisinde artırılmalı veya portföye yeni hangi spesifik varlıklar eklenebilir? Nedenleri ile açıkla.

        5. **Yatırımcı Disiplini (Notu):** Psikolojik olarak mevcut oynaklığı nasıl yönetmem gerektiğine dair kısa, etkili bir not ekle.

        Format: Analizi profesyonel bir dil ile, Markdown formatında, tablolar ve vurucu başlıklar kullanarak Türkçe sun.
        """

        with st.spinner("Gemini portföyünüzü analiz ediyor..."):
            # Attempt to use the latest Flash models (Note: 3.0 is not yet released, using 2.0 Flash as the current state-of-the-art)
            selected_model = None
            response = None
            last_error = ""
            # Priority list (bare names)
            priority_models = ['gemini-2.0-flash-exp', 'gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']
            
            for model_name in priority_models:
                try:
                    model = genai.GenerativeModel(model_name)
                    # Try a small test call if list_models is restricted
                    response = model.generate_content(prompt)
                    if response:
                        selected_model = model_name
                        break
                except Exception as e:
                    last_error = f"{model_name}: {str(e)}"
                    if "API_KEY_INVALID" in last_error or "400" in last_error:
                        break
                    continue
            
            # If priority fails, try to DISCOVER available models for this specific key
            if not response:
                try:
                    available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                    for m_name in available:
                        if m_name not in priority_models: # Don't retry failures
                            try:
                                model = genai.GenerativeModel(m_name)
                                response = model.generate_content(prompt)
                                if response:
                                    selected_model = m_name
                                    break
                            except: continue
                except: pass

            if not response:
                st.error(f"❌ Analiz motoru başlatılamadı.")
                st.markdown(f'<div style="background:rgba(255,0,0,0.1); padding:10px; border-radius:5px; font-size:0.8rem; color:#ffbaba;">Son Hata Detayı: {last_error}</div>', unsafe_allow_html=True)
                st.info("💡 Lütfen API anahtarınızın 'Generative AI' yetkisinin açık olduğunu ve doğru girildiğini kontrol edin.")
                st.session_state.trigger_ai_analysis = False
                return
                
            st.markdown(f'<div class="ai-response">{response.text}</div>', unsafe_allow_html=True)
            
    except Exception as e:
        st.error(f"Analiz sırasında bir hata oluştu: {e}")

@st.dialog("📈 Teknik Grafik", width="large")
def asset_chart_dialog(symbol, asset_type):
    # Ultra-aggressive CSS to force dark theme and white text in dialogs
    st.markdown("""
        <style>
            div[data-testid="stDialog"] > div:first-child, div[role="dialog"] { 
                background-color: #0b0e14 !important; 
            }
            div[data-testid="stDialog"] h3 { color: #00f2ff !important; margin-bottom: 20px; }
        </style>
    """, unsafe_allow_html=True)
    
    import plotly.graph_objects as go
    
    t = str(asset_type).lower()
    is_tefas = any(x in t for x in ["tefas", "fon", "bes", "oks"])
    is_bist = "bist" in t
    
    if is_tefas or is_bist:
        title_suffix = "Fiyat Geçmişi (TEFAS)" if is_tefas else "Teknik Grafik (BIST)"
        st.markdown(f"### {symbol} - {title_suffix}")
        
        with st.spinner("Veriler yükleniyor..."):
            hist = get_history(symbol, period="1y", asset_type=asset_type)
            
        if not hist.empty:
            fig = go.Figure()
            
            if is_bist and all(col in hist.columns for col in ['Open', 'High', 'Low', 'Close']):
                # Candlestick for BIST
                fig.add_trace(go.Candlestick(
                    x=hist.index,
                    open=hist['Open'],
                    high=hist['High'],
                    low=hist['Low'],
                    close=hist['Close'],
                    name=symbol,
                    increasing_line_color='#00ff88', 
                    decreasing_line_color='#ff3e3e'
                ))
            else:
                # Line chart for TEFAS or if OHLC is missing
                fig.add_trace(go.Scatter(
                    x=hist.index, 
                    y=hist['Close'],
                    name=symbol,
                    fill='tonexty',
                    fillcolor='rgba(0, 242, 255, 0.1)',
                    line=dict(color='#00f2ff', width=3),
                    hovertemplate='%{y:,.2f} TL<br>%{x}<extra></extra>'
                ))
            
            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=0, r=0, t=20, b=0),
                height=900,
                xaxis=dict(
                    showgrid=False, 
                    rangeslider=dict(visible=True, bgcolor='rgba(255,255,255,0.05)'),
                    type='date'
                ),
                yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', side="right", tickformat=",.2f"),
                hovermode="x unified"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.error("Veri alınamadı. Lütfen sembolü kontrol edin.")
    else:
        tv_sym = get_tradingview_symbol(symbol, asset_type)
        st.markdown(f"### {symbol} - Canlı Grafik")
        
        import streamlit.components.v1 as components
        
        # Using Direct Iframe for guaranteed height stability in Streamlit
        tv_url = f"https://s.tradingview.com/widgetembed/?symbol={tv_sym}&interval=D&hidesidetoolbar=0&symboledit=1&saveimage=1&toolbarbg=f1f3f6&theme=dark&style=1&timezone=Europe%2FIstanbul&locale=tr"
        
        tv_iframe = f"""
        <div style="height:800px; width:100%;">
            <iframe 
                src="{tv_url}"
                width="100%" 
                height="800" 
                frameborder="0" 
                allowfullscreen 
                scrolling="no"
                style="display:block; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1);"
            ></iframe>
        </div>
        """
        components.html(tv_iframe, height=820)

def get_tradingview_symbol(symbol, asset_type):
    s = str(symbol).upper().strip()
    t = str(asset_type).lower()
    
    if "bist" in t:
        return f"BIST:{s.replace('.IS', '')}"
    elif "kripto" in t:
        # Clean the base symbol
        base = s.replace("-USD", "").replace("-USDT", "").replace("USDT", "").replace("USD", "")
        
        # If the result is empty or it was originally USDT/USDC, show it against TRY
        if base == "" or s in ["USDT", "USDC", "BUSD"]:
            return "BINANCE:USDTTRY"
            
        return f"BINANCE:{base}USDT"
    elif "abd" in t:
        return s
    elif "döviz" in t:
        if any(x in s for x in ["USD", "USDT", "DOLAR"]): return "FX_IDC:USDTRY"
        if "EUR" in s: return "FX_IDC:EURTRY"
        if "GBP" in s: return "FX_IDC:GBPTRY"
        return s
    elif "emtia" in t:
        if "ALTIN" in s or "GC=F" in s or "XAU" in s: return "TVC:GOLD"
        if "GÜMÜŞ" in s or "GUMUS" in s or "SI=F" in s or "XAG" in s: return "TVC:SILVER"
        return s
    return s

@st.dialog("Portföy İçeriği", width="large")
def portfolio_details_dialog(p_name, p_list):
    # Aggressive CSS to ensure high-contrast colors and visibility
    st.markdown("""
        <style>
            /* Reset any transparency or dimming */
            div[role="dialog"] * { opacity: 1.0 !important; }
            
            /* Table Styling */
            .p-details-table { width: 100%; border-collapse: collapse; background-color: #0b0e14; border-radius: 12px; overflow: hidden; border: 1px solid rgba(255,255,255,0.15); }
            .p-details-table th { background: rgba(255,255,255,0.08); color: rgba(255,255,255,0.6) !important; padding: 15px; text-align: left; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; }
            .p-details-table td { padding: 15px; border-bottom: 1px solid rgba(255,255,255,0.05); }
            
            /* Explicit White for normal cells */
            .p-td-white { color: #FFFFFF !important; font-size: 0.9rem; }
            .p-td-muted { color: rgba(255,255,255,0.7) !important; font-size: 0.9rem; }
            
            /* Vibrant Profit/Loss */
            .val-green { color: #00ff88 !important; font-weight: 800 !important; font-size: 1rem !important; }
            .val-red { color: #ff3e3e !important; font-weight: 800 !important; font-size: 1rem !important; }
            .kz-sub { font-size: 0.75rem; font-weight: 400; opacity: 0.8 !important; margin-top: 2px; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown(f"<h3 style='color:#00f2ff !important; font-size:1.3rem; font-weight:700; margin-bottom:20px; text-shadow: 0 0 10px rgba(0,242,255,0.3);'>📂 {p_name} İçeriği</h3>", unsafe_allow_html=True)
    
    if not p_list:
        st.info("Bu portföyde henüz varlık bulunmuyor.")
        return

    rows = ""
    for h in p_list:
        curr = h.get("Para", "TL")
        try:
            t_val = float(h.get('Toplam (%)', 0))
            t_amt = float(h.get('Toplam_KZ', 0))
            d_val = float(h.get('Günlük (%)', 0))
            d_amt = float(h.get('Gunluk_KZ', 0))
        except:
            t_val = 0; t_amt = 0; d_val = 0; d_amt = 0
            
        # Determine CSS classes
        d_cls = "val-green" if d_val > 0 else ("val-red" if d_val < 0 else "p-td-white")
        t_cls = "val-green" if t_val > 0 else ("val-red" if t_val < 0 else "p-td-white")
        
        d_sign = "+" if d_val > 0 else ""
        t_sign = "+" if t_val > 0 else ""
        
        rows += f"""<tr>
            <td class="p-td-white" style="font-weight:700;">{h.get('Emoji', '💰')} {h.get('Varlık', '-')}</td>
            <td class="p-td-muted">{h.get('Adet', 0):,.2f}</td>
            <td class="p-td-muted">{h.get('Maliyet', 0):,.2f} {curr}</td>
            <td class="p-td-white">{h.get('Güncel', 0):,.2f} {curr}</td>
            <td class="p-td-white" style="font-weight:600;">{h.get('Deger', 0):,.2f} {curr}</td>
            <td class="{d_cls}">
                %{d_val:.2f}<br>
                <div class="kz-sub">({d_sign}{d_amt:,.2f} {curr})</div>
            </td>
            <td class="{t_cls}">
                %{t_val:.1f}<br>
                <div class="kz-sub">({t_sign}{t_amt:,.0f} {curr})</div>
            </td>
        </tr>"""

    st.markdown(f"""
    <div style="margin-bottom: 20px;">
        <table class="p-details-table">
            <thead>
                <tr>
                    <th>VARLIK</th>
                    <th>ADET</th>
                    <th>MALİYET</th>
                    <th>GÜNCEL</th>
                    <th>DEĞER</th>
                    <th>GÜNLÜK K/Z</th>
                    <th>TOPLAM K/Z</th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
    </div>
    """, unsafe_allow_html=True)

@st.dialog("➕ Varlık Yönetimi", width="large")
def asset_management_dialog():
    # Ultra-aggressive CSS to force dark theme and white text in dialogs
    st.markdown("""
        <style>
            /* 1. Dialog Background */
            div[data-testid="stDialog"] > div:first-child, div[role="dialog"] { 
                background-color: #0b0e14 !important; 
            }
            
            /* 2. Labels & General Text */
            div[data-testid="stDialog"] label, div[data-testid="stDialog"] p, div[data-testid="stDialog"] span { 
                color: #FFFFFF !important; 
            }
            
            /* 3. Input Containers (Text, Number, Select) */
            div[data-testid="stDialog"] [data-baseweb="input"], 
            div[data-testid="stDialog"] [data-baseweb="base-input"],
            div[data-testid="stDialog"] [data-baseweb="select"],
            div[data-testid="stDialog"] input,
            div[data-testid="stDialog"] select {
                background-color: #1a1c23 !important;
                color: white !important;
                border: 1px solid rgba(255,255,255,0.15) !important;
                border-radius: 8px !important;
            }

            /* 4. Force Input Text Color */
            div[data-testid="stDialog"] input {
                color: white !important;
                background-color: #1a1c23 !important;
                -webkit-text-fill-color: white !important;
            }

            /* 5. Selectbox Dropdown Fix (Inside Dialog) */
            [data-baseweb="popover"] div, [data-baseweb="menu"] div, [data-baseweb="menu"] li {
                background-color: #1a1c23 !important;
                color: white !important;
            }
            
            [data-baseweb="menu"] li:hover {
                background-color: rgba(0, 242, 255, 0.2) !important;
                color: #00f2ff !important;
            }
            
            /* 6. Tabs styling */
            .stTabs [data-baseweb="tab-list"] { background-color: transparent !important; }
            .stTabs [data-baseweb="tab"] { color: rgba(255,255,255,0.4) !important; }
            .stTabs [aria-selected="true"] { color: #00f2ff !important; border-bottom-color: #00f2ff !important; }
            
            /* 7. Radio Buttons */
            div[role="radiogroup"] label { color: white !important; }
        </style>
    """, unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["Varlık Ekle", "Varlık Sil"])
    all_p = st.session_state.get('all_p_list', [])

    if not all_p:
        st.warning("⚠️ Önce bir portföy oluşturmalısınız!")
        if st.button("📁 Portföy Yönetimine Git"):
            st.session_state.show_asset_modal = False
            st.session_state.show_portfolio_modal = True
            st.rerun()
        return

    with tab1:
        st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)

        # Better way to handle auto-fill without flaky callbacks
        s_input = st.session_state.get("add_symbol", "").strip().upper()
        t_input = st.session_state.get("add_type", "bist hisse")
        
        # Track previous to detect change
        if "last_s" not in st.session_state: st.session_state.last_s = ""
        if "last_t" not in st.session_state: st.session_state.last_t = ""
        
        if (s_input != st.session_state.last_s or t_input != st.session_state.last_t) and s_input:
            # Standardization
            fs = s_input
            if "bist" in t_input.lower() and not fs.endswith(".IS"): fs = f"{fs}.IS"
            elif "kripto" in t_input.lower() and "-" not in fs: fs = f"{fs}-USD"
            elif "döviz" in t_input.lower():
                if fs == "USD": fs = "USDTRY=X"
                elif fs in ["EUR", "EYR"]: fs = "EURTRY=X"
            
            # Fetch
            d = get_current_data(fs, t_input)
            if d:
                # DIRECTLY SET THE WIDGET STATE KEY
                st.session_state["add_cost_widget"] = float(d["price"])
                st.session_state.last_s = s_input
                st.session_state.last_t = t_input
                st.rerun()
            
            st.session_state.last_s = s_input
            st.session_state.last_t = t_input

        with col1:
            selected_portfolio = st.selectbox("📁 Portföy Seçin", all_p, key="add_portfolio")
            asset_type = st.selectbox("📊 Varlık Tipi", [
                "bist hisse", "abd hisse/etf", "tefas fon", "kripto", "döviz", "emtia", "eurobond", "bes/oks", "nakit"
            ], key="add_type")
            
            # Helper for Cash
            ph_text = "🔤 Varlık Sembolü"
            if asset_type == "nakit":
                 ph_text = "Tanım (Örn: TL, Kasa)"
                 
            asset_symbol = st.text_input(ph_text, key="add_symbol").strip().upper()
        
        with col2:
            asset_amount = st.number_input("🔢 Adet (Miktar)", min_value=0.0, value=1.0, step=0.0001, format="%.4f", key="add_amount")
            # The widget now takes its value directly from the session_state key modified above
            
            # Auto-set cost for Cash
            val_cost = 0.0
            if asset_type == "nakit":
                 val_cost = 1.0
            
            asset_cost = st.number_input("💰 Birim Maliyet", min_value=0.0, value=val_cost, step=0.0001, format="%.4f", key="add_cost_widget")

            purchase_date = st.date_input("📅 Alış Tarihi", value=datetime.now(), key="add_date")
        
        st.markdown("<div style='margin-top:25px;'></div>", unsafe_allow_html=True)
        if asset_symbol and asset_amount is not None and asset_cost is not None:
            # Calculate total impact
            rate = 1.0
            if asset_type in ["abd hisse/etf", "kripto"]:
                usd_data = get_current_data("USDTRY=X", "döviz")
                rate = usd_data["price"] if usd_data else 34.0
            
            total_val = asset_amount * asset_cost * rate
            
            st.markdown(f"""
                <div style="background:rgba(0, 242, 255, 0.05); border:1px solid rgba(0, 242, 255, 0.2); border-radius:10px; padding:15px; margin-top:10px;">
                    <div style="color:rgba(255,255,255,0.6); font-size:0.75rem;">Eklenecek Toplam Değer:</div>
                    <div style="color:#00f2ff; font-weight:700; font-size:1.2rem;">{total_val:,.2f} TL</div>
                </div>
            """, unsafe_allow_html=True)
            
            high_value = total_val > 500000 # 500k limit for warning
            
            if high_value:
                st.warning("⚠️ Girdiğiniz miktar portföy için oldukça yüksek görünüyor. Lütfen rakamları kontrol edin.")
                confirm = st.checkbox("Rakamların doğruluğunu onaylıyorum", key="entry_confirm")
            else:
                confirm = True

            st.markdown("<div style='margin-top:15px;'></div>", unsafe_allow_html=True)
            if st.button("🚀 Varlık Ekle", type="primary", use_container_width=True, disabled=not confirm):
                valid_data = get_current_data(asset_symbol, asset_type)
                
                if valid_data:
                    success = add_asset(selected_portfolio, asset_symbol, asset_amount, asset_cost, asset_type, purchase_date.strftime("%Y-%m-%d"))
                    if success:
                        st.success(f"✅ {asset_symbol} eklendi!")
                        # FORCE CACHE CLEAR on new entries to fix graph immediately
                        st.cache_data.clear()
                        st.session_state.show_asset_modal = False
                        st.rerun()
                    else: 
                        st.error("❌ Hata.")
                else:
                    st.error(f"❌ '{asset_symbol}' bulunamadı!")
        else: 
            st.write("") # Placeholder


    
    with tab2:
        st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            remove_portfolio = st.selectbox("📁 Portföy Seçin", all_p, key="remove_portfolio")
            # Fresh holdings data
            fresh_holdings = get_all_holdings()
            p_holdings = [h for h in fresh_holdings if h["p"] == remove_portfolio]
            h_symbols = sorted(list(set([h["symbol"] for h in p_holdings])))
            
            r_symbol = None
            if h_symbols:
                r_symbol = st.selectbox("📝 Varlık Seçin", h_symbols, key="remove_symbol")
                s_holdings = [h for h in p_holdings if h["symbol"] == r_symbol]
                p_dates = sorted(list(set([h["purchase_date"] for h in s_holdings])))
                r_date = st.selectbox("📅 Alış Tarihi", p_dates, key="remove_date")
            else:
                st.info("Bu portföyde varlık bulunmuyor.")

        with col2:
            if r_symbol:
                r_action = st.radio("⚙️ İşlem Tipi", ["Varlık Sat", "Sadece Sil (Satmadan)"], key="remove_action")
                if r_action == "Varlık Sat":
                    r_amount = st.number_input("🔢 Satılacak Adet", min_value=0.0, value=None, placeholder="1.0", step=0.0001, format="%.4f", key="remove_amount")
                    r_price = st.number_input("💰 Satış Fiyatı", min_value=0.0, value=None, placeholder="0.00", step=0.01, key="remove_price")

                    if st.button("🗑️ Varlığı Sat", type="primary", use_container_width=True):
                        # Add None checks before comparison
                        if r_amount is not None and r_price is not None and r_amount > 0 and r_price > 0:
                            success = remove_asset(remove_portfolio, r_symbol, r_amount, r_price, r_date)
                            if success:
                                st.success(f"✅ Satış başarılı!")
                                st.session_state.show_asset_modal = False
                                st.rerun()
                            else: st.error("❌ Hata.")
                        else: st.warning("⚠️ Lütfen satılacak adet ve satış fiyatını girin.")
                else:
                    if st.button("❌ Portföyden Kalıcı Olarak Sil", type="primary", use_container_width=True):
                        success = delete_asset(remove_portfolio, r_symbol, r_date)
                        if success:
                            st.success(f"✅ Silindi!")
                            st.session_state.show_asset_modal = False
                            st.rerun()
                        else: st.error("❌ Hata.")

@st.dialog("📁 Portföy Yönetimi", width="medium")
def portfolio_management_dialog():
    # Global CSS handles dialog theme
    pass

    
    all_p = st.session_state.get('all_p_list', [])

    # SELECTION SECTION (Filter for totals)
    st.markdown('<p style="color: rgba(255,255,255,0.9); font-size: 1rem; font-weight: 600; margin-bottom: 10px;">📊 Hesaplama Filtresi</p>', unsafe_allow_html=True)
    
    def on_selection_change():
        """Save selected portfolios when selection changes."""
        new_selection = st.session_state.p_filter_select
        st.session_state.selected_p = new_selection
        save_selected_portfolios(new_selection)
    
    st.multiselect(
        "Genel toplama dahil edilecek olanları seçin",
        all_p,
        default=st.session_state.selected_p if st.session_state.selected_p else all_p,
        key="p_filter_select",
        on_change=on_selection_change
    )
    
    # Update button to refresh the page
    if st.button("🔄 Güncelle ve Kapat", type="primary", use_container_width=True):
        st.session_state.show_portfolio_modal = False
        st.rerun()

    st.markdown('<div style="margin: 15px 0; border-bottom: 1px solid rgba(255,255,255,0.1);"></div>', unsafe_allow_html=True)

    # NEW PORTFOLIO SECTION (compact form)
    st.markdown('<p style="color: rgba(255,255,255,0.9); font-size: 1rem; font-weight: 600; margin-bottom: 5px;">➕ Yeni Portföy Ekle</p>', unsafe_allow_html=True)
    with st.form("new_portfolio_form", clear_on_submit=True):
        col1, col2 = st.columns([3, 1])
        with col1:
            new_name = st.text_input("Portföy Adı", placeholder="Örn: Emeklilik Hesabı", label_visibility="collapsed")
        with col2:
            submit = st.form_submit_button("Ekle", type="primary", use_container_width=True)
            
        if submit:
            if new_name.strip():
                if create_portfolio(new_name.strip()):
                    # Automatically add to selection
                    if "selected_p" in st.session_state:
                        if new_name.strip() not in st.session_state.selected_p:
                            st.session_state.selected_p.append(new_name.strip())
                            save_selected_portfolios(st.session_state.selected_p)
                    st.success(f"✅ '{new_name}' oluşturuldu!")
                    # Close modal after success to avoid lingering state
                    st.session_state.show_portfolio_modal = False
                    st.rerun()
                else:
                    st.error("❌ Bu isimde bir portföy zaten var veya bir hata oluştu.")
            else:
                st.warning("⚠️ Lütfen bir isim girin.")
    
    st.markdown('<div style="margin: 15px 0; border-bottom: 1px solid rgba(255,255,255,0.1);"></div>', unsafe_allow_html=True)
    
    # MIGRATION SECTION
    st.markdown('<p style="color: rgba(255,255,255,0.9); font-size: 1rem; font-weight: 600; margin-bottom: 5px;">📥 Yerel Verileri Aktar</p>', unsafe_allow_html=True)
    st.markdown('<p style="color: rgba(255,255,255,0.5); font-size: 0.8rem; margin-bottom: 15px;">Supabase öncesi yazdığınız verileri buraya aktarabilirsiniz.</p>', unsafe_allow_html=True)
    
    if st.button("📁 portfolio.json'dan Verileri Aktar", use_container_width=True):
        success, message = migrate_local_to_supabase()
        if success:
            st.success(message)
            st.rerun()
        else:
            # Try the backup location if root not found or empty
            success, message = migrate_local_to_supabase("backups/v1_stable/portfolio.json")
            if success:
                st.success(message)
                st.rerun()
            else:
                st.error("Yerel veri bulunamadı.")

    if st.button("🔗 Supabase'deki Sahipsiz Verileri Hesabıma Tanımla", use_container_width=True):
        success, message = claim_orphaned_supabase_data()
        if success:
            st.success(message)
            st.rerun()
        else:
            st.info(message)

    st.markdown('<div style="margin: 15px 0; border-bottom: 1px solid rgba(255,255,255,0.1);"></div>', unsafe_allow_html=True)

@st.dialog("📋 İşlem Geçmişi Listesi", width="large")
def transaction_history_dialog():
    st.markdown("""
        <style>
            .trans-row {
                background: rgba(255, 255, 255, 0.03);
                border-radius: 10px;
                padding: 15px;
                margin-bottom: 15px;
                border: 1px solid rgba(255, 255, 255, 0.05);
            }
            .trans-symbol { color: #00f2ff; font-weight: 700; font-size: 1.1rem; }
            .trans-meta { color: rgba(255,255,255,0.4); font-size: 0.8rem; margin-top: 4px; }
            .trans-details { color: white; font-weight: 500; font-size: 0.9rem; margin-top: 8px; }
        </style>
    """, unsafe_allow_html=True)
    
    all_h = get_all_holdings()
    if not all_h:
        st.info("Henüz kayıtlı bir işlem bulunmuyor.")
        return
        
    all_h.sort(key=lambda x: x.get('purchase_date', '2000-01-01'), reverse=True)
    
    for i, h in enumerate(all_h):
        with st.container():
            col_text, col_btn = st.columns([5, 1])
            with col_text:
                total_cost = h['amount'] * h['cost']
                st.markdown(f"""
                    <div class="trans-row">
                        <div class="trans-symbol">{h['symbol']} <span style="font-size:0.75rem; font-weight:400; color:rgba(255,255,255,0.3);">| {h['p']}</span></div>
                        <div class="trans-meta">📅 {h['purchase_date']} | 🏷️ {h['type'].upper()}</div>
                        <div class="trans-details">
                            {h['amount']:,} adet @ {h['cost']:,} TL
                            <br>
                            <span style="color:rgba(255,255,255,0.5); font-size:0.8rem;">Toplam Maliyet: {total_cost:,.2f} TL</span>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
            with col_btn:
                st.markdown("<div style='margin-top:25px;'></div>", unsafe_allow_html=True)
                if st.button("🗑️ Sil", key=f"dialog_del_{i}", use_container_width=True):
                    if delete_asset(h['p'], h['symbol'], h['purchase_date']):
                        st.success(f"{h['symbol']} silindi.")
                        st.cache_data.clear()
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("Silinemedi.")

    
    # EXISTING PORTFOLIOS SECTION (compact grid)

    st.markdown('<p style="color: rgba(255,255,255,0.9); font-size: 1rem; font-weight: 600; margin-bottom: 10px;">📂 Portföyleriniz</p>', unsafe_allow_html=True)
    
    portfolios_fresh = load_portfolio()
    all_portfolios_fresh = list(portfolios_fresh["portfolios"].keys())
    
    if all_portfolios_fresh:
        for idx, portfolio_name in enumerate(all_portfolios_fresh):
            # Get portfolio stats
            portfolio_holdings = [h for h in get_all_holdings() if h["p"] == portfolio_name]
            num_assets = len(portfolio_holdings)
            
            # Calculate total value
            total_value = 0
            for h in portfolio_holdings:
                curr_d = get_current_data(h["symbol"], h.get("type"))
                if curr_d:
                    total_value += curr_d["price"] * h["amount"]
            
            # Compact card
            col_card, col_btn1, col_btn2 = st.columns([6, 1, 1])
            
            with col_card:
                # Determine glow color based on value
                glow_color = "0, 242, 255" if total_value > 0 else "255, 255, 255"
                
                st.markdown(f"""
                <div style="background: rgba(11, 14, 20, 0.8); border: 1px solid rgba({glow_color}, 0.2); border-radius: 8px; padding: 12px 16px; box-shadow: 0 0 15px rgba({glow_color}, 0.1);">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div><span style="color: rgba(255,255,255,0.95); font-size: 1rem; font-weight: 600;">📁 {portfolio_name}</span></div>
                        <div style="text-align: right;">
                            <span style="color: rgba(255,255,255,0.5); font-size: 0.75rem;">{num_assets} varlık</span><br>
                            <span style="color: rgba({glow_color}, 0.9); font-size: 0.85rem; font-weight: 600;">₺{total_value:,.0f}</span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            with col_btn1:
                st.write("")
                st.button("✏️", key=f"edit_p_{idx}", use_container_width=True, disabled=True)
            
            with col_btn2:
                st.write("")
                if len(all_portfolios_fresh) > 1:
                    if st.button("🗑️", key=f"del_p_{idx}", use_container_width=True):
                        if delete_portfolio(portfolio_name):
                            st.success("✅ Silindi!")
                            # Update selected list if deleted portfolio was in it
                            if "selected_p" in st.session_state and portfolio_name in st.session_state.selected_p:
                                st.session_state.selected_p.remove(portfolio_name)
                                save_selected_portfolios(st.session_state.selected_p)
                            st.rerun()
                        else:
                            st.error("❌ Hata!")
                else:
                    st.button("🗑️", key=f"delete_{idx}", use_container_width=True, disabled=True, help="En az 1 portföy gerekli")
    else:
        st.info("ℹ️ Henüz portföy yok.")

# ==================== PAGE CONFIG & AUTH ====================
st.set_page_config(page_title="Finansal Terminal", layout="wide", initial_sidebar_state="collapsed")
init_auth_state()

if not get_current_user():
    render_auth_page()
    st.stop()

# Initialize theme BEFORE CSS
if "theme" not in st.session_state:
    st.session_state.theme = "dark"  # Default: Dark mode

# PREMIUM MODERN DESIGN SYSTEM (v4) - DYNAMIC THEME
# Theme Colors
theme = st.session_state.theme
if theme == "dark":
    bg_primary = "#0b0e14"
    bg_secondary = "#1a1c23"
    bg_card = "rgba(255,255,255,0.05)"
    bg_card_hover = "rgba(255,255,255,0.08)"
    text_primary = "#ffffff"
    text_secondary = "rgba(255,255,255,0.7)"
    text_muted = "rgba(255,255,255,0.4)"
    border_color = "rgba(255,255,255,0.1)"
    accent_color = "#00f2ff"
    accent_glow = "rgba(0,242,255,0.3)"
else:  # light theme - IMPROVED CONTRAST
    bg_primary = "#f8f9fa"
    bg_secondary = "#ffffff"
    bg_card = "rgba(255, 255, 255, 0.95)"  # More opaque cards
    bg_card_hover = "rgba(0, 0, 0, 0.08)"  # Stronger hover
    text_primary = "#0a0a0a"  # Much darker for readability
    text_secondary = "rgba(0, 0, 0, 0.75)"  # Darker secondary
    text_muted = "rgba(0, 0, 0, 0.55)"  # Darker muted
    border_color = "rgba(0, 0, 0, 0.15)"  # Stronger borders
    accent_color = "#0055ff"  # More vibrant blue
    accent_glow = "rgba(0, 85, 255, 0.25)"  # Stronger glow

st.markdown(f"""
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
<style>
    /* 1. Global & Background */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');
    * {{ font-family: 'Outfit', sans-serif !important; }}
    
    header[data-testid="stHeader"] {{ display: none !important; }}
    
    html, body, [data-testid="stAppViewContainer"], .stApp, [data-testid="stAppViewBlockContainer"], .block-container {{
        background-color: {bg_primary} !important;
        padding-top: 0rem !important;
        margin-top: 0rem !important;
        color: {text_primary} !important;
    }}

    .main .block-container {{ 
        padding-left: 0 !important;
        padding-right: 0 !important;
        max-width: 100% !important; 
        min-height: 100vh;
    }}

    /* Remove Sidebar */
    section[data-testid="stSidebar"] {{
        display: none !important;
    }}
    button[kind="header"] {{
        display: none !important;
    }}

    /* Selectbox Visibility Fix */
    div[data-baseweb="select"] > div {{
        background-color: {bg_card} !important;
        border: 1px solid {border_color} !important;
        color: {text_primary} !important;
        font-weight: 600 !important;
    }}
    [data-baseweb="popover"] ul {{
        background-color: {bg_secondary} !important;
        border: 1px solid {border_color} !important;
    }}
    [data-baseweb="popover"] li {{
        background-color: {bg_secondary} !important;
        color: {text_primary} !important;
        font-family: 'Outfit', sans-serif !important;
    }}
    [data-baseweb="popover"] li:hover {{
        background-color: {accent_color} !important;
        color: {bg_primary} !important;
    }}
    div.stSelectbox div[role="listbox"] {{
        background-color: {bg_secondary} !important;
    }}
    div[data-baseweb="select"] svg {{
        fill: {text_primary} !important;
    }}

    /* Modal Close Button Fix */
    div[data-testid="stDialog"] button[aria-label="Close"] {{
        color: {text_primary} !important;
        opacity: 1 !important;
        background-color: {bg_card} !important;
        border-radius: 50%;
        transition: all 0.2s;
    }}
    div[data-testid="stDialog"] button[aria-label="Close"]:hover {{
        background-color: rgba(255, 62, 62, 0.8) !important;
        transform: scale(1.1);
    }}
    div[data-testid="stDialog"] button[aria-label="Close"] svg {{
        fill: white !important;
        stroke: white !important;
    }}

    .glass-nav {{
        position: sticky;
        top: 0;
        z-index: 999999;
        background: {f'rgba(11, 14, 20, 0.95)' if theme == 'dark' else 'rgba(248, 249, 250, 0.95)'};
        backdrop-filter: blur(20px);
        border-bottom: 1px solid {border_color};
        padding: 5px 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        height: 50px;
    }}

    .glass-card {{
        background: {f'rgba(23, 27, 33, 0.7)' if theme == 'dark' else 'rgba(255, 255, 255, 0.9)'};
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid {border_color};
        border-radius: 16px;
        box-shadow: 0 8px 32px 0 {f'rgba(0, 0, 0, 0.4)' if theme == 'dark' else 'rgba(0, 0, 0, 0.08)'};
        margin-bottom: 20px;
    }}
    
    .text-glow-green {{ color: #00ff88 !important; text-shadow: 0 0 10px rgba(0, 255, 136, 0.3) !important; }}
    .text-glow-red {{ color: #ff3e3e !important; text-shadow: 0 0 10px rgba(255, 62, 62, 0.3) !important; }}
    .text-glow-cyan {{ color: {accent_color} !important; text-shadow: 0 0 10px {accent_glow} !important; }}
    
    .metric-label {{ color: {text_muted}; font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; }}
    .metric-value {{ color: {text_primary}; font-size: 1.4rem; font-weight: 700; margin-top: 5px; }}

    /* Active Tab Button Styling (Primary) */
    div.stButton > button[kind="primary"] {{
        background-color: transparent !important;
        color: {accent_color} !important;
        border: none !important;
        border-bottom: 2px solid {accent_color} !important;
        border-radius: 0 !important;
        font-weight: 700 !important;
        box-shadow: none !important;
    }}
    div.stButton > button[kind="secondary"] {{
        background-color: transparent !important;
        border: none !important;
        color: {text_secondary} !important;
        box-shadow: none !important;
    }}
    div.stButton > button:focus {{
        color: {text_primary} !important;
        border-color: transparent !important;
        box-shadow: none !important;
    }}

    .ticker-bar {{
        background: {bg_card};
        border-bottom: 1px solid {border_color};
        padding: 8px 0;
        overflow: hidden;
        white-space: nowrap;
        width: 100%;
    }}
    .ticker-wrapper {{
        display: inline-block;
        animation: ticker 60s linear infinite;
    }}
    @keyframes ticker {{
        0% {{ transform: translateX(0); }}
        100% {{ transform: translateX(-50%); }}
    }}
    .ticker-item {{
        display: inline-block;
        margin-right: 40px;
        font-size: 0.85rem;
        font-weight: 600;
    }}
    
    .nav-tab {{
        color: {text_muted};
        font-weight: 600;
        font-size: 0.85rem;
        padding: 5px 0;
        cursor: pointer;
        transition: all 0.3s;
        border-bottom: 2px solid transparent;
    }}
    .nav-tab.active {{
        color: {accent_color};
        border-bottom: 2px solid {accent_color};
    }}
    .nav-tab:hover {{
        color: {text_primary};
    }}

    .flex {{ display: flex; }}
    .gap-6 {{ gap: 1.5rem; }}
    .mb-8 {{ margin-bottom: 2rem; }}
    
    .metric-card {{
        padding: 20px;
        flex: 1;
        text-align: center;
        min-width: 150px;
    }}

    .modern-table {{
        width: 100%;
        border-collapse: collapse;
        margin-top: 10px;
    }}
    .modern-table th {{
        text-align: left;
        color: rgba(255, 255, 255, 0.4);
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1px;
        padding: 12px 15px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    }}
    .modern-table td {{
        padding: 15px;
        font-size: 0.85rem;
        color: rgba(255, 255, 255, 0.8);
        border-bottom: 1px solid rgba(255, 255, 255, 0.03);
    }}
    .modern-table tr:hover {{
        background: rgba(255, 255, 255, 0.02);
    }}

    div.stButton > button, div.stButton > button p, div.stButton > button span {{
        white-space: nowrap !important;
        font-size: 0.78rem !important;
    }}
    div.stButton > button {{
        background: rgba(255, 255, 255, 0.03) !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-radius: 8px !important;
        color: rgba(255, 255, 255, 0.7) !important;
        font-weight: 600 !important;
        padding: 0px 15px !important;
        min-height: 38px !important;
        height: 38px !important;
        width: auto !important;
    }}
    div.stButton > button:hover {{
        background: rgba(0, 242, 255, 0.1) !important;
        border-color: #00f2ff !important;
    }}
    
    /* Segmented Control Dark Theme */
    div[data-baseweb="segmented-control"] {{
        background: rgba(23, 27, 33, 0.9) !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        border-radius: 8px !important;
    }}
    div[data-baseweb="segmented-control"] button {{
        background: transparent !important;
        color: rgba(255, 255, 255, 0.5) !important;
        font-weight: 600 !important;
        font-size: 0.8rem !important;
    }}
    div[data-baseweb="segmented-control"] button[aria-checked="true"] {{
        background: rgba(0, 242, 255, 0.25) !important;
        color: #00f2ff !important;
    }}
    div[data-baseweb="segmented-control"] button:hover {{
        color: white !important;
    }}
    
    /* ULTIMATE INPUT UNIFICATION */
    /* Target every possible text container in these widgets */
    div[data-testid="stTextInput"] input,
    div[data-testid="stNumberInput"] input,
    div[data-baseweb="select"] [data-testid="stMarkdownContainer"] p,
    div[data-baseweb="select"] div[aria-selected="true"],
    div[data-baseweb="select"] span,
    div[data-baseweb="input"] input {{
        font-size: 0.9rem !important;
        font-weight: 600 !important; /* Semi-Bold for all */
        font-family: 'Outfit', sans-serif !important;
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
        line-height: 45px !important;
        padding-top: 0 !important;
        padding-bottom: 0 !important;
    }}

    /* Container Box Consistency - Flexible height for multiselect */
    div[data-baseweb="select"] > div,
    div[data-baseweb="input"],
    div[data-baseweb="base-input"],
    div[data-testid="stTextInput"] > div > div,
    div[data-testid="stNumberInput"] > div > div {{
        background-color: #1a1c23 !important; 
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        border-radius: 8px !important;
        min-height: 45px !important; /* Allowed to grow */
        height: auto !important;
    }}

    /* Target the text/input elements inside - remove forced line-height that prevents wrapping */
    div[data-testid="stTextInput"] input,
    div[data-testid="stNumberInput"] input,
    div[data-baseweb="select"] [data-testid="stMarkdownContainer"] p,
    div[data-baseweb="select"] div[aria-selected="true"],
    div[data-baseweb="select"] span {{
        font-size: 0.9rem !important;
        font-weight: 600 !important;
        font-family: 'Outfit', sans-serif !important;
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
        padding-top: 5px !important; /* Balanced padding for multi-line */
        padding-bottom: 5px !important;
    }}

    /* Placeholder Unification */
    ::placeholder,
    div[data-baseweb="select"] [data-baseweb="select"] div[aria-hidden="true"] {{
        color: rgba(255, 255, 255, 0.4) !important;
        -webkit-text-fill-color: rgba(255, 255, 255, 0.4) !important;
        font-weight: 600 !important;
    }}
    
    /* Remove borders and paddings from inner inputs */
    div[data-testid="stTextInput"] input,
    div[data-testid="stNumberInput"] input {{
        border: none !important;
        background: transparent !important;
        padding-left: 12px !important;
        outline: none !important;
    }}

    div[data-testid="stTextInput"] label,
    div[data-testid="stNumberInput"] label {{
        color: rgba(255, 255, 255, 0.5) !important;
        font-size: 0.8rem !important;
        font-weight: 500 !important;
        margin-bottom: 4px !important;
    }}

    /* Hide number input spinners and step buttons */
    div[data-testid="stNumberInput"] button {{
        display: none !important;
    }}

    /* DIALOG & MODAL UNIFICATION (v4) */
    div[data-testid="stDialog"] > div:first-child, div[role="dialog"] {{
        background-color: #0b0e14 !important;
        border: 1px solid rgba(0, 242, 255, 0.1) !important;
        box-shadow: 0 0 50px rgba(0, 0, 0, 0.8) !important;
    }}
    
    div[data-testid="stDialog"] h1, 
    div[data-testid="stDialog"] h2, 
    div[data-testid="stDialog"] h3, 
    div[data-testid="stDialog"] p, 
    div[data-testid="stDialog"] label, 
    div[data-testid="stDialog"] span {{
        color: #FFFFFF !important;
    }}

    /* MULTISELECT PILLS (TAGS) UNIFICATION */
    div[data-baseweb="tag"] {{
        background-color: rgba(0, 242, 255, 0.15) !important;
        border: 1px solid rgba(0, 242, 255, 0.3) !important;
        border-radius: 4px !important;
    }}
    div[data-baseweb="tag"] span {{
        color: #00f2ff !important;
        font-weight: 600 !important;
    }}
    div[data-baseweb="tag"] svg {{
        fill: #00f2ff !important;
    }}
    
    /* FORM & TAB UNIFICATION IN DIALOGS */
    div[data-testid="stDialog"] .stTabs [data-baseweb="tab-list"] {{ background-color: transparent !important; }}
    div[data-testid="stDialog"] .stTabs [data-baseweb="tab"] {{ color: rgba(255,255,255,0.4) !important; }}
    div[data-testid="stDialog"] .stTabs [aria-selected="true"] {{ color: #00f2ff !important; border-bottom-color: #00f2ff !important; }}
    
    div[data-testid="stForm"] {{
        background-color: rgba(255,255,255,0.02) !important;
        border: 1px solid rgba(255,255,255,0.05) !important;
        border-radius: 12px !important;
    }}
    /* Ultimate Neon Toast Styling */
    div[data-testid="stToast"] {{
        background: rgba(11, 14, 20, 0.95) !important;
        backdrop-filter: blur(20px) !important;
        border: 2px solid #00f2ff !important;
        border-radius: 12px !important;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.6), 0 0 20px rgba(0, 242, 255, 0.2) !important;
        width: 400px !important;
    }}
    div[data-testid="stToast"] [data-testid="stMarkdownContainer"] p {{
        color: white !important;
        font-weight: 700 !important;
        font-size: 1.05rem !important;
    }}
    /* Dynamic Colors based on content */
    div[data-testid="stToast"]:has(p:contains("AL SİNYALİ")) {{
        border-color: #00ff88 !important;
        box-shadow: 0 0 30px rgba(0, 255, 136, 0.3) !important;
    }}
    div[data-testid="stToast"]:has(p:contains("SAT SİNYALİ")) {{
        border-color: #ff3e3e !important;
        box-shadow: 0 0 30px rgba(255, 62, 62, 0.3) !important;
    }}
</style>

""", unsafe_allow_html=True)

# 1. INITIAL SESSION STATE & DATA LOAD (TOP PRIORITY FOR SPEED)
if "show_asset_modal" not in st.session_state: st.session_state.show_asset_modal = False
if "show_history_modal" not in st.session_state: st.session_state.show_history_modal = False
if "show_portfolio_modal" not in st.session_state: st.session_state.show_portfolio_modal = False
if "show_portfolio_details" not in st.session_state: st.session_state.show_portfolio_details = False
if "portfolio_details_name" not in st.session_state: st.session_state.portfolio_details_name = None
if "portfolio_details_data" not in st.session_state: st.session_state.portfolio_details_data = []
if "active_tab" not in st.session_state: st.session_state.active_tab = "PORTFÖYÜM"
if "chart_asset" not in st.session_state: st.session_state.chart_asset = None
if "chart_asset_type" not in st.session_state: st.session_state.chart_asset_type = None

portfolio_data = load_portfolio()
all_portfolios = list(portfolio_data["portfolios"].keys())
st.session_state['all_p_list'] = all_portfolios

if "selected_p" not in st.session_state:
    saved_selected = load_selected_portfolios()
    st.session_state.selected_p = [p for p in saved_selected if p in all_portfolios] if saved_selected else all_portfolios.copy()
else:
    # Crucial: Always filter out deleted portfolios to prevent multiselect errors
    st.session_state.selected_p = [p for p in st.session_state.selected_p if p in all_portfolios]
    if not st.session_state.selected_p and all_portfolios:
        st.session_state.selected_p = all_portfolios.copy()


all_holdings = get_all_holdings()

# 2. BULK PRE-FETCH (Everything in one go)
ticker_symbols = [
    ("BIST100", "XU100.IS"), ("BIST30", "XU030.IS"), ("NASDAQ", "^IXIC"), 
    ("S&P 500", "^GSPC"), ("VIX", "^VIX"), ("DAX", "^GDAXI"), ("NIKKEI", "^N225"),
    ("ALTIN", "ALTIN"), ("GÜMÜŞ", "GÜMÜŞ"), ("DOLAR", "USDTRY=X"), 
    ("EURO", "EURTRY=X"), ("BTC", "BTC-USD"), ("ETH", "ETH-USD")
]

if "portfolio_data_loaded" not in st.session_state:
    st.session_state.portfolio_data_loaded = False

# Only fetch if not loaded or specifically requested
if not st.session_state.portfolio_data_loaded:
    with st.spinner("🚀 Veriler güncelleniyor..."):
        # Add actual tickers for aliases like ALTIN/GÜMÜŞ to pre-fetch their dependencies
        extra_tickers = [{"symbol": "GC=F", "type": "ticker"}, {"symbol": "SI=F", "type": "ticker"}]
        fetch_list = all_holdings + [{"symbol": s[1], "type": "ticker"} for s in ticker_symbols] + extra_tickers
        fetch_list += [{"symbol": "USDTRY=X", "type": "döviz"}, {"symbol": "ALTIN", "type": "emtia"}, {"symbol": "GÜMÜŞ", "type": "emtia"}]
        fetch_all_prices_parallel(fetch_list)
        st.session_state.portfolio_data_loaded = True

# Periodic Check & Notification System
if "notified_ids" not in st.session_state: st.session_state.notified_ids = set()
if "last_alert_check" not in st.session_state: st.session_state.last_alert_check = 0

# Check frequently (every 5s) for instant reaction
if time.time() - st.session_state.last_alert_check > 5:
    new_hits = check_alerts()
    if new_hits:
        has_new = False
        for t in new_hits:
            al_id = str(t.get("id"))
            if al_id not in st.session_state.notified_ids:
                action = t.get("action_type", "STRATEJİ")
                # Normalize for display
                disp_action = "AL" if "AL" in action else ("SAT" if "SAT" in action else action)
                icon = "🟢" if disp_action == "AL" else "🔴"
                st.toast(f"{icon} **{disp_action} SİNYALİ:** {t['symbol']} hedefe ulaştı! 🔥", icon="🚀")
                st.session_state.notified_ids.add(al_id)
                has_new = True
        if has_new:
            time.sleep(1) # Give toast time to register
            st.rerun()
    st.session_state.last_alert_check = time.time()

# 3. CONSTRUCT TICKER BAR HTML (Now instant from cache)
ticker_data_html = ""
for label, sym in ticker_symbols:
    atype = "ticker"
    if sym in ["ALTIN", "GÜMÜŞ"]: atype = "emtia"
    elif sym.endswith("=X"): atype = "döviz"
    
    d = get_current_data(sym, asset_type=atype)
    if d:
        change = (d["price"]/d["prev_close"]-1)*100
        cls = "text-glow-green" if change >= 0 else "text-glow-red"
        arrow = "▲" if change >= 0 else "▼"
        ticker_data_html += f'<div class="ticker-item">{label} <span class="{cls}">{d["price"]:,.2f} {arrow} %{change:.2f}</span></div>'

if not ticker_data_html:
    ticker_data_html = '<div class="ticker-item" style="color:rgba(255,255,255,0.2);">Veri akışı şu an durduruldu.</div>'



nav_cols = st.columns([1, 1], gap="large")
with nav_cols[0]:
    # Interactive Tab Switcher
    tab_cols = st.columns(4, gap="small")
    tabs = ["PORTFÖYÜM", "PORTFÖY ANALİZİ", "STRATEJİLER", "İZLEME LİSTESİ"]
    # Safe Tab Switching Callback
    def change_tab(t):
        st.session_state.active_tab = t
        st.session_state.show_asset_modal = False
        st.session_state.show_portfolio_modal = False
        st.session_state.show_portfolio_details = False
        if t == "PORTFÖY ANALİZİ":
            st.session_state.trigger_ai_analysis = True

    for i, tab in enumerate(tabs):
        with tab_cols[i]:
            is_active = st.session_state.active_tab == tab
            btn_type = "primary" if is_active else "secondary"
            st.button(tab, key=f"tab_{tab}", on_click=change_tab, args=(tab,), type=btn_type, use_container_width=True)

with nav_cols[1]:

    # ACTION BUTTONS
    btn_cols = st.columns([1.2, 1.2, 0.8], gap="small")
    with btn_cols[0]:
        if st.button("➕ VARLIK EKLE/SİL", use_container_width=True):
            st.session_state.show_asset_modal = True
            st.session_state.show_portfolio_modal = False
            # Force close watchlist mode if open (optional but cleaner)
            if st.session_state.active_tab == "İZLEME LİSTESİ":
                 pass 

    with btn_cols[1]:
        if st.button("📁 PORTFÖY YÖNET", use_container_width=True):
            st.session_state.show_portfolio_modal = True
            st.session_state.show_asset_modal = False
    with btn_cols[2]:
        # Compact Row for Refresh and Logout
        sub_btn_cols = st.columns(2)
        with sub_btn_cols[0]:
            if st.button("🔄", help="Verileri Güncelle", use_container_width=True):
                st.session_state.portfolio_data_loaded = False
                if "watchlist_data_loaded" in st.session_state:
                    st.session_state.watchlist_data_loaded = False
                st.rerun()
        with sub_btn_cols[1]:
            if st.button("🚪", help="Çıkış Yap", use_container_width=True):
                logout()


    
st.markdown(f"""
<div class="ticker-bar" style="margin-top: 15px; margin-bottom: 25px;">
    <div style="display: flex; width: 200%;">
        <div class="ticker-wrapper" style="display: flex; white-space: nowrap;">
            {ticker_data_html}
            {ticker_data_html}
            {ticker_data_html}
            {ticker_data_html}
        </div>
    </div>
</div>
<style>
    @keyframes ticker-scroll {{
        0% {{ transform: translateX(0); }}
        100% {{ transform: translateX(-50%); }}
    }}
    .ticker-wrapper {{
        animation: ticker-scroll 40s linear infinite !important;
    }}
    .ticker-item {{
        display: inline-block;
        margin-right: 50px;
        font-size: 0.9rem;
        font-weight: 600;
        white-space: nowrap;
    }}
</style>
""", unsafe_allow_html=True)

# 4. DATA CONTROLLER

# --- WATCHLIST LOGIC ---
if st.session_state.active_tab == "İZLEME LİSTESİ":
    st.markdown('<div style="margin-top:0px; margin-bottom:25px; display:flex; align-items:center; gap:12px;"><i class="fas fa-eye" style="color:#00f2ff; font-size:1.5rem;"></i><span style="color:white; font-weight:700; font-size:1.4rem; letter-spacing:-0.5px;">İzleme Listesi</span></div>', unsafe_allow_html=True)
    
    col_w_list, col_w_add = st.columns([2, 1], gap="large")
    
    with col_w_add:
        st.markdown('<div class="glass-card" style="padding:20px; border:1px solid rgba(0, 242, 255, 0.15);">', unsafe_allow_html=True)
        st.markdown('<p style="color:white; font-weight:700; font-size:1rem; margin-bottom:15px;">➕ Listeye Ekle</p>', unsafe_allow_html=True)
        
        with st.form("watchlist_add_form", clear_on_submit=True):
            w_type = st.selectbox("Varlık Tipi", ["bist hisse", "abd hisse/etf", "kripto", "döviz", "emtia", "tefas fon"], key="w_add_type")
            w_sym = st.text_input("Sembol", placeholder="Örn: AKBNK, AAPL").upper().strip()
            
            if st.form_submit_button("Ekle", type="primary", use_container_width=True):
                if w_sym:
                    # Validate
                    with st.spinner("Kontrol ediliyor..."):
                        d = get_current_data(w_sym, w_type)
                    if d:
                        succ, msg = add_to_watchlist(w_sym, w_type)
                        if succ:
                            st.success("Eklendi")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.warning(msg)
                    else:
                        st.error("Sembol bulunamadı")
                else:
                    st.warning("Sembol girin")
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col_w_list:
        w_list = get_watchlist()
        if not w_list:
             st.info("İzleme listeniz boş. Sağ taraftan varlık ekleyebilirsiniz.")
        else:
            # Prepare Watchlist for Bulk Engine
            w_fetch = [{"symbol": x["symbol"], "type": x["type"]} for x in w_list]
            w_json = json.dumps(w_fetch, default=str)
            
            # Use the bulk engine without an intrusive full-page spinner
            w_bulk = calculate_technical_scores_bulk(w_json)

            # Pre-calculate data and scores for sorting
            enriched_watchlist = []
            for item in w_list:
                s = item["symbol"]
                t = item["type"]
                # Get Pre-calculated data
                res = w_bulk.get((s, t), {})
                if not res or "error" in res: continue

                price = res["price"]
                prev = res["prev"]
                pct = ((price / prev) - 1) * 100 if prev > 0 else 0
                color = "#00ff88" if pct > 0 else ("#ff3e3e" if pct < 0 else "white")
                sign = "+" if pct > 0 else ""
                cat_idx, currency, emoji = get_asset_details(s, t)

                # Use pre-calculated indicators
                st_data = res.get("st")
                kama_data = res.get("kama")
                obv_data = res.get("obv")
                adx_data = res.get("adx")
                t_score = res.get("score", 0.0)
                score_color = res.get("color", "rgba(255,255,255,0.1)")
                score_label = res.get("label", "N/A")

                # Generate Sparkline from pre-calculated points
                sparkline_svg = ""
                pts = res.get("spark_points", "")
                if pts:
                    s_color = res.get("spark_color", "#cccccc")
                    sparkline_svg = f'<svg width="100" height="30" style="margin: 0 10px;"><polyline points="{pts}" fill="none" stroke="{s_color}" stroke-width="2" /></svg>'

                enriched_watchlist.append({
                    "item": item, "s": s, "t": t, "price": price, "pct": pct, "color": color, "sign": sign,
                    "emoji": emoji, "currency": currency, "spark": sparkline_svg,
                    "st": st_data, "kama": kama_data, "obv": obv_data, "adx": adx_data,
                    "t_score": t_score, "score_color": score_color, "score_label": score_label
                })

            # SORT BY SCORE DESCENDING
            enriched_watchlist.sort(key=lambda x: x["t_score"], reverse=True)

            # RENDER CARDS
            for d in enriched_watchlist:
                item = d["item"]; s = d["s"]; t = d["t"]; price = d["price"]; pct = d["pct"]
                color = d["color"]; sign = d["sign"]; emoji = d["emoji"]; currency = d["currency"]
                sparkline_svg = d["spark"]; st_data = d["st"]; kama_data = d["kama"]
                obv_data = d["obv"]; adx_data = d["adx"]; t_score = d["t_score"]
                score_color = d["score_color"]; score_label = d["score_label"]

                initial_p = item.get("initial_price", 0)
                perf_since_add = 0; perf_color = "rgba(255,255,255,0.5)"; perf_sign = ""
                if initial_p > 0 and price > 0:
                    perf_since_add = ((price / initial_p) - 1) * 100
                    if perf_since_add > 0: perf_color = "#00ff88"; perf_sign = "+"
                    elif perf_since_add < 0: perf_color = "#ff3e3e"; perf_sign = ""
                
                col_card, col_del = st.columns([12, 1])
                with col_card:
                    st.markdown(f"""
                    <div class="glass-card" style="padding:15px; margin-bottom:0px; display:flex; justify-content:space-between; align-items:center; min-height: 100px;">
                        <div style="display:flex; align-items:center; gap:15px; flex:1.2;">
                            <div style="font-size:1.5rem;">{emoji}</div>
                            <div>
                                <div style="color:white; font-weight:700; font-size:1.1rem;">{s}</div>
                                <div style="color:rgba(255,255,255,0.5); font-size:0.75rem;">{t.upper()}</div>
                            </div>
                        </div>
                        <div style="flex:0.8; display:flex; flex-direction:column; align-items:center; justify-content:center; border-left:1px solid rgba(255,255,255,0.1); border-right:1px solid rgba(255,255,255,0.1); margin: 0 10px;">
                            <div style="font-size:1.4rem; font-weight:900; color:{score_color}; line-height:1;">{t_score:.1f}</div>
                            <div style="font-size:0.55rem; font-weight:800; color:{score_color}; opacity:0.8; margin-top:3px; letter-spacing:0.5px;">{score_label}</div>
                        </div>
                        <div style="flex:2.5; display:flex; flex-direction:column; align-items:center; gap:8px;">
                            {sparkline_svg}
                            <div style="display:flex; gap:6px;">
                                <div style="background:{st_data['bg']}; border:1px solid {st_data['color']}40; padding:2px 6px; border-radius:4px; font-size:0.6rem; color:{st_data['color']}; text-align:center; min-width:60px;">
                                    <div style="font-weight:700; opacity:0.8;">ST {st_data['val']:,.1f}</div>
                                    <div style="font-weight:800;">%{st_data['dist']:.1f}</div>
                                </div>
                                <div style="background:{kama_data['bg']}; border:1px solid {kama_data['color']}40; padding:2px 6px; border-radius:4px; font-size:0.6rem; color:{kama_data['color']}; text-align:center; min-width:60px;">
                                    <div style="font-weight:700; opacity:0.8;">KAMA {kama_data['val']:,.1f}</div>
                                    <div style="font-weight:800;">%{kama_data['dist']:.1f}</div>
                                </div>
                                <div style="background:{obv_data['bg']}; border:1px solid {obv_data['color']}40; padding:2px 6px; border-radius:4px; font-size:0.6rem; color:{obv_data['color']}; text-align:center; display:flex; align-items:center; justify-content:center; min-width:60px; font-weight:800;">OBV {obv_data['trend'].upper()}</div>
                                <div style="background:{adx_data['bg']}; border:1px solid {adx_data['color']}40; padding:2px 6px; border-radius:4px; font-size:0.6rem; color:{adx_data['color']}; text-align:center; min-width:60px;">
                                    <div style="font-weight:700; opacity:0.8;">ADX {adx_data['val']:.1f}</div>
                                    <div style="font-weight:800;">{adx_data['label']}</div>
                                </div>
                            </div>
                        </div>
                        <div style="text-align:right; flex:1;">
                            <div style="color:white; font-weight:600; font-size:0.9rem;">{initial_p:,.2f}</div>
                            <div style="color:{perf_color}; font-weight:700; font-size:0.85rem;">{perf_sign}%{perf_since_add:.2f}</div>
                            <div style="color:rgba(255,255,255,0.4); font-size:0.65rem; margin-top:2px; font-weight:600;">
                                {(lambda d: (lambda diff: "Bugün" if diff == 0 else "Dün" if diff == 1 else f"{diff} gün önce")((datetime.now().date() - datetime.fromisoformat(d).date()).days))(item.get("added_at", datetime.now().isoformat()))}
                            </div>
                        </div>
                        <div style="text-align:right; flex:1.5;">
                            <div style="color:white; font-weight:700; font-size:1.1rem;">{price:,.2f} <span style="font-size:0.8rem; color:rgba(255,255,255,0.5);">{currency}</span></div>
                            <div style="color:{color}; font-weight:600; font-size:0.9rem;">{sign}%{pct:.2f} (Günlük)</div>
                        </div>
                    </div>
                    """.replace('\n', '').replace('    ', ''), unsafe_allow_html=True)
                
                with col_del:
                    st.write(""); st.write("")
                    if st.button("🗑️", key=f"del_w_{s}", help="Listeden Çıkar"):
                        remove_from_watchlist(s)
                        st.rerun()
                st.markdown("<div style='margin-bottom:10px;'></div>", unsafe_allow_html=True)

if st.session_state.active_tab in ["PORTFÖYÜM", "PORTFÖY ANALİZİ"]:
    # Load strategy hits with robust symbol matching
    all_strategies = load_alerts()
    strategy_hits = {}
    for a in all_strategies:
        if a.get("is_hit"):
            # Standardize symbol for matching (e.g. EREGL.IS -> EREGL)
            s_clean = a['symbol'].upper().replace(".IS", "").split(".")[0].strip()
            s_type = a.get('type','').lower().strip()
            action = a.get("action_type", "")
            # Normalize action
            norm_action = "AL" if "AL" in action else ("SAT" if "SAT" in action else action)
            strategy_hits[f"{s_clean}_{s_type}"] = norm_action

    agg_holdings = [h for h in all_holdings if h["p"] in st.session_state.selected_p] if all_holdings else []

    categories = [
        {"name": "BIST Hisse", "val": 0, "val_tl": 0, "change": 0, "daily": 0, "currency": "TL", "icon": "fa-chart-line", "emoji": "🔴", "cost": 0, "prev": 0},
        {"name": "ABD Hisse/ETF", "val": 0, "val_tl": 0, "change": 0, "daily": 0, "currency": "USD", "icon": "fa-globe-americas", "emoji": "🔵", "cost": 0, "prev": 0},
        {"name": "TEFAS Fon", "val": 0, "val_tl": 0, "change": 0, "daily": 0, "currency": "TL", "icon": "fa-vault", "emoji": "🏦", "cost": 0, "prev": 0},
        {"name": "Kripto", "val": 0, "val_tl": 0, "change": 0, "daily": 0, "currency": "USD", "icon": "fa-bitcoin", "emoji": "🪙", "cost": 0, "prev": 0},
        {"name": "Döviz", "val": 0, "val_tl": 0, "change": 0, "daily": 0, "currency": "TL", "icon": "fa-coins", "emoji": "💵", "cost": 0, "prev": 0},
        {"name": "Emtia", "val": 0, "val_tl": 0, "change": 0, "daily": 0, "currency": "TL", "icon": "fa-gem", "emoji": "👑", "cost": 0, "prev": 0},
        {"name": "Eurobond", "val": 0, "val_tl": 0, "change": 0, "daily": 0, "currency": "TL", "icon": "fa-file-invoice-dollar", "emoji": "📉", "cost": 0, "prev": 0},
        {"name": "BES/OKS", "val": 0, "val_tl": 0, "change": 0, "daily": 0, "currency": "TL", "icon": "fa-piggy-bank", "emoji": "🐖", "cost": 0, "prev": 0},
        {"name": "Nakit", "val": 0, "val_tl": 0, "change": 0, "daily": 0, "currency": "TL", "icon": "fa-wallet", "emoji": "💵", "cost": 0, "prev": 0}
    ]

    total_val_tl = 0; total_prev = 0; total_cost = 0; detailed_list = []
    p_metrics = {p: {"val": 0, "prev": 0, "cost": 0} for p in all_portfolios}

    usd_data = get_current_data("USDTRY=X", "döviz")
    usd_rate = usd_data["price"] if usd_data else 34.0

    gold_data = get_current_data("ALTIN", "emtia")
    gold_gram_price = gold_data["price"] if gold_data else 3000.0

    # Merge Holdings across portfolios
    merged_holdings = {}
    
    for h in agg_holdings:
        sym = h["symbol"]
        if sym not in merged_holdings:
            merged_holdings[sym] = {
                "symbol": sym,
                "type": h.get("type", ""),
                "amount": 0.0,
                "total_cost_val": 0.0,
                "portfolios": set(),
            }
        
        merged_holdings[sym]["amount"] += h["amount"]
        merged_holdings[sym]["total_cost_val"] += h["amount"] * h["cost"]
        merged_holdings[sym]["portfolios"].add(h["p"])

    # --- PERFORMANCE OPTIMIZATION: PARALLEL FETCH & SCORE ---
    if agg_holdings:
        # 1. Fetch scores in bulk with Caching (TTL 5 mins)
        h_json = json.dumps(agg_holdings, default=str)
        bulk_scores = calculate_technical_scores_bulk(h_json)
            
        # 2. SEAMLESS INJECTION: Pre-warm PRICE_CACHE with bulk results to avoid extra calls in loop
        for (bs_sym, bs_type), bs_data in bulk_scores.items():
            if bs_data.get("price", 0) > 0:
                # Standardize key for injection
                std_s = bs_sym
                if "bist" in bs_type.lower() and not std_s.endswith(".IS"): std_s = f"{std_s}.IS"
                elif "kripto" in bs_type.lower() and "-" not in std_s: std_s = f"{std_s}-USD"
                elif "döviz" in bs_type.lower():
                    s_up = bs_sym.upper()
                    if s_up == "USD": std_s = "USDTRY=X"
                    elif s_up in ["EUR", "EYR"]: std_s = "EURTRY=X"
                
                PRICE_CACHE[(std_s, bs_type.lower())] = {
                    "price": bs_data["price"],
                    "prev_close": bs_data["prev"],
                    "change_pct": ((bs_data["price"]/bs_data["prev"])-1)*300 if bs_data["prev"] else 0
                }
    else:
        bulk_scores = {}

    # Now populate detailed_list from merged_holdings
    for sym, m_data in merged_holdings.items():
        amount = m_data["amount"]
        avg_cost = m_data["total_cost_val"] / amount if amount > 0 else 0
        p_names = ", ".join(sorted(list(m_data["portfolios"])))
        if len(m_data["portfolios"]) > 1:
            p_names = f"{len(m_data['portfolios'])} Portföy" 

        t = m_data.get("type", "").lower()
        d = get_current_data(sym, t) # This will now hit PRICE_CACHE instantly
        cat_idx, currency, cat_emoji = get_asset_details(sym, t)
        
        if d:
            p_val_orig = d["price"] * amount
            prev_val_orig = d["prev_close"] * amount
            cost_val_orig = m_data["total_cost_val"]
            
            rate = usd_rate if currency == "USD" else 1.0
            v = p_val_orig * rate
            
            # Use pre-calculated bulk score (instant)
            score_data = bulk_scores.get((sym, t), {"score": 0.0, "color": "rgba(255,255,255,0.1)", "label": "N/A"})
            t_score = score_data["score"]
            score_color = score_data["color"]
            score_label = score_data["label"]

            # Let's populate detailed_list here
            detailed_list.append({
                "Emoji": cat_emoji, "Varlık": sym, "Portföy": p_names,
                "Adet": amount, "Maliyet": avg_cost, "T_Maliyet": cost_val_orig,
                "Güncel": d["price"], "Deger": p_val_orig, "Deger_TL": v, 
                "Gunluk_KZ": p_val_orig - prev_val_orig,
                "Toplam_KZ": p_val_orig - cost_val_orig,
                "Gunluk_KZ_TL": (p_val_orig - prev_val_orig) * rate,
                "Toplam_KZ_TL": (p_val_orig - cost_val_orig) * rate,
                "Günlük (%)": (d["price"]/d["prev_close"]-1)*100,
                "Toplam (%)": (d["price"]/avg_cost-1)*100 if avg_cost > 0 else 0, "Para": currency,
                "Signal": strategy_hits.get(f'{sym.upper().replace(".IS", "").split(".")[0].strip()}_{t}', get_strategy_signal(sym, t)),
                "t_score": t_score, "score_color": score_color, "score_label": score_label
            })

        else:
            cv_orig = m_data["total_cost_val"]
            rate = usd_rate if currency == "USD" else 1.0
            cv = cv_orig * rate
            
            detailed_list.append({
                "Emoji": "⚠️", "Varlık": f"{sym} (Veri Yok)", "Portföy": p_names,
                "Adet": amount, "Maliyet": avg_cost, "T_Maliyet": cv_orig,
                "Güncel": avg_cost, "Deger": cv_orig, "Deger_TL": cv, "Gunluk_KZ": 0, "Toplam_KZ": 0,
                "Gunluk_KZ_TL": 0, "Toplam_KZ_TL": 0,
                "Günlük (%)": 0, "Toplam (%)": 0, "Para": currency
            })
            
    # Re-run loop for Category Totals & Overall Metrics (This must run on INDIVIDUAL holdings to be accurate per portfolio)
    # The previous loop (lines 1075++) was doing BOTH (detailed_list append AND metric calc).
    # I replaced that entire block. So I MUST re-implement category/total calculation logic here or inside the merged loop.
    # PROBLEM: Risk analysis relies on 'val_tl' in 'agg_holdings'. Merged loop doesn't update agg_holdings.
    # SOLUTION: Restore the original loop for METRICS ONLY (remove detailed_list.append), and use the new merged loop for DETAILED_LIST.
    
    # ... Restoring Metric Calculation Loop (invisible) ...
    for h in agg_holdings:
        d = get_current_data(h["symbol"], h.get("type"))
        t = h.get("type", "").lower()
        cat_idx, currency, cat_emoji = get_asset_details(h["symbol"], t)
        
        if d:
            rate = usd_rate if currency == "USD" else 1.0
            v = d["price"] * h["amount"] * rate
            h["val_tl"] = v # Critical for Risk Module
            
            total_val_tl += v
            total_prev += d["prev_close"] * h["amount"] * rate
            total_cost += h["cost"] * h["amount"] * rate
            
            if h["p"] in p_metrics:
                p_metrics[h["p"]]["val"] += v
                p_metrics[h["p"]]["prev"] += d["prev_close"] * h["amount"] * rate
                p_metrics[h["p"]]["cost"] += h["cost"] * h["amount"] * rate

            # Category Accumulation
            c_val = d["price"] * h["amount"]
            c_cost = h["cost"] * h["amount"]
            c_prev = d["prev_close"] * h["amount"]
            
            if categories[cat_idx]["currency"] == "USD":
                categories[cat_idx]["val"] += c_val
                categories[cat_idx]["cost"] += c_cost
                categories[cat_idx]["prev"] += c_prev
            else:
                categories[cat_idx]["val"] += v
                categories[cat_idx]["cost"] += c_cost * rate
                categories[cat_idx]["prev"] += c_prev * rate
                
            categories[cat_idx]["val_tl"] += v
        else:
             # Fallback for no data
            cv_orig = h["cost"]*h["amount"]
            rate = usd_rate if currency == "USD" else 1.0
            cv = cv_orig * rate
            h["val_tl"] = cv
            total_val_tl += cv; total_prev += cv; total_cost += cv
            
            if h["p"] in p_metrics:
                p_metrics[h["p"]]["val"] += cv; p_metrics[h["p"]]["prev"] += cv; p_metrics[h["p"]]["cost"] += cv
            
            if categories[cat_idx]["currency"] == "USD":
                categories[cat_idx]["val"] += cv_orig
                categories[cat_idx]["cost"] += cv_orig
                categories[cat_idx]["prev"] += cv_orig
            else:
                categories[cat_idx]["val"] += cv
                categories[cat_idx]["cost"] += cv
                categories[cat_idx]["prev"] += cv
            categories[cat_idx]["val_tl"] += cv


    # Calculate Category Percentages
    for c in categories:
        if c["cost"] > 0:
            c["change"] = (c["val"] / c["cost"] - 1) * 100
        if c["prev"] > 0:
            c["daily"] = (c["val"] / c["prev"] - 1) * 100

    avg_total = (total_val_tl/total_cost - 1)*100 if total_cost else 0
    avg_daily = (total_val_tl/total_prev - 1)*100 if total_prev else 0

    # Calculate Professional Portfolio Metrics (XIRR, TWR, Alpha)
    portfolio_metrics = get_portfolio_metrics(agg_holdings, period=st.session_state.get("chart_period", "1mo"))

    # 2. MAIN LAYOUT
    # Calculate Totals
    total_kz_amount = total_val_tl - total_cost
    daily_kz_amount = total_val_tl - total_prev
    tkz_sign = "+" if total_kz_amount >= 0 else ""
    dkz_sign = "+" if daily_kz_amount >= 0 else ""
    
    tv_usd = total_val_tl / usd_rate
    tv_gold = total_val_tl / gold_gram_price if gold_gram_price else 0
    total_kz_usd = total_kz_amount / usd_rate
    daily_kz_usd = daily_kz_amount / usd_rate
    
    # Calculate Real USD Daily Return
    usd_daily_change_pct = ((usd_data["price"] / usd_data["prev_close"]) - 1) * 100 if usd_data and usd_data["prev_close"] else 0
    daily_usd_pct = 0
    if (1 + usd_daily_change_pct/100) != 0:
        daily_usd_pct = ((1 + avg_daily/100) / (1 + usd_daily_change_pct/100) - 1) * 100
    d_usd_sign = "+" if daily_usd_pct >= 0 else ""

    if detailed_list:
        sorted_detailed_list = sorted(detailed_list, key=lambda x: x.get("Günlük (%)", 0))
    else:
        sorted_detailed_list = []


    # --- RISK ANALYSIS CALCULATION (SHARED) ---
    risk_map = {
        "kripto": 9.0, "crypto": 9.0, "coin": 9.0,
        "bist hisse": 7.0, "hisse": 7.0, "stock": 7.0, "bist": 7.0,
        "abd hisse/etf": 6.5, "abd hisse": 6.5, "etf": 6.0,
        "tefas fon": 5.0, "fon": 5.0, "tefas": 5.0,
        "emtia": 3.0, "altın": 3.0, "altin": 3.0, "gold": 3.0, "gümüş": 3.5, "silver": 3.5,
        "döviz": 2.0, "usd": 2.0, "eur": 2.0, "forex": 8.0,
        "nakit": 1.0, "cash": 1.0, "tl": 1.0
    }
    
    total_risk_score = 0
    total_val_calc = 0
    
    if agg_holdings:
        for h in agg_holdings:
            val = h.get("val_tl", 0)
            if val > 0:
                rtype = str(h.get("type", "")).lower().strip()
                rscore = 6.0 
                for k, v in risk_map.items():
                    if k in rtype:
                        rscore = v
                        break
                total_risk_score += val * rscore
                total_val_calc += val
        
        risk_val = (total_risk_score / total_val_calc) if total_val_calc > 0 else 0
    else:
        risk_val = 0

    if st.session_state.active_tab == "PORTFÖYÜM":
        cols = st.columns([1, 2], gap="medium")

        with cols[0]:
            # --- RISK ANALYSIS MODULE DISPLAY ---
            risk_percent = min(max((risk_val / 10.0) * 100, 0), 100)
            
            if risk_val < 3.5:
                r_label = "DÜŞÜK RİSK"
                r_color = "#00ff88"
                r_desc = "Defansif ve güvenli liman ağırlıklı."
            elif risk_val < 7.0:
                r_label = "ORTA RİSK"
                r_color = "#ffcc00"
                r_desc = "Dengeli büyüme ve çeşitlilik."
            else:
                r_label = "YÜKSEK RİSK"
                r_color = "#ff3e3e"
                r_desc = "Yüksek getiri potansiyeli, yüksek volatilite."
    
            risk_html = (
                f'<div class="glass-card" style="padding:20px; margin-bottom:15px; border:1px solid rgba(255,255,255,0.05); background: linear-gradient(180deg, rgba(255,255,255,0.03) 0%, rgba(0,0,0,0) 100%);">'
                f'<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">'
                f'<div style="font-size:0.75rem; font-weight:800; color:rgba(255,255,255,0.5); letter-spacing:1px;">RİSK PROFİLİ</div>'
                f'<div style="font-size:0.85rem; font-weight:800; color:{r_color}; text-shadow:0 0 10px {r_color}40;">{r_label} ({risk_val:.1f}/10)</div>'
                f'</div>'
                
                f'<div style="height:6px; width:100%; background:rgba(255,255,255,0.1); border-radius:3px; position:relative; margin-bottom:8px;">'
                f'<div style="height:100%; width:100%; background:linear-gradient(90deg, #00ff88 0%, #ffcc00 50%, #ff3e3e 100%); border-radius:3px; opacity:0.8;"></div>'
                f'<div style="position:absolute; left:{risk_percent}%; top:50%; transform:translate(-50%, -50%); width:14px; height:14px; background:#fff; border:3px solid #0b0e14; border-radius:50%; box-shadow:0 0 10px rgba(255,255,255,0.8);"></div>'
                f'</div>'
                
                f'<div style="font-size:0.75rem; color:rgba(255,255,255,0.4); text-align:right;">'
                f'{r_desc}'
                f'</div>'
                f'</div>'
            )
            st.markdown(risk_html, unsafe_allow_html=True)
    
            
            # --- ISI HARİTASI (EN ÜSTTE) ---
            if detailed_list:
                df_heat = pd.DataFrame(detailed_list)
                # BAŞLIK KALDIRILDI
                
                fig_heat = px.treemap(
                    df_heat,
                    path=[px.Constant("TÜM VARLIKLAR"), 'Emoji', 'Varlık'],
                    values='Deger_TL',
                    color='Günlük (%)',
                    color_continuous_scale=[[0, '#ff3e3e'], [0.5, '#171b21'], [1, '#00ff88']],
                    color_continuous_midpoint=0,
                    custom_data=['Varlık', 'Deger_TL', 'Günlük (%)']
                )
                
                # ADIM 3: TAMAMEN SESSİZ MOD - Sadece İsim ve Renk
                fig_heat.update_traces(
                    hoverinfo='none', # Hiçbir şey gösterme
                    hovertemplate=None,
                    texttemplate="<b>%{label}</b>", # Sadece İsim
                    textposition="middle center",
                    textfont=dict(size=14, color="white", family="Outfit"),
                    marker=dict(line=dict(width=1, color='rgba(0,0,0,0.5)'))
                )
                
                fig_heat.update_layout(
                    margin=dict(t=30, l=0, r=0, b=0),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    height=380,
                    coloraxis_showscale=False
                )
                
                st.markdown('<div class="glass-card" style="padding:5px; overflow:hidden;">', unsafe_allow_html=True)
                st.plotly_chart(
                    fig_heat, 
                    use_container_width=True, 
                    config={'displayModeBar': False},
                    key="razor_heat_hover_mode" 
                )
                
                # --- YATAY RENK SKALASI (LEGEND BAR) ---
                st.markdown("""
                <div style="margin-top: 10px; margin-bottom: 5px; padding: 0 5px;">
                    <div style="display: flex; justify-content: space-between; font-size: 11px; color: rgba(255,255,255,0.5); font-weight: 500; font-family: 'Outfit', sans-serif;">
                        <span>DÜŞÜŞ</span>
                        <span>NÖTR</span>
                        <span>YÜKSELİŞ</span>
                    </div>
                    <div style="
                        height: 4px;
                        width: 100%;
                        border-radius: 2px;
                        margin-top: 4px;
                        background: linear-gradient(90deg, #ff3e3e 0%, #171b21 50%, #00ff88 100%);
                        box-shadow: 0 1px 3px rgba(0,0,0,0.5);
                    "></div>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown('</div><div style="margin-bottom: 20px;"></div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="glass-card" style="padding:40px; text-align:center; color:rgba(255,255,255,0.2);">Veri bulunmamaktadır.</div>', unsafe_allow_html=True)
    
            # --- PASTA GRAFİK (ALTTA) ---
            pie_data = [{"Kategori": f"{c['emoji']} {c['name']}", "Değer": c["val_tl"]} for c in categories if c["val_tl"] > 0]
            if pie_data:
                df_pie = pd.DataFrame(pie_data)
                fig_pie = px.pie(df_pie, values='Değer', names='Kategori', hole=0.6,
                                color_discrete_sequence=['#00f2ff', '#00ff88', '#7000ff', '#ff0070', '#ffcc00', '#0070ff', '#ff3e3e', '#ffffff'])
                fig_pie.update_traces(
                    textinfo='none', # Pastada yüzdeleri kaldır
                    pull=[0.02] * len(df_pie),
                    hovertemplate="<b>%{label}</b><br>₺%{value:,.0f} (%{percent})<extra></extra>"
                )
                fig_pie.update_layout(
                    showlegend=True, 
                    legend=dict(
                        orientation="h", # Açıklamalar alt satırda (yatay)
                        yanchor="top", 
                        y=-0.1, 
                        xanchor="center", 
                        x=0.5, 
                        font=dict(color="white", size=8),
                        bgcolor='rgba(0,0,0,0)',
                        itemsizing='constant'
                    ),
                    margin=dict(t=10, b=80, l=10, r=10), # Alt marjı legend için artır
                    paper_bgcolor='rgba(0,0,0,0)', 
                    height=380 # Legend aşağı indiği için yüksekliği biraz artır
                )
                st.markdown('<div class="glass-card p-6">', unsafe_allow_html=True)
                st.plotly_chart(fig_pie, use_container_width=True, config={'displayModeBar': False})
                st.markdown('</div>', unsafe_allow_html=True)
    
            if "chart_period" not in st.session_state:
                st.session_state.chart_period = "5d"
            
            # BAŞLIK KALDIRILDI
            
            period_options = {"1 Hafta": "5d", "1 Ay": "1mo", "3 Ay": "3mo", "6 Ay": "6mo", "1 Yıl": "1y"}
            period_labels = list(period_options.keys())
            current_label = [k for k, v in period_options.items() if v == st.session_state.chart_period]
            current_idx = period_labels.index(current_label[0]) if current_label else 1
            
            def on_period_change():
                st.session_state.chart_period = period_options[st.session_state.period_select_chart]
            
            st.selectbox("Dönem", period_labels, index=current_idx, key="period_select_chart", label_visibility="collapsed", on_change=on_period_change)
            
            if agg_holdings:
                history_df = get_portfolio_history(agg_holdings, period=st.session_state.chart_period)
                if not history_df.empty:
                    import plotly.graph_objects as go
                    st.markdown('<div class="glass-card p-6">', unsafe_allow_html=True)
                    fig_perf = go.Figure()
                    fig_perf.add_trace(go.Scatter(x=history_df.index, y=history_df['Total_Cost'], name='Toplam Maliyet', line=dict(color='rgba(255, 255, 255, 0.4)', width=2, dash='dash'), hovertemplate='%{y:,.0f} TL<extra></extra>'))
                    fig_perf.add_trace(go.Scatter(x=history_df.index, y=history_df['Market_Value'], name='Piyasa Değeri', fill='tonexty', fillcolor='rgba(0, 242, 255, 0.1)', line=dict(color='#00f2ff', width=3), hovertemplate='%{y:,.0f} TL<extra></extra>'))
                    fig_perf.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=0, r=0, t=10, b=0), height=350, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color="rgba(255,255,255,0.7)")), hovermode='x unified', xaxis=dict(showgrid=False, color='grey', zeroline=False), yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', color='grey', zeroline=False))
                    st.plotly_chart(fig_perf, use_container_width=True, config={'displayModeBar': False})
                    st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="glass-card p-6" style="text-align:center; color:rgba(255,255,255,0.4); padding:40px;">Tarihsel veri yükleniyor...</div>', unsafe_allow_html=True)
            st.markdown('<div style="margin-top:20px; margin-bottom:20px;"></div>', unsafe_allow_html=True)
            if st.button("📂 TÜM İŞLEM GEÇMİŞİNİ GÖRÜNTÜLE / SİL", use_container_width=True, type="secondary"):
                st.session_state.show_history_modal = True
            
            simple_ret = portfolio_metrics.get("simple_return"); xirr_val = portfolio_metrics.get("xirr"); inv_days = portfolio_metrics.get("investment_days")
            twr_val = portfolio_metrics.get("twr"); bench_val = portfolio_metrics.get("benchmark_return"); alpha_val = portfolio_metrics.get("alpha")
            
            simple_display = f"%{simple_ret:.1f}" if simple_ret is not None else "—"; xirr_display = f"%{xirr_val:.1f}" if xirr_val is not None else "—"
            days_display = f"{inv_days} gün" if inv_days is not None else "—"; twr_display = f"%{twr_val:.1f}" if twr_val is not None else "—"
            bench_display = f"%{bench_val:.1f}" if bench_val is not None else "—"; alpha_display = f"%{alpha_val:+.1f}" if alpha_val is not None else "—"
            
            simple_cls = "text-glow-green" if simple_ret and simple_ret >= 0 else ("text-glow-red" if simple_ret and simple_ret < 0 else "")
            xirr_cls = "text-glow-green" if xirr_val and xirr_val >= 0 else ("text-glow-red" if xirr_val and xirr_val < 0 else "")
            twr_cls = "text-glow-green" if twr_val and twr_val >= 0 else ("text-glow-red" if twr_val and twr_val < 0 else "")
            bench_cls = "text-glow-green" if bench_val and bench_val >= 0 else ("text-glow-red" if bench_val and bench_val < 0 else "")
            alpha_cls = "text-glow-green" if alpha_val and alpha_val >= 0 else ("text-glow-red" if alpha_val and alpha_val < 0 else "")
            
            html_out = f'<div class="glass-card" style="padding: 15px; overflow: hidden;"><div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; width: 100%;">'
            html_out += f'<div style="text-align: center; padding: 12px 5px; background: rgba(255,255,255,0.03); border-radius: 12px; border: 1px solid rgba(255,255,255,0.08); display: flex; flex-direction: column; justify-content: center; min-height: 85px;"><div style="color: rgba(255,255,255,0.4); font-size: 0.6rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 5px;">Basit Getiri</div><div class="{simple_cls}" style="font-size: 1.15rem; font-weight: 800;">{simple_display}</div><div style="color: rgba(255,255,255,0.25); font-size: 0.55rem; margin-top: 4px;">{days_display} toplam</div></div>'
            html_out += f'<div style="text-align: center; padding: 12px 5px; background: rgba(112, 0, 255, 0.05); border: 1px solid rgba(112, 0, 255, 0.2); border-radius: 12px; display: flex; flex-direction: column; justify-content: center; min-height: 85px;"><div style="color: rgba(255,255,255,0.4); font-size: 0.6rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 5px;">XIRR (Yıllık)</div><div class="{xirr_cls if xirr_val is not None else ""}" style="font-size: 1.15rem; font-weight: 800;">{xirr_display if xirr_val is not None else "Bekleniyor"}</div><div style="color: rgba(255,255,255,0.25); font-size: 0.55rem; margin-top: 4px;">{"Yıllık" if xirr_val is not None else "30 gün veri gerekli"}</div></div>'
            html_out += f'<div style="text-align: center; padding: 12px 5px; background: rgba(255,255,255,0.03); border-radius: 12px; border: 1px solid rgba(255,255,255,0.08); display: flex; flex-direction: column; justify-content: center; min-height: 85px;"><div style="color: rgba(255,255,255,0.4); font-size: 0.6rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 5px;">TWR</div><div class="{twr_cls}" style="font-size: 1.15rem; font-weight: 800;">{twr_display}</div><div style="color: rgba(255,255,255,0.25); font-size: 0.55rem; margin-top: 4px;">Zaman ağırlıklı</div></div>'
            # Re-add BIST100 Card
            html_out += f'<div style="text-align: center; padding: 12px 5px; background: rgba(255,255,255,0.03); border-radius: 12px; border: 1px solid rgba(255,255,255,0.08); display: flex; flex-direction: column; justify-content: center; min-height: 85px;"><div style="color: rgba(255,255,255,0.4); font-size: 0.6rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 5px;">BIST100</div><div class="{bench_cls}" style="font-size: 1.15rem; font-weight: 800;">{bench_display}</div><div style="color: rgba(255,255,255,0.25); font-size: 0.55rem; margin-top: 4px;">Piyasa</div></div>'
    
            # ADD USD VALUE CARD
            tv_usd = total_val_tl / usd_rate
            html_out += f'<div style="text-align: center; padding: 12px 5px; background: rgba(255,255,255,0.03); border-radius: 12px; border: 1px solid rgba(255,255,255,0.08); display: flex; flex-direction: column; justify-content: center; min-height: 85px;"><div style="color: rgba(255,255,255,0.4); font-size: 0.6rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 5px;">VARLIK (USD)</div><div style="color: #00f2ff; font-size: 1.15rem; font-weight: 800;">${tv_usd:,.0f}</div><div style="color: rgba(255,255,255,0.25); font-size: 0.55rem; margin-top: 4px;">Kur: {usd_rate:.2f}</div></div>'
    
            # ALPHA CALCULATION
            try:
                bench_change = float(bench_display.replace("%", "").strip())
            except:
                bench_change = 0.0
                
            alpha_val = avg_total - bench_change
            alpha_cls = "text-[#00ff88]" if alpha_val >= 0 else "text-[#ff3e3e]"
            alpha_sign = "+" if alpha_val >= 0 else ""
            
            html_out += f'<div style="text-align: center; padding: 12px 5px; background: rgba(0, 242, 255, 0.05); border-radius: 12px; border: 1px solid rgba(0, 242, 255, 0.2); display: flex; flex-direction: column; justify-content: center; min-height: 85px;"><div style="color: rgba(255,255,255,0.4); font-size: 0.6rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 5px;">ALPHA (α)</div><div style="color:{"#00ff88" if alpha_val>=0 else "#ff3e3e"}; font-size: 1.15rem; font-weight: 800;">{alpha_sign}%{alpha_val:.1f}</div><div style="color: rgba(255,255,255,0.25); font-size: 0.55rem; margin-top: 4px;">Piyasa Farkı</div></div>'
            
            html_out += '</div></div>'
            st.write(html_out, unsafe_allow_html=True)
    
            # --- MARKET SENTIMENT (VIX) ---
            vix_data = get_current_data("^VIX", "endeks")
            vix_val = vix_data["price"] if vix_data else 0
            vix_change = ((vix_data["price"] / vix_data["prev_close"] - 1) * 100) if vix_data and vix_data["prev_close"] else 0
            
            if vix_val > 0:
                if vix_val < 17:
                    fear_label = "SAKİN PİYASA"
                    fear_color = "#00ff88" # Green
                    fear_emoji = "😎"
                    fear_desc = "Risk iştahı yüksek, korku düşük."
                elif vix_val < 25:
                    fear_label = "NORMAL / ENDİŞELİ"
                    fear_color = "#ffcc00" # Yellow
                    fear_emoji = "🤔"
                    fear_desc = "Volatilite artıyor, dikkatli olun."
                else:
                    fear_label = "YÜKSEK KORKU"
                    fear_color = "#ff3e3e" # Red
                    fear_emoji = "😱"
                    fear_desc = "Panik satışları ve yüksek stres."
                
                v_change_color = "#ff3e3e" if vix_change > 0 else "#00ff88" # VIX artarsa kötü (Kırmızı)
                
                st.markdown(f"""
                <div class="glass-card" style="padding:15px; display:flex; justify-content:space-between; align-items:center; margin-top:20px; margin-bottom:0px; border-left:4px solid {fear_color};">
                    <div>
                        <div style="font-size:0.7rem; font-weight:800; color:rgba(255,255,255,0.5); letter-spacing:1px; margin-bottom:5px;">KORKU ENDEKSİ (VIX)</div>
                        <div style="font-size:1.6rem; font-weight:800; color:white; line-height:1;">{vix_val:.2f}</div>
                        <div style="font-size:0.75rem; color:{fear_color}; font-weight:700; margin-top:5px;">{fear_label}</div>
                        <div style="font-size:0.65rem; color:rgba(255,255,255,0.4); margin-top:2px;">{fear_desc}</div>
                    </div>
                    <div style="text-align:right;">
                        <div style="background:{v_change_color}20; color:{v_change_color}; padding:4px 8px; border-radius:6px; font-weight:700; font-size:0.8rem; display:inline-block; margin-bottom:5px;">
                            {'+' if vix_change > 0 else ''}{vix_change:.2f}%
                        </div>
                        <div style="font-size:2.5rem; line-height:1; filter: drop-shadow(0 0 10px {fear_color}60);">{fear_emoji}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
            # --- CRYPTO FEAR & GREED INDEX ---
            fng_data = get_crypto_fng()
            if fng_data:
                fng_val = int(fng_data.get("value", 50))
                fng_class = fng_data.get("value_classification", "Neutral")
                
                # Color Mapping
                if fng_val < 25: 
                    fng_color = "#ff3e3e"; fng_emoji = "☠️"; fng_trend = "AŞIRI KORKU"
                elif fng_val < 46: 
                    fng_color = "#ffcc00"; fng_emoji = "😨"; fng_trend = "KORKU"
                elif fng_val < 55: 
                    fng_color = "#cccccc"; fng_emoji = "😐"; fng_trend = "NÖTR"
                elif fng_val < 76: 
                    fng_color = "#00ff88"; fng_emoji = "🤑"; fng_trend = "AÇGÖZLÜLÜK"
                else: 
                    fng_color = "#00f2ff"; fng_emoji = "🚀"; fng_trend = "AŞIRI AÇGÖZLÜLÜK"
                
                st.markdown(f"""
                <div class="glass-card" style="padding:15px; display:flex; justify-content:space-between; align-items:center; margin-top:10px; margin-bottom:0px; border-left:4px solid {fng_color};">
                    <div>
                        <div style="font-size:0.7rem; font-weight:800; color:rgba(255,255,255,0.5); letter-spacing:1px; margin-bottom:5px;">KRİPTO AÇGÖZLÜLÜK</div>
                        <div style="font-size:1.6rem; font-weight:800; color:white; line-height:1;">{fng_val}</div>
                        <div style="font-size:0.75rem; color:{fng_color}; font-weight:700; margin-top:5px;">{fng_class}</div>
                        <div style="font-size:0.65rem; color:rgba(255,255,255,0.4); margin-top:2px;">{fng_trend}</div>
                    </div>
                    <div style="text-align:right;">
                        <div style="font-size:2.5rem; line-height:1; filter: drop-shadow(0 0 10px {fng_color}60);">{fng_emoji}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
            # --- TRADINGVIEW TECHNICAL ANALYSIS WIDGET ---
            import streamlit.components.v1 as components
            
            # Widget HTML
            tv_widget_code = """
            <!-- TradingView Widget BEGIN -->
            <div class="tradingview-widget-container">
              <div class="tradingview-widget-container__widget"></div>
              <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-technical-analysis.js" async>
              {
              "interval": "4h",
              "width": "100%",
              "isTransparent": true,
              "height": "400",
              "symbol": "BIST:XU100",
              "showIntervalTabs": true,
              "displayMode": "single",
              "locale": "tr",
              "colorTheme": "dark"
              }
              </script>
            </div>
            <!-- TradingView Widget END -->
            <style>
                .tradingview-widget-container { background: transparent !important; }
            </style>
            """
            
            st.markdown('<div class="glass-card" style="padding:0; overflow:hidden; border:1px solid rgba(255,255,255,0.05);">', unsafe_allow_html=True)
            components.html(tv_widget_code, height=410, scrolling=False)
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Old Risk/Insight location cleared
    
        with cols[1]:
            # METRIC CARDS RE-ADDED
            d_color = "text-[#00ff88]" if daily_kz_amount >= 0 else "text-[#ff3e3e]"
            t_color = "text-[#00ff88]" if total_kz_amount >= 0 else "text-[#ff3e3e]"
            dkz_sign = "+" if daily_kz_amount >= 0 else ""
            tkz_sign = "+" if total_kz_amount >= 0 else ""
            
            tv_tl_str = f"{total_val_tl:,.0f} TL"
            tv_usd_str = f"${tv_usd:,.0f}"
            tv_gold_str = f"{tv_gold:,.1f} gr Altın"
            dkz_str = f"{dkz_sign}{daily_kz_amount:,.0f} TL"
            tkz_str = f"{tkz_sign}{total_kz_amount:,.0f} TL"
            avg_d_str = f"%{avg_daily:+.2f}"
            avg_t_str = f"%{avg_total:+.2f}"
            
            # Updated Premium Design for Metric Cards
            d_color_main = "#00ff88" if daily_kz_amount >= 0 else "#ff3e3e"
            t_color_main = "#00ff88" if total_kz_amount >= 0 else "#ff3e3e"
            
            cards_html = (
                f'<div style="display:flex; gap:12px; margin-bottom:15px; width:100%;">'
                
                # CARD 1: TOPLAM VARLIK
                f'<div style="flex:1; background:linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.02) 100%); border:1px solid rgba(255,255,255,0.1); border-radius:12px; padding:12px 15px; position:relative; overflow:hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.2); min-height: 100px; display: flex; flex-direction: column; justify-content: center;">'
                    f'<div style="position:absolute; top:-5px; right:-5px; font-size:4rem; opacity:0.04; transform:rotate(10deg);">💼</div>'
                    f'<div style="color:rgba(255,255,255,0.5); font-size:0.7rem; font-weight:700; text-transform:uppercase; letter-spacing:1px; margin-bottom:4px;">TOPLAM VARLIK</div>'
                    f'<div style="color:white; font-size:1.5rem; font-weight:800; letter-spacing:-0.5px; text-shadow: 0 2px 10px rgba(255,255,255,0.1);">{tv_tl_str}</div>'
                    f'<div style="display:flex; gap:8px; margin-top:4px; font-size:0.7rem; color:rgba(255,255,255,0.4); font-weight:500;">'
                        f'<span>{tv_usd_str}</span><span style="opacity:0.3;">|</span><span>{tv_gold_str}</span>'
                    f'</div>'
                f'</div>'
                
                # CARD 2: GÜNLÜK DEĞİŞİM
                f'<div style="flex:1; background:linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.02) 100%); border:1px solid rgba(255,255,255,0.1); border-bottom:3px solid {d_color_main}; border-radius:12px; padding:12px 15px; position:relative; overflow:hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.2); min-height: 100px; display: flex; flex-direction: column; justify-content: center;">'
                    f'<div style="position:absolute; top:-5px; right:-5px; font-size:4rem; opacity:0.04; transform:rotate(10deg);">📈</div>'
                    f'<div style="color:rgba(255,255,255,0.5); font-size:0.7rem; font-weight:700; text-transform:uppercase; letter-spacing:1px; margin-bottom:4px;">GÜNLÜK DEĞİŞİM</div>'
                    f'<div style="color:{d_color_main}; font-size:1.5rem; font-weight:800; letter-spacing:-0.5px; text-shadow: 0 0 25px {d_color_main}30;">{dkz_str}</div>'
                    f'<div style="margin-top:4px;">'
                        f'<span style="background:{d_color_main}15; color:{d_color_main}; padding:2px 8px; border-radius:6px; font-size:0.75rem; font-weight:700; border:1px solid {d_color_main}30;">{avg_d_str}</span>'
                    f'</div>'
                f'</div>'
                
                # CARD 3: TOPLAM KAR/ZARAR
                f'<div style="flex:1; background:linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.02) 100%); border:1px solid rgba(255,255,255,0.1); border-bottom:3px solid {t_color_main}; border-radius:12px; padding:12px 15px; position:relative; overflow:hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.2); min-height: 100px; display: flex; flex-direction: column; justify-content: center;">'
                    f'<div style="position:absolute; top:-5px; right:-5px; font-size:4rem; opacity:0.04; transform:rotate(10deg);">💰</div>'
                    f'<div style="color:rgba(255,255,255,0.5); font-size:0.7rem; font-weight:700; text-transform:uppercase; letter-spacing:1px; margin-bottom:4px;">TOPLAM K/Z</div>'
                    f'<div style="color:{t_color_main}; font-size:1.5rem; font-weight:800; letter-spacing:-0.5px; text-shadow: 0 0 25px {t_color_main}30;">{tkz_str}</div>'
                    f'<div style="margin-top:4px;">'
                        f'<span style="background:{t_color_main}15; color:{t_color_main}; padding:2px 8px; border-radius:6px; font-size:0.75rem; font-weight:700; border:1px solid {t_color_main}30;">{avg_t_str}</span>'
                    f'</div>'
                f'</div>'
                
                f'</div>'
            )
            st.markdown(cards_html, unsafe_allow_html=True)
            st.markdown('<div class="glass-card p-6">', unsafe_allow_html=True)
            # Custom Header with st.columns for perfect alignment
            h_cols = st.columns([3.5, 2.5, 2, 2, 1])
            headers = ["PORTFÖY ADI", "TOPLAM DEĞER", "GÜNLÜK K/Z", "TOPLAM K/Z", ""]
            for i, h_text in enumerate(headers):
                with h_cols[i]:
                    st.markdown(f'<div style="color: rgba(255, 255, 255, 0.4); font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; padding: 10px 0;">{h_text}</div>', unsafe_allow_html=True)
            
            st.markdown('<div style="border-bottom: 1px solid rgba(255, 255, 255, 0.05); margin-bottom: 10px;"></div>', unsafe_allow_html=True)
    
            
            # Sort portfolios by value (largest first) and show all, gray out ones not in selected_p
            # First calculate values for all portfolios for sorting
            portfolio_values = {}
            for p_name in all_portfolios:
                if p_name in st.session_state.selected_p:
                    portfolio_values[p_name] = p_metrics.get(p_name, {"val": 0})["val"]
                else:
                    # Calculate value for excluded portfolios
                    exc_val = 0
                    for h in [hd for hd in all_holdings if hd["p"] == p_name]:
                        d = get_current_data(h["symbol"], h.get("type"))
                        if d:
                            t = h.get("type", "").lower()
                            currency = "USD" if ("abd" in t or "kripto" in t or ("emtia" in t and h["symbol"].upper() not in ["ALTIN", "GÜMÜŞ"])) else "TL"
                            rate = usd_rate if currency == "USD" else 1.0
                            exc_val += d["price"] * h["amount"] * rate
                    portfolio_values[p_name] = exc_val
            
            # Sort: included portfolios first (by value desc), then excluded (by value desc)
            included_portfolios = sorted([p for p in all_portfolios if p in st.session_state.selected_p], 
                                          key=lambda x: portfolio_values.get(x, 0), reverse=True)
            excluded_portfolios = sorted([p for p in all_portfolios if p not in st.session_state.selected_p], 
                                          key=lambda x: portfolio_values.get(x, 0), reverse=True)
            sorted_portfolios = included_portfolios + excluded_portfolios
            
            for p_name in sorted_portfolios:
                m = p_metrics.get(p_name, {"val": 0, "cost": 0, "prev": 0})
                is_included = p_name in st.session_state.selected_p
                
                # Calculate portfolio value for all portfolios
                if not is_included:
                    # Recalculate for excluded portfolios
                    p_holdings_fixed = [h for h in all_holdings if h["p"] == p_name]
                    exc_val = 0
                    exc_cost = 0
                    exc_prev = 0
                    for h in p_holdings_fixed:
                        d = get_current_data(h["symbol"], h.get("type"))
                        if d:
                            cat_idx, currency, cat_emoji = get_asset_details(h["symbol"], h.get("type", ""))
                            rate = usd_rate if currency == "USD" else 1.0
                            exc_val += d["price"] * h["amount"] * rate
                            exc_cost += h["cost"] * h["amount"] * rate
                            exc_prev += d["prev_close"] * h["amount"] * rate
                    m = {"val": exc_val, "cost": exc_cost, "prev": exc_prev}
                
                if True:  # Show all portfolios
                    pt = (m["val"]/m["cost"]-1)*100 if m["cost"] else 0
                    pd = (m["val"]/m["prev"]-1)*100 if m.get("prev") and m["prev"] > 0 else 0
                    
                    total_kz_tl = m["val"] - m["cost"]
                    daily_kz_tl = m["val"] - m["prev"]
                    
                    t_sign = "+" if total_kz_tl >= 0 else ""
                    d_sign = "+" if daily_kz_tl >= 0 else ""
                    
                    if is_included:
                        # Normal styling
                        name_color = "white"
                        val_color = "white"
                        icon_color = "#00f2ff"
                        t_cls = "text-glow-green" if pt > 0 else ("text-glow-red" if pt < 0 else "")
                        status_badge = ""
                    else:
                        # Muted styling for excluded
                        name_color = "rgba(255,255,255,0.25)"
                        val_color = "rgba(255,255,255,0.2)"
                        icon_color = "rgba(255,255,255,0.1)"
                        t_cls = ""
                        status_badge = '<span style="background:rgba(255,255,255,0.05); color:rgba(255,255,255,0.3); font-size:0.6rem; padding:2px 6px; border-radius:4px; margin-left:8px; border:1px solid rgba(255,255,255,0.05);">Dahil değil</span>'
                    
                    rc = st.columns([3.5, 2.5, 2, 2, 1])
                    with rc[0]: 
                        st.markdown(f'<div style="line-height:20px; padding: 10px 0 10px 15px; color:{name_color}; font-size:0.85rem;"><i class="fas fa-folder" style="color:{icon_color}; margin-right:8px;"></i>{p_name}{status_badge}</div>', unsafe_allow_html=True)
                    with rc[1]: 
                        val_display = f"{m['val']:,.0f} TL" if m["val"] > 0 else "—"
                        st.markdown(f'<div style="line-height:40px; color:{val_color}; font-size:0.85rem;">{val_display}</div>', unsafe_allow_html=True)
                    with rc[2]: 
                        d_cls = "text-glow-green" if daily_kz_tl > 0 else ("text-glow-red" if daily_kz_tl < 0 else "") if is_included else ""
                        d_opacity = "1" if is_included else "0.2"
                        st.markdown(f'<div style="line-height:20px; padding: 5px 0; font-size:0.85rem; color:{val_color}; opacity:{d_opacity};" class="{d_cls}">%{pd:.1f}<br><span style="font-size:0.7rem; opacity:0.6;">{d_sign}{daily_kz_tl:,.0f} TL</span></div>', unsafe_allow_html=True)
                    with rc[3]: 
                        t_cls = "text-glow-green" if total_kz_tl > 0 else ("text-glow-red" if total_kz_tl < 0 else "") if is_included else ""
                        t_opacity = "1" if is_included else "0.2"
                        st.markdown(f'<div style="line-height:20px; padding: 5px 0; font-size:0.85rem; color:{val_color}; opacity:{t_opacity};" class="{t_cls}">%{pt:.1f}<br><span style="font-size:0.7rem; opacity:0.6;">{t_sign}{total_kz_tl:,.0f} TL</span></div>', unsafe_allow_html=True)
                    with rc[4]: 
                        if st.button("👁️", key=f"vp_{p_name}"):
                            # Build detailed list for this specific portfolio
                            pl = []
                            portfolio_holdings = [h for h in all_holdings if h["p"] == p_name]
                            for h in portfolio_holdings:
                                d = get_current_data(h["symbol"], h.get("type"))
                                if d:
                                    cat_idx, currency, cat_emoji = get_asset_details(h["symbol"], h.get("type", ""))
                                    pl.append({
                                        "Emoji": cat_emoji, "Varlık": h["symbol"], "Portföy": p_name,
                                        "Adet": h["amount"], "Maliyet": h["cost"], "T_Maliyet": h["cost"]*h["amount"],
                                        "Güncel": d["price"], "Deger": d["price"]*h["amount"], 
                                        "Gunluk_KZ": (d["price"] - d["prev_close"])*h["amount"],
                                        "Toplam_KZ": (d["price"] - h["cost"])*h["amount"], 
                                        "Günlük (%)": (d["price"]/d["prev_close"]-1)*100,
                                        "Toplam (%)": (d["price"]/h["cost"]-1)*100, "Para": currency
                                    })
                                else:
                                    # If no data is available, use cost as current value
                                    cat_idx, currency, cat_emoji = get_asset_details(h["symbol"], h.get("type", ""))
                                    pl.append({
                                        "Emoji": cat_emoji, "Varlık": f"{h['symbol']} (Veri Yok)", "Portföy": p_name,
                                        "Adet": h["amount"], "Maliyet": h["cost"], "T_Maliyet": h["cost"]*h["amount"],
                                        "Güncel": h["cost"], "Deger": h["cost"]*h["amount"], 
                                        "Gunluk_KZ": 0,
                                        "Toplam_KZ": 0, 
                                        "Günlük (%)": 0,
                                        "Toplam (%)": 0, "Para": currency
                                    })
                            # Set session state to show dialog (no rerun needed)
                            st.session_state.show_portfolio_details = True
                            st.session_state.portfolio_details_name = p_name
                            st.session_state.portfolio_details_data = pl
    
            st.markdown('</div>', unsafe_allow_html=True)
    
            st.markdown('<div style="margin-top:30px; margin-bottom:15px; display:flex; align-items:center; gap:10px;"><i class="fas fa-chart-pie" style="color:#00f2ff;"></i><span style="color:white; font-weight:600; font-size:1rem;">Varlık Dağılımı</span></div>', unsafe_allow_html=True)
            st.markdown('<div class="glass-card p-6">', unsafe_allow_html=True)
            
            # Header for categories
            # Custom Header for Asset Distribution
            c_h_cols = st.columns([2.5, 2, 2, 1.2, 1.3, 1])
            c_headers = ["KATEGORİ", "MALİYET", "DEĞER", "GÜNLÜK", "TOPLAM", ""]
            for i, h_text in enumerate(c_headers):
                with c_h_cols[i]:
                    st.markdown(f'<div style="color: rgba(255, 255, 255, 0.4); font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; padding: 10px 0;">{h_text}</div>', unsafe_allow_html=True)
            
            st.markdown('<div style="border-bottom: 1px solid rgba(255, 255, 255, 0.05); margin-bottom: 10px;"></div>', unsafe_allow_html=True)
    
    
            sorted_categories = sorted(categories, key=lambda x: x["val_tl"], reverse=True)
            for c in sorted_categories:
                if c['val_tl'] > 0:
                    v_str = f"{c['val']:,.0f} {c['currency']}"
                    c_str = f"{c['cost']:,.0f} {c['currency']}"
                    d_val = f"%{c['daily']:.1f}"
                    t_val = f"%{c['change']:.1f}"
                    
                    # Calculate amounts
                    d_amt = c['val'] - c['prev']
                    t_amt = c['val'] - c['cost']
                    d_sign = "+" if d_amt > 0 else ""
                    t_sign = "+" if t_amt > 0 else ""
                    
                    d_cls = "text-glow-green" if c["daily"] > 0 else ("text-glow-red" if c["daily"] < 0 else "")
                    t_cls = "text-glow-green" if c["change"] > 0 else ("text-glow-red" if c["change"] < 0 else "")
                    
                    c_cols = st.columns([2.5, 2, 2, 1.2, 1.3, 1])
                    with c_cols[0]:
                        st.markdown(f'<div style="line-height:40px; color:white; font-weight:500; font-size:0.85rem; padding-left:15px;">{c["emoji"]} {c["name"]}</div>', unsafe_allow_html=True)
                    with c_cols[1]:
                        st.markdown(f'<div style="line-height:40px; color:white; font-size:0.85rem;">{c_str}</div>', unsafe_allow_html=True)
                    with c_cols[2]:
                        st.markdown(f'<div style="line-height:40px; color:white; font-size:0.85rem; font-weight:600;">{v_str}</div>', unsafe_allow_html=True)
                    with c_cols[3]:
                        st.markdown(f'<div style="line-height:20px; padding: 5px 0; font-size:0.85rem;" class="{d_cls}">{d_val}<br><span style="font-size:0.7rem; opacity:0.6;">{d_sign}{d_amt:,.0f} {c["currency"]}</span></div>', unsafe_allow_html=True)
                    with c_cols[4]:
                        st.markdown(f'<div style="line-height:20px; padding: 5px 0; font-size:0.85rem;" class="{t_cls}">{t_val}<br><span style="font-size:0.7rem; opacity:0.6;">{t_sign}{t_amt:,.0f} {c["currency"]}</span></div>', unsafe_allow_html=True)
                    with c_cols[5]:
                        if st.button("👁️", key=f"vc_{c['name']}"):
                            # Filter detailed_list by category name logic
                            cat_assets = [h for h in detailed_list if c["emoji"] in h.get("Emoji", "")]
                            if not cat_assets:
                                cat_assets = [h for h in detailed_list if h.get("Emoji") == c["emoji"]]
                            # Set session state to show dialog (no rerun needed)
                            st.session_state.show_portfolio_details = True
                            st.session_state.portfolio_details_name = f"{c['emoji']} {c['name']} Varlıkları"
                            st.session_state.portfolio_details_data = cat_assets
                            
            st.markdown('</div>', unsafe_allow_html=True)
    
            # ALL ASSETS
            if "asset_sort_by" not in st.session_state:
                st.session_state.asset_sort_by = "Değer"
            
            # Header and Sort Controls in a single line
            header_cols = st.columns([1, 1])
            with header_cols[0]:
                st.markdown('<div style="margin-top:10px; margin-bottom:15px; display:flex; align-items:center; gap:10px;"><i class="fas fa-list-ul" style="color:#00f2ff;"></i><span style="color:white; font-weight:600; font-size:1rem;">Tüm Varlıklarım</span></div>', unsafe_allow_html=True)
            
            with header_cols[1]:
                sort_options = {"Değer": "Deger_TL", "Günlük %": "Günlük (%)", "Toplam %": "Toplam (%)", "Teknik Skor": "t_score"}
                def on_sort_change():
                    st.session_state.asset_sort_by = st.session_state.asset_sort_radio
                st.radio("Sırala", options=list(sort_options.keys()), key="asset_sort_radio", index=list(sort_options.keys()).index(st.session_state.asset_sort_by), horizontal=True, label_visibility="collapsed", on_change=on_sort_change)
    
            # Custom Header for All Assets (Tightened Varlık-Skor relationship)
            a_h_cols = st.columns([1.3, 0.7, 2.8, 1.8, 1.8, 1.8, 1.5, 1.5, 0.5])
            a_headers = ["VARLIK", "SKOR", "MALİYET", "TOPLAM ALIŞ", "GÜNCEL", "TOPLAM DEĞER", "GÜNLÜK K/Z", "TOPLAM K/Z", ""]
            for i, h_text in enumerate(a_headers):
                with a_h_cols[i]:
                    align = "center" if h_text == "MALİYET" else "left"
                    st.markdown(f'<div style="color: rgba(255, 255, 255, 0.4); font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; padding: 10px 0; text-align: {align};">{h_text}</div>', unsafe_allow_html=True)
            
            st.markdown('<div style="border-bottom: 1px solid rgba(255, 255, 255, 0.05); margin-bottom: 10px;"></div>', unsafe_allow_html=True)

            sort_key = sort_options.get(st.session_state.asset_sort_by, "Deger_TL")
            sorted_detailed_list = sorted(detailed_list, key=lambda x: x.get(sort_key, 0), reverse=True)
            for i, h in enumerate(sorted_detailed_list):
                curr = h.get("Para", "TL")
                g_kz = h.get("Gunluk_KZ", 0)
                t_kz = h.get("Toplam_KZ", 0)
                g_cls = "text-glow-green" if g_kz > 0 else ("text-glow-red" if g_kz < 0 else "")
                t_cls = "text-glow-green" if t_kz > 0 else ("text-glow-red" if t_kz < 0 else "")
                
                # Technical Score Data
                ts = h.get("t_score", 0)
                ts_col = h.get("score_color", "#cccccc")
                ts_lab = h.get("score_label", "N/A")

                # Highlight columns if sorted
                g_style = "background: rgba(0, 242, 255, 0.03); border-radius: 4px; padding: 2px 5px;" if sort_key == "Günlük (%)" else ""
                t_style = "background: rgba(0, 242, 255, 0.03); border-radius: 4px; padding: 2px 5px;" if sort_key == "Toplam (%)" else ""
                v_style = "font-weight:700; color:#00f2ff;" if sort_key == "Deger_TL" else ""

                r_cols = st.columns([1.3, 0.7, 2.8, 1.8, 1.8, 1.8, 1.5, 1.5, 0.5])
                with r_cols[0]:
                    sig = h.get("Signal")
                    norm_sig = "AL" if sig and "AL" in str(sig) else ("SAT" if sig and "SAT" in str(sig) else None)
                    signal_tag = ""
                    if norm_sig:
                        tag_color = "#00ff88" if norm_sig == "AL" else "#ff3e3e"
                        tag_bg = "rgba(0, 255, 136, 0.15)" if norm_sig == "AL" else "rgba(255, 62, 62, 0.15)"
                        tag_border = "rgba(0, 255, 136, 0.3)" if norm_sig == "AL" else "rgba(255, 62, 62, 0.3)"
                        signal_tag = f'<span style="background:{tag_bg}; color:{tag_color}; font-size:0.6rem; padding:1px 5px; border-radius:3px; margin-left:5px; border:1px solid {tag_border}; font-weight:700;">{norm_sig}</span>'
                    st.markdown(f'<div style="line-height:20px; color:white; font-weight:700; font-size:1.05rem;">{h["Emoji"]} {h["Varlık"]}{signal_tag}<br><span style="font-size:0.75rem; color:rgba(255,255,255,0.4); font-weight:500;">{h["Portföy"]}</span></div>', unsafe_allow_html=True)
                
                with r_cols[1]: # SCORE COLUMN (Left aligned to Varık)
                    st.markdown(f"""
                        <div style="display:flex; flex-direction:column; align-items:flex-start; justify-content:center; line-height:1; padding-top:5px;">
                            <div style="font-size:1.1rem; font-weight:900; color:{ts_col};">{ts:.1f}</div>
                            <div style="font-size:0.55rem; font-weight:800; color:{ts_col}; opacity:0.8; margin-top:2px;">{ts_lab}</div>
                        </div>
                    """, unsafe_allow_html=True)

                with r_cols[2]:
                    st.markdown(f'<div style="line-height:40px; color:rgba(255,255,255,0.7); font-size:0.85rem; text-align: center;">{h["Maliyet"]:,.2f} {curr}</div>', unsafe_allow_html=True)
                with r_cols[3]:
                    st.markdown(f'<div style="line-height:40px; color:rgba(255,255,255,0.7); font-size:0.85rem;">{h["T_Maliyet"]:,.2f} {curr}</div>', unsafe_allow_html=True)
                with r_cols[4]:
                    st.markdown(f'<div style="line-height:40px; color:white; font-size:0.85rem;">{h["Güncel"]:,.2f} {curr}</div>', unsafe_allow_html=True)
                with r_cols[5]:
                    st.markdown(f'<div style="line-height:40px; color:white; font-size:0.85rem; {v_style}">{h["Deger"]:,.2f} {curr}</div>', unsafe_allow_html=True)
                with r_cols[6]:
                    st.markdown(f'<div style="line-height:18px; padding: 4px 0; font-size:0.85rem; {g_style}" class="{g_cls}">%{h["Günlük (%)"]:.2f}<br><span style="font-size:0.7rem; opacity:0.6;">({g_kz:,.0f})</span></div>', unsafe_allow_html=True)
                with r_cols[7]:
                    st.markdown(f'<div style="line-height:18px; padding: 4px 0; font-size:0.85rem; {t_style}" class="{t_cls}">%{h["Toplam (%)"]:.2f}<br><span style="font-size:0.7rem; opacity:0.6;">({t_kz:,.0f})</span></div>', unsafe_allow_html=True)
                with r_cols[8]:
                    st.write("") # Vertical offset
                    if st.button("📊", key=f"chart_btn_{h['Varlık']}_{i}"):
                        st.session_state.chart_asset = h['Varlık']
                        orig_type = "bist hisse"
                        for ah in agg_holdings:
                            if ah['symbol'] == h['Varlık']:
                                orig_type = ah.get('type', 'bist hisse')
                                break
                        st.session_state.chart_asset_type = orig_type
                        st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    


    elif st.session_state.active_tab == "PORTFÖY ANALİZİ":
        # --- GEMINI AI ANALYSIS TAB ---
        st.markdown(f'<div style="margin-top:0px; margin-bottom:25px; display:flex; align-items:center; gap:12px;"><span>🤖</span><span style="color:white; font-weight:700; font-size:1.4rem; letter-spacing:-0.5px;">Yapay Zeka Portföy Analisti</span></div>', unsafe_allow_html=True)
        
        # 1. Premium AI Analysis Zone
        st.markdown("""
            <style>
                .ai-master-zone {
                    padding: 40px 0;
                    width: 100%;
                    max-width: 900px;
                    margin: 0 auto;
                    text-align: center;
                }
                .ai-master-zone div[data-testid="stButton"] button {
                    background: linear-gradient(135deg, rgba(0, 242, 255, 0.2) 0%, rgba(10, 15, 20, 0.95) 100%) !important;
                    border: 2px solid rgba(0, 242, 255, 0.5) !important;
                    border-radius: 25px !important;
                    height: 120px !important;
                    width: 100% !important;
                    box-shadow: 0 15px 50px rgba(0, 0, 0, 0.5) !important;
                    transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275) !important;
                    backdrop-filter: blur(25px) !important;
                }
                .ai-status-card {
                    background: rgba(255, 255, 255, 0.03);
                    border: 1px solid rgba(0, 242, 255, 0.2);
                    border-radius: 20px;
                    padding: 40px;
                    margin-bottom: 30px;
                }
                @keyframes pulse-ai {
                    0% { opacity: 0.6; transform: scale(1); }
                    50% { opacity: 1; transform: scale(1.02); }
                    100% { opacity: 0.6; transform: scale(1); }
                }
                .ai-pulse-text {
                    color: #00f2ff;
                    font-size: 1.5rem;
                    font-weight: 800;
                    animation: pulse-ai 2s infinite ease-in-out;
                }
            </style>
        """, unsafe_allow_html=True)

        st.markdown('<div class="ai-master-zone">', unsafe_allow_html=True)
        
        # Trigger analysis if coming from tab click or first time
        should_run = False
        if st.session_state.get("trigger_ai_analysis", False):
            st.session_state.trigger_ai_analysis = False
            should_run = True

        if not should_run:
            if st.button("🔄 ANALİZİ BAŞLAT / YENİLE", key="ai_analiz_tab_btn", use_container_width=True):
                should_run = True

        if should_run:
            
            fund_contents = {}
            # Silent processing (no standard spinner)
            for asset in agg_holdings:
                a_type = str(asset.get("type", "")).lower()
                if any(x in a_type for x in ["tefas", "fon", "bes", "oks"]):
                    symbol = asset.get("symbol", "").upper()
                    try:
                        import borsapy
                        fund = borsapy.Fund(symbol)
                        alloc = fund.allocation
                        if not alloc.empty:
                            latest_date = alloc['Date'].max()
                            latest_alloc = alloc[alloc['Date'] == latest_date]
                            fund_contents[symbol] = latest_alloc[['asset_type', 'weight']].to_dict(orient='records')
                    except: pass

            p_data = {
                "toplam_deger_tl": total_val_tl,
                "toplam_deger_usd": tv_usd,
                "gunluk_kz_tl": daily_kz_amount,
                "toplam_kz_tl": total_kz_amount,
                "toplam_kz_usd": total_kz_usd,
                "risk_skoru": risk_val,
                "guncel_usd_kuru": usd_rate,
                "kategoriler": [{cat['name']: f"{cat['val']:,.0f} {cat['currency']} (%{cat['val_tl']/total_val_tl*100:.1f} pay)"} for cat in categories if cat['val_tl'] > 0],
                "en_cok_yukselen": f"{sorted_detailed_list[-1]['Varlık']} (%{sorted_detailed_list[-1]['Günlük (%)']:.1f})" if detailed_list and sorted_detailed_list[-1].get("Günlük (%)", 0) > 0 else "Yok",
                "en_cok_dusende": f"{sorted_detailed_list[0]['Varlık']} (%{sorted_detailed_list[0]['Günlük (%)']:.1f})" if detailed_list and sorted_detailed_list[0].get("Günlük (%)", 0) < 0 else "Yok",
                "fon_icerikleri_ozeti": fund_contents
            }
            ai_analysis_dialog(str(p_data))
        st.markdown('</div>', unsafe_allow_html=True)

elif st.session_state.active_tab == "STRATEJİLER":
    st.markdown("""
        <style>
            .strategy-view-header {
                margin: 0px 0 30px 0;
            }
            .alert-card {
                background: linear-gradient(145deg, rgba(23, 27, 33, 0.9) 0%, rgba(11, 14, 20, 0.95) 100%);
                backdrop-filter: blur(15px);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 16px;
                padding: 16px 20px;
                margin-bottom: 12px;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                position: relative;
                overflow: hidden;
            }
            .alert-card:hover {
                transform: translateY(-4px);
                box-shadow: 0 12px 40px rgba(0, 0, 0, 0.6);
            }
            .alert-card::before {
                content: "";
                position: absolute;
                top: 0; left: 0; width: 4px; height: 100%;
                opacity: 0.8;
            }
            .alert-active-alim {
                background: linear-gradient(145deg, rgba(0, 255, 136, 0.05) 0%, rgba(11, 14, 20, 0.98) 100%) !important;
                border: 1px solid rgba(0, 255, 136, 0.15) !important;
                box-shadow: 0 8px 32px rgba(0, 255, 136, 0.05);
            }
            .alert-active-alim::before { background: #00ff88; box-shadow: 0 0 15px #00ff88; }
            
            .alert-active-satis {
                background: linear-gradient(145deg, rgba(255, 62, 62, 0.05) 0%, rgba(11, 14, 20, 0.98) 100%) !important;
                border: 1px solid rgba(255, 62, 62, 0.15) !important;
                box-shadow: 0 8px 32px rgba(255, 62, 62, 0.05);
            }
            .alert-active-satis::before { background: #ff3e3e; box-shadow: 0 0 15px #ff3e3e; }

            .alert-triggered::before { background: #ffffff; box-shadow: 0 0 15px #ffffff; }
            
            .alert-triggered {
                background: linear-gradient(145deg, rgba(255, 255, 255, 0.03) 0%, rgba(23, 27, 33, 0.8) 100%);
                border: 1px solid rgba(255, 255, 255, 0.1) !important;
            }

            .label-mini {
                color: rgba(255, 255, 255, 0.4);
                font-size: 0.65rem;
                font-weight: 800;
                text-transform: uppercase;
                letter-spacing: 1.2px;
                margin-bottom: 4px;
            }
            
            .val-main {
                color: white;
                font-size: 1.4rem;
                font-weight: 800;
                letter-spacing: -0.5px;
            }

            .progress-container-v2 {
                height: 8px;
                width: 100%;
                background: rgba(255, 255, 255, 0.05);
                border-radius: 4px;
                margin-top: 20px;
                position: relative;
                overflow: hidden;
            }
            .progress-fill-v2 {
                height: 100%;
                border-radius: 4px;
                transition: width 1s ease-out;
            }
            .fill-alim { background: linear-gradient(90deg, #00ff8850, #00ff88); box-shadow: 0 0 15px #00ff8880; }
            .fill-satis { background: linear-gradient(90deg, #ff3e3e50, #ff3e3e); box-shadow: 0 0 15px #ff3e3e80; }
            
            .strategy-status-tag {
                padding: 4px 10px;
                border-radius: 6px;
                font-size: 0.7rem;
                font-weight: 800;
                letter-spacing: 0.5px;
                display: inline-flex;
                align-items: center;
                gap: 5px;
            }
            .tag-alim, .tag-al { background: rgba(0, 255, 136, 0.1); color: #00ff88; border: 1px solid rgba(0, 255, 136, 0.2); }
            .tag-satis, .tag-sat { background: rgba(255, 62, 62, 0.1); color: #ff3e3e; border: 1px solid rgba(255, 255, 255, 0.2); }
            .tag-triggered { background: rgba(255, 255, 255, 0.1); color: #ffffff; border: 1px solid rgba(255, 255, 255, 0.2); }
            
            /* Custom Scrollbar for tabs */
            [data-baseweb="tab-highlight"] { background-color: #00f2ff !important; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="strategy-view-header"><div style="display:flex; align-items:center; gap:12px;"><i class="fas fa-chess" style="color:#00f2ff; font-size:1.8rem;"></i><span style="color:white; font-weight:800; font-size:1.8rem; letter-spacing:-1px;">Strateji Takip Merkezi</span></div></div>', unsafe_allow_html=True)
    
    col_new, col_list = st.columns([1, 2], gap="large")
    
    with col_new:
        st.markdown('<div class="glass-card" style="padding:30px; border:1px solid rgba(0, 242, 255, 0.2); background: rgba(0, 242, 255, 0.02);">', unsafe_allow_html=True)
        st.markdown('<p style="color:white; font-weight:800; font-size:1.2rem; margin-bottom:25px; display:flex; align-items:center; gap:10px;">🎯 Yeni Strateji</p>', unsafe_allow_html=True)
        
        with st.form("new_strategy_form_v2", clear_on_submit=True):
            a_action = st.radio("🎬 İşlem", ["AL", "SAT"], horizontal=True)
            a_type = st.selectbox("📊 Tip", ["bist hisse", "abd hisse/etf", "kripto", "döviz", "emtia", "tefas fon"])
            a_sym = st.text_input("🔤 Sembol", placeholder="Örn: THYAO, BTC...").upper().strip()
            a_target = st.number_input("💰 Hedef Fiyat", min_value=0.0, value=None, placeholder="Fiyat girin", step=0.0001, format="%.4f")
            
            st.markdown('<div style="margin-top:20px;"></div>', unsafe_allow_html=True)
            submit_a = st.form_submit_button("🚀 STRATEJİ EKLENSİN", type="primary", use_container_width=True)
            
            if submit_a:
                if a_sym and a_target is not None and a_target > 0:
                    with st.spinner("🔍 Doğrulanıyor..."):
                        valid = get_current_data(a_sym, a_type)
                    if valid:
                        curr_p = valid['price']
                        a_cond = "Fiyat Üstünde" if a_target >= curr_p else "Fiyat Altında"
                        success, msg = add_alert(a_sym, a_target, a_cond, a_type, initial_price=curr_p, action_type=a_action)
                        if success:
                            st.toast(f"✅ {msg}", icon="🚀")
                            time.sleep(1)
                            st.rerun()
                        else: st.error(f"❌ {msg}")
                    else: st.error(f"❌ '{a_sym}' bulunamadı.")
                else: st.warning("⚠️ Eksik bilgi.")

        st.markdown('</div>', unsafe_allow_html=True)

    with col_list:
        all_alerts = load_alerts()
        # Separate active and history
        active_alerts = [a for a in all_alerts if not a.get("triggered", False)]
        history_alerts = [a for a in all_alerts if a.get("triggered", False)]
        
        # Group active strategies by Symbol
        asset_strategies = {}
        for a in active_alerts:
            s_key = a['symbol']
            if s_key not in asset_strategies: asset_strategies[s_key] = []
            asset_strategies[s_key].append(a)

        # Get portfolio assets
        p_assets = {}
        # Use existing all_holdings or fetch
        source_holdings = globals().get('all_holdings', [])
        if not source_holdings:
             try: source_holdings = get_all_holdings()
             except: pass
        
        for h in source_holdings:
            s = h['symbol']
            if s not in p_assets: p_assets[s] = {"type": h.get("type", "bist hisse"), "amount": 0}
            p_assets[s]["amount"] += h.get("amount", 0)

        # Tabs
        tab_portfolio, tab_watched = st.tabs(["💼 Varlıklarım", "👀 Takip Edilenler"])

        
        # Helper to render a card
        def render_sc_card(sym, is_watched_tab=False):
            # Determine Type
            atype = "bist hisse" # Default
            # Try to infer type from existing strategies or portfolio
            if sym in asset_strategies and asset_strategies[sym]:
                atype = asset_strategies[sym][0]["type"]
            elif sym in p_assets:
                atype = p_assets[sym]["type"]
            
            curr_data = get_current_data(sym, atype)
            # Fallback for crypto
            if not curr_data and atype != "kripto":
                curr_data = get_current_data(sym, "kripto")
                if curr_data: atype = "kripto" # Update type if found as crypto
            
            curr_price = curr_data["price"] if curr_data else 0
            
            strategies = asset_strategies.get(sym, [])
            
            if strategies:
                # STRATEGY CARDS
                for al in strategies:
                    al_id = al.get('id', al.get('created_at'))
                    raw_action = al.get("action_type", "STRATEJİ")
                    action = "AL" if "AL" in raw_action else ("SAT" if "SAT" in raw_action else raw_action)
                    target = al.get('target_price', 1)
                    initial = al.get('initial_price', target)
                    
                    # Logic for display
                    if curr_price <= target:
                        left_p, left_lbl, left_glow, left_c = curr_price, "GÜNCEL", "text-shadow:0 0 20px rgba(0,242,255,0.4);", "#00f2ff"
                        right_p, right_lbl, right_glow, right_c = target, "HEDEF", "", "#fff"
                        bar_align = "flex-end"
                    else:
                        left_p, left_lbl, left_glow, left_c = target, "HEDEF", "", "#fff"
                        right_p, right_lbl, right_glow, right_c = curr_price, "GÜNCEL", "text-shadow:0 0 20px rgba(0,242,255,0.4);", "#00f2ff"
                        bar_align = "flex-start"

                    dist_pct = (target/curr_price - 1) * 100 if curr_price > 0 else 0
                    abs_dist = abs(dist_pct)
                    progress = min(abs_dist * 10, 100) if abs_dist <= 10 else 100
                    
                    cls_suffix = "alim" if "AL" in action else "satis"
                    emoji = "🟢" if "AL" in action else "🔴"
                    prog_txt = f'<div style="font-size:0.6rem; color:rgba(255,255,255,0.3); font-weight:800; text-align:center; margin-top:10px; letter-spacing:1px;">KALAN: %{abs_dist:.2f}</div>' if abs_dist <= 10 else ""

                    # Define trig_at (Time display)
                    try:
                        c_date_str = al.get('created_at', datetime.now().isoformat())
                        c_date = datetime.fromisoformat(c_date_str)
                        d_diff = (datetime.now().date() - c_date.date()).days
                        if d_diff == 0: trig_at = "Bugün"
                        elif d_diff == 1: trig_at = "Dün"
                        else: trig_at = f"{d_diff} gün önce"
                    except:
                        trig_at = "Yeni"


                    col_card, col_del = st.columns([12, 1])
                    with col_card:
                        st.markdown(f"""<div class="alert-card alert-active-{cls_suffix}" style="padding: 10px 15px;">
<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
<div style="display:flex; align-items:center; gap:8px;">
<span style="color:white; font-weight:800; font-size:1.1rem; letter-spacing:-0.5px;">{sym}</span>
<span class="strategy-status-tag tag-{cls_suffix}" style="padding:1px 6px; font-size:0.6rem;">{emoji} {action}</span>
</div>
<div style="background:rgba(255,255,255,0.05); padding:2px 8px; border-radius:80px; border:1px solid rgba(255,255,255,0.1); display:flex; align-items:center;">
<span style="color:rgba(255,255,255,0.5); font-size:0.6rem; font-weight:700; margin-right:4px;">BAŞ:</span>
<span style="color:white; font-size:0.7rem; font-weight:800;">{initial:,.2f}</span>
</div>
</div>
<div style="display:flex; justify-content:space-between; align-items:flex-end; position:relative; margin-bottom:4px;">
<div style="text-align:left;">
<div class="label-mini" style="font-size:0.55rem; margin-bottom:0;">{left_lbl}</div>
<div class="val-main" style="color:{left_c}; {left_glow}; font-size:1.0rem; line-height:1.1;">{left_p:,.2f}</div>
</div>
<div style="position:absolute; left:50%; bottom:2px; transform:translateX(-50%); text-align:center;">
<div style="background:{'#00ff8820' if abs_dist < 1 else 'rgba(255,255,255,0.05)'}; color:{'#00ff88' if abs_dist < 1 else 'rgba(255,255,255,0.4)'}; padding:1px 8px; border-radius:8px; font-weight:800; font-size:0.7rem; border:1px solid {'#00ff8840' if abs_dist < 1 else 'transparent'};">%{abs_dist:.2f}</div>
</div>
<div style="text-align:right;">
<div class="label-mini" style="font-size:0.55rem; margin-bottom:0;">{right_lbl}</div>
<div class="val-main" style="color:{right_c}; {right_glow}; font-size:1.0rem; line-height:1.1;">{right_p:,.2f}</div>
</div>
</div>
<div class="progress-container-v2" style="display:flex; justify-content:{bar_align}; margin-top:4px; height:4px; background:rgba(255,255,255,0.1);">
<div class="progress-fill-v2 fill-{cls_suffix}" style="width:{progress}%;"></div>
</div>
</div>""", unsafe_allow_html=True)
                    
                    with col_del:
                        st.write("") 
                        st.write("") 
                        st.write("")
                        if st.button("✕", key=f"del_al_{al_id}", help="Stratejiyi Kaldır"):
                            delete_alert(al_id)
                            st.rerun()

            elif not is_watched_tab:
                # NO STRATEGY CARD (Only for owned assets tab)
                # NO STRATEGY CARD (Only for owned assets tab)
                col_card = st.columns(1)[0]
                with col_card:
                     # Calculate simple change if available
                     change_pct = 0
                     if curr_data and curr_data.get('prev_close'):
                         change_pct = (curr_price / curr_data['prev_close'] - 1) * 100
                     
                     pct_color = "#00ff88" if change_pct >= 0 else "#ff3e3e"
                     sign = "+" if change_pct >= 0 else ""
                     
                     st.markdown(f"""
                        <div class="glass-card" style="padding:15px; display:flex; justify-content:space-between; align-items:center; border-left: 4px solid rgba(255,255,255,0.1); margin-bottom: 0px;">
                            <div>
                                <div style="font-size:1.2rem; font-weight:800; color:white;">{sym}</div>
                                <div style="font-size:0.7rem; color:rgba(255,255,255,0.4); text-transform:uppercase;">{atype}</div>
                            </div>
                            <div style="text-align:right;">
                                <div style="font-size:1.1rem; font-weight:700; color:white;">{curr_price:,.2f}</div>
                                <div style="font-size:0.8rem; font-weight:600; color:{pct_color};">{sign}%{change_pct:.2f}</div>
                            </div>
                        </div>
                     """, unsafe_allow_html=True)
                     
                     # Manual Toggle for Strategy Form (Avoids expander glitch)
                     form_key = f"show_form_{sym}"
                     if st.button("🎯 STRATEJİ OLUŞTUR", key=f"btn_toggle_{sym}", use_container_width=True):
                         st.session_state[form_key] = not st.session_state.get(form_key, False)
                     
                     if st.session_state.get(form_key, False):
                         st.markdown('<div style="background:rgba(255,255,255,0.03); border-radius:12px; padding:15px; margin-top:5px; border:1px solid rgba(255,255,255,0.05); animation: fadeIn 0.3s;">', unsafe_allow_html=True)
                         with st.form(f"quick_add_{sym}"):
                             q_cols = st.columns(2)
                             with q_cols[0]:
                                 q_action = st.radio("İşlem", ["AL", "SAT"], horizontal=True, key=f"q_act_{sym}")
                             with q_cols[1]:
                                 q_target = st.number_input("Hedef", min_value=0.0, value=float(curr_price), step=0.01, key=f"q_tgt_{sym}")
                             
                             st.write("")
                             if st.form_submit_button("ONAYLA", type="primary", use_container_width=True):
                                 q_cond = "Fiyat Üstünde" if q_target >= curr_price else "Fiyat Altında"
                                 succ, msg = add_alert(sym, q_target, q_cond, atype, initial_price=curr_price, action_type=q_action)
                                 if succ: 
                                     st.session_state[form_key] = False # Close form
                                     st.rerun()
                                 else: st.error(msg)
                         st.markdown('</div>', unsafe_allow_html=True)
                                 
        # RENDER LOOPS
        # Type Priority Helper
        def get_type_prio(t):
            t = t.lower() if t else ""
            if "kripto" in t: return 0
            if "bist" in t: return 1
            if "abd" in t or "etf" in t or "nasdaq" in t: return 2
            if "emtia" in t or "altın" in t or "gümüş" in t: return 3
            if "tefas" in t or "fon" in t: return 4
            if "döviz" in t: return 5
            return 99

        with tab_portfolio:
            # Sort: 1) Has Strategy? (0/1) 2) Type Priority 3) Alphabetical
            p_syms = sorted(
                list(p_assets.keys()),
                key=lambda sym: (
                    0 if sym in asset_strategies and asset_strategies[sym] else 1,
                    get_type_prio(p_assets[sym].get("type", "")),
                    sym
                )
            )
            
            if not p_syms:
                st.info("Portföyünüzde varlık bulunamadı.")
            else:
                 st.markdown('<div style="margin-top:10px;"></div>', unsafe_allow_html=True)
                 for sym in p_syms: render_sc_card(sym, is_watched_tab=False)
        
        with tab_watched:
             # Sort: 1) Type Priority 2) Alphabetical (All have strategies here)
             w_syms = sorted(
                 list(set(asset_strategies.keys()) - set(p_assets.keys())),
                 key=lambda sym: (
                     get_type_prio(asset_strategies[sym][0].get("type", "")) if asset_strategies.get(sym) else 99,
                     sym
                 )
             )
             
             if not w_syms:
                 st.info("Portföy dışı takip edilen strateji yok.")
             else:
                 st.markdown('<div style="margin-top:10px;"></div>', unsafe_allow_html=True)
                 for sym in w_syms: render_sc_card(sym, is_watched_tab=True)





# 6. MODALS (Stay at the bottom)
if st.session_state.show_asset_modal: asset_management_dialog()
if st.session_state.show_portfolio_modal: portfolio_management_dialog()
if st.session_state.show_portfolio_details: 
    portfolio_details_dialog(st.session_state.portfolio_details_name, st.session_state.portfolio_details_data)
    st.session_state.show_portfolio_details = False  # Reset after showing
if st.session_state.chart_asset:
    asset_chart_dialog(st.session_state.chart_asset, st.session_state.chart_asset_type)
    st.session_state.chart_asset = None # Reset

if st.session_state.show_history_modal:
    transaction_history_dialog()
    st.session_state.show_history_modal = False
