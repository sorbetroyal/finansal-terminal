from utils import get_all_holdings, get_current_data
import pandas as pd

holdings = get_all_holdings()
print(f"Total holdings found: {len(holdings)}")

total_tl = 0
for h in holdings:
    d = get_current_data(h['symbol'], h.get('type'))
    price = d['price'] if d else 0
    val = price * h['amount']
    
    # Simple conversion logic
    t = str(h.get('type', '')).lower()
    is_usd = any(x in t for x in ["abd", "kripto"]) or ("emtia" in t and h["symbol"].upper() not in ["ALTIN", "GÜMÜŞ"])
    
    if is_usd:
        usd = get_current_data("USDTRY=X", "döviz")
        rate = usd['price'] if usd else 34.0
        val_tl = val * rate
    else:
        val_tl = val
        
    print(f"Asset: {h['symbol']}, Amount: {h['amount']}, Price: {price}, Val TL: {val_tl:,.0f} ({h['p']})")
    total_tl += val_tl

print(f"\nFinal Calculated Total TL: {total_tl:,.0f}")
