import borsapy
try:
    t = borsapy.tcmb.TCMB()
    r = t.rates()
    print(r.columns.tolist())
    print(r.head())
except Exception as e:
    print(f"Error: {e}")
