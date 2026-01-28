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

# Load environment variables
load_dotenv()

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==================== MARKET DATA FUNCTIONS ====================

# Global cache for prices to speed up app
PRICE_CACHE = {}

@st.cache_data(ttl=60)  # Cache for 1 minute
def get_current_data(symbol, asset_type=None):
    """Fetch current price and daily change for a symbol with basic caching."""
    # 1. Standardization (MUST BE FIRST for cache consistency)
    a_type = str(asset_type).lower() if asset_type else ""
    s_upper = str(symbol).upper()
    
    # Standardize symbol based on type
    std_symbol = symbol
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
    
    try:
        # 3. Special Handling/Fetch
        if any(x in a_type for x in ["tefas", "fon", "bes", "oks"]):
            try:
                fund = borsapy.Fund(symbol)
                info = fund.info
                price = info.get('price', 0)
                daily_ret = info.get('daily_return', 0)
                prev_close = price / (1 + (daily_ret / 100)) if daily_ret else price
                return {"price": price, "prev_close": prev_close, "change_pct": daily_ret}
            except:
                return None
        
        if s_upper == "ALTIN":
            ons = get_current_data("GC=F", "ticker")
            usd = get_current_data("USDTRY=X", "döviz")
            if ons and usd:
                p = (ons["price"] / 31.1035) * usd["price"]
                prev = (ons["prev_close"] / 31.1035) * usd["prev_close"]
                return {"price": p, "prev_close": prev, "change_pct": ((p/prev)-1)*100 if prev else 0}
            return None

        if s_upper == "GÜMÜŞ":
            ons = get_current_data("SI=F", "ticker")
            usd = get_current_data("USDTRY=X", "döviz")
            if ons and usd:
                p = (ons["price"] / 31.1035) * usd["price"]
                prev = (ons["prev_close"] / 31.1035) * usd["prev_close"]
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
    
    # Separation: yfinance vs borsapy vs special
    yf_tickers = []
    for sym, t in unique_symbols:
        if any(x in t for x in ["tefas", "fon", "bes", "oks"]):
            continue # Handled by remaining/get_current_data
        if sym.upper() in ["ALTIN", "GÜMÜŞ"]:
            continue # Handled by remaining/get_current_data
    # Separation & Standardization (Consistency is KEY)
    yf_tickers = []
    unique_standardized = []
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
            if any(x in t for x in ["tefas", "fon", "bes", "oks"]) or s_up in ["ALTIN", "GÜMÜŞ"]:
                pass # Handled by remaining
            else:
                yf_tickers.append(cache_key)
    
    # 1. Bulk download for yfinance
    if yf_tickers:
        sym_list = list(set([x[0] for x in yf_tickers]))
        try:
            data = yf.download(sym_list, period="5d", interval="1d", group_by='ticker', progress=False)
            if not data.empty:
                for std_s, t in yf_tickers:
                    try:
                        ticker_data = data[std_s] if len(sym_list) > 1 else data
                        if not ticker_data.empty:
                            closes = ticker_data['Close'].dropna()
                            if len(closes) >= 1:
                                price = round(float(closes.iloc[-1]), 4)
                                prev_close = round(float(closes.iloc[-2]), 4) if len(closes) >= 2 else price
                                PRICE_CACHE[(std_s, t)] = {
                                    "price": price, "prev_close": prev_close, 
                                    "change_pct": ((price/prev_close)-1)*100 if prev_close else 0
                                }
                    except: continue
        except: pass
        
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
            
        if symbol.upper() == "ALTIN":
            gold_ons = get_history("GC=F", period=period)
            usd_try = get_history("USDTRY=X", period=period)
            if not gold_ons.empty and not usd_try.empty:
                df = gold_ons[["Close"]].join(usd_try[["Close"]], lsuffix='_ons', rsuffix='_usd', how='inner')
                df["Close"] = (df["Close_ons"] / 31.1035) * df["Close_usd"]
                return df
        
        ticker = yf.Ticker(symbol)
        return ticker.history(period=period)
    except: return pd.DataFrame()

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
        is_usd = any(x in t for x in ["abd", "kripto"]) or ("emtia" in t and s.upper() not in ["ALTIN", "GÜMÜŞ"])
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
            raw_usd_hist = bulk_data["USDTRY=X"]["Close"] if len(yf_tickers) > 1 else bulk_data["Close"]
        except: pass
    
    # 3. Process each holding
    val_series_dict = {}
    cost_series_dict = {}
    
    for h in holdings:
        s = h["symbol"]; t = h.get("type", "").lower()
        p_date = pd.to_datetime(h["purchase_date"]).tz_localize(None).normalize()
        is_usd = any(x in t for x in ["abd", "kripto"]) or ("emtia" in t and s.upper() not in ["ALTIN", "GÜMÜŞ"])
        
        # Get current data for fallback and today
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
                if s_up == "USD": std_s = "USDTRY=X"; s = std_s
                elif s_up in ["EUR", "EYR"]: std_s = "EURTRY=X"; s = std_s
                elif s_up == "GBP": std_s = "GBPTRY=X"; s = std_s

            if not bulk_data.empty:
                try:
                    asset_df = bulk_data[std_s] if len(yf_tickers) > 1 else bulk_data
                    if not asset_df.empty: prices = asset_df["Close"]
                except: pass
        
        # Robust construction: if prices empty, use current price as a flat line
        if prices.empty:
            # Create a basic index from existing bulk_data or a range
            idx = bulk_data.index if not bulk_data.empty else pd.date_range(end=today, periods=30)
            prices = pd.Series(cur_price, index=idx)
        
        # Append today's data to prices to ensure most recent is included
        if today not in prices.index:
            prices = pd.concat([prices, pd.Series({today: cur_price})])
            prices = prices[~prices.index.duplicated(keep='last')].sort_index()

        # Values & Costs
        v = prices * h["amount"]
        c = pd.Series(h["cost"] * h["amount"], index=prices.index)
        
        if is_usd:
            # Reindex USD rates to match prices index
            r = raw_usd_hist.reindex(prices.index).ffill().fillna(usd_now)
            if today in prices.index and today not in raw_usd_hist.index:
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

def get_ticker_news(symbol):
    """Fetch news for a specific ticker."""
    try:
        ticker = yf.Ticker(symbol)
        return ticker.news[:5]
    except:
        return []

def get_market_news():
    """Fetch general market news."""
    try:
        ticker = yf.Ticker("TRY=X")
        return ticker.news[:8]
    except:
        return []

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
            if any(x in t for x in ["abd", "kripto"]) or ("emtia" in t and h["symbol"].upper() not in ["ALTIN", "GÜMÜŞ"]):
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
        
        # Determine if this is a USD asset
        is_usd = any(x in t for x in ["abd", "kripto"]) or ("emtia" in t and symbol.upper() not in ["ALTIN", "GÜMÜŞ"])
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

# ==================== SUPABASE PORTFOLIO FUNCTIONS ====================

def load_portfolio():
    """Load all portfolios and holdings from Supabase."""
    try:
        # Get all portfolios
        portfolios_response = supabase.table("portfolios").select("*").execute()
        portfolios = portfolios_response.data
        
        # Get all holdings
        holdings_response = supabase.table("holdings").select("*").execute()
        holdings = holdings_response.data
        
        # Structure data
        result = {
            "portfolios": {},
            "selected_for_total": []
        }
        
        # Build portfolio structure
        for portfolio in portfolios:
            portfolio_id = portfolio["id"]
            portfolio_name = portfolio["name"]
            
            # Get holdings for this portfolio
            portfolio_holdings = [
                {
                    "symbol": h["symbol"],
                    "type": h["type"],
                    "amount": float(h["amount"]),
                    "cost": float(h["cost"]),
                    "purchase_date": h["purchase_date"],
                    "p": portfolio_name  # Add portfolio name for aggregation
                }
                for h in holdings if h["portfolio_id"] == portfolio_id
            ]
            
            result["portfolios"][portfolio_name] = {
                "id": portfolio_id,
                "holdings": portfolio_holdings,
                "history": []  # History can be added later if needed
            }
            result["selected_for_total"].append(portfolio_name)
        
        # If no portfolios exist, create a default one
        if not result["portfolios"]:
            create_portfolio("Genel")
            return load_portfolio()
        
        return result
        
    except Exception as e:
        print(f"Error loading portfolios: {e}")
        return {
            "portfolios": {"Genel": {"holdings": [], "history": []}},
            "selected_for_total": ["Genel"]
        }

def save_all_portfolios(data):
    """Deprecated: Data is automatically saved to Supabase."""
    pass

def create_portfolio(name):
    """Create a new portfolio in Supabase."""
    try:
        response = supabase.table("portfolios").insert({"name": name}).execute()
        return True
    except Exception as e:
        print(f"Error creating portfolio: {e}")
        return False

def delete_portfolio(name):
    """Delete a portfolio from Supabase."""
    try:
        # Get portfolio ID
        response = supabase.table("portfolios").select("id").eq("name", name).execute()
        if response.data:
            portfolio_id = response.data[0]["id"]
            # Delete portfolio (holdings will be deleted automatically due to CASCADE)
            supabase.table("portfolios").delete().eq("id", portfolio_id).execute()
            return True
        return False
    except Exception as e:
        print(f"Error deleting portfolio: {e}")
        return False

def add_asset(portfolio_name, symbol, amount, cost, asset_type=None, purchase_date=None):
    """Add an asset to a portfolio in Supabase."""
    try:
        # Get portfolio ID
        response = supabase.table("portfolios").select("id").eq("name", portfolio_name).execute()
        if not response.data:
            return False
        
        portfolio_id = response.data[0]["id"]
        
        # Use today's date if not provided
        if purchase_date is None:
            purchase_date = datetime.now().strftime("%Y-%m-%d")
        
        # Check if this exact holding exists (same symbol, portfolio, and date)
        existing = supabase.table("holdings").select("*").eq("portfolio_id", portfolio_id).eq("symbol", symbol).eq("purchase_date", purchase_date).execute()
        
        if existing.data:
            # Update existing holding
            holding = existing.data[0]
            total_units = float(holding["amount"]) + amount
            avg_cost = ((float(holding["amount"]) * float(holding["cost"])) + (amount * cost)) / total_units
            
            supabase.table("holdings").update({
                "amount": total_units,
                "cost": round(avg_cost, 4)
            }).eq("id", holding["id"]).execute()
        else:
            # Insert new holding
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
    """Hard delete an asset record from a portfolio in Supabase."""
    try:
        # Get portfolio ID
        response = supabase.table("portfolios").select("id").eq("name", portfolio_name).execute()
        if not response.data:
            return False
        
        portfolio_id = response.data[0]["id"]
        
        # Build query
        query = supabase.table("holdings").delete().eq("portfolio_id", portfolio_id).eq("symbol", symbol)
        
        if purchase_date:
            query = query.eq("purchase_date", purchase_date)
            
        query.execute()
        return True
    except Exception as e:
        print(f"Error deleting asset: {e}")
        return False

def remove_asset(portfolio_name, symbol, amount, price, purchase_date=None):
    """Remove (sell) an asset from a portfolio in Supabase."""
    try:
        # Get portfolio ID
        response = supabase.table("portfolios").select("id").eq("name", portfolio_name).execute()
        if not response.data:
            return False
        
        portfolio_id = response.data[0]["id"]
        
        # Get holdings for this symbol
        query = supabase.table("holdings").select("*").eq("portfolio_id", portfolio_id).eq("symbol", symbol)
        
        if purchase_date:
            query = query.eq("purchase_date", purchase_date)
        
        holdings_response = query.execute()
        
        if not holdings_response.data:
            return False
        
        # Remove from the first matching holding
        holding = holdings_response.data[0]
        current_amount = float(holding["amount"])
        
        if current_amount >= amount:
            new_amount = current_amount - amount
            
            if new_amount == 0:
                # Delete the holding
                supabase.table("holdings").delete().eq("id", holding["id"]).execute()
            else:
                # Update the amount
                supabase.table("holdings").update({"amount": new_amount}).eq("id", holding["id"]).execute()
            
            return True
        else:
            return False  # Not enough units
            
    except Exception as e:
        print(f"Error removing asset: {e}")
        return False

def get_all_holdings():
    """Get all holdings across all portfolios with portfolio names."""
    try:
        # Get all holdings with portfolio info
        response = supabase.table("holdings").select("*, portfolios(name)").execute()
        
        holdings = []
        for h in response.data:
            holdings.append({
                "symbol": h["symbol"],
                "type": h["type"],
                "amount": float(h["amount"]),
                "cost": float(h["cost"]),
                "purchase_date": h["purchase_date"],
                "p": h["portfolios"]["name"]  # Portfolio name
            })
        
        return holdings
        
    except Exception as e:
        print(f"Error getting all holdings: {e}")
        return []

# ==================== SELECTED PORTFOLIOS FUNCTIONS ====================

import json

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "settings.json")

def load_selected_portfolios():
    """Load selected portfolios from settings file."""
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                settings = json.load(f)
                return settings.get("selected_portfolios", None)
        return None
    except Exception as e:
        print(f"Error loading selected portfolios: {e}")
        return None

def save_selected_portfolios(selected_list):
    """Save selected portfolios to settings file."""
    try:
        settings = {}
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                settings = json.load(f)
        
        settings["selected_portfolios"] = selected_list
        
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Error saving selected portfolios: {e}")
        return False
