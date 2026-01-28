import borsapy
try:
    t = borsapy.tcmb.TCMB()
    print("borsapy.tcmb.TCMB dir:", [m for m in dir(t) if not m.startswith("_")])
except Exception as e:
    print(f"Error: {e}")
