from utils import (get_current_data, load_portfolio, add_asset, remove_asset, delete_asset,
                   get_history, create_portfolio, delete_portfolio, save_all_portfolios, get_all_holdings, get_portfolio_history,
                   load_selected_portfolios, save_selected_portfolios, get_portfolio_metrics, fetch_all_prices_parallel)
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# ==================== DIALOG FUNCTIONS ====================

@st.dialog("Portföy İçeriği", width="large")
def portfolio_details_dialog(p_name, p_list):
    # Ultra-explicit CSS to force white text and dark background
    st.markdown("""
        <style>
            div[data-testid="stDialog"] div, 
            div[data-testid="stDialog"] p, 
            div[data-testid="stDialog"] span { 
                color: #FFFFFF; 
            }
            div[role="dialog"] td { color: #FFFFFF; }
            div[role="dialog"] th { color: #FFFFFF; font-weight: 900; }
            div[role="dialog"] { background-color: #0b111a !important; }
            div[data-testid="stDialog"] > div:first-child { background-color: #0b111a !important; }
            .profit-text { color: #00ff88 !important; text-shadow: 0 0 10px rgba(0, 255, 136, 0.5) !important; }
            .loss-text { color: #ff3333 !important; text-shadow: 0 0 10px rgba(255, 51, 51, 0.5) !important; }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown(f"<h3 style='color:#00f2ff !important; font-size:1.3rem; font-weight:700; margin-bottom:20px;'>📂 {p_name} İçeriği</h3>", unsafe_allow_html=True)
    
    if not p_list:
        st.info("Bu portföyde henüz varlık bulunmuyor.")
        return

    rows = ""
    for h in p_list:
        curr = h.get("Para", "TL")
        t_val = h.get('Toplam (%)', 0)
        t_amt = h.get('Toplam_KZ', 0)
        
        # Determine class and sign
        if t_val > 0:
            kz_class = "profit-text"
            sign = "+"
        elif t_val < 0:
            kz_class = "loss-text"
            sign = ""
        else:
            kz_class = ""
            sign = ""
        
        rows += f"""<tr style="border-bottom: 1px solid rgba(255,255,255,0.2);">
            <td style="padding:15px; color:#FFFFFF !important; font-weight:600; font-size:0.95rem;">{h.get('Emoji', '💰')} {h.get('Varlık', '-')}</td>
            <td style="padding:15px; color:#FFFFFF !important; font-weight:500; font-size:0.95rem;">{h.get('Adet', 0):,.2f}</td>
            <td style="padding:15px; color:#FFFFFF !important; font-weight:500; font-size:0.95rem;">{h.get('Maliyet', 0):,.2f} {curr}</td>
            <td style="padding:15px; color:#FFFFFF !important; font-weight:500; font-size:0.95rem;">{h.get('Güncel', 0):,.2f} {curr}</td>
            <td style="padding:15px; color:#FFFFFF !important; font-weight:700; font-size:0.95rem;">{h.get('Deger', 0):,.2f} {curr}</td>
            <td style="padding:15px; font-weight:800; font-size:1rem;" class="{kz_class}">
                %{t_val:.1f}<br>
                <div style="font-size:0.75rem;">({sign}{t_amt:,.0f} {curr})</div>
            </td>
        </tr>"""

    st.markdown(f"""
    <div style="background-color: #0b111a; padding: 10px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.2);">
        <table style="width:100%; border-collapse:collapse; background-color: transparent;">
            <thead style="background:rgba(255,255,255,0.15);">
                <tr>
                    <th style="padding:15px; color:#FFFFFF !important; font-weight:900; font-size:0.85rem; text-transform:uppercase; letter-spacing:1px; text-align:left; border-bottom:3px solid #00f2ff;">VARLIK</th>
                    <th style="padding:15px; color:#FFFFFF !important; font-weight:900; font-size:0.85rem; text-transform:uppercase; letter-spacing:1px; text-align:left; border-bottom:3px solid #00f2ff;">ADET</th>
                    <th style="padding:15px; color:#FFFFFF !important; font-weight:900; font-size:0.85rem; text-transform:uppercase; letter-spacing:1px; text-align:left; border-bottom:3px solid #00f2ff;">MALİYET</th>
                    <th style="padding:15px; color:#FFFFFF !important; font-weight:900; font-size:0.85rem; text-transform:uppercase; letter-spacing:1px; text-align:left; border-bottom:3px solid #00f2ff;">GÜNCEL</th>
                    <th style="padding:15px; color:#FFFFFF !important; font-weight:900; font-size:0.85rem; text-transform:uppercase; letter-spacing:1px; text-align:left; border-bottom:3px solid #00f2ff;">DEĞER</th>
                    <th style="padding:15px; color:#FFFFFF !important; font-weight:900; font-size:0.85rem; text-transform:uppercase; letter-spacing:1px; text-align:left; border-bottom:3px solid #00f2ff;">K/Z %</th>
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
                border-radius: 8px !important;
            }

            /* 4. Force Input Text Color */
            div[data-testid="stDialog"] input {
                color: white !important;
                background-color: #1a1c23 !important;
                -webkit-text-fill-color: white !important;
            }

            /* 5. Selectbox items */
            div[data-baseweb="select"] > div {
                background-color: #1a1c23 !important;
                color: white !important;
                border: 1px solid rgba(255,255,255,0.2) !important;
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
            asset_symbol = st.text_input("🔤 Varlık Sembolü", key="add_symbol").upper()
        
        with col2:
            asset_amount = st.number_input("🔢 Adet", min_value=0.0, value=1.0, step=0.0001, format="%.4f", key="add_amount")
            # The widget now takes its value directly from the session_state key modified above
            asset_cost = st.number_input("💰 Birim Maliyet", min_value=0.0, step=0.0001, format="%.4f", key="add_cost_widget")
            purchase_date = st.date_input("📅 Alış Tarihi", value=datetime.now(), key="add_date")
        
        st.markdown("<div style='margin-top:25px;'></div>", unsafe_allow_html=True)
        if st.button("🚀 Varlık Ekle", type="primary", use_container_width=True):
            if asset_symbol and asset_amount > 0 and asset_cost > 0:
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
                    r_amount = st.number_input("🔢 Satılacak Adet", min_value=0.0, value=1.0, step=0.0001, format="%.4f", key="remove_amount")
                    r_price = st.number_input("💰 Satış Fiyatı", min_value=0.0, value=0.0, step=0.01, key="remove_price")
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
    # Dark theme styling
    st.markdown("""
    <style>
        [data-testid="stDialog"] {
            background-color: rgba(11, 14, 20, 0.98) !important;
        }
        [data-testid="stDialog"] > div {
            background-color: rgba(11, 14, 20, 0.98) !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
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

# PAGE CONFIG
st.set_page_config(page_title="Finansal Terminal v4", layout="wide", initial_sidebar_state="collapsed")

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

    div.stButton > button {
        background: rgba(255, 255, 255, 0.03) !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-radius: 10px !important;
        color: rgba(255, 255, 255, 0.7) !important;
        font-weight: 600 !important;
        font-size: 0.75rem !important;
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
    
    /* Selectbox Dark Theme */
    div[data-baseweb="select"] > div {
        background: rgba(23, 27, 33, 0.95) !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        border-radius: 8px !important;
    }
    div[data-baseweb="select"] > div > div {
        color: rgba(255, 255, 255, 0.8) !important;
    }
    div[data-baseweb="popover"] > div {
        background: rgba(23, 27, 33, 0.98) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
    }
    div[data-baseweb="menu"] {
        background: rgba(23, 27, 33, 0.98) !important;
    }
    div[data-baseweb="menu"] li {
        color: rgba(255, 255, 255, 0.7) !important;
    }
    div[data-baseweb="menu"] li:hover {
        background: rgba(0, 242, 255, 0.15) !important;
        color: #00f2ff !important;
    }
</style>
""", unsafe_allow_html=True)

# 1. INITIAL SESSION STATE & DATA LOAD (TOP PRIORITY FOR SPEED)
if "show_asset_modal" not in st.session_state: st.session_state.show_asset_modal = False
if "show_portfolio_modal" not in st.session_state: st.session_state.show_portfolio_modal = False

portfolio_data = load_portfolio()
all_portfolios = list(portfolio_data["portfolios"].keys())
st.session_state['all_p_list'] = all_portfolios

if "selected_p" not in st.session_state:
    saved_selected = load_selected_portfolios()
    st.session_state.selected_p = [p for p in saved_selected if p in all_portfolios] if saved_selected else all_portfolios.copy()

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
    d = get_current_data(sym, asset_type="ticker") # Consistency fix
    if d:
        change = (d["price"]/d["prev_close"]-1)*100
        cls = "text-glow-green" if change >= 0 else "text-glow-red"
        arrow = "▲" if change >= 0 else "▼"
        ticker_data_html += f'<div class="ticker-item">{label} <span class="{cls}">{d["price"]:,.2f} {arrow} %{change:.2f}</span></div>'

if not ticker_data_html:
    ticker_data_html = '<div class="ticker-item" style="color:rgba(255,255,255,0.2);">Veri akışı şu an durduruldu.</div>'



nav_cols = st.columns([1.5, 1], gap="small")
with nav_cols[0]:
    st.markdown("""
    <div style="display: flex; justify-content: flex-start; gap: 30px; align-items: center; margin-top: 10px; padding-left: 20px;">
        <span class="nav-tab active">PORTFÖYÜM</span>
        <span class="nav-tab">HABERLER</span>
        <span class="nav-tab">ALARM</span>
        <span class="nav-tab">ANALİZ</span>
    </div>
    """, unsafe_allow_html=True)

with nav_cols[1]:
    # ACTION BUTTONS
    btn_cols = st.columns([1, 1])
    with btn_cols[0]:
        if st.button("➕ VARLIK EKLE/SİL", use_container_width=True):
            st.session_state.show_asset_modal = True
            st.session_state.show_portfolio_modal = False
            # removed st.rerun() to prevent double render
    with btn_cols[1]:
        if st.button("📁 PORTFÖY YÖNET", use_container_width=True):
            st.session_state.show_portfolio_modal = True
            st.session_state.show_asset_modal = False
            # removed st.rerun() to prevent double render
    
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

# 4. AGGREGATE SUMMARY DATA
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
        currency = "TL" if h["symbol"].upper() in ["ALTIN", "GÜMÜŞ"] else "USD"
    elif "eurobond" in t: cat_idx = 6
    elif "bes" in t or "oks" in t: cat_idx = 7
    
    if d:
        p_val_orig = d["price"]*h["amount"]
        prev_val_orig = d["prev_close"]*h["amount"]
        cost_val_orig = h["cost"]*h["amount"]
        rate = usd_rate if currency == "USD" else 1.0
        v = p_val_orig * rate
        
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
            "Güncel": d["price"], "Deger": p_val_orig, "Deger_TL": v, "Gunluk_KZ": p_val_orig - prev_val_orig,
            "Toplam_KZ": p_val_orig - cost_val_orig, "Günlük (%)": (d["price"]/d["prev_close"]-1)*100,
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
cols = st.columns([1.8, 5], gap="large")

with cols[0]:
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
    
    # PORTFOLIO HISTORICAL CHART
    if "chart_period" not in st.session_state:
        st.session_state.chart_period = "1mo"
    
    # Header
    st.markdown('<div style="margin-top:20px; margin-bottom:10px; display:flex; align-items:center; gap:10px;"><i class="fas fa-chart-area" style="color:#00f2ff;"></i><span style="color:white; font-weight:600; font-size:1rem;">Portföy Performansı</span></div>', unsafe_allow_html=True)
    
    # Period selector
    period_options = {"1 Hafta": "5d", "1 Ay": "1mo", "3 Ay": "3mo", "6 Ay": "6mo", "1 Yıl": "1y"}
    period_labels = list(period_options.keys())
    
    # Find current index
    current_label = [k for k, v in period_options.items() if v == st.session_state.chart_period]
    current_idx = period_labels.index(current_label[0]) if current_label else 1
    
    def on_period_change():
        selected_label = st.session_state.period_select_chart
        st.session_state.chart_period = period_options[selected_label]
    
    st.selectbox(
        "Dönem",
        period_labels,
        index=current_idx,
        key="period_select_chart",
        label_visibility="collapsed",
        on_change=on_period_change
    )
    
    # Get portfolio history data
    if agg_holdings:
        history_df = get_portfolio_history(agg_holdings, period=st.session_state.chart_period)
        
        if not history_df.empty:
            import plotly.graph_objects as go
            st.markdown('<div class="glass-card p-6">', unsafe_allow_html=True)
            
            fig_perf = go.Figure()
            
            # 1. Total Cost Trace (Dashed Line)
            fig_perf.add_trace(go.Scatter(
                x=history_df.index, y=history_df['Total_Cost'],
                name='Toplam Maliyet',
                line=dict(color='rgba(255, 255, 255, 0.4)', width=2, dash='dash'),
                hovertemplate='%{y:,.0f} TL<extra></extra>'
            ))
            
            # 2. Market Value Trace (Filled Area)
            fig_perf.add_trace(go.Scatter(
                x=history_df.index, y=history_df['Market_Value'],
                name='Piyasa Değeri',
                fill='tonexty',
                fillcolor='rgba(0, 242, 255, 0.1)',
                line=dict(color='#00f2ff', width=3),
                hovertemplate='%{y:,.0f} TL<extra></extra>'
            ))
            
            fig_perf.update_layout(
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=0, r=0, t=10, b=0), height=350,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color="rgba(255,255,255,0.7)")),
                hovermode='x unified',
                xaxis=dict(showgrid=False, color='grey', zeroline=False),
                yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', color='grey', zeroline=False)
            )
            
            st.plotly_chart(fig_perf, use_container_width=True, config={'displayModeBar': False})
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="glass-card p-6" style="text-align:center; color:rgba(255,255,255,0.4); padding:40px;">Tarihsel veri yükleniyor...</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="glass-card p-6" style="text-align:center; color:rgba(255,255,255,0.4); padding:40px;">Portföyde varlık bulunmuyor</div>', unsafe_allow_html=True)



    # PROFESSIONAL METRICS PANEL
    st.markdown('<div style="margin-top:20px; margin-bottom:10px; display:flex; align-items:center; gap:10px;"><i class="fas fa-chart-pie" style="color:#00f2ff;"></i><span style="color:white; font-weight:600; font-size:1rem;">Profesyonel Metrikler</span></div>', unsafe_allow_html=True)
    
    # Get all metrics
    simple_ret = portfolio_metrics.get("simple_return")
    xirr_val = portfolio_metrics.get("xirr")
    inv_days = portfolio_metrics.get("investment_days")
    twr_val = portfolio_metrics.get("twr")
    bench_val = portfolio_metrics.get("benchmark_return")
    alpha_val = portfolio_metrics.get("alpha")
    
    # Format values
    simple_display = f"%{simple_ret:.1f}" if simple_ret is not None else "—"
    xirr_display = f"%{xirr_val:.1f}" if xirr_val is not None else "—"
    days_display = f"{inv_days} gün" if inv_days is not None else "—"
    twr_display = f"%{twr_val:.1f}" if twr_val is not None else "—"
    bench_display = f"%{bench_val:.1f}" if bench_val is not None else "—"
    alpha_display = f"%{alpha_val:+.1f}" if alpha_val is not None else "—"
    
    # Determine colors
    simple_cls = "text-glow-green" if simple_ret and simple_ret >= 0 else ("text-glow-red" if simple_ret and simple_ret < 0 else "")
    xirr_cls = "text-glow-green" if xirr_val and xirr_val >= 0 else ("text-glow-red" if xirr_val and xirr_val < 0 else "")
    twr_cls = "text-glow-green" if twr_val and twr_val >= 0 else ("text-glow-red" if twr_val and twr_val < 0 else "")
    bench_cls = "text-glow-green" if bench_val and bench_val >= 0 else ("text-glow-red" if bench_val and bench_val < 0 else "")
    alpha_cls = "text-glow-green" if alpha_val and alpha_val >= 0 else ("text-glow-red" if alpha_val and alpha_val < 0 else "")
    
    # Build HTML as a single line to avoid markdown indentation issues
    html_out = f'<div class="glass-card" style="padding: 15px; overflow: hidden;">'
    html_out += f'<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; width: 100%;">'
    # Row 1
    html_out += f'<div style="text-align: center; padding: 12px 5px; background: rgba(255,255,255,0.03); border-radius: 12px; border: 1px solid rgba(255,255,255,0.08); display: flex; flex-direction: column; justify-content: center; min-height: 85px;">'
    html_out += f'<div style="color: rgba(255,255,255,0.4); font-size: 0.6rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 5px;">Basit Getiri</div>'
    html_out += f'<div class="{simple_cls}" style="font-size: 1.15rem; font-weight: 800;">{simple_display}</div>'
    html_out += f'<div style="color: rgba(255,255,255,0.25); font-size: 0.55rem; margin-top: 4px;">{days_display} toplam</div></div>'
    
    xirr_box_style = "background: rgba(112, 0, 255, 0.05); border: 1px solid rgba(112, 0, 255, 0.2);"
    html_out += f'<div style="text-align: center; padding: 12px 5px; {xirr_box_style} border-radius: 12px; display: flex; flex-direction: column; justify-content: center; min-height: 85px;">'
    html_out += f'<div style="color: rgba(255,255,255,0.4); font-size: 0.6rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 5px;">XIRR (Yıllık)</div>'
    x_val_style = f"font-size: {'1.0rem' if xirr_val is None else '1.15rem'}; font-weight: 800;"
    if xirr_val is None: x_val_style += " color: rgba(255,255,255,0.6);"
    html_out += f'<div class="{xirr_cls if xirr_val is not None else ""}" style="{x_val_style}">{xirr_display if xirr_val is not None else "Bekleniyor"}</div>'
    html_out += f'<div style="color: rgba(255,255,255,0.25); font-size: 0.55rem; margin-top: 4px;">{"Yıllıklaştırılmış" if xirr_val is not None else "30 gün veri gerekli"}</div></div>'
    
    html_out += f'<div style="text-align: center; padding: 12px 5px; background: rgba(255,255,255,0.03); border-radius: 12px; border: 1px solid rgba(255,255,255,0.08); display: flex; flex-direction: column; justify-content: center; min-height: 85px;">'
    html_out += f'<div style="color: rgba(255,255,255,0.4); font-size: 0.6rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 5px;">TWR (Dönemsel)</div>'
    html_out += f'<div class="{twr_cls}" style="font-size: 1.15rem; font-weight: 800;">{twr_display}</div>'
    html_out += f'<div style="color: rgba(255,255,255,0.25); font-size: 0.55rem; margin-top: 4px;">Zaman ağırlıklı</div></div>'
    # Row 2
    html_out += f'<div style="text-align: center; padding: 12px 5px; background: rgba(255,255,255,0.03); border-radius: 12px; border: 1px solid rgba(255,255,255,0.08); display: flex; flex-direction: column; justify-content: center; min-height: 85px;">'
    html_out += f'<div style="color: rgba(255,255,255,0.4); font-size: 0.6rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 5px;">BIST100</div>'
    html_out += f'<div class="{bench_cls}" style="font-size: 1.15rem; font-weight: 800;">{bench_display}</div>'
    html_out += f'<div style="color: rgba(255,255,255,0.25); font-size: 0.55rem; margin-top: 4px;">Karşılaştırma</div></div>'
    
    alfa_msg = "🎯 Piyasayı yendin!" if alpha_val and alpha_val > 0 else ("📉 Piyasanın altında" if alpha_val and alpha_val < 0 else "BIST100 ile fark")
    html_out += f'<div style="grid-column: span 2; text-align: center; padding: 12px 15px; background: rgba(0, 242, 255, 0.05); border-radius: 12px; border: 2px solid rgba(0, 242, 255, 0.2); display: flex; flex-direction: column; justify-content: center; min-height: 85px; position: relative; overflow: hidden;">'
    html_out += f'<div style="color: rgba(255,255,255,0.5); font-size: 0.65rem; font-weight: 800; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 4px;">ALFA (α) - Piyasa Performans Farkı</div>'
    html_out += f'<div class="{alpha_cls}" style="font-size: 1.5rem; font-weight: 900; line-height: 1;">{alpha_display}</div>'
    html_out += f'<div style="color: rgba(255,255,255,0.4); font-size: 0.65rem; margin-top: 6px; font-weight: 600;">{alfa_msg}</div></div>'
    html_out += '</div></div>'
    
    st.write(html_out, unsafe_allow_html=True)



with cols[1]:
    # METRICS Row
    tv_usd = total_val_tl / usd_rate
    tv_gold = total_val_tl / gold_gram_price if gold_gram_price else 0
    st.markdown(f"""<div class="flex gap-6 mb-8">
<div class="glass-card metric-card" style="flex:1.5;"><div class="metric-label">TOPLAM VARLIK</div><div class="metric-value text-glow-cyan">{total_val_tl:,.0f} TL <span style="font-size:0.8rem; opacity:0.5;">/ {tv_usd:,.0f} $ / {tv_gold:,.1f} gr AU</span></div></div>
<div class="glass-card metric-card"><div class="metric-label">TOPLAM DEĞİŞİM</div><div class="metric-value {'text-glow-green' if avg_total>=0 else 'text-glow-red'}">%{avg_total:.2f}</div></div>
<div class="glass-card metric-card"><div class="metric-label">GÜNLÜK DEĞİŞİM</div><div class="metric-value {'text-glow-green' if avg_daily>=0 else 'text-glow-red'}">%{avg_daily:.2f}</div></div>
</div>""", unsafe_allow_html=True)

    # PORTFOLIOS
    st.markdown('<div style="margin-top:20px; margin-bottom:15px; display:flex; align-items:center; gap:10px;"><i class="fas fa-folder" style="color:#00f2ff;"></i><span style="color:white; font-weight:600; font-size:1rem;">Portföylerim</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="glass-card p-6">', unsafe_allow_html=True)
    st.markdown("""<table class="modern-table" style="margin-bottom:10px;"><thead>
        <tr><th style="width:40%;">PORTFÖY ADI</th><th style="width:30%;">TOPLAM</th><th style="width:20%;">K/Z %</th><th style="width:10%;"></th></tr>
    </thead></table>""", unsafe_allow_html=True)
    
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
        
        # Calculate portfolio value for all portfolios (including excluded ones)
        if not is_included:
            # Recalculate for excluded portfolios
            excluded_holdings = [h for h in all_holdings if h["p"] == p_name]
            exc_val = 0
            exc_cost = 0
            for h in excluded_holdings:
                d = get_current_data(h["symbol"], h.get("type"))
                if d:
                    t = h.get("type", "").lower()
                    currency = "USD" if ("abd" in t or "kripto" in t or ("emtia" in t and h["symbol"].upper() not in ["ALTIN", "GÜMÜŞ"])) else "TL"
                    rate = usd_rate if currency == "USD" else 1.0
                    exc_val += d["price"] * h["amount"] * rate
                    exc_cost += h["cost"] * h["amount"] * rate
            m = {"val": exc_val, "cost": exc_cost, "prev": exc_val}
        
        if True:  # Show all portfolios, even if value is 0
            pt = (m["val"]/m["cost"]-1)*100 if m["cost"] else 0
            
            if is_included:
                # Normal styling for included portfolios
                name_color = "white"
                val_color = "white"
                t_cls = "text-glow-green" if pt > 0 else ("text-glow-red" if pt < 0 else "")
                status_badge = ""
            else:
                # Gray styling for excluded portfolios
                name_color = "rgba(255,255,255,0.3)"
                val_color = "rgba(255,255,255,0.3)"
                t_cls = ""
                pt_style = f"color: rgba(255,255,255,0.3);"
                status_badge = '<span style="background:rgba(255,255,255,0.1); color:rgba(255,255,255,0.4); font-size:0.6rem; padding:2px 6px; border-radius:4px; margin-left:8px;">Dahil değil</span>'
            
            rc = st.columns([4, 3, 2, 1])
            with rc[0]: 
                st.markdown(f'<div style="line-height:40px; color:{name_color}; font-size:0.85rem; padding-left:15px;">📁 {p_name}{status_badge}</div>', unsafe_allow_html=True)
            with rc[1]: 
                val_display = f"{m['val']:,.0f} TL" if m["val"] > 0 else "—"
                st.markdown(f'<div style="line-height:40px; color:{val_color}; font-size:0.85rem;">{val_display}</div>', unsafe_allow_html=True)
            with rc[2]: 
                if is_included:
                    st.markdown(f'<div style="line-height:40px; font-size:0.85rem;" class="{t_cls}">%{pt:.1f}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div style="line-height:40px; font-size:0.85rem; color:rgba(255,255,255,0.3);">%{pt:.1f}</div>', unsafe_allow_html=True)
            with rc[3]: 
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
    st.markdown("""<table class="modern-table" style="margin-bottom:10px;"><thead>
        <tr><th style="width:25%;">KATEGORİ</th><th style="width:20%;">MALİYET</th><th style="width:20%;">DEĞER</th><th style="width:12%;">GÜNLÜK</th><th style="width:13%;">TOPLAM</th><th style="width:10%;"></th></tr>
    </thead></table>""", unsafe_allow_html=True)

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
                    # If emoji matching is too loose, check more carefully
                    if not cat_assets:
                        # Fallback: determine category based on asset type if needed, but detailed_list already has categories mapped
                        # Since we used the categories list to populate detailed_list, emojis should match.
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
        # Custom CSS for sorting buttons is already in the global CSS (segmented-control)
        # We'll use a standard radio but it will be styled by the existing system
        sort_options = {"Değer": "Deger_TL", "Günlük %": "Günlük (%)", "Toplam %": "Toplam (%)"}
        
        def on_sort_change():
            st.session_state.asset_sort_by = st.session_state.asset_sort_radio
            
        st.radio(
            "Sırala",
            options=list(sort_options.keys()),
            key="asset_sort_radio",
            index=list(sort_options.keys()).index(st.session_state.asset_sort_by),
            horizontal=True,
            label_visibility="collapsed",
            on_change=on_sort_change
        )

    sort_key = sort_options.get(st.session_state.asset_sort_by, "Deger")
    
    dr = ""
    # Sort assets by chosen criteria (largest first)
    sorted_detailed_list = sorted(detailed_list, key=lambda x: x.get(sort_key, 0), reverse=True)
    
    for h in sorted_detailed_list:
        curr = h.get("Para", "TL")
        g_kz = h.get("Gunluk_KZ", 0)
        t_kz = h.get("Toplam_KZ", 0)
        g_cls = "text-glow-green" if g_kz > 0 else ("text-glow-red" if g_kz < 0 else "")
        t_cls = "text-glow-green" if t_kz > 0 else ("text-glow-red" if t_kz < 0 else "")
        
        # Highlight sorting column
        val_style = "font-weight:600;" if sort_key == "Deger_TL" else ""
        g_row_cls = "background: rgba(0, 242, 255, 0.03);" if sort_key == "Günlük (%)" else ""
        t_row_cls = "background: rgba(0, 242, 255, 0.03);" if sort_key == "Toplam (%)" else ""
        
        dr += f"""<tr style="border-bottom: 1px solid rgba(255,255,255,0.03);">
            <td style="color:white !important; font-weight:500; padding:12px 15px;">{h['Emoji']} {h['Varlık']}<br><span style="font-size:0.7rem; color:#00f2ff;">{h['Portföy']}</span></td>
            <td style="color:white !important; padding:12px 15px;">{h['Maliyet']:,.2f} {curr}</td>
            <td style="color:white !important; padding:12px 15px;">{h['T_Maliyet']:,.2f} {curr}</td>
            <td style="color:white !important; padding:12px 15px;">{h['Güncel']:,.2f} {curr}</td>
            <td style="color:white !important; {val_style} padding:12px 15px;">{h['Deger']:,.2f} {curr}</td>
            <td class="{g_cls}" style="{g_row_cls} padding:12px 15px;">%{h["Günlük (%)"]:.2f}<br><span style="font-size:0.7rem;">({g_kz:,.0f})</span></td>
            <td class="{t_cls}" style="{t_row_cls} padding:12px 15px;">%{h["Toplam (%)"]:.2f}<br><span style="font-size:0.7rem;">({t_kz:,.0f})</span></td>
        </tr>"""
    
    if dr:
        st.markdown(f"""
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
        """, unsafe_allow_html=True)

if st.session_state.show_asset_modal: asset_management_dialog()
if st.session_state.show_portfolio_modal: portfolio_management_dialog()
