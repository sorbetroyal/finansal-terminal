import borsapy
import pandas as pd
from datetime import datetime, timedelta

def test_hist():
    print("Testing history for TTE (TEFAS)...")
    try:
        fund = borsapy.Fund("TTE")
        df = fund.history(period="1mo")
        print(f"DF Head:\n{df.head() if not df.empty else 'EMPTY'}")
        print(f"DF Shape: {df.shape}")
    except Exception as e:
        print(f"Error: {e}")

    print("\nTesting YF for USDTRY=X...")
    import yfinance as yf
    try:
        df = yf.download("USDTRY=X", period="1mo", progress=False)
        print(f"USD Head:\n{df.head() if not df.empty else 'EMPTY'}")
        print(f"USD Shape: {df.shape}")
    except Exception as e:
        print(f"Error: {e}")

test_hist()
