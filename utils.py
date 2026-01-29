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
                fund = borsapy.Fund(std_symbol)
                info = fund.info
                price = info.get('price', 0)
                daily_ret = info.get('daily_return', 0)
                prev_close = price / (1 + (daily_ret / 100)) if daily_ret else price
                return {"price": price, "prev_close": prev_close, "change_pct": daily_ret}
            except:
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

def get_current_data(symbol, asset_type=None):
    """Fetch current price with global cache priority, then falling back to cached single fetch."""
    # 1. Standardization (MUST BE FIRST for cache consistency)
    a_type = str(asset_type).lower() if asset_type else ""
    s_upper = str(symbol).upper()
    
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
            
            # Gold Spot Calculation (for Emtia or variants)
            gold_ons = get_history("GC=F", period=period)
            usd_try = get_history("USDTRY=X", period=period)
            if not gold_ons.empty and not usd_try.empty:
                df = gold_ons[["Close"]].join(usd_try[["Close"]], lsuffix='_ons', rsuffix='_usd', how='inner')
                gram_gold = (df["Close_ons"] / 31.1035) * df["Close_usd"]
                
                multiplier = 1.0
                if "ÇEYREK" in s_up: multiplier = 1.6065
                elif "YARIM" in s_up: multiplier = 3.2130
                elif "TAM" in s_up: multiplier = 6.4260
                elif "ATA" in s_up: multiplier = 6.6150
                # Note: ALTIN.S1 is handled by borsapy above, if fails we don't fallback to spot gram because price is different
                
                df["Close"] = gram_gold * multiplier
                return df
        
        ticker = yf.Ticker(symbol)
        return ticker.history(period=period)
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

def check_alerts():
    """Check all active alerts against current prices and update Supabase."""
    user_id = get_user_id()
    alerts = load_alerts()
    active_alerts = [a for a in alerts if not a.get("triggered", False)]
    
    if not active_alerts:
        return []

    # Pre-fetch prices
    fetch_list = [{"symbol": a["symbol"], "type": a.get("type")} for a in active_alerts]
    fetch_all_prices_parallel(fetch_list)
    
    triggered_alerts = []
    
    for alert in active_alerts:
        data = get_current_data(alert["symbol"], alert.get("type"))
        if data:
            price = data["price"]
            condition = alert["condition"]
            target = alert["target_price"]
            
            is_triggered = False
            if condition == "Fiyat Üstünde" and price >= target:
                is_triggered = True
            elif condition == "Fiyat Altında" and price <= target:
                is_triggered = True
            
            if is_triggered:
                alert["triggered"] = True
                alert["triggered_at"] = datetime.now().isoformat()
                alert["trigger_price"] = price
                triggered_alerts.append(alert)
                
                # Update in DB
                try:
                    if user_id:
                        supabase.table("alerts").update({
                            "triggered": True, 
                            "triggered_at": alert["triggered_at"], 
                            "trigger_price": price
                        }).eq("id", alert["id"]).eq("user_id", user_id).execute()
                    else:
                        raise Exception("No user_id")
                except:
                    # Fallback update in local alerts.json if needed
                    pass
    
    if triggered_alerts:
        # Final local sync
        try:
            full_list = load_alerts()
            for t in triggered_alerts:
                for a in full_list:
                    if str(a.get("id")) == str(t.get("id")):
                        a["triggered"] = True
                        a["triggered_at"] = t["triggered_at"]
                        a["trigger_price"] = t["trigger_price"]
            save_alerts_local(full_list)
        except:
            pass
        
    return triggered_alerts




