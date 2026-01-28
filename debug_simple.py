from utils import get_all_holdings, get_current_data
from datetime import datetime

holdings = get_all_holdings()

print("=== VARLIK BAZINDA GETIRI ===")
print()

total_cost_tl = 0
total_current_tl = 0

# Get USD rate
usd_data = get_current_data("USDTRY=X", "döviz")
usd_rate = usd_data["price"] if usd_data else 35.0
print(f"USD/TRY Kuru: {usd_rate:.2f}")
print()

for h in holdings:
    symbol = h['symbol']
    amount = h['amount']
    cost = h['cost']
    t = h.get('type', '').lower()
    
    d = get_current_data(symbol, h.get('type'))
    current_price = d['price'] if d else cost
    
    # Determine if USD asset
    is_usd = any(x in t for x in ['abd', 'kripto']) or ('emtia' in t and symbol.upper() not in ['ALTIN', 'GUMUS'])
    
    cost_total = cost * amount
    current_total = current_price * amount
    
    # Convert to TL for total
    if is_usd:
        cost_tl = cost_total * usd_rate
        current_tl = current_total * usd_rate
        currency = "USD"
    else:
        cost_tl = cost_total
        current_tl = current_total
        currency = "TL"
    
    total_cost_tl += cost_tl
    total_current_tl += current_tl
    
    # Individual return
    ret = ((current_price / cost) - 1) * 100 if cost > 0 else 0
    
    print(f"{symbol} ({currency}):")
    print(f"  Maliyet: {cost:.2f} x {amount} = {cost_total:.2f} {currency} ({cost_tl:.2f} TL)")
    print(f"  Guncel:  {current_price:.2f} x {amount} = {current_total:.2f} {currency} ({current_tl:.2f} TL)")
    print(f"  Getiri:  %{ret:.2f}")
    print()

print("=" * 50)
print(f"TOPLAM MALIYET (TL): {total_cost_tl:,.2f}")
print(f"TOPLAM DEGER (TL):   {total_current_tl:,.2f}")
print(f"BASIT GETIRI:        %{((total_current_tl / total_cost_tl) - 1) * 100:.2f}")
