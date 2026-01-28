from utils import get_all_holdings, get_current_data
from datetime import datetime

holdings = get_all_holdings()
print("=== PORTFÖY VERİLERİ ===")
print()

cash_flows = []
dates = []
total_cost = 0
total_current = 0

for h in holdings:
    cost = h['cost'] * h['amount']
    total_cost += cost
    
    d = get_current_data(h['symbol'], h.get('type'))
    current_val = d['price'] * h['amount'] if d else cost
    total_current += current_val
    
    print(f"Varlık: {h['symbol']}")
    print(f"  Alış Tarihi: {h['purchase_date']}")
    print(f"  Adet: {h['amount']}")
    print(f"  Maliyet: {h['cost']:.4f} (Toplam: {cost:.2f})")
    if d:
        print(f"  Güncel: {d['price']:.4f} (Değer: {current_val:.2f})")
    else:
        print(f"  Güncel: N/A (Değer: {current_val:.2f})")
    print()
    
    cash_flows.append(-cost)
    dates.append(h['purchase_date'])

# Bugünkü değer
cash_flows.append(total_current)
dates.append(datetime.now().strftime('%Y-%m-%d'))

print("=== NAKİT AKIŞLARI (XIRR için) ===")
for cf, dt in zip(cash_flows, dates):
    sign = "+" if cf > 0 else ""
    print(f"  {dt}: {sign}{cf:,.2f} TL")

print()
print(f"Toplam Yatırım: {total_cost:,.2f} TL")
print(f"Güncel Değer: {total_current:,.2f} TL")
print(f"Basit Getiri: %{((total_current/total_cost)-1)*100:.1f}")

# XIRR Hesaplama
print()
print("=== XIRR HESAPLAMA ===")
from datetime import datetime as dt_class

# Tarihleri datetime'a çevir
date_objs = []
for d in dates:
    if isinstance(d, str):
        date_objs.append(datetime.strptime(d, "%Y-%m-%d"))
    else:
        date_objs.append(d)

# İlk tarihten itibaren yıl hesapla
first_date = min(date_objs)
years = [(d - first_date).days / 365.0 for d in date_objs]

print("Tarih -> Yıl dönüşümü:")
for d, y in zip(dates, years):
    print(f"  {d}: {y:.4f} yıl")

print()
print("XIRR Denklemi:")
print("NPV(r) = ", end="")
for i, (cf, y) in enumerate(zip(cash_flows, years)):
    if i > 0:
        print(" + ", end="")
    print(f"({cf:.0f}/(1+r)^{y:.3f})", end="")
print(" = 0")

# XIRR'ı hesapla
from utils import calculate_portfolio_xirr
xirr = calculate_portfolio_xirr(holdings)
print()
print(f"Çözüm: r = XIRR = %{xirr:.1f}")
