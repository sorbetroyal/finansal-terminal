from utils import (get_current_data, load_portfolio, add_asset, remove_asset, delete_asset,
                   get_history, create_portfolio, delete_portfolio, save_all_portfolios, get_all_holdings, get_portfolio_history,
                   load_selected_portfolios, save_selected_portfolios, get_portfolio_metrics, fetch_all_prices_parallel,
                   load_alerts, add_alert, delete_alert, check_alerts, migrate_local_to_supabase, claim_orphaned_supabase_data)
from auth import init_auth_state, get_current_user, render_auth_page, logout
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import requests
import time
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




@st.dialog("Portföy İçeriği", width="large")
def portfolio_details_dialog(p_name, p_list):
    # Aggressive CSS to ensure high-contrast colors and visibility
    st.markdown("""
        <style>
            /* Reset any transparency or dimming */
            div[role="dialog"] * { opacity: 1.0 !important; }
            
            /* Table Styling */
            .p-details-table { width: 100%; border-collapse: collapse; background-color: #0b0e14; border-radius: 12px; overflow: hidden; border: 1px solid rgba(255,255,255,0.1); }
            .p-details-table th { background: rgba(255,255,255,0.05); color: rgba(255,255,255,0.5) !important; padding: 15px; text-align: left; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; }
            .p-details-table td { padding: 15px; color: #FFFFFF !important; font-size: 0.9rem; border-bottom: 1px solid rgba(255,255,255,0.05); }
            
            /* Neon Profit/Loss */
            .neon-green-text { color: #00FF00 !important; font-weight: 900 !important; text-shadow: 0 0 8px rgba(0, 255, 0, 0.6) !important; filter: drop-shadow(0 0 2px black); }
            .neon-red-text { color: #FF0000 !important; font-weight: 900 !important; text-shadow: 0 0 8px rgba(255, 0, 0, 0.6) !important; filter: drop-shadow(0 0 2px black); }
            .kz-sub { font-size: 0.75rem; font-weight: 400; opacity: 0.9 !important; margin-top: 2px; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown(f"<h3 style='color:#00f2ff !important; font-size:1.3rem; font-weight:700; margin-bottom:20px; text-shadow: 0 0 10px rgba(0,242,255,0.3);'>📂 {p_name} İçeriği</h3>", unsafe_allow_html=True)
    
    if not p_list:
        st.info("Bu portföyde henüz varlık bulunmuyor.")
        return

    rows = ""
    for h in p_list:
        curr = h.get("Para", "TL")
        # Handle decimal rounding for metrics
        t_val = float(h.get('Toplam (%)', 0))
        t_amt = float(h.get('Toplam_KZ', 0))
        d_val = float(h.get('Günlük (%)', 0))
        d_amt = float(h.get('Gunluk_KZ', 0))
        
        # Determine CSS classes
        d_cls = "neon-green-text" if d_val > 0 else ("neon-red-text" if d_val < 0 else "")
        t_cls = "neon-green-text" if t_val > 0 else ("neon-red-text" if t_val < 0 else "")
        
        d_sign = "+" if d_val > 0 else ""
        t_sign = "+" if t_val > 0 else ""
        
        rows += f"""<tr>
            <td style="font-weight:700;">{h.get('Emoji', '💰')} {h.get('Varlık', '-')}</td>
            <td style="color:rgba(255,255,255,0.7) !important;">{h.get('Adet', 0):,.2f}</td>
            <td style="color:rgba(255,255,255,0.7) !important;">{h.get('Maliyet', 0):,.2f} {curr}</td>
            <td>{h.get('Güncel', 0):,.2f} {curr}</td>
            <td style="font-weight:600;">{h.get('Deger', 0):,.2f} {curr}</td>
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
                "bist hisse", "abd hisse/etf", "tefas fon", "kripto", "döviz", "emtia", "eurobond", "bes/oks"
            ], key="add_type")
            asset_symbol = st.text_input("🔤 Varlık Sembolü", key="add_symbol").strip().upper()
        
        with col2:
            asset_amount = st.number_input("🔢 Adet", min_value=0.0, value=None, placeholder="1.0", step=0.0001, format="%.4f", key="add_amount")
            # The widget now takes its value directly from the session_state key modified above
            asset_cost = st.number_input("💰 Birim Maliyet", min_value=0.0, value=None, placeholder="0.00", step=0.0001, format="%.4f", key="add_cost_widget")

            purchase_date = st.date_input("📅 Alış Tarihi", value=datetime.now(), key="add_date")
        
        st.markdown("<div style='margin-top:25px;'></div>", unsafe_allow_html=True)
        if st.button("🚀 Varlık Ekle", type="primary", use_container_width=True):
            if asset_symbol and asset_amount is not None and asset_cost is not None and asset_amount > 0 and asset_cost > 0:
                with st.spinner(f"🔍 {asset_symbol} kontrol ediliyor..."):
                    valid_data = get_current_data(asset_symbol, asset_type)
                
                if valid_data:
                    success = add_asset(selected_portfolio, asset_symbol, asset_amount, asset_cost, asset_type, purchase_date.strftime("%Y-%m-%d"))
                    if success:
                        st.success(f"✅ {asset_symbol} eklendi!")
                        st.session_state.show_asset_modal = False
                        st.rerun()
                    else: 
                        st.error("❌ Hata.")
                else:
                    st.error(f"❌ '{asset_symbol}' bulunamadı!")
            else: 
                st.warning("⚠️ Bilgileri eksiksiz girin.")


    
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
                        if r_amount > 0 and r_price > 0:
                            success = remove_asset(remove_portfolio, r_symbol, r_amount, r_price, r_date)
                            if success:
                                st.success(f"✅ Satış başarılı!")
                                st.session_state.show_asset_modal = False
                                st.rerun()
                            else: st.error("❌ Hata.")
                        else: st.warning("⚠️ Bilgileri doldurun.")
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


# PREMIUM MODERN DESIGN SYSTEM (v4)
st.markdown("""
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
<style>
    /* 1. Global & Deep Space Background */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');
    * { font-family: 'Outfit', sans-serif !important; }
    
    header[data-testid="stHeader"] { display: none !important; }
    
    html, body, [data-testid="stAppViewContainer"], .stApp, [data-testid="stAppViewBlockContainer"], .block-container {
        background-color: #0b0e14 !important;
        padding-top: 0rem !important;
        margin-top: 0rem !important;
        color: white !important;
    }

    .main .block-container { 
        padding-left: 0 !important;
        padding-right: 0 !important;
        max-width: 100% !important; 
        min-height: 100vh;
    }

    /* Selectbox Visibility Fix */
    div[data-baseweb="select"] > div {
        background-color: rgba(255,255,255,0.05) !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        color: white !important;
        font-weight: 600 !important;
    }
    /* ULTIMATE SELECTBOX LIST VISIBILITY FIX */
    [data-baseweb="popover"] ul {
        background-color: #1a1c23 !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
    }
    [data-baseweb="popover"] li {
        background-color: #1a1c23 !important;
        color: #FFFFFF !important;
        font-family: 'Outfit', sans-serif !important;
    }
    [data-baseweb="popover"] li:hover {
        background-color: #00f2ff !important;
        color: #0b0e14 !important;
    }
    /* Simple fallback for any other dropdown type */
    div.stSelectbox div[role="listbox"] {
        background-color: #1a1c23 !important;
    }
    div[data-baseweb="select"] svg {
        fill: white !important;
    }

    /* Modal Close Button Fix */
    div[data-testid="stDialog"] button[aria-label="Close"] {
        color: white !important;
        opacity: 1 !important;
        background-color: rgba(255,255,255,0.1) !important;
        border-radius: 50%;
        transition: all 0.2s;
    }
    div[data-testid="stDialog"] button[aria-label="Close"]:hover {
        background-color: rgba(255, 62, 62, 0.8) !important;
        transform: scale(1.1);
    }
    div[data-testid="stDialog"] button[aria-label="Close"] svg {
        fill: white !important;
        stroke: white !important;
    }

    .glass-nav {
        position: sticky;
        top: 0;
        z-index: 999999;
        background: rgba(11, 14, 20, 0.95);
        backdrop-filter: blur(20px);
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        padding: 5px 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        height: 50px;
    }

    .glass-card {
        background: rgba(23, 27, 33, 0.7);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.4);
        margin-bottom: 20px;
    }
    
    .text-glow-green { color: #00ff88 !important; text-shadow: 0 0 10px rgba(0, 255, 136, 0.3) !important; }
    .text-glow-red { color: #ff3e3e !important; text-shadow: 0 0 10px rgba(255, 62, 62, 0.3) !important; }
    .text-glow-cyan { color: #00f2ff !important; text-shadow: 0 0 10px rgba(0, 242, 255, 0.3) !important; }
    
    .metric-label { color: rgba(255,255,255,0.4); font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; }
    .metric-value { color: white; font-size: 1.4rem; font-weight: 700; margin-top: 5px; }

    /* Active Tab Button Styling (Primary) */
    div.stButton > button[kind="primary"] {
        background-color: transparent !important;
        color: #00f2ff !important;
        border: none !important;
        border-bottom: 2px solid #00f2ff !important;
        border-radius: 0 !important;
        font-weight: 700 !important;
        box-shadow: none !important;
    }
    div.stButton > button[kind="secondary"] {
        background-color: transparent !important;
        border: none !important;
        color: rgba(255,255,255,0.6) !important;
        box-shadow: none !important;
    }
    div.stButton > button:focus {
        color:white !important;
        border-color: transparent !important;
        box-shadow: none !important;
    }

    .ticker-bar {
        background: rgba(255, 255, 255, 0.02);
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        padding: 8px 0;
        overflow: hidden;
        white-space: nowrap;
        width: 100%;
    }
    .ticker-wrapper {
        display: inline-block;
        animation: ticker 60s linear infinite;
    }
    @keyframes ticker {
        0% { transform: translateX(0); }
        100% { transform: translateX(-50%); }
    }
    .ticker-item {
        display: inline-block;
        margin-right: 40px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    
    .nav-tab {
        color: rgba(255, 255, 255, 0.4);
        font-weight: 600;
        font-size: 0.85rem;
        padding: 5px 0;
        cursor: pointer;
        transition: all 0.3s;
        border-bottom: 2px solid transparent;
    }
    .nav-tab.active {
        color: #00f2ff;
        border-bottom: 2px solid #00f2ff;
    }
    .nav-tab:hover {
        color: white;
    }

    .flex { display: flex; }
    .gap-6 { gap: 1.5rem; }
    .mb-8 { margin-bottom: 2rem; }
    
    .metric-card {
        padding: 20px;
        flex: 1;
        text-align: center;
        min-width: 150px;
    }

    .modern-table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 10px;
    }
    .modern-table th {
        text-align: left;
        color: rgba(255, 255, 255, 0.4);
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1px;
        padding: 12px 15px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    }
    .modern-table td {
        padding: 15px;
        font-size: 0.85rem;
        color: rgba(255, 255, 255, 0.8);
        border-bottom: 1px solid rgba(255, 255, 255, 0.03);
    }
    .modern-table tr:hover {
        background: rgba(255, 255, 255, 0.02);
    }

    div.stButton > button, div.stButton > button p, div.stButton > button span {
        white-space: nowrap !important;
        font-size: 0.78rem !important;
    }
    div.stButton > button {
        background: rgba(255, 255, 255, 0.03) !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-radius: 8px !important;
        color: rgba(255, 255, 255, 0.7) !important;
        font-weight: 600 !important;
        padding: 0px 15px !important;
        min-height: 38px !important;
        height: 38px !important;
        width: auto !important;
    }
    div.stButton > button:hover {
        background: rgba(0, 242, 255, 0.1) !important;
        border-color: #00f2ff !important;
    }
    
    /* Segmented Control Dark Theme */
    div[data-baseweb="segmented-control"] {
        background: rgba(23, 27, 33, 0.9) !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        border-radius: 8px !important;
    }
    div[data-baseweb="segmented-control"] button {
        background: transparent !important;
        color: rgba(255, 255, 255, 0.5) !important;
        font-weight: 600 !important;
        font-size: 0.8rem !important;
    }
    div[data-baseweb="segmented-control"] button[aria-checked="true"] {
        background: rgba(0, 242, 255, 0.25) !important;
        color: #00f2ff !important;
    }
    div[data-baseweb="segmented-control"] button:hover {
        color: white !important;
    }
    
    /* ULTIMATE INPUT UNIFICATION */
    /* Target every possible text container in these widgets */
    div[data-testid="stTextInput"] input,
    div[data-testid="stNumberInput"] input,
    div[data-baseweb="select"] [data-testid="stMarkdownContainer"] p,
    div[data-baseweb="select"] div[aria-selected="true"],
    div[data-baseweb="select"] span,
    div[data-baseweb="input"] input {
        font-size: 0.9rem !important;
        font-weight: 600 !important; /* Semi-Bold for all */
        font-family: 'Outfit', sans-serif !important;
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
        line-height: 45px !important;
        padding-top: 0 !important;
        padding-bottom: 0 !important;
    }

    /* Container Box Consistency - Flexible height for multiselect */
    div[data-baseweb="select"] > div,
    div[data-baseweb="input"],
    div[data-baseweb="base-input"],
    div[data-testid="stTextInput"] > div > div,
    div[data-testid="stNumberInput"] > div > div {
        background-color: #1a1c23 !important; 
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        border-radius: 8px !important;
        min-height: 45px !important; /* Allowed to grow */
        height: auto !important;
    }

    /* Target the text/input elements inside - remove forced line-height that prevents wrapping */
    div[data-testid="stTextInput"] input,
    div[data-testid="stNumberInput"] input,
    div[data-baseweb="select"] [data-testid="stMarkdownContainer"] p,
    div[data-baseweb="select"] div[aria-selected="true"],
    div[data-baseweb="select"] span {
        font-size: 0.9rem !important;
        font-weight: 600 !important;
        font-family: 'Outfit', sans-serif !important;
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
        padding-top: 5px !important; /* Balanced padding for multi-line */
        padding-bottom: 5px !important;
    }

    /* Placeholder Unification */
    ::placeholder,
    div[data-baseweb="select"] [data-baseweb="select"] div[aria-hidden="true"] {
        color: rgba(255, 255, 255, 0.4) !important;
        -webkit-text-fill-color: rgba(255, 255, 255, 0.4) !important;
        font-weight: 600 !important;
    }
    
    /* Remove borders and paddings from inner inputs */
    div[data-testid="stTextInput"] input,
    div[data-testid="stNumberInput"] input {
        border: none !important;
        background: transparent !important;
        padding-left: 12px !important;
        outline: none !important;
    }

    div[data-testid="stTextInput"] label,
    div[data-testid="stNumberInput"] label {
        color: rgba(255, 255, 255, 0.5) !important;
        font-size: 0.8rem !important;
        font-weight: 500 !important;
        margin-bottom: 4px !important;
    }

    /* Hide number input spinners and step buttons */
    div[data-testid="stNumberInput"] button {
        display: none !important;
    }

    /* DIALOG & MODAL UNIFICATION (v4) */
    div[data-testid="stDialog"] > div:first-child, div[role="dialog"] {
        background-color: #0b0e14 !important;
        border: 1px solid rgba(0, 242, 255, 0.1) !important;
        box-shadow: 0 0 50px rgba(0, 0, 0, 0.8) !important;
    }
    
    div[data-testid="stDialog"] h1, 
    div[data-testid="stDialog"] h2, 
    div[data-testid="stDialog"] h3, 
    div[data-testid="stDialog"] p, 
    div[data-testid="stDialog"] label, 
    div[data-testid="stDialog"] span {
        color: #FFFFFF !important;
    }

    /* MULTISELECT PILLS (TAGS) UNIFICATION */
    div[data-baseweb="tag"] {
        background-color: rgba(0, 242, 255, 0.15) !important;
        border: 1px solid rgba(0, 242, 255, 0.3) !important;
        border-radius: 4px !important;
    }
    div[data-baseweb="tag"] span {
        color: #00f2ff !important;
        font-weight: 600 !important;
    }
    div[data-baseweb="tag"] svg {
        fill: #00f2ff !important;
    }
    
    /* FORM & TAB UNIFICATION IN DIALOGS */
    div[data-testid="stDialog"] .stTabs [data-baseweb="tab-list"] { background-color: transparent !important; }
    div[data-testid="stDialog"] .stTabs [data-baseweb="tab"] { color: rgba(255,255,255,0.4) !important; }
    div[data-testid="stDialog"] .stTabs [aria-selected="true"] { color: #00f2ff !important; border-bottom-color: #00f2ff !important; }
    
    div[data-testid="stForm"] {
        background-color: rgba(255,255,255,0.02) !important;
        border: 1px solid rgba(255,255,255,0.05) !important;
        border-radius: 12px !important;
    }
</style>

""", unsafe_allow_html=True)

# 1. INITIAL SESSION STATE & DATA LOAD (TOP PRIORITY FOR SPEED)
if "show_asset_modal" not in st.session_state: st.session_state.show_asset_modal = False
if "show_portfolio_modal" not in st.session_state: st.session_state.show_portfolio_modal = False
if "active_tab" not in st.session_state: st.session_state.active_tab = "PORTFÖYÜM"

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

with st.spinner("🚀 Portföy yükleniyor..."):
    # Add actual tickers for aliases like ALTIN/GÜMÜŞ to pre-fetch their dependencies
    extra_tickers = [{"symbol": "GC=F", "type": "ticker"}, {"symbol": "SI=F", "type": "ticker"}]
    fetch_list = all_holdings + [{"symbol": s[1], "type": "ticker"} for s in ticker_symbols] + extra_tickers
    fetch_list += [{"symbol": "USDTRY=X", "type": "döviz"}, {"symbol": "ALTIN", "type": "emtia"}, {"symbol": "GÜMÜŞ", "type": "emtia"}]
    fetch_all_prices_parallel(fetch_list)

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
    tab_cols = st.columns([1, 1, 1, 1], gap="small")
    tabs = ["PORTFÖYÜM", "STRATEJİLERİM"]
    # Safe Tab Switching Callback
    def change_tab(t):
        st.session_state.active_tab = t
        st.session_state.show_asset_modal = False
        st.session_state.show_portfolio_modal = False

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
    with btn_cols[1]:
        if st.button("📁 PORTFÖY YÖNET", use_container_width=True):
            st.session_state.show_portfolio_modal = True
            st.session_state.show_asset_modal = False
    with btn_cols[2]:
        if st.button("🚪 ÇIKIŞ", use_container_width=True):
            logout()
            st.rerun()
    
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

# 4. TAB CONTROLLER
if st.session_state.active_tab == "PORTFÖYÜM":
    agg_holdings = [h for h in all_holdings if h["p"] in st.session_state.selected_p] if all_holdings else []

    categories = [
        {"name": "BIST Hisse", "val": 0, "val_tl": 0, "change": 0, "daily": 0, "currency": "TL", "icon": "fa-chart-line", "emoji": "🔴", "cost": 0, "prev": 0},
        {"name": "ABD Hisse/ETF", "val": 0, "val_tl": 0, "change": 0, "daily": 0, "currency": "USD", "icon": "fa-globe-americas", "emoji": "🔵", "cost": 0, "prev": 0},
        {"name": "TEFAS Fon", "val": 0, "val_tl": 0, "change": 0, "daily": 0, "currency": "TL", "icon": "fa-vault", "emoji": "🏦", "cost": 0, "prev": 0},
        {"name": "Kripto", "val": 0, "val_tl": 0, "change": 0, "daily": 0, "currency": "USD", "icon": "fa-bitcoin", "emoji": "🪙", "cost": 0, "prev": 0},
        {"name": "Döviz", "val": 0, "val_tl": 0, "change": 0, "daily": 0, "currency": "TL", "icon": "fa-coins", "emoji": "💵", "cost": 0, "prev": 0},
        {"name": "Emtia", "val": 0, "val_tl": 0, "change": 0, "daily": 0, "currency": "TL", "icon": "fa-gem", "emoji": "👑", "cost": 0, "prev": 0},
        {"name": "Eurobond", "val": 0, "val_tl": 0, "change": 0, "daily": 0, "currency": "TL", "icon": "fa-file-invoice-dollar", "emoji": "📉", "cost": 0, "prev": 0},
        {"name": "BES/OKS", "val": 0, "val_tl": 0, "change": 0, "daily": 0, "currency": "TL", "icon": "fa-piggy-bank", "emoji": "🐖", "cost": 0, "prev": 0}
    ]

    total_val_tl = 0; total_prev = 0; total_cost = 0; detailed_list = []
    p_metrics = {p: {"val": 0, "prev": 0, "cost": 0} for p in all_portfolios}

    usd_data = get_current_data("USDTRY=X", "döviz")
    usd_rate = usd_data["price"] if usd_data else 34.0

    gold_data = get_current_data("ALTIN", "emtia")
    gold_gram_price = gold_data["price"] if gold_data else 3000.0

    for h in agg_holdings:
        d = get_current_data(h["symbol"], h.get("type"))
        t = h.get("type", "").lower()
        cat_idx = 0; currency = "TL"
        if "abd" in t: cat_idx = 1; currency = "USD"
        elif "tefas" in t or "fon" in t: cat_idx = 2
        elif "kripto" in t: cat_idx = 3; currency = "USD"
        elif "döviz" in t: cat_idx = 4
        elif "emtia" in t: 
            cat_idx = 5
            s_up = h["symbol"].upper()
            gold_tl_symbols = ["ALTIN", "GÜMÜŞ", "GUMUS", "ÇEYREK", "YARIM", "TAM", "ATA"]
            is_gold_tl = any(sym in s_up for sym in gold_tl_symbols)
            currency = "TL" if is_gold_tl else "USD"
        elif "eurobond" in t: cat_idx = 6
        elif "bes" in t or "oks" in t: cat_idx = 7
        
        if d:
            p_val_orig = d["price"]*h["amount"]
            prev_val_orig = d["prev_close"]*h["amount"]
            cost_val_orig = h["cost"]*h["amount"]
            rate = usd_rate if currency == "USD" else 1.0
            v = p_val_orig * rate
            h["val_tl"] = v  # Store for Risk Analysis and other modules
            
            total_val_tl += v; total_prev += prev_val_orig * rate; total_cost += cost_val_orig * rate
            if h["p"] in p_metrics:
                p_metrics[h["p"]]["val"] += v
                p_metrics[h["p"]]["prev"] += prev_val_orig * rate
                p_metrics[h["p"]]["cost"] += cost_val_orig * rate
                
            # Category Accumulation
            if categories[cat_idx]["currency"] == "USD":
                categories[cat_idx]["val"] += p_val_orig
                categories[cat_idx]["cost"] += cost_val_orig
                categories[cat_idx]["prev"] += prev_val_orig
            else:
                categories[cat_idx]["val"] += v
                categories[cat_idx]["cost"] += cost_val_orig * rate
                categories[cat_idx]["prev"] += prev_val_orig * rate
                
            categories[cat_idx]["val_tl"] += v
                
            detailed_list.append({
                "Emoji": categories[cat_idx]["emoji"], "Varlık": h["symbol"], "Portföy": h["p"],
                "Adet": h["amount"], "Maliyet": h["cost"], "T_Maliyet": cost_val_orig,
                "Güncel": d["price"], "Deger": p_val_orig, "Deger_TL": v, 
                "Gunluk_KZ": p_val_orig - prev_val_orig,
                "Toplam_KZ": p_val_orig - cost_val_orig,
                "Gunluk_KZ_TL": (p_val_orig - prev_val_orig) * rate,
                "Toplam_KZ_TL": (p_val_orig - cost_val_orig) * rate,
                "Günlük (%)": (d["price"]/d["prev_close"]-1)*100,
                "Toplam (%)": (d["price"]/h["cost"]-1)*100, "Para": currency
            })

        else:
            cv_orig = h["cost"]*h["amount"]
            rate = usd_rate if currency == "USD" else 1.0
            cv = cv_orig * rate
            total_val_tl += cv; total_prev += cv; total_cost += cv
            if h["p"] in p_metrics:
                p_metrics[h["p"]]["val"] += cv; p_metrics[h["p"]]["prev"] += cv; p_metrics[h["p"]]["cost"] += cv
                
            # Category Accumulation
            if categories[cat_idx]["currency"] == "USD":
                categories[cat_idx]["val"] += cv_orig
                categories[cat_idx]["cost"] += cv_orig
                categories[cat_idx]["prev"] += cv_orig
            else:
                categories[cat_idx]["val"] += cv
                categories[cat_idx]["cost"] += cv
                categories[cat_idx]["prev"] += cv
                
            categories[cat_idx]["val_tl"] += cv
                
            detailed_list.append({
                "Emoji": "⚠️", "Varlık": f"{h['symbol']} (Veri Yok)", "Portföy": h["p"],
                "Adet": h["amount"], "Maliyet": h["cost"], "T_Maliyet": cv_orig,
                "Güncel": h["cost"], "Deger": cv_orig, "Deger_TL": cv, "Gunluk_KZ": 0, "Toplam_KZ": 0,
                "Gunluk_KZ_TL": 0, "Toplam_KZ_TL": 0,
                "Günlük (%)": 0, "Toplam (%)": 0, "Para": currency
            })


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


    cols = st.columns([1, 2], gap="medium")

    with cols[0]:
        # --- RISK ANALYSIS MODULE (MOVED TO TOP) ---
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

        # --- AI INSIGHT CARD (AKILLI ASİSTAN) ---
        insight_text = ""
        insight_color = "#ffffff"
        insight_icon = "🤖"
        
        if daily_kz_amount > 0:
            if total_val_tl > 0 and daily_kz_amount > total_val_tl * 0.015: 
                insight_text = "Harika bir gün! Portföyünüz piyasadan hızlı yükseliyor. Trend takibi stratejilerini gözden geçirebilirsin."
                insight_icon = "🚀"
                insight_color = "#00ff88"
            else:
                insight_text = "Yeşil bir gün. Portföyünüz istikrarlı büyüyor. Nakit akışını yönetmeyi unutma."
                insight_icon = "📈"
                insight_color = "#00f2ff"
        else:
            if total_val_tl > 0 and daily_kz_amount < total_val_tl * -0.015: 
                insight_text = "Sakin ol. Piyasalar dalgalıdır. Bu düşüş, sağlam varlıklarda bir alım fırsatı olabilir."
                insight_icon = "🛡️"
                insight_color = "#ff3e3e"
            else:
                insight_text = "Ufak bir geri çekilme. Uzun vadeli hedeflerine odaklan. Panik satışına gerek yok."
                insight_icon = "👀"
                insight_color = "#ffcc00"
        
        # Add Top Gainer & Loser Context
        if detailed_list:
            sorted_list = sorted(detailed_list, key=lambda x: x.get("Günlük (%)", 0))
            top_loser = sorted_list[0] if sorted_list[0].get("Günlük (%)", 0) < 0 else None
            top_gainer = sorted_list[-1] if sorted_list[-1].get("Günlük (%)", 0) > 0 else None
            
            summary_html = ""
            if top_gainer:
                sym = top_gainer['Varlık'].split('(')[0].strip()
                summary_html += f"<div style='margin-top:4px;'><span style='color:#00ff88; font-weight:700;'>🚀 {sym}: +%{top_gainer['Günlük (%)']:.2f}</span></div>"
            
            if top_loser:
                sym_l = top_loser['Varlık'].split('(')[0].strip()
                summary_html += f"<div><span style='color:#ff3e3e; font-weight:700;'>🔻 {sym_l}: %{top_loser['Günlük (%)']:.2f}</span></div>"
                
            if summary_html:
                insight_text += f"<div style='font-size:0.75rem; margin-top:5px; border-top:1px solid rgba(255,255,255,0.1); padding-top:5px;'>{summary_html}</div>"

        st.markdown(f"""
        <div class="glass-card" style="padding:15px; display:flex; gap:15px; align-items:center; border:1px solid {insight_color}40; background: linear-gradient(90deg, {insight_color}10 0%, rgba(0,0,0,0) 100%); margin-bottom:15px;">
            <div style="font-size:2rem; filter: drop-shadow(0 0 10px {insight_color});">{insight_icon}</div>
            <div>
                <div style="font-size:0.7rem; color:{insight_color}; font-weight:700; text-transform:uppercase; margin-bottom:4px; letter-spacing:1px;">GÜNLÜK İÇGÖRÜ</div>
                <div style="font-size:0.85rem; color:rgba(255,255,255,0.9); line-height:1.4; font-weight:500;">{insight_text}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
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
        else:
            st.markdown('<div class="glass-card p-6" style="text-align:center; color:rgba(255,255,255,0.4); padding:40px;">Portföyde varlık bulunmuyor</div>', unsafe_allow_html=True)

        # PROFESSIONAL METRICS PANEL
        
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
            f'<div style="display:flex; gap:15px; margin-bottom:25px; width:100%;">'
            
            # CARD 1: TOPLAM VARLIK
            f'<div style="flex:1; background:linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.02) 100%); border:1px solid rgba(255,255,255,0.1); border-radius:16px; padding:20px; position:relative; overflow:hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.2);">'
                f'<div style="position:absolute; top:-10px; right:-5px; font-size:6rem; opacity:0.05; transform:rotate(10deg);">💼</div>'
                f'<div style="color:rgba(255,255,255,0.5); font-size:0.75rem; font-weight:700; text-transform:uppercase; letter-spacing:1px; margin-bottom:8px;">TOPLAM VARLIK</div>'
                f'<div style="color:white; font-size:1.8rem; font-weight:800; letter-spacing:-0.5px; text-shadow: 0 2px 10px rgba(255,255,255,0.1);">{tv_tl_str}</div>'
                f'<div style="display:flex; gap:10px; margin-top:8px; font-size:0.75rem; color:rgba(255,255,255,0.4); font-weight:500;">'
                    f'<span>{tv_usd_str}</span><span style="opacity:0.3;">|</span><span>{tv_gold_str}</span>'
                f'</div>'
            f'</div>'
            
            # CARD 2: GÜNLÜK DEĞİŞİM
            f'<div style="flex:1; background:linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.02) 100%); border:1px solid rgba(255,255,255,0.1); border-bottom:3px solid {d_color_main}; border-radius:16px; padding:20px; position:relative; overflow:hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.2);">'
                f'<div style="position:absolute; top:-10px; right:-5px; font-size:6rem; opacity:0.05; transform:rotate(10deg);">📈</div>'
                f'<div style="color:rgba(255,255,255,0.5); font-size:0.75rem; font-weight:700; text-transform:uppercase; letter-spacing:1px; margin-bottom:8px;">GÜNLÜK DEĞİŞİM</div>'
                f'<div style="color:{d_color_main}; font-size:1.8rem; font-weight:800; letter-spacing:-0.5px; text-shadow: 0 0 25px {d_color_main}30;">{dkz_str}</div>'
                f'<div style="margin-top:8px;">'
                    f'<span style="background:{d_color_main}15; color:{d_color_main}; padding:4px 10px; border-radius:8px; font-size:0.8rem; font-weight:700; border:1px solid {d_color_main}30;">{avg_d_str}</span>'
                f'</div>'
            f'</div>'
            
            # CARD 3: TOPLAM KAR/ZARAR
            f'<div style="flex:1; background:linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.02) 100%); border:1px solid rgba(255,255,255,0.1); border-bottom:3px solid {t_color_main}; border-radius:16px; padding:20px; position:relative; overflow:hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.2);">'
                f'<div style="position:absolute; top:-10px; right:-5px; font-size:6rem; opacity:0.05; transform:rotate(10deg);">💰</div>'
                f'<div style="color:rgba(255,255,255,0.5); font-size:0.75rem; font-weight:700; text-transform:uppercase; letter-spacing:1px; margin-bottom:8px;">TOPLAM K/Z</div>'
                f'<div style="color:{t_color_main}; font-size:1.8rem; font-weight:800; letter-spacing:-0.5px; text-shadow: 0 0 25px {t_color_main}30;">{tkz_str}</div>'
                f'<div style="margin-top:8px;">'
                    f'<span style="background:{t_color_main}15; color:{t_color_main}; padding:4px 10px; border-radius:8px; font-size:0.8rem; font-weight:700; border:1px solid {t_color_main}30;">{avg_t_str}</span>'
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
                        t = h.get("type", "").lower()
                        currency = "USD" if ("abd" in t or "kripto" in t or ("emtia" in t and h["symbol"].upper() not in ["ALTIN", "GÜMÜŞ"])) else "TL"
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
                        if is_included:
                            pl = [h for h in detailed_list if h["Portföy"] == p_name]
                        else:
                            # Build detailed list for excluded portfolio
                            pl = []
                            excluded_holdings = [h for h in all_holdings if h["p"] == p_name]
                            for h in excluded_holdings:
                                d = get_current_data(h["symbol"], h.get("type"))
                                if d:
                                    t = h.get("type", "").lower()
                                    currency = "USD" if ("abd" in t or "kripto" in t or ("emtia" in t and h["symbol"].upper() not in ["ALTIN", "GÜMÜŞ"])) else "TL"
                                    cat_emoji = "🔴" if "bist" in t else ("🔵" if "abd" in t else ("🏦" if "tefas" in t or "fon" in t else ("🪙" if "kripto" in t else ("💵" if "döviz" in t else ("👑" if "emtia" in t else ("📉" if "eurobond" in t else ("🐖" if "bes" in t or "oks" in t else "💰")))))))
                                    pl.append({
                                        "Emoji": cat_emoji, "Varlık": h["symbol"], "Portföy": p_name,
                                        "Adet": h["amount"], "Maliyet": h["cost"], "T_Maliyet": h["cost"]*h["amount"],
                                        "Güncel": d["price"], "Deger": d["price"]*h["amount"], 
                                        "Gunluk_KZ": (d["price"] - d["prev_close"])*h["amount"],
                                        "Toplam_KZ": (d["price"] - h["cost"])*h["amount"], 
                                        "Günlük (%)": (d["price"]/d["prev_close"]-1)*100,
                                        "Toplam (%)": (d["price"]/h["cost"]-1)*100, "Para": currency
                                    })
                        portfolio_details_dialog(p_name, pl)

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
                    st.markdown(f'<div style="line-height:40px; font-size:0.85rem;" class="{d_cls}">{d_val}</div>', unsafe_allow_html=True)
                with c_cols[4]:
                    st.markdown(f'<div style="line-height:40px; font-size:0.85rem;" class="{t_cls}">{t_val}</div>', unsafe_allow_html=True)
                with c_cols[5]:
                    if st.button("👁️", key=f"vc_{c['name']}"):
                        # Filter detailed_list by category name logic
                        cat_assets = [h for h in detailed_list if c["emoji"] in h.get("Emoji", "")]
                        if not cat_assets:
                            cat_assets = [h for h in detailed_list if h.get("Emoji") == c["emoji"]]
                        portfolio_details_dialog(f"{c['emoji']} {c['name']} Varlıkları", cat_assets)
                        
        st.markdown('</div>', unsafe_allow_html=True)

        # ALL ASSETS
        if "asset_sort_by" not in st.session_state:
            st.session_state.asset_sort_by = "Değer"
        
        # Header and Sort Controls in a single line
        header_cols = st.columns([1, 1])
        with header_cols[0]:
            st.markdown('<div style="margin-top:10px; margin-bottom:15px; display:flex; align-items:center; gap:10px;"><i class="fas fa-list-ul" style="color:#00f2ff;"></i><span style="color:white; font-weight:600; font-size:1rem;">Tüm Varlıklarım</span></div>', unsafe_allow_html=True)
        
        with header_cols[1]:
            sort_options = {"Değer": "Deger_TL", "Günlük %": "Günlük (%)", "Toplam %": "Toplam (%)"}
            def on_sort_change():
                st.session_state.asset_sort_by = st.session_state.asset_sort_radio
            st.radio("Sırala", options=list(sort_options.keys()), key="asset_sort_radio", index=list(sort_options.keys()).index(st.session_state.asset_sort_by), horizontal=True, label_visibility="collapsed", on_change=on_sort_change)

        sort_key = sort_options.get(st.session_state.asset_sort_by, "Deger")
        dr = ""
        sorted_detailed_list = sorted(detailed_list, key=lambda x: x.get(sort_key, 0), reverse=True)
        for h in sorted_detailed_list:
            curr = h.get("Para", "TL")
            g_kz = h.get("Gunluk_KZ", 0)
            t_kz = h.get("Toplam_KZ", 0)
            g_cls = "text-glow-green" if g_kz > 0 else ("text-glow-red" if g_kz < 0 else "")
            t_cls = "text-glow-green" if t_kz > 0 else ("text-glow-red" if t_kz < 0 else "")
            val_style = "font-weight:600;" if sort_key == "Deger_TL" else ""
            g_row_cls = "background: rgba(0, 242, 255, 0.03);" if sort_key == "Günlük (%)" else ""
            t_row_cls = "background: rgba(0, 242, 255, 0.03);" if sort_key == "Toplam (%)" else ""
            
            # Pre-format values to avoid f-string syntax errors
            maliyet_str = f"{h['Maliyet']:,.2f}"
            tmaliyet_str = f"{h['T_Maliyet']:,.2f}"
            guncel_str = f"{h['Güncel']:,.2f}"
            deger_str = f"{h['Deger']:,.2f}"
            gunluk_yuzde_str = f"%{h['Günlük (%)']:.2f}"
            toplam_yuzde_str = f"%{h['Toplam (%)']:.2f}"
            g_kz_str = f"({g_kz:,.0f})"
            t_kz_str = f"({t_kz:,.0f})"

            dr += f'''<tr style="border-bottom: 1px solid rgba(255,255,255,0.03);">
                <td style="color:white !important; font-weight:500; padding:12px 15px;">{h['Emoji']} {h['Varlık']}<br><span style="font-size:0.7rem; color:#00f2ff;">{h['Portföy']}</span></td>
                <td style="color:white !important; padding:12px 15px;">{maliyet_str} {curr}</td>
                <td style="color:white !important; padding:12px 15px;">{tmaliyet_str} {curr}</td>
                <td style="color:white !important; padding:12px 15px;">{guncel_str} {curr}</td>
                <td style="color:white !important; {val_style} padding:12px 15px;">{deger_str} {curr}</td>
                <td class="{g_cls}" style="{g_row_cls} padding:12px 15px;">{gunluk_yuzde_str}<br><span style="font-size:0.7rem;">{g_kz_str}</span></td>
                <td class="{t_cls}" style="{t_row_cls} padding:12px 15px;">{toplam_yuzde_str}<br><span style="font-size:0.7rem;">{t_kz_str}</span></td>
            </tr>'''
        
        if dr:
            table_html = f'''
            <div class="glass-card" style="padding: 10px; overflow-x: auto;">
                <table class="modern-table" style="width:100%; border-collapse: collapse;">
                    <thead>
                        <tr>
                            <th style="color:rgba(255,255,255,0.4); text-align:left; padding:12px 15px; font-size:0.7rem;">VARLIK</th>
                            <th style="color:rgba(255,255,255,0.4); text-align:left; padding:12px 15px; font-size:0.7rem;">MALİYET</th>
                            <th style="color:rgba(255,255,255,0.4); text-align:left; padding:12px 15px; font-size:0.7rem;">TOPLAM ALIŞ</th>
                            <th style="color:rgba(255,255,255,0.4); text-align:left; padding:12px 15px; font-size:0.7rem;">GÜNCEL</th>
                            <th style="color:rgba(255,255,255,0.4); text-align:left; padding:12px 15px; font-size:0.7rem;">TOPLAM DEĞER</th>
                            <th style="color:rgba(255,255,255,0.4); text-align:left; padding:12px 15px; font-size:0.7rem; {'border-left:1px solid rgba(0,242,255,0.2);' if sort_key == 'Günlük (%)' else ''}">GÜNLÜK K/Z</th>
                            <th style="color:rgba(255,255,255,0.4); text-align:left; padding:12px 15px; font-size:0.7rem; {'border-left:1px solid rgba(0,242,255,0.2);' if sort_key == 'Toplam (%)' else ''}">TOPLAM K/Z</th>
                        </tr>
                    </thead>
                    <tbody>{dr}</tbody>
                </table>
            </div>
            '''
            st.markdown(table_html, unsafe_allow_html=True)



elif st.session_state.active_tab == "STRATEJİLERİM":
    st.markdown("""
        <style>
            .alert-card {
                background: rgba(23, 27, 33, 0.6);
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 16px;
                padding: 15px 20px;
                margin-bottom: 12px;
                transition: transform 0.2s, border-color 0.2s;
            }
            .alert-card:hover {
                border-color: rgba(0, 242, 255, 0.3);
                transform: translateY(-2px);
            }
            .alert-triggered {
                border-left: 4px solid #ff3e3e !important;
                background: linear-gradient(90deg, rgba(255, 62, 62, 0.05) 0%, rgba(23, 27, 33, 0.6) 100%);
            }
            .alert-active-alim {
                border-left: 4px solid #00ff88 !important;
            }
            .alert-active-satis {
                border-left: 4px solid #ffcc00 !important;
            }
            .progress-bg {
                height: 4px;
                width: 100%;
                background: rgba(255, 255, 255, 0.05);
                border-radius: 2px;
                margin-top: 10px;
                overflow: hidden;
            }
            .progress-fill {
                height: 100%;
                background: #00f2ff;
                box-shadow: 0 0 10px rgba(0, 242, 255, 0.5);
            }
            .progress-fill-alim { background: #00ff88; box-shadow: 0 0 10px rgba(0, 255, 136, 0.5); }
            .progress-fill-satis { background: #ffcc00; box-shadow: 0 0 10px rgba(255, 204, 0, 0.5); }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<div style="margin-top:0px; margin-bottom:25px; display:flex; align-items:center; gap:12px;"><i class="fas fa-chess" style="color:#00f2ff; font-size:1.5rem;"></i><span style="color:white; font-weight:700; font-size:1.4rem; letter-spacing:-0.5px;">Strateji Takip Merkezi</span></div>', unsafe_allow_html=True)
    
    col_new, col_list = st.columns([1.1, 2], gap="large")
    
    with col_new:
        st.markdown('<div class="glass-card" style="padding:25px; border:1px solid rgba(0, 242, 255, 0.15);">', unsafe_allow_html=True)
        st.markdown('<p style="color:white; font-weight:700; font-size:1.1rem; margin-bottom:20px; display:flex; align-items:center; gap:8px;">🎯 Yeni Strateji Tanımla</p>', unsafe_allow_html=True)
        
        with st.form("new_strategy_form", clear_on_submit=True):
            a_action = st.radio("🎬 İşlem Tipi", ["ALIM", "SATIŞ"], horizontal=True)
            a_type = st.selectbox("📊 Varlık Tipi", ["bist hisse", "abd hisse/etf", "kripto", "döviz", "emtia", "tefas fon"])
            a_sym = st.text_input("🔤 Varlık Sembolü", placeholder="Örn: THYAO, BTC, XAU").upper().strip()
            
            a_target = st.number_input("💰 Hedef Fiyat", min_value=0.0, value=None, placeholder="0.00", step=0.0001, format="%.4f")
            
            st.markdown('<div style="margin-top:15px;"></div>', unsafe_allow_html=True)
            submit_a = st.form_submit_button("🚀 Stratejiyi Aktifleştir", type="primary", use_container_width=True)
            
            if submit_a:
                if a_sym and a_target is not None and a_target > 0:
                    with st.spinner("🔍 Sembol doğrulanıyor..."):
                        valid = get_current_data(a_sym, a_type)
                    if valid:
                        # Auto-determine condition based on current price vs target
                        curr_p = valid['price']
                        if a_target >= curr_p:
                            a_cond = "Fiyat Üstünde"
                        else:
                            a_cond = "Fiyat Altında"
                            
                        if add_alert(a_sym, a_target, a_cond, a_type, initial_price=curr_p, action_type=a_action):
                            st.success(f"✅ {a_sym} {a_action} stratejisi kuruldu! (Hedef: {a_target:,.2f})")
                            time.sleep(1)
                            st.rerun()
                        else: st.error("❌ Veritabanı hatası.")
                    else: st.error(f"❌ '{a_sym}' bulunamadı.")
                else: st.warning("⚠️ Lütfen tüm alanları doldurun.")

        st.markdown('</div>', unsafe_allow_html=True)

    with col_list:
        all_alerts = load_alerts()
        tab_active, tab_history = st.tabs(["📋 Aktif Stratejiler", "🕒 Tamamlananlar"])
        
        active_alerts = [a for a in all_alerts if not a.get("triggered", False)]
        history_alerts = [a for a in all_alerts if a.get("triggered", False)]
        
        with tab_active:
            if not active_alerts:
                st.markdown('<div style="padding:40px; text-align:center; color:rgba(255,255,255,0.2); border:1px dashed rgba(255,255,255,0.1); border-radius:16px;">Aktif strateji bulunmuyor.</div>', unsafe_allow_html=True)
            else:
                for al in active_alerts:
                    al_id = al.get('id', al.get('created_at'))
                    curr = get_current_data(al['symbol'], al.get('type'))
                    action = al.get("action_type", "STRATEJİ")
                    
                    # Progress calculation
                    initial = al.get('initial_price', 0)
                    target = al.get('target_price', 1)
                    current_p = curr['price'] if curr else initial
                    
                    if initial > 0 and target != initial:
                        total_dist = abs(target - initial)
                        curr_dist = abs(current_p - initial)
                        progress = min(max((curr_dist / total_dist) * 100, 0), 100)
                    else:
                        progress = 0
                    
                    curr_fmt = f"{current_p:,.4f}" if curr else "Veri Yok"
                    dist_pct = (target/current_p - 1) * 100 if current_p > 0 else 0
                    abs_dist = abs(dist_pct)
                    
                    # Logic: Bar reflects the distance (max 10%). 
                    # If target is ABOVE (> current), bar shrinks towards the RIGHT.
                    # If target is BELOW (< current), bar shrinks towards the LEFT.
                    bar_width = min(max(abs_dist * 10, 0), 100) # 1% dist = 10% bar width
                    
                    alignment = "flex-end" if dist_pct > 0 else "flex-start"
                    cls_suffix = "alim" if action == "ALIM" else "satis"
                    action_emoji = "🟢" if action == "ALIM" else "🟠"
                    
                    st.markdown(f"""
                        <div class="alert-card alert-active-{cls_suffix}">
                            <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:10px;">
                                <div>
                                    <div style="display:flex; align-items:center; gap:8px;">
                                        <span style="color:white; font-weight:700; font-size:1.1rem;">{action_emoji} {al['symbol']}</span>
                                        <span style="color:rgba(255,255,255,0.5); font-size:0.75rem; font-weight:700;">{action}</span>
                                    </div>
                                    <div style="color:white; font-size:1.1rem; font-weight:800; margin-top:5px;">
                                        {target:,.4f}
                                    </div>
                                </div>
                                <div style="text-align:right;">
                                    <div style="color:rgba(255,255,255,0.4); font-size:0.7rem; font-weight:700; text-transform:uppercase;">GÜNCEL FİYAT</div>
                                    <div style="color:#00f2ff; font-size:1.1rem; font-weight:800;">{curr_fmt}</div>
                                    <div style="color:rgba(255,255,255,0.4); font-size:0.75rem; font-weight:600;">%{abs_dist:.2f} Mesafe</div>
                                </div>
                            </div>
                            <div class="progress-bg" style="display:flex; justify-content:{alignment};">
                                <div class="progress-fill progress-fill-{cls_suffix}" style="width:{bar_width}%; border-radius:2px;"></div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

                    
                    col_del1, col_del2 = st.columns([5, 1])
                    with col_del2:
                        if st.button("🗑️ Sil", key=f"del_al_{al_id}", use_container_width=True):
                            delete_alert(al_id)
                            st.rerun()

        with tab_history:
            if not history_alerts:
                st.markdown('<div style="padding:40px; text-align:center; color:rgba(255,255,255,0.2); border:1px dashed rgba(255,255,255,0.1); border-radius:16px;">Tamamlanmış strateji yok.</div>', unsafe_allow_html=True)
            else:
                for al in sorted(history_alerts, key=lambda x: x.get('triggered_at', ''), reverse=True):
                    al_id = al.get('id', al.get('created_at'))
                    trig_at = al.get('triggered_at', '').split('T')[0] if 'T' in al.get('triggered_at', '') else 'Bilinmiyor'
                    action = al.get("action_type", "STRATEJİ")
                    
                    st.markdown(f"""
                        <div class="alert-card alert-triggered">
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <div>
                                    <div style="display:flex; align-items:center; gap:8px;">
                                        <span style="color:rgba(255,255,255,0.6); font-weight:700; font-size:1rem;">✅ {al['symbol']} {action} Hedefi</span>
                                    </div>
                                    <div style="color:rgba(255,255,255,0.4); font-size:0.8rem; margin-top:2px;">
                                        {al['target_price']:,.4f} noktasında tetiklendi.
                                    </div>
                                </div>
                                <div style="text-align:right;">
                                    <div style="color:#ff3e3e; font-size:1rem; font-weight:800;">🔔 {al.get('trigger_price',0):,.4f}</div>
                                    <div style="color:rgba(255,255,255,0.3); font-size:0.65rem; font-weight:600;">{trig_at}</div>
                                </div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    col_del1, col_del2 = st.columns([5, 1])
                    with col_del2:
                        if st.button("🗑️ Arşivi Sil", key=f"del_h_{al_id}", use_container_width=True):
                            delete_alert(al_id)
                            st.rerun()

    # Periodic Check
    if "last_alert_check" not in st.session_state: st.session_state.last_alert_check = 0
    if time.time() - st.session_state.last_alert_check > 60:
        triggered = check_alerts()
        if triggered:
            for t in triggered:
                action = t.get("action_type", "STRATEJİ")
                st.toast(f"🎯 {action} SİNYALİ: {t['symbol']} hedef fiyata ulaştı!", icon="🚀")
        st.session_state.last_alert_check = time.time()



# 6. MODALS (Stay at the bottom)
if st.session_state.show_asset_modal: asset_management_dialog()
if st.session_state.show_portfolio_modal: portfolio_management_dialog()
