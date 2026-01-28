import borsapy
try:
    print("Testing borsapy.tcmb.inflation()...")
    inf = borsapy.tcmb.inflation()
    print("Type:", type(inf))
    print("Data:")
    print(inf)
except Exception as e:
    print(f"Error: {e}")
