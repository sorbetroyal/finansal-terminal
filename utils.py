import yfinance as yf
import borsapy
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from supabase import create_client, Client
from dotenv import load_dotenv
import os
import streamlit as st
from concurrent.futures import ThreadPoolExecutor
import json

# Load environment variables
load_dotenv()

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_db():
    """Returns an authenticated Supabase client for the current session."""
    token = st.session_state.get("access_token")
    if token:
        # Inject the user's token into the postgrest client for RLS
        supabase.postgrest.auth(token)
    return supabase

# ==================== SETTINGS FUNCTIONS ====================

def get_user_setting(key, default=None):
    """Retrieve a setting value from Supabase for the current user."""
    user_id = get_user_id()
    if not user_id:
        return default
    try:
        db = get_db()
        response = db.table("user_settings").select("setting_value").eq("user_id", user_id).eq("setting_key", key).execute()
        if response.data:
            return response.data[0]["setting_value"]
    except Exception as e:
        print(f"Error getting setting {key}: {e}")
    return default

def save_user_setting(key, value):
    """Save or update a setting value in Supabase for the current user."""
    user_id = get_user_id()
    if not user_id:
        return False, "Kullanıcı oturumu bulunamadı."
    try:
        db = get_db()
        # Check if setting exists
        existing = db.table("user_settings").select("id").eq("user_id", user_id).eq("setting_key", key).execute()
        if existing.data:
            db.table("user_settings").update({"setting_value": value}).eq("id", existing.data[0]["id"]).execute()
        else:
            db.table("user_settings").insert({
                "user_id": user_id,
                "setting_key": key,
                "setting_value": value
            }).execute()
        return True, "Başarıyla kaydedildi."
    except Exception as e:
        err_msg = str(e)
        print(f"Error saving setting {key}: {err_msg}")
        return False, err_msg

def get_gemini_api_key():
    """Get the user's Gemini API key from Supabase."""
    return get_user_setting("gemini_api_key")

def save_gemini_api_key(api_key):
    """Save the user's Gemini API key to Supabase."""
    return save_user_setting("gemini_api_key", api_key)

def is_gold_tl_asset(symbol):
    """Checks if an asset symbol refers to a gold/silver commodity denominated in TL."""
    if not symbol: return False
    s_up = str(symbol).upper()
    # Support multiple variants and common spelling differences
    gold_tl_symbols = ["ALTIN", "GÜMÜŞ", "GUMUS", "ÇEYREK", "CEYREK", "YARIM", "TAM", "ATA"]
    return any(sym in s_up for sym in gold_tl_symbols)

def get_asset_details(symbol, asset_type):
    """Returns (cat_idx, currency, emoji) for a given symbol and asset type."""
    s_up = str(symbol).upper()
    t = str(asset_type).lower()
    
    # Defaults
    cat_idx = 0; currency = "TL"; emoji = "🔴" # BIST Defaults
    
    if "abd" in t:
        cat_idx = 1; currency = "USD"; emoji = "🔵"
    elif "tefas" in t or "fon" in t:
        cat_idx = 2; currency = "TL"; emoji = "🏦"
    elif "kripto" in t:
        cat_idx = 3; currency = "USD"; emoji = "🪙"
    elif "döviz" in t:
        cat_idx = 4; currency = "TL"; emoji = "💵"
    elif "emtia" in t:
        cat_idx = 5; currency = "USD"; emoji = "👑" # Commodities default to USD (Foreign stocks/options)
    elif "eurobond" in t:
        cat_idx = 6; currency = "TL"; emoji = "📉"
    elif "bes" in t or "oks" in t:
        cat_idx = 7; currency = "TL"; emoji = "🐖"
    elif "nakit" in t:
        cat_idx = 8; currency = "TL"; emoji = "💵"
    else:
        # Check if it's a BIST stock (fallback)
        if "bist" in t:
            cat_idx = 0; currency = "TL"; emoji = "🔴"
        else:
            cat_idx = 0; currency = "TL"; emoji = "💰"

    # CRITICAL OVERRIDE: Gold/Silver variants are ALWAYS TL denominated and Category 5 (Emtia)
    if is_gold_tl_asset(s_up):
        currency = "TL"
        # If it's BIST Certificate, categorize as BIST (if already BIST) or Emtia
        if "S1" in s_up or ("ALTIN" in s_up and "bist" in t):
            if "bist" in t:
                cat_idx = 0; emoji = "🔴"
            else:
                cat_idx = 5; emoji = "👑"
        else:
            cat_idx = 5; emoji = "👑"
            
    return cat_idx, currency, emoji

# ==================== MARKET DATA FUNCTIONS ====================

# Global cache for prices to speed up app
PRICE_CACHE = {}

@st.cache_data(ttl=60, show_spinner=False)
def _fetch_single_symbol(std_symbol, a_type):
    """Cached fallback for fetching single symbol data."""
    try:
        std_symbol = std_symbol.strip()
        s_upper = std_symbol.upper().replace(".IS", "")
        
        # 1. Special Handling for BIST Gold Certificate (ALTIN.S1)
        if s_upper == "ALTIN.S1" or (s_upper == "ALTIN" and "bist" in a_type.lower()):
            try:
                # BIST Gold Certificate lookup
                t = borsapy.Ticker("ALTIN")
                info = t.info
                price = info.get('last', 0)
                change = info.get('change_percent', 0)
                prev_close = price / (1 + (change / 100)) if change else price
                if price > 0:
                    return {"price": price, "prev_close": prev_close, "change_pct": change}
            except:
                pass 

        # 2. Existing Special Handling/Fetch (Funds etc)
        if any(x in a_type.lower() for x in ["tefas", "fon", "bes", "oks"]):
            try:
                # Special Case: ZPX and other BIST BYFs sometimes coded as funds
                if s_upper.startswith("ZPX") or s_upper.startswith("KPT") or s_upper.startswith("USDTR"):
                    ticker = yf.Ticker(f"{s_upper}.IS")
                    history = ticker.history(period="2d")
                    if not history.empty:
                        price = round(float(history['Close'].iloc[-1]), 4)
                        prev_close = round(float(history['Close'].iloc[-2]), 4) if len(history) > 1 else price
                        return {"price": price, "prev_close": prev_close, "change_pct": ((price/prev_close)-1)*100 if prev_close else 0}

                fund = borsapy.Fund(std_symbol)
                info = fund.info
                price = info.get('price', 0)
                daily_ret = info.get('daily_return', 0)
                prev_close = price / (1 + (daily_ret / 100)) if daily_ret else price
                
                # If borsapy fails to find price but it might be a BIST ETF
                if price <= 0:
                    ticker = yf.Ticker(f"{s_upper}.IS")
                    history = ticker.history(period="2d")
                    if not history.empty:
                        price = round(float(history['Close'].iloc[-1]), 4)
                        prev_close = round(float(history['Close'].iloc[-2]), 4) if len(history) > 1 else price
                        return {"price": price, "prev_close": prev_close, "change_pct": ((price/prev_close)-1)*100 if prev_close else 0}

                return {"price": price, "prev_close": prev_close, "change_pct": daily_ret}
            except:
                # Final fallback for BIST ETFs marked as funds
                try:
                    ticker = yf.Ticker(f"{s_upper}.IS")
                    history = ticker.history(period="2d")
                    if not history.empty:
                        price = round(float(history['Close'].iloc[-1]), 4)
                        prev_close = round(float(history['Close'].iloc[-2]), 4) if len(history) > 1 else price
                        return {"price": price, "prev_close": prev_close, "change_pct": ((price/prev_close)-1)*100 if prev_close else 0}
                except: pass
                return None
        
        # 3. Spot Gold / Silver / Gold Variants Calculation logic
        # Spot Gold (ALTIN) or Retail Gold (ÇEYREK etc.)
        gold_variants = ["ALTIN", "ÇEYREK", "YARIM", "TAM", "ATA"]
        if any(v in s_upper for v in gold_variants):
            ons = get_current_data("GC=F", "ticker")
            usd = get_current_data("USDTRY=X", "döviz")
            if ons and usd:
                # Base: 1 Gram Gold (24K)
                gram_p = (ons["price"] / 31.1035) * usd["price"]
                gram_prev = (ons["prev_close"] / 31.1035) * usd["prev_close"]
                
                # Multipliers for retail gold (24K equivalents)
                multiplier = 1.0
                if "ÇEYREK" in s_upper: multiplier = 1.6065
                elif "YARIM" in s_upper: multiplier = 3.2130
                elif "TAM" in s_upper: multiplier = 6.4260
                elif "ATA" in s_upper: multiplier = 6.6150
                
                p = gram_p * multiplier
                prev = gram_prev * multiplier
                return {"price": p, "prev_close": prev, "change_pct": ((p/prev)-1)*100 if prev else 0}
            return None

        if s_upper in ["GÜMÜŞ", "GUMUS", "GUMUS.S1"]:
            ons = get_current_data("SI=F", "ticker")
            usd = get_current_data("USDTRY=X", "döviz")
            if ons and usd:
                p = (ons["price"] / 31.1035) * usd["price"]
                prev = (ons["prev_close"] / 31.1035) * usd["prev_close"]
                
                if "S1" in s_upper:
                    p = p / 100 
                    prev = prev / 100
                return {"price": p, "prev_close": prev, "change_pct": ((p/prev)-1)*100 if prev else 0}
            return None

        t = yf.Ticker(std_symbol)
        history = t.history(period="2d")
        if not history.empty:
            price = history['Close'].iloc[-1]
            prev_close = history['Close'].iloc[-2] if len(history) > 1 else price
            return {"price": price, "prev_close": prev_close, "change_pct": ((price/prev_close)-1)*100 if prev_close else 0}
    except Exception as e:
        return None

# ==================== STRATEGY FUNCTIONS (Supertrend + KAMA) ====================

def calculate_kama(df, period=21, fast=2, slow=30):
    """Calculate Kaufman's Adaptive Moving Average with improved robustness."""
    if len(df) < period + 2:
        return pd.Series(df['Close'].values, index=df.index)
    
    close = df['Close']
    change = abs(close - close.shift(period))
    volatility = abs(close - close.shift(1)).rolling(period).sum()
    
    # Avoid division by zero
    er = (change / volatility).fillna(0)
    fast_sc = 2 / (fast + 1)
    slow_sc = 2 / (slow + 1)
    sc = (er * (fast_sc - slow_sc) + slow_sc)**2
    
    kama = pd.Series(index=df.index, dtype=float)
    # Start KAMA with Close
    start_idx = period
    kama.iloc[start_idx] = close.iloc[start_idx]
    
    for i in range(start_idx + 1, len(df)):
        prev_kama = kama.iloc[i-1]
        kama.iloc[i] = prev_kama + sc.iloc[i] * (close.iloc[i] - prev_kama)
        
    return kama.ffill()

def calculate_supertrend(df, period=10, multiplier=3):
    """Calculate Supertrend indicator with improved robustness for funds."""
    if df.empty or len(df) < 2:
        return pd.Series(index=df.index, dtype=float)
        
    # Synthesis for funds where High/Low might be missing
    if 'High' not in df.columns or 'Low' not in df.columns:
        df = df.copy()
        df['High'] = df['Close']
        df['Low'] = df['Close']
        
    if len(df) < period + 2:
         return pd.Series(df['Close'].values, index=df.index)

    hl2 = (df['High'] + df['Low']) / 2
    # ATR manual calculation
    h_l = df['High'] - df['Low']
    h_pc = abs(df['High'] - df['Close'].shift(1))
    l_pc = abs(df['Low'] - df['Close'].shift(1))
    tr = pd.concat([h_l, h_pc, l_pc], axis=1).max(axis=1)
    atr = tr.rolling(period).mean().fillna(tr)
    
    upperband = hl2 + (multiplier * atr)
    lowerband = hl2 - (multiplier * atr)
    
    st = pd.Series(True, index=df.index)
    st_val = pd.Series(index=df.index, dtype=float)
    
    # Initial seed
    st_val.iloc[0] = hl2.iloc[0]
    
    for i in range(1, len(df)):
        # Finalize bands
        if df['Close'].iloc[i] > upperband.iloc[i-1]:
            st.iloc[i] = True
        elif df['Close'].iloc[i] < lowerband.iloc[i-1]:
            st.iloc[i] = False
        else:
            st.iloc[i] = st.iloc[i-1]
            if st.iloc[i] and lowerband.iloc[i] < lowerband.iloc[i-1]:
                lowerband.iloc[i] = lowerband.iloc[i-1]
            if not st.iloc[i] and upperband.iloc[i] > upperband.iloc[i-1]:
                upperband.iloc[i] = upperband.iloc[i-1]
        
        st_val.iloc[i] = lowerband.iloc[i] if st.iloc[i] else upperband.iloc[i]
        
    return st_val.ffill()

def calculate_technical_score_internal(hist, current_price):
    """Core logic for 0-10 technical scoring."""
    t_score = 0.0; score_color = "rgba(255,255,255,0.1)"; score_label = "N/A"
    try:
        if not hist.empty and len(hist) > 30:
            st_series = calculate_supertrend(hist)
            kama_series = calculate_kama(hist, period=min(21, len(hist)-2))
            obv_series = calculate_obv(hist)
            adx_series = calculate_adx(hist)
            macd_df = calculate_macd(hist)
            
            l_st = st_series.iloc[-1] if not st_series.empty else 0
            l_kama = kama_series.iloc[-1] if not kama_series.empty else 0
            l_adx = adx_series.iloc[-1] if not adx_series.empty else 0
            
            st_above = current_price > l_st and l_st > 0
            kama_above = current_price > l_kama and l_kama > 0
            
            # 1. Trend Yönü (Max 4.5)
            if st_above: t_score += 2.5
            if kama_above: t_score += 2.0

            # 2. Momentum (MACD) (Max 2.5)
            if not macd_df.empty:
                l_macd = macd_df.iloc[-1]
                p_macd = macd_df.iloc[-2]
                
                is_buy = l_macd['MACD'] > l_macd['Signal']
                hist_rising = l_macd['Histogram'] > p_macd['Histogram']
                
                if is_buy:
                    if hist_rising: t_score += 2.5 # AL (GÜÇLÜ)
                    else: t_score += 1.5 # AL (ZAYIF)
                else:
                    if hist_rising: t_score += 1.0 # SAT ama dipten dönüş emaresi (SAT ZAYIF)
                    else: pass # SAT (GÜÇLÜ) -> 0 puan

            # 3. Trend Gücü (ADX) (Max 1.5)
            if l_adx > 25: t_score += 1.0
            if l_adx > 45: t_score += 0.5
            
            # 4. Hacim Onayı (OBV) (Max 1.5)
            if not obv_series.empty and len(obv_series) > 1:
                if obv_series.iloc[-1] >= obv_series.iloc[-2]: t_score += 1.5
            
            # Corrections
            t_score = max(0, min(10, t_score))
            
            if t_score < 4: score_label, score_color = "ZAYIF", "#ff3e3e"
            elif t_score < 7.5: score_label, score_color = "ORTA", "#ffcc00"
            else: score_label, score_color = "GÜÇLÜ", "#00ff88"
            
            if t_score >= 9.0: score_label = "ELMAS"
    except: pass
    return t_score, score_color, score_label

@st.cache_data(ttl=300, show_spinner=False)
def calculate_technical_scores_bulk(holdings_json, period="3mo"):
    """
    Ultra-optimized bulk technical score calculation with cross-session caching.
    Note: Input is converted to JSON string to make it hashable for st.cache_data.
    """
    holdings = json.loads(holdings_json)
    if not holdings: return {}
    
    unique_assets = []
    seen = set()
    for h in holdings:
        key = (h["symbol"], h.get("type", "bist hisse"))
        if key not in seen:
            unique_assets.append(key)
            seen.add(key)

    results = {}
    yf_keys = []
    special_keys = []
    
    for key in unique_assets:
        sym, t = key
        t_low = t.lower()
        if any(x in t_low for x in ["tefas", "fon", "bes", "oks"]) or is_gold_tl_asset(sym):
            special_keys.append(key)
        else:
            yf_keys.append(key)

    # 1. Bulk YFinance Download
    bulk_hist_data = {}
    if yf_keys:
        try:
            yf_symbols = []
            symbol_to_key = {}
            for k in yf_keys:
                s, t = k
                std_s = s
                if "bist" in t.lower() and not std_s.endswith(".IS"): std_s = f"{std_s}.IS"
                elif "kripto" in t.lower() and "-" not in std_s: std_s = f"{std_s}-USD"
                elif "döviz" in t.lower():
                    s_up = s.upper()
                    if s_up == "USD": std_s = "USDTRY=X"
                    elif s_up in ["EUR", "EYR"]: std_s = "EURTRY=X"
                yf_symbols.append(std_s)
                symbol_to_key[std_s] = k
            
            # One shot download - this is the most efficient way for YF
            df_bulk = yf.download(yf_symbols, period=period, group_by='ticker', progress=False, threads=True)
            for std_s in yf_symbols:
                ticker_df = df_bulk[std_s] if len(yf_symbols) > 1 else df_bulk
                if not ticker_df.empty:
                    bulk_hist_data[symbol_to_key[std_s]] = ticker_df.dropna(subset=['Close'])
        except: pass

    def process_single(asset_key):
        sym, t = asset_key
        try:
            hist = bulk_hist_data.get(asset_key, pd.DataFrame())
            if hist.empty or len(hist) < 5:
                hist = get_history(sym, period=period, asset_type=t)
            
            if hist.empty:
                return asset_key, {"error": "Empty history"}

            curr_price = float(hist['Close'].iloc[-1])
            prev_price = float(hist['Close'].iloc[-2]) if len(hist) > 1 else curr_price
            
            # 1. Indicators
            st_data = {"val": 0, "dist": 0, "color": "#cccccc", "bg": "rgba(255,255,255,0.05)"}
            kama_data = {"val": 0, "dist": 0, "color": "#cccccc", "bg": "rgba(255,255,255,0.05)"}
            obv_data = {"trend": "Nötr", "color": "#cccccc", "bg": "rgba(255,255,255,0.05)"}
            adx_data = {"val": 0, "label": "ZAYIF", "color": "#cccccc", "bg": "rgba(255,255,255,0.05)"}
            
            # Supertrend
            st_series = calculate_supertrend(hist)
            if not st_series.empty:
                l_st = st_series.iloc[-1]
                if l_st > 0:
                    st_dist = ((curr_price / l_st) - 1) * 100
                    st_color = "#00ff88" if curr_price > l_st else "#ff3e3e"
                    st_data = {"val": l_st, "dist": st_dist, "color": st_color, "bg": f"{st_color}20"}
            
            # KAMA
            kama_series = calculate_kama(hist, period=min(21, len(hist)-2))
            if not kama_series.empty:
                l_kama = kama_series.iloc[-1]
                if l_kama > 0:
                    kama_dist = ((curr_price / l_kama) - 1) * 100
                    kama_color = "#00ff88" if curr_price > l_kama else "#ff3e3e"
                    kama_data = {"val": l_kama, "dist": kama_dist, "color": kama_color, "bg": f"{kama_color}20"}
            
            # OBV
            obv_series = calculate_obv(hist)
            if not obv_series.empty and len(obv_series) > 1:
                l_obv = obv_series.iloc[-1]; p_obv = obv_series.iloc[-2]
                obv_trend = "Yükselen" if l_obv >= p_obv else "Düşen"
                obv_color = "#00ff88" if obv_trend == "Yükselen" else "#ff3e3e"
                obv_data = {"trend": obv_trend, "color": obv_color, "bg": f"{obv_color}20"}
            
            # ADX
            adx_series = calculate_adx(hist); l_adx = 0
            if not adx_series.empty:
                l_adx = adx_series.iloc[-1]
                is_uptrend = curr_price > kama_data["val"] if kama_data["val"] > 0 else True
                if l_adx < 20: adx_label, adx_col = "ZAYIF", "#cccccc"
                elif l_adx < 25:
                    adx_label = "ORTA"
                    adx_col = "#00ff88" if is_uptrend else "#ff3e3e"
                elif l_adx < 50:
                    adx_label = "GÜÇLÜ"
                    adx_col = "#00ff88" if is_uptrend else "#ff3e3e"
                else: 
                    adx_label = "ÇOK GÜÇLÜ"
                    adx_col = "#00ff88" if is_uptrend else "#ff3e3e"
                    adx_col = "#00ff88" if is_uptrend else "#ff3e3e"
                adx_data = {"val": l_adx, "label": adx_label, "color": adx_col, "bg": f"{adx_col}20"}
            
            # MACD
            macd_data = {"label": "NÖTR", "color": "#cccccc", "bg": "rgba(255,255,255,0.05)"}
            try:
                macd_df = calculate_macd(hist)
                if not macd_df.empty:
                    l_macd = macd_df.iloc[-1]
                    p_macd = macd_df.iloc[-2]
                    
                    is_buy = l_macd['MACD'] > l_macd['Signal']
                    hist_rising = l_macd['Histogram'] > p_macd['Histogram']
                    
                    if is_buy:
                        # AL Bölgesinde (Pozitif Momentum)
                        if hist_rising:
                            m_lab, m_col = "AL (GÜÇLÜ)", "#00ff88"  # Momentum artıyor
                        else:
                            m_lab, m_col = "AL (ZAYIF)", "#aaff00"  # Momentum azalıyor (Tepe dönüşü olabilir)
                    else:
                        # SAT Bölgesinde (Negatif Momentum)
                        if not hist_rising:
                            m_lab, m_col = "SAT (GÜÇLÜ)", "#ff3e3e" # Düşüş hızlanıyor
                        else:
                            m_lab, m_col = "SAT (ZAYIF)", "#ffaa00" # Düşüş yavaşlıyor (Dip dönüşü olabilir)
                        
                    macd_data = {"label": m_lab, "color": m_col, "bg": f"{m_col}20"}
            except: pass

            # Technical Score
            score, color, label = calculate_technical_score_internal(hist, curr_price)
            
            # Sparkline Points (Last 30 days)
            spark_points = []
            closes_30 = hist['Close'].tail(30).values
            if len(closes_30) > 1:
                min_c, max_c = min(closes_30), max(closes_30)
                rng = max_c - min_c if max_c != min_c else 1
                for i, v in enumerate(closes_30):
                    px = (i / (len(closes_30) - 1)) * 100
                    py = 30 - ((v - min_c) / rng) * 30
                    spark_points.append(f"{px:.1f},{py:.1f}")
            
            return asset_key, {
                "score": score, "color": color, "label": label, 
                "price": curr_price, "prev": prev_price,
                "st": st_data, "kama": kama_data, "obv": obv_data, "adx": adx_data, "macd": macd_data,
                "spark_points": " ".join(spark_points),
                "spark_color": "#00ff88" if closes_30[-1] >= closes_30[0] else "#ff3e3e"
            }
        except: pass
        return asset_key, {"score": 0, "color": "rgba(255,255,255,0.1)", "label": "N/A", "price": 0, "prev": 0}

    with ThreadPoolExecutor(max_workers=10) as executor:
        batch_results = list(executor.map(process_single, unique_assets))
        
    for key, data in batch_results:
        results[key] = data
        
    return results

def calculate_obv(df):
    """Calculate On-Balance Volume (OBV) with momentum fallback for funds."""
    if df.empty:
        return pd.Series(dtype=float)
        
    if 'Volume' not in df.columns or df['Volume'].sum() == 0:
        # Fallback for funds: Use Price Momentum instead of OBV
        # If today's price > yesterday, it's a positive 'volume-less' flow
        return df['Close'].diff().fillna(0).cumsum()
    
    obv = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()
    return obv

def calculate_adx(df, period=14):
    """Calculate ADX with robustness for funds (synthetic High/Low)."""
    if df.empty or len(df) < 2:
        return pd.Series(0.0, index=df.index)
        
    df = df.copy()
    if 'High' not in df.columns or 'Low' not in df.columns:
        df['High'] = df['Close']
        df['Low'] = df['Close']

    if len(df) < period * 2:
        # Return simplified momentum strength for short periods
        return abs(df['Close'].diff(period)).fillna(0)
    
    high = df['High']
    low = df['Low']
    close = df['Close']
    
    # True Range
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(period).mean().fillna(tr)
    
    # Directional Movement
    up_move = high.diff()
    down_move = low.diff().abs()
    
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
    
    # Avoid div by zero in DI
    p_roll = pd.Series(plus_dm, index=df.index).rolling(period).mean()
    m_roll = pd.Series(minus_dm, index=df.index).rolling(period).mean()
    
    plus_di = 100 * (p_roll / atr).fillna(0)
    minus_di = 100 * (m_roll / atr).fillna(0)
    
    sum_di = (plus_di + minus_di)
    dx = 100 * (abs(plus_di - minus_di) / sum_di.replace(0, 1)).fillna(0)
    adx = dx.rolling(period).mean().fillna(0)
    
    return adx

def calculate_macd(df, fast=12, slow=26, signal=9):
    """Calculate MACD, Signal line, and Histogram."""
    if df.empty or len(df) < slow + signal:
        return pd.DataFrame()
        
    close = df['Close']
    exp1 = close.ewm(span=fast, adjust=False).mean()
    exp2 = close.ewm(span=slow, adjust=False).mean()
    macd = exp1 - exp2
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    histogram = macd - signal_line
    
    return pd.DataFrame({
        'MACD': macd,
        'Signal': signal_line,
        'Histogram': histogram
    })

@st.cache_data(ttl=3600, show_spinner=False)
def get_strategy_signal(symbol, asset_type):
    """
    Checks the SAT condition: Price < Supertrend AND Price < KAMA.
    Parameters: ST (10, 3), KAMA (21, 2, 30)
    """
    try:
        # Fetch at least 60 days to have enough room for 21-period indicators
        hist = get_history(symbol, period="60d", asset_type=asset_type)
        if hist.empty or len(hist) < 30:
            return False
            
        current_price = hist['Close'].iloc[-1]
        kama = calculate_kama(hist, period=21)
        st_val = calculate_supertrend(hist, period=10, multiplier=3)
        
        if kama.empty or st_val.empty:
            return False
            
        latest_kama = kama.iloc[-1]
        latest_st = st_val.iloc[-1]
        
        # Supertrend direction: if current price is below the trend line (which is upperband in downtrend)
        # In our calculation ST_val is the stop line.
        # If Price < ST_val AND Price < KAMA -> SAT (Sinyal: Bozulma)
        if current_price < latest_st and current_price < latest_kama:
            return True
        return False
    except:
        return False

def get_current_data(symbol, asset_type=None):
    """Fetch current price with global cache priority, then falling back to cached single fetch."""
    # 1. Standardization (MUST BE FIRST for cache consistency)
    a_type = str(asset_type).lower() if asset_type else ""
    s_upper = str(symbol).upper()
    
    # NAKIT HANDLING
    if "nakit" in a_type:
        return {"price": 1.0, "prev_close": 1.0, "change_pct": 0.0}

    # Standardize symbol based on type
    std_symbol = str(symbol).strip()
    if "bist" in a_type and not std_symbol.endswith(".IS"): std_symbol = f"{std_symbol}.IS"
    if "kripto" in a_type and "-" not in std_symbol: std_symbol = f"{std_symbol}-USD"
    if "döviz" in a_type:
        if s_upper == "USD": std_symbol = "USDTRY=X"
        elif s_upper in ["EUR", "EYR"]: std_symbol = "EURTRY=X"
        elif s_upper == "GBP": std_symbol = "GBPTRY=X"
    if s_upper == "DOLAR": std_symbol = "USDTRY=X" # Global alias

    # 2. Check global cache (populated by bulk fetch)
    cache_key = (std_symbol, a_type)
    if cache_key in PRICE_CACHE:
        return PRICE_CACHE[cache_key]
    
    # 3. Fallback to single cached fetch
    return _fetch_single_symbol(std_symbol, a_type)

@st.cache_data(ttl=60, show_spinner=False)
def _fetch_bulk_data(yf_tickers_tuple):
    """
    Internal cached function to perform the actual bulk download.
    Input must be hashable (tuple), returns a dictionary of data results.
    """
    if not yf_tickers_tuple:
        return {}
        
    results = {}
    sym_list = list(set([x[0] for x in yf_tickers_tuple]))
    
    try:
        # Use threads = True for faster download
        data = yf.download(sym_list, period="5d", interval="1d", group_by='ticker', progress=False, threads=True)
        
        if not data.empty:
            for std_s, t in yf_tickers_tuple:
                try:
                    ticker_data = data[std_s] if len(sym_list) > 1 else data
                    if not ticker_data.empty:
                        closes = ticker_data['Close'].dropna()
                        if len(closes) >= 1:
                            price = round(float(closes.iloc[-1]), 4)
                            prev_close = round(float(closes.iloc[-2]), 4) if len(closes) >= 2 else price
                            results[(std_s, t)] = {
                                "price": price, 
                                "prev_close": prev_close, 
                                "change_pct": ((price/prev_close)-1)*100 if prev_close else 0
                            }
                except: continue
    except: 
        pass
        
    return results

def fetch_all_prices_parallel(holdings):
    """Fetch prices for all holdings in parallel to save time."""
    unique_symbols = []
    seen = set()
    for h in holdings:
        # Standardize symbol based on type
        symbol = h["symbol"]
        asset_type = str(h.get("type", "")).lower()
        if "bist" in asset_type and not symbol.endswith(".IS"): symbol = f"{symbol}.IS"
        if "kripto" in asset_type and "-" not in symbol: symbol = f"{symbol}-USD"
        if "döviz" in asset_type:
            s_up = symbol.upper()
            if s_up == "USD": symbol = "USDTRY=X"
            elif s_up in ["EUR", "EYR"]: symbol = "EURTRY=X"
            elif s_up == "GBP": symbol = "GBPTRY=X"
        
        key = (symbol, asset_type)
        if key not in seen:
            unique_symbols.append(key)
            seen.add(key)
    
    # Separation & Standardization (Consistency is KEY)
    yf_tickers = []
    seen_std = set()

    for h in holdings:
        s = h["symbol"]; t = str(h.get("type", "")).lower(); s_up = str(s).upper()
        
        # EXACT SAME LOGIC AS get_current_data
        std_s = s
        if "bist" in t and not std_s.endswith(".IS"): std_s = f"{std_s}.IS"
        if "kripto" in t and "-" not in std_s: std_s = f"{std_s}-USD"
        if "döviz" in t:
            if s_up == "USD": std_s = "USDTRY=X"
            elif s_up in ["EUR", "EYR"]: std_s = "EURTRY=X"
            elif s_up == "GBP": std_s = "GBPTRY=X"
        if s_up == "DOLAR": std_s = "USDTRY=X"

        cache_key = (std_s, t)
        if cache_key not in seen_std:
            seen_std.add(cache_key)
            if any(x in t for x in ["tefas", "fon", "bes", "oks"]) or is_gold_tl_asset(s_up):
                pass # Handled by remaining (get_current_data)
            else:
                yf_tickers.append(cache_key)
    
    # 1. Bulk download via Cached Helper
    if yf_tickers:
        # Convert list to tuple for caching hashability
        bulk_results = _fetch_bulk_data(tuple(yf_tickers))
        # Update global cache
        PRICE_CACHE.update(bulk_results)
        
    # 2. Parallel for everything else (Special, BorsaPy, failed YF)
    # Collect ALL final keys we need to have in PRICE_CACHE
    final_keys = seen_std
    remaining = [k for k in final_keys if k not in PRICE_CACHE]
    
    if remaining:
        with ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(lambda x: (x, get_current_data(x[0], x[1])), remaining))
        
        for key, data in results:
            if data: PRICE_CACHE[key] = data
    
    return PRICE_CACHE

@st.cache_data(ttl=3600)
def get_history(symbol, period="1mo", asset_type=None):
    """Fetch history for a symbol with standardization."""
    # ... existing implementation is fine as a fallback ...
    try:
        a_type = str(asset_type).lower() if asset_type else ""
        if any(x in a_type for x in ["tefas", "fon", "bes", "oks"]):
            fund = borsapy.Fund(symbol)
            df = fund.history(period=period)
            if not df.empty: return df.rename(columns={"Price": "Close"})
            return pd.DataFrame()
        
        if "bist" in a_type and not symbol.endswith(".IS"): symbol = f"{symbol}.IS"
        if "döviz" in a_type:
            s_up = symbol.upper()
            if s_up == "USD": symbol = "USDTRY=X"
            elif s_up in ["EUR", "EYR"]: symbol = "EURTRY=X"
            elif s_up == "GBP": symbol = "GBPTRY=X"
        if "kripto" in a_type and "-" not in symbol: symbol = f"{symbol}-USD"
            
        s_up = symbol.upper()
        if is_gold_tl_asset(s_up):
            try:
                # BIST Gold Certificate check
                if "S1" in s_up or ("ALTIN" in s_up and "bist" in a_type):
                    t = borsapy.Ticker("ALTIN")
                    df = t.history(period=period)
                    if not df.empty: return df
            except:
                pass
            
        if is_gold_tl_asset(s_up):
            try:
                # BIST Gold Certificate check
                if "S1" in s_up or ("ALTIN" in s_up and "bist" in a_type):
                    t = borsapy.Ticker("ALTIN")
                    df = t.history(period=period)
                    if not df.empty: return df
            except:
                pass
            
            # Gold Spot Calculation (for Emtia or variants)
            # Use yf.download directly to avoid recursion issues and be more efficient
            try:
                spot_data = yf.download(["GC=F", "USDTRY=X"], period=period, progress=False, group_by='ticker')
                if not spot_data.empty:
                    ons = spot_data["GC=F"]["Close"].ffill().bfill()
                    usd = spot_data["USDTRY=X"]["Close"].ffill().bfill()
                    
                    # Align dates
                    combined = pd.DataFrame({"ons": ons, "usd": usd}).dropna()
                    if not combined.empty:
                        gram_gold = (combined["ons"] / 31.1035) * combined["usd"]
                        
                        multiplier = 1.0
                        if "ÇEYREK" in s_up: multiplier = 1.6065
                        elif "YARIM" in s_up: multiplier = 3.2130
                        elif "TAM" in s_up: multiplier = 6.4260
                        elif "ATA" in s_up: multiplier = 6.6150
                        
                        price_series = gram_gold * multiplier
                        # Synthesize full OHLC for indicators
                        df_res = pd.DataFrame({
                            "Open": price_series,
                            "High": price_series,
                            "Low": price_series,
                            "Close": price_series
                        }, index=combined.index)
                        return df_res
            except:
                pass
            return pd.DataFrame()
        
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period)
        
        # SPECIAL FALLBACK: If ZPX30 history is empty or too short, use XU030.IS (underlying index)
        if (s_up == "ZPX30" or s_up == "ZPX30.IS") and (df.empty or len(df) < 5):
            df_index = yf.Ticker("XU030.IS").history(period=period)
            if not df_index.empty:
                # SCALE THE INDEX DATA to match ZPX30 price level
                # Get current price of ZPX30 from PRICE_CACHE or a single fetch
                current_price = 0
                z_data = get_current_data("ZPX30", "bist hisse")
                if z_data: current_price = z_data["price"]
                
                if current_price > 0:
                    index_last_close = df_index['Close'].iloc[-1]
                    ratio = current_price / index_last_close
                    # Scale all numerical columns
                    for col in ['Open', 'High', 'Low', 'Close']:
                        if col in df_index.columns:
                            df_index[col] = df_index[col] * ratio
                return df_index
                
        return df
    except: return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_portfolio_history(holdings, period="1mo"):
    """Aggregate historical value and cost of holdings with robust normalization and fallback."""
    if not holdings: return pd.DataFrame()
    
    # 0. Get current date for 'today' point
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # 1. Categorize and prepare tickers
    yf_tickers = set()
    has_usd = False
    
    for h in holdings:
        s = h["symbol"]; t = str(h.get("type", "")).lower()
        s_up = s.upper()
        is_usd = (any(x in t for x in ["abd", "kripto"]) or ("emtia" in t)) and not is_gold_tl_asset(s_up)
        if is_usd: has_usd = True
        
        if not any(x in t for x in ["tefas", "fon", "bes", "oks"]):
            std_s = s
            if "bist" in t and not std_s.endswith(".IS"): std_s = f"{std_s}.IS"
            elif "kripto" in t and "-" not in std_s: std_s = f"{std_s}-USD"
            elif "döviz" in t:
                s_up = s.upper()
                if s_up == "USD": std_s = "USDTRY=X"
                elif s_up in ["EUR", "EYR"]: std_s = "EURTRY=X"
                elif s_up == "GBP": std_s = "GBPTRY=X"
            yf_tickers.add(std_s)
    
    if has_usd: yf_tickers.add("USDTRY=X")
    
    # 2. Bulk Fetch YFinance
    bulk_data = pd.DataFrame()
    if yf_tickers:
        try:
            bulk_data = yf.download(list(yf_tickers), period=period, progress=False, group_by='ticker')
            bulk_data.index = pd.to_datetime(bulk_data.index).tz_localize(None).normalize()
        except: pass

    # Get current USD rate for fallback
    usd_data_now = get_current_data("USDTRY=X", "döviz")
    usd_now = usd_data_now["price"] if usd_data_now else 34.0
    
    # Unified USD rates series (hist + current today)
    raw_usd_hist = pd.Series()
    if has_usd and not bulk_data.empty:
        try:
            # When group_by='ticker' is used, columns are MultiIndex (Ticker, Attribute)
            if "USDTRY=X" in bulk_data.columns.get_level_values(0):
                raw_usd_hist = bulk_data["USDTRY=X"]["Close"]
            else:
                # Fallback: if single ticker was requested and it was USDTRY=X
                raw_usd_hist = bulk_data.iloc[:, bulk_data.columns.get_level_values(1) == 'Close'].iloc[:, 0]
        except: pass
    
    # 3. Process each holding
    val_series_dict = {}
    cost_series_dict = {}
    
    for h in holdings:
        s = h["symbol"]; t = h.get("type", "").lower()
        p_date = pd.to_datetime(h["purchase_date"]).tz_localize(None).normalize()
        s_up = s.upper()
        is_usd = (any(x in t for x in ["abd", "kripto"]) or ("emtia" in t)) and not is_gold_tl_asset(s_up)
        
        # Get current data for fallback and today consistency
        cur = get_current_data(s, t)
        cur_price = cur["price"] if cur else h["cost"]
        
        prices = pd.Series()
        
        # Try to get history
        if any(x in t for x in ["tefas", "fon", "bes", "oks"]):
            hist = get_history(s, period=period, asset_type=t)
            if not hist.empty:
                hist.index = pd.to_datetime(hist.index).tz_localize(None).normalize()
                prices = hist["Close"]
        else:
            std_s = s
            if "bist" in t and not std_s.endswith(".IS"): std_s = f"{std_s}.IS"
            elif "kripto" in t and "-" not in std_s: std_s = f"{std_s}-USD"
            elif "döviz" in t:
                s_up = s.upper()
                if (s_up == "USD") or (s_up == "DOLAR"): std_s = "USDTRY=X"
                elif s_up in ["EUR", "EYR"]: std_s = "EURTRY=X"
                elif s_up == "GBP": std_s = "GBPTRY=X"

            if not bulk_data.empty:
                try:
                    # Robust MultiIndex access
                    if std_s in bulk_data.columns.get_level_values(0):
                        prices = bulk_data[std_s]["Close"]
                    elif len(yf_tickers) == 1:
                        prices = bulk_data.iloc[:, bulk_data.columns.get_level_values(1) == 'Close'].iloc[:, 0]
                except: pass
        
        # Robust construction: if prices empty, use current price as a flat line
        if prices.empty:
            idx = bulk_data.index if not bulk_data.empty else pd.date_range(end=today, periods=30)
            prices = pd.Series(cur_price, index=idx)
        
        # ALWAYS force today point to match current data exactly
        prices = prices.copy()
        prices.loc[today] = cur_price
        prices = prices[~prices.index.duplicated(keep='last')].sort_index()

        # Values & Costs
        v = prices * h["amount"]
        c = pd.Series(h["cost"] * h["amount"], index=prices.index)
        
        if is_usd:
            # Reindex USD rates and ALWAYS force today rate to match current data
            r = raw_usd_hist.reindex(prices.index).ffill().fillna(usd_now)
            r.loc[today] = usd_now
            v = v * r
            c = c * r
        
        # Apply purchase date mask (Zero before purchase)
        v = v.copy(); v.loc[v.index < p_date] = 0
        c = c.copy(); c.loc[c.index < p_date] = 0
        
        key = f"{s}_{id(h)}"
        val_series_dict[key] = v
        cost_series_dict[key] = c

    # 4. Final Aggregation
    if val_series_dict:
        v_df = pd.DataFrame(val_series_dict).sort_index().ffill().fillna(0)
        c_df = pd.DataFrame(cost_series_dict).sort_index().ffill().fillna(0)
        
        final_idx = v_df.index.union(c_df.index)
        v_df = v_df.reindex(final_idx).ffill().fillna(0)
        c_df = c_df.reindex(final_idx).ffill().fillna(0)
        
        result = pd.DataFrame(index=final_idx)
        result["Market_Value"] = v_df.sum(axis=1)
        result["Total_Cost"] = c_df.sum(axis=1)
        return result
        
    return pd.DataFrame()



# ==================== PERFORMANCE METRICS FUNCTIONS ====================

def calculate_xirr(cash_flows, dates):
    """
    Calculate XIRR (Extended Internal Rate of Return).
    Cash flows: list of amounts (negative for investments, positive for current value)
    Dates: list of datetime objects corresponding to cash flows
    """
    if len(cash_flows) < 2 or len(cash_flows) != len(dates):
        return None
    
    # Convert dates to years from first date
    first_date = min(dates)
    years = [(d - first_date).days / 365.0 for d in dates]
    
    # Check if time period is too short (less than 30 days)
    max_years = max(years)
    if max_years < 0.082:  # Less than ~30 days (30/365)
        return None
    
    def npv(rate):
        return sum(cf / ((1 + rate) ** y) for cf, y in zip(cash_flows, years))
    
    try:
        from scipy.optimize import brentq
        # Try to find rate between -90% and 500%
        result = brentq(npv, -0.9, 5.0, maxiter=100) * 100
        # Bound result to reasonable range
        return max(min(result, 999.9), -99.9)
    except:
        try:
            from scipy.optimize import newton
            result = newton(npv, 0.1, maxiter=100) * 100
            return max(min(result, 999.9), -99.9)
        except:
            # Fallback: simple return calculation
            total_invested = sum(-cf for cf in cash_flows if cf < 0)
            total_value = sum(cf for cf in cash_flows if cf > 0)
            if total_invested > 0:
                return ((total_value / total_invested) - 1) * 100
            return None

def calculate_portfolio_xirr(holdings):
    """
    Calculate XIRR for the entire portfolio.
    Uses purchase dates and current values.
    """
    if not holdings:
        return None
        
    cash_flows = []
    dates = []
    total_cost = 0
    total_current_value = 0
    
    for h in holdings:
        # Investment (negative cash flow)
        cost_amount = h["cost"] * h["amount"]
        total_cost += cost_amount
        
        try:
            purchase_date = datetime.strptime(h["purchase_date"], "%Y-%m-%d") if isinstance(h["purchase_date"], str) else h["purchase_date"]
        except:
            purchase_date = datetime.now() - timedelta(days=30)  # Default to 30 days ago
        
        cash_flows.append(-cost_amount)
        dates.append(purchase_date)
        
        # Get current value
        d = get_current_data(h["symbol"], h.get("type"))
        if d:
            # Convert USD to TL if needed
            t = h.get("type", "").lower()
            s_up = h["symbol"].upper()
            if (any(x in t for x in ["abd", "kripto"]) or ("emtia" in t)) and not is_gold_tl_asset(s_up):
                usd_data = get_current_data("USDTRY=X", "döviz")
                rate = usd_data["price"] if usd_data else 34.0
            else:
                rate = 1.0
            total_current_value += d["price"] * h["amount"] * rate
        else:
            total_current_value += cost_amount  # Fallback to cost
    
    if total_current_value > 0 and total_cost > 0:
        # Add current portfolio value as positive cash flow (today)
        cash_flows.append(total_current_value)
        dates.append(datetime.now())
        
        xirr_result = calculate_xirr(cash_flows, dates)
        
        # If XIRR is None because of the 30-day rule, return None
        if xirr_result is None:
            return None
            
        # If XIRR is unreasonable, bound it
        if abs(xirr_result) > 1000:
            simple_return = ((total_current_value / total_cost) - 1) * 100
            return max(min(simple_return, 999.9), -99.9)
        
        return xirr_result
    
    return None

def calculate_twr(holdings, period="1y"):
    """
    Calculate TWR (Time-Weighted Return) for the portfolio.
    This measures investment performance independent of cash flows.
    """
    # Get portfolio history
    history_df = get_portfolio_history(holdings, period=period)
    
    if history_df is None or history_df.empty or "Total" not in history_df.columns:
        return None, None
    
    # Get daily returns
    total_values = history_df["Total"]
    
    if len(total_values) < 2:
        return None, None
    
    # Calculate daily returns
    daily_returns = total_values.pct_change().dropna()
    
    # Calculate TWR: (1 + r1) * (1 + r2) * ... * (1 + rn) - 1
    twr = (1 + daily_returns).prod() - 1
    
    # Annualized TWR
    num_days = (total_values.index[-1] - total_values.index[0]).days
    if num_days > 0:
        annualized_twr = ((1 + twr) ** (365 / num_days)) - 1
    else:
        annualized_twr = twr
    
    return twr * 100, annualized_twr * 100  # Return as percentages

@st.cache_data(ttl=3600)
def get_benchmark_performance(benchmark_symbol="XU100.IS", period="1y"):
    """
    Get benchmark (e.g., BIST100) performance for comparison.
    Returns total return and annualized return.
    """
    try:
        ticker = yf.Ticker(benchmark_symbol)
        hist = ticker.history(period=period)
        
        if hist.empty or len(hist) < 2:
            return None, None
        
        # Total return
        total_return = (hist['Close'].iloc[-1] / hist['Close'].iloc[0] - 1) * 100
        
        # Annualized return
        num_days = (hist.index[-1] - hist.index[0]).days
        if num_days > 0:
            annualized = (((hist['Close'].iloc[-1] / hist['Close'].iloc[0]) ** (365 / num_days)) - 1) * 100
        else:
            annualized = total_return
        
        return total_return, annualized
    except Exception as e:
        print(f"Error getting benchmark performance: {e}")
        return None, None

def calculate_alpha(portfolio_return, benchmark_return):
    """
    Calculate Alpha: Portfolio outperformance vs benchmark.
    Alpha = Portfolio Return - Benchmark Return
    """
    if portfolio_return is None or benchmark_return is None:
        return None
    return portfolio_return - benchmark_return

def get_portfolio_metrics(holdings, period="1y"):
    """
    Get comprehensive portfolio performance metrics.
    Returns: dict with XIRR, TWR, Benchmark, Alpha, Simple Return
    """
    metrics = {
        "xirr": None,
        "simple_return": None,
        "investment_days": None,
        "twr": None,
        "twr_annualized": None,
        "benchmark_return": None,
        "benchmark_annualized": None,
        "alpha": None,
        "alpha_annualized": None
    }
    
    if not holdings:
        return metrics
    
    # Calculate Simple Return (Total Cost vs Current Value in TL)
    total_cost_tl = 0
    total_current_tl = 0
    earliest_date = None
    
    # Get current USD rate for conversion
    usd_data = get_current_data("USDTRY=X", "döviz")
    usd_rate = usd_data["price"] if usd_data else 34.0
    
    for h in holdings:
        symbol = h['symbol']
        amount = h['amount']
        cost = h['cost']
        t = h.get('type', '').lower()
        
        # Get current value
        d = get_current_data(symbol, h.get('type'))
        current_price = d['price'] if d else cost
        
        s_up = symbol.upper()
        is_usd = (any(x in t for x in ["abd", "kripto"]) or ("emtia" in t)) and not is_gold_tl_asset(s_up)
        rate = usd_rate if is_usd else 1.0
        
        # Add to TL totals
        total_cost_tl += (cost * amount * rate)
        total_current_tl += (current_price * amount * rate)
        
        # Track earliest purchase date
        try:
            pdate = datetime.strptime(h["purchase_date"], "%Y-%m-%d") if isinstance(h["purchase_date"], str) else h["purchase_date"]
            if earliest_date is None or pdate < earliest_date:
                earliest_date = pdate
        except:
            pass
    
    # Calculate simple return in TL terms
    if total_cost_tl > 0:
        metrics["simple_return"] = ((total_current_tl / total_cost_tl) - 1) * 100
    
    # Calculate investment days
    if earliest_date:
        metrics["investment_days"] = (datetime.now() - earliest_date).days
    
    # Calculate XIRR
    metrics["xirr"] = calculate_portfolio_xirr(holdings)
    
    # Calculate TWR
    twr, twr_ann = calculate_twr(holdings, period=period)
    metrics["twr"] = twr
    metrics["twr_annualized"] = twr_ann
    
    # Get Benchmark Performance (BIST100)
    bench_ret, bench_ann = get_benchmark_performance("XU100.IS", period=period)
    metrics["benchmark_return"] = bench_ret
    metrics["benchmark_annualized"] = bench_ann
    
    # Calculate Alpha
    if twr is not None and bench_ret is not None:
        metrics["alpha"] = calculate_alpha(twr, bench_ret)
    if twr_ann is not None and bench_ann is not None:
        metrics["alpha_annualized"] = calculate_alpha(twr_ann, bench_ann)
    
    return metrics

# ==================== SUPABASE PORTFOLIO FUNCTIONS (with user_id) ====================

def get_user_id():
    """Get current user's ID from session state."""
    user = st.session_state.get("user")
    if not user:
        return None
    # Support both object and dict formats for user
    if hasattr(user, 'id'):
        return str(user.id)
    if isinstance(user, dict) and 'id' in user:
        return str(user['id'])
    return None

def migrate_local_to_supabase(json_path="portfolio.json"):
    """Migrate data from local JSON file to Supabase for the current user."""
    user_id = get_user_id()
    if not user_id:
        return False, "Kullanıcı girişi yapılmamış."
    
    if not os.path.exists(json_path):
        return False, f"Yerel veri dosyası bulunamadı: {json_path}"
    
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            local_data = json.load(f)
        
        if "portfolios" not in local_data:
            return False, "Geçersiz dosya formatı."
        
        success_count = 0
        for p_name, p_data in local_data["portfolios"].items():
            # 1. Create or Get portfolio
            # First check if this user already has it
            existing_p = supabase.table("portfolios").select("id").eq("user_id", user_id).eq("name", p_name).execute()
            
            if existing_p.data:
                p_id = existing_p.data[0]["id"]
            else:
                # Check if an orphaned portfolio with this name exists
                orphaned_p = supabase.table("portfolios").select("id").is_("user_id", "null").eq("name", p_name).execute()
                
                if orphaned_p.data:
                    # Claim the orphaned one
                    p_id = orphaned_p.data[0]["id"]
                    supabase.table("portfolios").update({"user_id": user_id}).eq("id", p_id).execute()
                else:
                    # Try to create new
                    try:
                        new_p = supabase.table("portfolios").insert({"name": p_name, "user_id": user_id}).execute()
                        if not new_p.data:
                            # If insert fails (maybe global unique constraint), try to find it regardless of user
                            any_p = supabase.table("portfolios").select("id").eq("name", p_name).execute()
                            if any_p.data:
                                p_id = any_p.data[0]["id"]
                            else:
                                continue
                        else:
                            p_id = new_p.data[0]["id"]
                    except:
                        # Fallback: try to find by name again
                        any_p = supabase.table("portfolios").select("id").eq("name", p_name).execute()
                        if any_p.data:
                            p_id = any_p.data[0]["id"]
                        else:
                            continue
            
            # 2. Add holdings
            for h in p_data.get("holdings", []):
                symbol = h.get("symbol")
                amount = float(h.get("amount", 0))
                cost = float(h.get("cost", 0))
                asset_type = h.get("type", "bist hisse")
                purchase_date = h.get("added_at", datetime.now().strftime("%Y-%m-%d"))
                if " " in purchase_date:
                    purchase_date = purchase_date.split(" ")[0]
                
                existing_h = supabase.table("holdings").select("id").eq("portfolio_id", p_id).eq("symbol", symbol).eq("purchase_date", purchase_date).execute()
                
                if not existing_h.data:
                    supabase.table("holdings").insert({
                        "portfolio_id": p_id,
                        "symbol": symbol,
                        "type": asset_type,
                        "amount": amount,
                        "cost": cost,
                        "purchase_date": purchase_date
                    }).execute()
                    success_count += 1
        return True, f"Başarıyla {success_count} varlık Supabase hesabınıza aktarıldı."
    except Exception as e:
        return False, f"Göç hatası: {str(e)}"


def claim_orphaned_supabase_data():
    """Assign all portfolios with NULL user_id to the current logged-in user."""
    user_id = get_user_id()
    if not user_id:
        return False, "Kullanıcı girişi yapılmamış."
    
    try:
        # 1. Find portfolios where user_id is null
        # Note: In Supabase/PostgREST, we use 'is.null' for filter
        response = supabase.table("portfolios").select("id").is_("user_id", "null").execute()
        
        if not response.data:
            return False, "Eşleşen sahipsiz veri bulunamadı."
        
        ids_to_claim = [p["id"] for p in response.data]
        
        # 2. Update these portfolios with current user_id
        for p_id in ids_to_claim:
            supabase.table("portfolios").update({"user_id": user_id}).eq("id", p_id).execute()
            
        return True, f"Başarıyla {len(ids_to_claim)} portföy hesabınıza tanımlandı."
        
    except Exception as e:
        return False, f"Hata: {str(e)}"

def load_portfolio():
    """Load portfolios for the current user from Supabase."""
    user_id = get_user_id()
    if not user_id:
        return {"portfolios": {}, "selected_for_total": []}
    
    try:
        # Get user's portfolios
        portfolios_response = supabase.table("portfolios").select("*").eq("user_id", user_id).execute()
        portfolios = portfolios_response.data
        
        # Get all holdings for user's portfolios
        portfolio_ids = [p["id"] for p in portfolios]
        holdings = []
        if portfolio_ids:
            holdings_response = supabase.table("holdings").select("*").in_("portfolio_id", portfolio_ids).execute()
            holdings = holdings_response.data
        
        # Structure data
        result = {
            "portfolios": {},
            "selected_for_total": []
        }
        
        for portfolio in portfolios:
            portfolio_id = portfolio["id"]
            portfolio_name = portfolio["name"]
            
            portfolio_holdings = [
                {
                    "symbol": h["symbol"],
                    "type": h["type"],
                    "amount": float(h["amount"]),
                    "cost": float(h["cost"]),
                    "purchase_date": h["purchase_date"],
                    "p": portfolio_name
                }
                for h in holdings if h["portfolio_id"] == portfolio_id
            ]
            
            result["portfolios"][portfolio_name] = {
                "id": portfolio_id,
                "holdings": portfolio_holdings,
                "history": []
            }
            result["selected_for_total"].append(portfolio_name)
        
        # If no portfolios exist, create a default one
        if not result["portfolios"]:
            if create_portfolio("Genel"):
                return load_portfolio()
            else:
                # Fallback to avoid infinite recursion
                return {"portfolios": {"Genel": {"holdings": [], "history": []}}, "selected_for_total": ["Genel"]}

        
        return result
        
    except Exception as e:
        print(f"Error loading portfolios: {e}")
        return {"portfolios": {"Genel": {"holdings": [], "history": []}}, "selected_for_total": ["Genel"]}

def save_all_portfolios(data):
    """Not used in Supabase mode - data is saved automatically."""
    pass

def create_portfolio(name):
    """Create a new portfolio for the current user."""
    user_id = get_user_id()
    if not user_id:
        return False
    try:
        # Check if THIS user already has a portfolio with this name
        existing = supabase.table("portfolios").select("id").eq("user_id", user_id).eq("name", name).execute()
        if existing.data:
            return True # Already exists for this user
            
        # Try to insert. If SQL constraint (unique name) still exists globally, this might fail,
        # but it will print the error instead of hanging.
        response = supabase.table("portfolios").insert({"name": name, "user_id": user_id}).execute()
        return True
    except Exception as e:
        print(f"Error creating portfolio: {e}")
        # If it fails, maybe try to claim an orphaned one or just return False
        return False



def delete_portfolio(name):
    """Delete a portfolio for the current user."""
    user_id = get_user_id()
    if not user_id:
        return False
    try:
        response = supabase.table("portfolios").select("id").eq("name", name).eq("user_id", user_id).execute()
        if response.data:
            portfolio_id = response.data[0]["id"]
            supabase.table("portfolios").delete().eq("id", portfolio_id).execute()
            return True
        return False
    except Exception as e:
        print(f"Error deleting portfolio: {e}")
        return False

def add_asset(portfolio_name, symbol, amount, cost, asset_type=None, purchase_date=None):
    """Add an asset to a portfolio."""
    user_id = get_user_id()
    if not user_id:
        return False
    try:
        response = supabase.table("portfolios").select("id").eq("name", portfolio_name).eq("user_id", user_id).execute()
        if not response.data:
            return False
        
        portfolio_id = response.data[0]["id"]
        
        if purchase_date is None:
            purchase_date = datetime.now().strftime("%Y-%m-%d")
        
        # Check if holding exists
        existing = supabase.table("holdings").select("*").eq("portfolio_id", portfolio_id).eq("symbol", symbol).eq("purchase_date", purchase_date).execute()
        
        if existing.data:
            holding = existing.data[0]
            total_units = float(holding["amount"]) + amount
            avg_cost = ((float(holding["amount"]) * float(holding["cost"])) + (amount * cost)) / total_units
            supabase.table("holdings").update({"amount": total_units, "cost": round(avg_cost, 4)}).eq("id", holding["id"]).execute()
        else:
            supabase.table("holdings").insert({
                "portfolio_id": portfolio_id,
                "symbol": symbol,
                "type": asset_type,
                "amount": amount,
                "cost": cost,
                "purchase_date": purchase_date
            }).execute()
        
        return True
    except Exception as e:
        print(f"Error adding asset: {e}")
        return False

def delete_asset(portfolio_name, symbol, purchase_date=None):
    """Delete an asset from a portfolio."""
    user_id = get_user_id()
    if not user_id:
        return False
    try:
        response = supabase.table("portfolios").select("id").eq("name", portfolio_name).eq("user_id", user_id).execute()
        if not response.data:
            return False
        
        portfolio_id = response.data[0]["id"]
        query = supabase.table("holdings").delete().eq("portfolio_id", portfolio_id).eq("symbol", symbol)
        
        if purchase_date:
            query = query.eq("purchase_date", purchase_date)
        
        query.execute()
        return True
    except Exception as e:
        print(f"Error deleting asset: {e}")
        return False

def remove_asset(portfolio_name, symbol, amount, price, purchase_date=None):
    """Sell/remove an asset from a portfolio."""
    user_id = get_user_id()
    if not user_id:
        return False
    try:
        response = supabase.table("portfolios").select("id").eq("name", portfolio_name).eq("user_id", user_id).execute()
        if not response.data:
            return False
        
        portfolio_id = response.data[0]["id"]
        query = supabase.table("holdings").select("*").eq("portfolio_id", portfolio_id).eq("symbol", symbol)
        
        if purchase_date:
            query = query.eq("purchase_date", purchase_date)
        
        holdings_response = query.execute()
        
        if not holdings_response.data:
            return False
        
        holding = holdings_response.data[0]
        current_amount = float(holding["amount"])
        
        if current_amount >= amount:
            new_amount = current_amount - amount
            if new_amount == 0:
                supabase.table("holdings").delete().eq("id", holding["id"]).execute()
            else:
                supabase.table("holdings").update({"amount": new_amount}).eq("id", holding["id"]).execute()
            return True
        return False
    except Exception as e:
        print(f"Error removing asset: {e}")
        return False

def get_all_holdings():
    """Get all holdings across all portfolios using cached load_portfolio."""
    try:
        data = load_portfolio()
        holdings = []
        if data and "portfolios" in data:
            for p_name, p_data in data["portfolios"].items():
                for h in p_data.get("holdings", []):
                    # Ensure format matches what app expects
                    holdings.append({
                        "symbol": h["symbol"],
                        "type": h["type"],
                        "amount": h["amount"],
                        "cost": h["cost"],
                        "purchase_date": h["purchase_date"],
                        "p": p_name
                    })
        return holdings
        
    except Exception as e:
        print(f"Error getting all holdings: {e}")
        return []

# ==================== SELECTED PORTFOLIOS FUNCTIONS ====================

import json

# SETTINGS_FILE is no longer needed for Supabase
# SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "settings.json")

def load_selected_portfolios():
    """Load selected portfolios from Supabase user_settings."""
    try:
        val = get_user_setting("selected_portfolios")
        if val:
            # Handle both stringified JSON (for text columns) and direct JSON (for jsonb columns)
            if isinstance(val, str):
                try:
                    return json.loads(val)
                except:
                    return []
            return val
        return None
    except Exception as e:
        print(f"Error loading selected portfolios: {e}")
        return None

def save_selected_portfolios(selected_list):
    """Save selected portfolios to Supabase user_settings."""
    try:
        # Serialize to ensure compatibility with potential TEXT columns
        val_to_save = json.dumps(selected_list, ensure_ascii=False)
        success, msg = save_user_setting("selected_portfolios", val_to_save)
        return success
    except Exception as e:
        print(f"Error saving selected portfolios: {e}")
        return False

# ==================== ALERT FUNCTIONS ====================

ALERTS_FILE = os.path.join(os.path.dirname(__file__), "alerts.json")

def load_alerts():
    """Load alerts for the current user strictly from Supabase."""
    user_id = get_user_id()
    if not user_id:
        return []

    try:
        db = get_db()
        response = db.table("alerts").select("*").eq("user_id", user_id).execute()
        if response.data:
            return response.data
    except Exception as e:
        print(f"Error loading alerts: {e}")
    
    return []



def save_alerts_local(alerts):
    """Save alerts to local file."""
    try:
        with open(ALERTS_FILE, "w", encoding="utf-8") as f:
            json.dump(alerts, f, ensure_ascii=False, indent=2)
        return True
    except:
        return False

def add_alert(symbol, target_price, condition, asset_type=None, initial_price=None, action_type="STRATEJİ"):
    """Add a new price alert/strategy strictly to Supabase."""
    user_id = get_user_id()
    if not user_id:
        return False, "Strateji eklemek için giriş yapmalısınız."
        
    alert_id = int(datetime.now().timestamp() * 1000)
    alert_data = {
        "id": alert_id,
        "user_id": user_id,
        "symbol": symbol.upper(),
        "target_price": float(target_price),
        "initial_price": float(initial_price) if initial_price is not None else None,
        "condition": condition, # "Fiyat Üstünde" or "Fiyat Altında"
        "type": asset_type,
        "action_type": action_type, # "ALIM" or "SATIŞ"
        "created_at": datetime.now().isoformat(),
        "triggered": False
    }
    
    try:
        db = get_db()
        db.table("alerts").insert(alert_data).execute()
        return True, "Strateji başarıyla eklendi."
    except Exception as e:
        print(f"Error adding alert: {e}")
        return False, f"Hata: {str(e)}"



def delete_alert(alert_id):
    """Delete an alert strictly from Supabase."""
    user_id = get_user_id()
    if not user_id:
        return False
        
    try:
        db = get_db()
        db.table("alerts").delete().eq("id", alert_id).eq("user_id", user_id).execute()
        return True
    except Exception as e:
        print(f"Error deleting alert: {e}")
        return False

def archive_alert(alert_id):
    """Archive an alert (set triggered=True) strictly in Supabase."""
    user_id = get_user_id()
    if not user_id: return False
    try:
        db = get_db()
        db.table("alerts").update({"triggered": True}).eq("id", alert_id).eq("user_id", user_id).execute()
        return True
    except Exception as e:
        print(f"Error archiving alert: {e}")
        return False

def check_alerts():
    """Check all active alerts against current prices and update Supabase."""
    user_id = get_user_id()
    alerts = load_alerts()
    # Manual archive requested: "triggered" means Archived. "is_hit" means reached target.
    active_alerts = [a for a in alerts if not a.get("triggered", False)]
    
    if not active_alerts:
        return []

    # Pre-fetch prices
    fetch_list = [{"symbol": a["symbol"], "type": a.get("type")} for a in active_alerts]
    fetch_all_prices_parallel(fetch_list)
    
    newly_hit_alerts = []
    
    for alert in active_alerts:
        data = get_current_data(alert["symbol"], alert.get("type"))
        if data:
            price = data["price"]
            condition = alert["condition"]
            target = alert["target_price"]
            already_hit = alert.get("is_hit", False)
            
            should_trigger = False
            if condition == "Fiyat Üstünde" and price >= target:
                should_trigger = True
            elif condition == "Fiyat Altında" and price <= target:
                should_trigger = True
            
            if should_trigger and not already_hit:
                alert["is_hit"] = True
                alert["triggered"] = True   # Auto-archive
                alert["triggered_at"] = datetime.now().isoformat()
                alert["trigger_price"] = price
                newly_hit_alerts.append(alert)
                
                # Update in DB
                try:
                    if user_id:
                        supabase.table("alerts").update({
                            "is_hit": True, 
                            "triggered": True,
                            "triggered_at": alert["triggered_at"], 
                            "trigger_price": price
                        }).eq("id", alert["id"]).eq("user_id", user_id).execute()
                except:
                    pass
    
    if newly_hit_alerts:
        try:
            full_list = load_alerts()
            for t in newly_hit_alerts:
                for a in full_list:
                    if str(a.get("id")) == str(t.get("id")):
                        a["is_hit"] = True
                        a["triggered"] = True
                        a["triggered_at"] = t["triggered_at"]
                        a["trigger_price"] = t["trigger_price"]
            save_alerts_local(full_list)
        except:
            pass
        
    return newly_hit_alerts

# ==================== WATCHLIST FUNCTIONS ====================

def get_watchlist():
    """Retrieve the user's watchlist from Supabase user_settings."""
    try:
        val = get_user_setting("user_watchlist")
        if val:
            if isinstance(val, str):
                try:
                    return json.loads(val)
                except:
                    return []
            return val
        return []
    except Exception as e:
        print(f"Error getting watchlist: {e}")
        return []

def add_to_watchlist(symbol, asset_type):
    """Add a symbol to the user's watchlist with initial price tracking."""
    try:
        current_list = get_watchlist()
        # Check for duplicates
        if any(item['symbol'] == symbol for item in current_list):
            return False, "Bu varlık zaten izleme listenizde."
        
        # Fetch current price for initial reference
        init_price = 0
        try:
            d = get_current_data(symbol, asset_type)
            if d:
                init_price = d.get("price", 0)
        except:
            pass
            
        current_list.append({
            "symbol": symbol,
            "type": asset_type,
            "added_at": datetime.now().isoformat(),
            "initial_price": init_price
        })
        
        # Save back
        val_to_save = json.dumps(current_list, ensure_ascii=False)
        success, msg = save_user_setting("user_watchlist", val_to_save)
        return success, msg
    except Exception as e:
        return False, str(e)

def remove_from_watchlist(symbol):
    """Remove a symbol from the user's watchlist."""
    try:
        current_list = get_watchlist()
        new_list = [item for item in current_list if item['symbol'] != symbol]
        
        if len(new_list) == len(current_list):
            return False, "Varlık bulunamadı."
            
        val_to_save = json.dumps(new_list, ensure_ascii=False)
        success, msg = save_user_setting("user_watchlist", val_to_save)
        return success, msg
    except Exception as e:
        return False, str(e)




