import borsapy

print("Testing borsapy.Fund...")
try:
    # Testing with a common fund code like 'TTE' (İş Portföy BIST Teknoloji Ağırlıklı Hisse Senedi Fonu)
    fund = borsapy.Fund("TTE")
    print(f"Fund Info for TTE: {fund.info}")
except Exception as e:
    print(f"Error: {e}")
